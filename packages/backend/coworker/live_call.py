"""Turn-taking for live meeting-bot calls.

The meeting bot streams transcript segments to our webhook. Answering each
segment as it lands makes the coworker talk over people who pause mid-thought,
answer "mm-hm", and keep talking when interrupted. Instead:

* **Backchannels** ("mm-hm", "yeah", "right") never start a turn.
* **End of turn**: segments are buffered in ``cw_turns``; the coworker
  answers once the other side has been quiet for ``COWORKER_TURN_SILENCE``
  seconds, with everything they said in that turn. The buffer lives in the
  database, so it works across server processes; the claim is an atomic
  ``UPDATE``, so one turn gets one reply.
* **Barge-in**: if they start talking while the coworker is speaking, the
  bot's audio is stopped and their words become the next turn.
* **Latency masking**: if the reply takes longer than ``FILLER_AFTER``
  seconds, the coworker says a short "Good question." first.
* Replies use ``llm.call_model`` (a fast model) and are kept short.

Per-turn timings land in the meeting's metrics (``turn_ms``) so p50/p95 can
be measured on real calls.
"""
from __future__ import annotations

import base64
import logging
import os
import re
import threading
import time
from typing import Any

from coworker.store import Store, iso

log = logging.getLogger("coworker.live_call")

FILLER_AFTER = 1.2
WORDS_PER_SECOND = 2.6  # spoken pace, to know roughly when the bot stops talking
BACKCHANNEL_RE = re.compile(
    r"^(?:(?:mm+[- ]?hm+|uh[- ]?huh|hmm+|yeah|yep|yup|yes|right|okay|ok|sure|got it|i see|cool|great|nice|wow|"
    r"ah+|oh+|uh+|um+|alright|true|exactly|makes sense|totally)[\s,.!]*){1,3}$",
    re.IGNORECASE,
)
_audio_cache: dict[tuple[str, str], bytes] = {}
_cache_lock = threading.Lock()


def silence_seconds() -> float:
    try:
        return max(0.0, float(os.environ.get("COWORKER_TURN_SILENCE", "0.8")))
    except ValueError:
        return 0.8


def is_backchannel(text: str) -> bool:
    return bool(BACKCHANNEL_RE.match((text or "").strip()))


def _speaking_until(meeting: dict[str, Any]) -> float:
    return float((meeting.get("metrics") or {}).get("speaking_until") or 0)


def _set_metric(store: Store, user_id: int, meeting_id: int, **values: Any) -> None:
    meeting = store.get("cw_meetings", meeting_id, user_id) or {}
    store.update("cw_meetings", meeting_id, user_id, {"metrics": {**(meeting.get("metrics") or {}), **values}})


def on_segment(store: Store, user_id: int, meeting_id: int, text: str) -> int | None:
    """Record what the other side just said. Returns the turn row id, or None if ignored."""
    text = (text or "").strip()
    meeting = store.get("cw_meetings", meeting_id, user_id)
    if not text or not meeting or meeting["status"] != "active" or is_backchannel(text):
        return None
    if _speaking_until(meeting) > time.time() and meeting.get("bot_id"):
        from coworker.connectors import recall
        from coworker.connectors.base import ConnectorError

        try:
            recall.stop_audio(meeting["bot_id"])
        except ConnectorError as exc:
            log.info("couldn't stop bot audio: %s", exc)
        metrics = meeting.get("metrics") or {}
        _set_metric(store, user_id, meeting_id, speaking_until=0, barge_ins=int(metrics.get("barge_ins", 0)) + 1)
    return store.insert("cw_turns", {"user_id": user_id, "meeting_id": meeting_id, "text": text, "created_at": iso()})


