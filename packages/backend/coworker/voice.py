"""Text-to-speech and voice cloning (ElevenLabs).

Without ``ELEVENLABS_API_KEY`` the web app falls back to the browser's
built-in speech synthesis, so calls still work end to end.
"""
from __future__ import annotations

import os
from typing import Any

import requests

API = "https://api.elevenlabs.io/v1"
TIMEOUT = 60


class VoiceError(Exception):
    pass


def is_configured() -> bool:
    return bool(os.environ.get("ELEVENLABS_API_KEY"))


def _headers() -> dict[str, str]:
    return {"xi-api-key": os.environ.get("ELEVENLABS_API_KEY", "")}


def default_voice_id() -> str:
    return os.environ.get("ELEVENLABS_DEFAULT_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")


def tts(text: str, voice_id: str | None = None) -> bytes:
    """MP3 audio for ``text`` using a low-latency model."""
    resp = requests.post(
        f"{API}/text-to-speech/{voice_id or default_voice_id()}",
        params={"output_format": "mp3_44100_128"},
        headers={**_headers(), "Content-Type": "application/json"},
        json={"text": text[:2500], "model_id": os.environ.get("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5")},
        timeout=TIMEOUT,
    )
    if resp.status_code != 200:
        raise VoiceError(f"Text-to-speech failed ({resp.status_code}): {resp.text[:200]}")
    return resp.content


def clone(name: str, files: list[tuple[str, bytes, str]], description: str = "") -> str:
    """Create an instant voice clone from samples. Returns the voice id."""
    resp = requests.post(
        f"{API}/voices/add",
        headers=_headers(),
        data={"name": name, "description": description},
        files=[("files", (fname, data, mime)) for fname, data, mime in files],
        timeout=TIMEOUT,
    )
    if resp.status_code != 200:
        raise VoiceError(f"Voice cloning failed ({resp.status_code}): {resp.text[:200]}")
    body: dict[str, Any] = resp.json()
    return str(body.get("voice_id", ""))


def delete(voice_id: str) -> bool:
    if not voice_id:
        return False
    resp = requests.delete(f"{API}/voices/{voice_id}", headers=_headers(), timeout=TIMEOUT)
    return resp.status_code in (200, 204, 404)
