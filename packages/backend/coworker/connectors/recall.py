"""Meeting bot via Recall.ai: join Zoom / Google Meet / Teams.

The bot joins with the name "<Name>'s AI coworker (Ourogen)", posts an AI
and recording disclosure in the meeting chat, streams transcripts to our
webhook, and can speak replies (TTS audio) or post them in chat.

Request shapes follow Recall's v1 bot API. Verify them against Recall's
current docs before relying on this outside the pilot.
"""
from __future__ import annotations

import os
from typing import Any

import requests

from coworker.connectors.base import ConnectorError

TIMEOUT = 30

# Recall only accepts output_audio for bots created with automatic_audio_output,
# which needs a clip of its own. A 0.3s silent mp3 enables speaking without
# playing anything on join.
SILENT_MP3_B64 = (
    "SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjYwLjE2LjEwMAAAAAAAAAAAAAAA//MYxAAAAANIAAAAAExBTUUzLjEwMFVVVVVVVVVVVVVVVVVV//MYxBcAAANIAAAAAFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV//MYxC4AAANIAAAAAFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV//MYxEUAAANIAAAAAFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV//MYxFwAAANIAAAAAFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV//MYxHMAAANIAAAAAFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV//MYxIoAAANIAAAAAFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV//MYxKEAAANIAAAAAFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV//MYxLgAAANIAAAAAFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV//MYxM8AAANIAAAAAFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV//MYxOYAAANIAAAAAFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV"
)


def is_configured() -> bool:
    return bool(os.environ.get("RECALL_API_KEY"))


def _base() -> str:
    return os.environ.get("RECALL_API_BASE", "https://us-east-1.recall.ai/api/v1").rstrip("/")


def _headers() -> dict[str, str]:
    return {"Authorization": f"Token {os.environ.get('RECALL_API_KEY', '')}", "Content-Type": "application/json"}


def _call(method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    resp = requests.request(method, f"{_base()}{path}", headers=_headers(), json=body, timeout=TIMEOUT)
    if resp.status_code >= 400:
        raise ConnectorError(f"Recall {path} failed ({resp.status_code}): {resp.text[:200]}")
    data: dict[str, Any] = resp.json() if resp.content else {}
    return data


def transcript_provider() -> dict[str, Any]:
    """Recall's own streaming transcription in low-latency mode works on every platform with
    no host settings; ``RECALL_TRANSCRIPT=captions`` uses the platform's captions instead."""
    if os.environ.get("RECALL_TRANSCRIPT", "low_latency") == "captions":
        return {"meeting_captions": {}}
    return {"recallai_streaming": {"mode": "prioritize_low_latency", "language_code": "en"}}


def create_bot(meeting_url: str, bot_name: str, disclosure: str, webhook_url: str) -> str:
    body = {
        "meeting_url": meeting_url,
        "bot_name": bot_name[:100],
        "chat": {"on_bot_join": {"send_to": "everyone", "message": disclosure[:500]}},
        "automatic_audio_output": {"in_call_recording": {"data": {"kind": "mp3", "b64_data": SILENT_MP3_B64}}},
        "recording_config": {
            "transcript": {"provider": transcript_provider()},
            "realtime_endpoints": [{"type": "webhook", "url": webhook_url, "events": ["transcript.data"]}],
        },
    }
    return str(_call("POST", "/bot/", body).get("id", ""))


def leave(bot_id: str) -> None:
    _call("POST", f"/bot/{bot_id}/leave_call/")


def stop_audio(bot_id: str) -> None:
    """Stop whatever the bot is saying (barge-in)."""
    _call("DELETE", f"/bot/{bot_id}/output_audio/")


def send_chat(bot_id: str, message: str) -> None:
    _call("POST", f"/bot/{bot_id}/send_chat_message/", {"message": message[:4000]})


def speak(bot_id: str, mp3_b64: str) -> None:
    _call("POST", f"/bot/{bot_id}/output_audio/", {"kind": "mp3", "b64_data": mp3_b64})


def parse_transcript_event(payload: dict[str, Any]) -> tuple[str, str, bool] | None:
    """Return (speaker_name, text, is_bot) from a transcript.data webhook."""
    data = (payload.get("data") or {}).get("data") or {}
    words = data.get("words") or []
    text = " ".join(w.get("text", "") for w in words).strip()
    if not text:
        return None
    participant = data.get("participant") or {}
    name = str(participant.get("name") or "Participant")
    return name, text, "ourogen" in name.lower()
