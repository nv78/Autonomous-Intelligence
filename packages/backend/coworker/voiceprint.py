"""Speaker check: does the consent recording sound like the voice samples?

Cloning requires that the person who recorded the consent statement is the
person in the samples. Otherwise anyone could upload someone else's talks
and record a consent themselves.

Two backends:

* ``local`` (default, no ML dependency): pitch plus spectral (MFCC)
  statistics. It's a coarse screen. It reliably catches a different
  speaker with a clearly different voice (e.g. a different gender or
  register), and returns ``inconclusive`` rather than guessing when the
  evidence is weak.
* ``resemblyzer`` (``VOICEPRINT_BACKEND=resemblyzer``, needs the
  ``resemblyzer`` package): a neural speaker embedding. Use it before
  general availability.

Results: ``match``, ``mismatch``, ``inconclusive``, or ``unavailable`` (no
decoder). Only ``match`` lets cloning proceed. An admin can override after
a manual review (``python -m coworker.admin approve-voice``).

Audio is decoded with ffmpeg (any format the browser records: webm/opus,
mp4/aac, wav, mp3, and the audio track of video files).
"""
from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any

import numpy as np

RATE = 16000
MIN_VOICED_SECONDS = 3.0


class DecodeError(Exception):
    pass


def available() -> bool:
    return shutil.which("ffmpeg") is not None


def decode(data: bytes) -> np.ndarray:
    """Any audio/video bytes to mono 16 kHz float32."""
    if not available():
        raise DecodeError("ffmpeg isn't installed")
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", "pipe:0", "-vn", "-f", "f32le", "-ac", "1", "-ar", str(RATE), "pipe:1"],
        input=data, capture_output=True, timeout=120, check=False,
    )
    if proc.returncode != 0 or not proc.stdout:
        raise DecodeError(proc.stderr.decode(errors="ignore")[:200] or "couldn't decode audio")
    return np.frombuffer(proc.stdout, dtype=np.float32).copy()


# -- local features ------------------------------------------------------------

def _frames(x: np.ndarray, size: int = 400, hop: int = 160) -> np.ndarray:
    if len(x) < size:
        x = np.pad(x, (0, size - len(x)))
    n = 1 + (len(x) - size) // hop
    idx = np.arange(size)[None, :] + hop * np.arange(n)[:, None]
    return x[idx]


def _mel_filters(n_fft: int = 512, n_mels: int = 40) -> np.ndarray:
    def hz_to_mel(f: np.ndarray | float) -> np.ndarray | float:
        return 2595 * np.log10(1 + np.asarray(f) / 700)

    mels = np.linspace(hz_to_mel(60), hz_to_mel(RATE / 2 - 200), n_mels + 2)
    hz = 700 * (10 ** (mels / 2595) - 1)
    bins = np.floor((n_fft + 1) * hz / RATE).astype(int)
    fb = np.zeros((n_mels, n_fft // 2 + 1))
    for m in range(1, n_mels + 1):
        lo, c, hi = bins[m - 1], bins[m], bins[m + 1]
        for k in range(lo, c):
            fb[m - 1, k] = (k - lo) / max(c - lo, 1)
        for k in range(c, hi):
            fb[m - 1, k] = (hi - k) / max(hi - c, 1)
    return fb


_FB = _mel_filters()
_DCT = np.cos(np.pi / 40 * (np.arange(40)[None, :] + 0.5) * np.arange(20)[:, None])


def _voiced(frames: np.ndarray) -> np.ndarray:
    energy = 10 * np.log10(np.mean(frames ** 2, axis=1) + 1e-10)
    return energy > max(np.percentile(energy, 30), energy.max() - 45)


def _pitch(frames: np.ndarray) -> float:
    """Median F0 over voiced frames by autocorrelation (60–400 Hz)."""
    lo, hi = RATE // 400, RATE // 60
    f0s = []
    for f in frames:
        f = f - f.mean()
        ac = np.correlate(f, f, mode="full")[len(f) - 1:]
        if ac[0] <= 0:
            continue
        seg = ac[lo:hi]
        lag = int(np.argmax(seg)) + lo
        if seg.max() / ac[0] > 0.3:
            f0s.append(RATE / lag)
    return float(np.median(f0s)) if f0s else 0.0


def features(x: np.ndarray) -> dict[str, Any]:
    x = np.append(x[0], x[1:] - 0.97 * x[:-1]) if len(x) > 1 else x
    frames = _frames(x)
    voiced = _voiced(frames)
    if voiced.sum() * 0.01 < MIN_VOICED_SECONDS:
        raise DecodeError(f"Need at least {MIN_VOICED_SECONDS:.0f} seconds of clear speech")
    v = frames[voiced] * np.hamming(frames.shape[1])
    power = np.abs(np.fft.rfft(v, 512)) ** 2
    mfcc = (_DCT @ np.log(power @ _FB.T + 1e-10).T).T[:, 1:]  # drop c0 (loudness)
    return {"mu": mfcc.mean(axis=0), "sd": mfcc.std(axis=0) + 1e-6, "f0": _pitch(v[:: max(1, len(v) // 300)]),
            "seconds": round(float(voiced.sum()) * 0.01, 1)}


def _compare_local(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    d = float(np.mean(np.abs(a["mu"] - b["mu"]) / (0.5 * (a["sd"] + b["sd"]))))
    ratio = (max(a["f0"], b["f0"]) / min(a["f0"], b["f0"])) if a["f0"] and b["f0"] else 1.0
    if ratio > 1.45 or d > 0.9:
        verdict = "mismatch"
    elif ratio < 1.25 and d < 0.55:
        verdict = "match"
    else:
        verdict = "inconclusive"
    return {"verdict": verdict, "distance": round(d, 3), "pitchRatio": round(ratio, 3),
            "pitchHz": [round(a["f0"]), round(b["f0"])]}


# -- neural backend ------------------------------------------------------------

def _compare_resemblyzer(xa: np.ndarray, xb: np.ndarray) -> dict[str, Any]:  # pragma: no cover - optional dependency
    from resemblyzer import VoiceEncoder, preprocess_wav

    enc = VoiceEncoder()
    ea, eb = enc.embed_utterance(preprocess_wav(xa, RATE)), enc.embed_utterance(preprocess_wav(xb, RATE))
    sim = float(np.dot(ea, eb) / (np.linalg.norm(ea) * np.linalg.norm(eb)))
    verdict = "match" if sim >= 0.75 else "mismatch" if sim < 0.6 else "inconclusive"
    return {"verdict": verdict, "similarity": round(sim, 3)}


def backend() -> str:
    return os.environ.get("VOICEPRINT_BACKEND", "local")


def compare(consent: bytes, sample: bytes) -> dict[str, Any]:
    """Compare two recordings. Never raises; decoding problems come back as
    ``unavailable`` or ``inconclusive`` with a reason."""
    try:
        xa, xb = decode(consent), decode(sample)
        if backend() == "resemblyzer":  # pragma: no cover - optional dependency
            return {**_compare_resemblyzer(xa, xb), "backend": "resemblyzer"}
        return {**_compare_local(features(xa), features(xb)), "backend": "local"}
    except DecodeError as exc:
        status = "unavailable" if not available() else "inconclusive"
        return {"verdict": status, "reason": str(exc), "backend": backend()}


def overall(results: list[dict[str, Any]]) -> str:
    """Every sample must match the consent recording."""
    verdicts = [r["verdict"] for r in results]
    if not verdicts:
        return "inconclusive"
    for v in ("mismatch", "unavailable", "inconclusive"):
        if v in verdicts:
            return v
    return "match"