def claim(store: Store, user_id: int, meeting_id: int, turn_id: int) -> str:
    """Take every waiting segment if ``turn_id`` is still the latest; '' if a newer one will answer."""
    latest = store.one("SELECT MAX(id) AS id FROM cw_turns WHERE meeting_id = %s AND user_id = %s AND status = 'new'",
                       (meeting_id, user_id))
    if not latest or int(latest.get("id") or 0) != turn_id:
        return ""
    taken = store.execute("UPDATE cw_turns SET status = 'taken', claimed_by = %s WHERE meeting_id = %s AND user_id = %s "
                          "AND status = 'new' AND id <= %s", (turn_id, meeting_id, user_id, turn_id))
    if not taken:
        return ""  # another process took it
    rows = store.query("SELECT text FROM cw_turns WHERE meeting_id = %s AND claimed_by = %s ORDER BY id", (meeting_id, turn_id))
    return " ".join(r["text"] for r in rows).strip()


def _audio(text: str, voice_id: str | None) -> bytes:
    from coworker import voice

    key = (voice_id or "", text)
    with _cache_lock:
        cached = _audio_cache.get(key)
    if cached is not None:
        return cached
    audio = voice.tts(text, voice_id)
    if len(text) < 40:  # fillers repeat; full replies don't
        with _cache_lock:
            _audio_cache[key] = audio
    return audio


def _say(store: Store, user_id: int, meeting: dict[str, Any], text: str) -> None:
    from coworker import voice
    from coworker.connectors import recall

    if not meeting.get("bot_id") or not text:
        return
    if voice.is_configured():
        voice_id = ((store.get_coworker(user_id) or {}).get("settings") or {}).get("voice_id")
        recall.speak(meeting["bot_id"], base64.b64encode(_audio(text, voice_id)).decode())
        _set_metric(store, user_id, meeting["id"], speaking_until=time.time() + len(text.split()) / WORDS_PER_SECOND)
    else:
        recall.send_chat(meeting["bot_id"], text)


def take_turn(store: Store, user_id: int, meeting_id: int, turn_id: int, wait: float | None = None) -> dict[str, Any] | None:
    """After the quiet window, answer everything said in this turn (unless a newer segment arrived)."""
    from coworker import meetings
    from coworker.connectors import recall
    from coworker.connectors.base import ConnectorError
    from coworker.voice import VoiceError

    time.sleep(silence_seconds() if wait is None else wait)
    text = claim(store, user_id, meeting_id, turn_id)
    if not text:
        return None
    started = time.monotonic()
    meeting = store.get("cw_meetings", meeting_id, user_id) or {}
    done = threading.Event()

    def filler() -> None:
        if not done.wait(FILLER_AFTER):
            try:
                _say(store, user_id, meeting, "Good question." if text.rstrip().endswith("?") else "Got it.")
            except (ConnectorError, VoiceError):
                pass

    threading.Thread(target=filler, name=f"call-filler-{meeting_id}", daemon=True).start()
    try:
        result = meetings.respond(store, user_id, meeting_id, text)
    finally:
        done.set()
    m = result["meeting"]
    try:
        _say(store, user_id, m, result["reply"])
        if result["ended"] and m.get("bot_id"):
            recall.leave(m["bot_id"])
    except (ConnectorError, VoiceError) as exc:
        log.warning("couldn't speak on call %s: %s", meeting_id, exc)
    elapsed = int((time.monotonic() - started) * 1000)
    metrics = (store.get("cw_meetings", meeting_id, user_id) or {}).get("metrics") or {}
    _set_metric(store, user_id, meeting_id, turn_ms=[*(metrics.get("turn_ms") or []), elapsed][-200:])
    return {**result, "turn_ms": elapsed}


def latency_summary(metrics: dict[str, Any]) -> dict[str, Any]:
    """p50/p95 of reply time (turn claimed to reply audio sent), in ms."""
    values = sorted(int(v) for v in metrics.get("turn_ms") or [])
    if not values:
        return {"turns": 0}

    def pct(p: float) -> int:
        return values[min(len(values) - 1, int(round(p * (len(values) - 1))))]

    return {"turns": len(values), "p50_ms": pct(0.5), "p95_ms": pct(0.95), "barge_ins": int(metrics.get("barge_ins", 0))}
