"""Live-call turn-taking: backchannels, end of turn, barge-in, filler, faster model, latency."""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from coworker import live_call, llm, meetings
from coworker.store import Store


@pytest.fixture
def s(tmp_path, monkeypatch):
    monkeypatch.setenv("COWORKER_OFFLINE", "1")
    store = Store(f"sqlite:///{tmp_path}/call.db")
    store.create_coworker(1, "Natan Vidra", "natan@anote.ai", mode="live")
    return store


@pytest.fixture
def meeting(s):
    m = meetings.start(s, 1, mode="bot", title="Northwind intro", prospect_name="Dana", meeting_url="https://zoom.us/j/1")
    s.update("cw_meetings", m["id"], 1, {"bot_id": "bot-1", "metrics": {**(m.get("metrics") or {}), "consent": "granted"}})
    return s.get("cw_meetings", m["id"], 1)


def test_backchannels_never_start_a_turn(s, meeting):
    for text in ("Mm-hm.", "yeah yeah", "Right, okay", "uh huh", "Makes sense!", "  "):
        assert live_call.is_backchannel(text) or not text.strip()
        assert live_call.on_segment(s, 1, meeting["id"], text) is None
    for text in ("Yeah, what does it cost?", "Okay so we have forty seats", "Right now we use spreadsheets"):
        assert not live_call.is_backchannel(text)


def test_one_reply_per_turn_with_everything_they_said(s, meeting):
    first = live_call.on_segment(s, 1, meeting["id"], "We have about forty people")
    second = live_call.on_segment(s, 1, meeting["id"], "and we need it by March. What does it cost?")
    assert first and second
    assert live_call.claim(s, 1, meeting["id"], first) == ""  # a newer segment will answer
    assert live_call.claim(s, 1, meeting["id"], second) == "We have about forty people and we need it by March. What does it cost?"
    assert live_call.claim(s, 1, meeting["id"], second) == ""  # already taken
    ended = s.get("cw_meetings", meeting["id"], 1)
    s.update("cw_meetings", meeting["id"], 1, {"status": "ended"})
    assert live_call.on_segment(s, 1, meeting["id"], "hello?") is None
    s.update("cw_meetings", meeting["id"], 1, {"status": ended["status"]})


def test_take_turn_speaks_records_latency_and_barge_in(s, meeting, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "el")
    turn = live_call.on_segment(s, 1, meeting["id"], "Is this a bot?")
    with patch("coworker.voice.tts", return_value=b"mp3") as tts, patch("coworker.connectors.recall.speak") as speak:
        result = live_call.take_turn(s, 1, meeting["id"], turn, wait=0)
    assert result and "AI" in result["reply"] and speak.call_count == 1
    m = s.get("cw_meetings", meeting["id"], 1)
    assert m["metrics"]["speaking_until"] > time.time() and len(m["metrics"]["turn_ms"]) == 1
    assert tts.call_count == 1

    with patch("coworker.connectors.recall.stop_audio") as stop:
        live_call.on_segment(s, 1, meeting["id"], "Sorry to interrupt, quick question")
    stop.assert_called_once_with("bot-1")
    m = s.get("cw_meetings", meeting["id"], 1)
    assert m["metrics"]["barge_ins"] == 1 and m["metrics"]["speaking_until"] == 0
    with patch("coworker.connectors.recall.stop_audio") as stop:
        live_call.on_segment(s, 1, meeting["id"], "and another thing")  # not speaking any more
    stop.assert_not_called()


def test_filler_covers_a_slow_reply(s, meeting, monkeypatch):
    monkeypatch.setattr(live_call, "FILLER_AFTER", 0.01)
    turn = live_call.on_segment(s, 1, meeting["id"], "How does pricing work?")
    real = meetings.respond

    def slow(*args, **kwargs):
        time.sleep(0.15)
        return real(*args, **kwargs)

    with patch("coworker.meetings.respond", side_effect=slow), patch("coworker.connectors.recall.send_chat") as chat:
        live_call.take_turn(s, 1, meeting["id"], turn, wait=0)
    said = [c.args[1] for c in chat.call_args_list]
    assert said[0] == "Good question." and len(said) == 2


def test_failures_dont_break_the_call(s, meeting, monkeypatch):
    from coworker.connectors.base import ConnectorError

    monkeypatch.setenv("ELEVENLABS_API_KEY", "el")
    s.update("cw_meetings", meeting["id"], 1, {"metrics": {"consent": "granted", "speaking_until": time.time() + 30}})
    with patch("coworker.connectors.recall.stop_audio", side_effect=ConnectorError("x")):
        turn = live_call.on_segment(s, 1, meeting["id"], "Can you hear me")
    with patch("coworker.voice.tts", return_value=b"mp3"), \
            patch("coworker.connectors.recall.speak", side_effect=ConnectorError("audio down")):
        assert live_call.take_turn(s, 1, meeting["id"], turn, wait=0) is not None
    assert live_call.take_turn(s, 1, meeting["id"], 99999, wait=0) is None


def test_latency_summary_and_meeting_summary(s, meeting):
    assert live_call.latency_summary({}) == {"turns": 0}
    summary = live_call.latency_summary({"turn_ms": [900, 1200, 700, 3000, 1100], "barge_ins": 2})
    assert summary == {"turns": 5, "p50_ms": 1100, "p95_ms": 3000, "barge_ins": 2}
    s.update("cw_meetings", meeting["id"], 1, {"metrics": {"consent": "granted", "turn_ms": [800, 1000]}})
    with patch("coworker.reports.post"):
        done = meetings.finish(s, 1, meeting["id"])
    assert meetings.summary_of(done)["latency"]["turns"] == 2


def test_call_model_is_the_fast_sibling(s, monkeypatch):
    monkeypatch.delenv("COWORKER_CALL_MODEL", raising=False)
    monkeypatch.delenv("COWORKER_MODEL", raising=False)
    with patch("coworker.store.get_store", return_value=s):
        assert llm.call_model(1) == "claude-haiku-5-5"
        s.update_coworker(1, settings={"model": "gpt-4o"})
        assert llm.call_model(1) == "gpt-4o-mini"
        s.update_coworker(1, settings={"model": "llama3.1"})
        assert llm.call_model(1) == "llama3.1"
        monkeypatch.setenv("COWORKER_CALL_MODEL", "claude-sonnet-5-5")
        assert llm.call_model(1) == "claude-sonnet-5-5"
        s.update_coworker(1, settings={"model": "gpt-4o", "call_model": "gpt-4o"})
        assert llm.call_model(1) == "gpt-4o"


def test_recall_transcription_mode(monkeypatch):
    from coworker.connectors import recall

    assert recall.transcript_provider() == {"recallai_streaming": {"mode": "prioritize_low_latency", "language_code": "en"}}
    monkeypatch.setenv("RECALL_TRANSCRIPT", "captions")
    assert recall.transcript_provider() == {"meeting_captions": {}}
    monkeypatch.setenv("COWORKER_TURN_SILENCE", "junk")
    assert live_call.silence_seconds() == 0.8
    monkeypatch.setenv("COWORKER_TURN_SILENCE", "1.5")
    assert live_call.silence_seconds() == 1.5
