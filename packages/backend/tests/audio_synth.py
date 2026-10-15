"""Synthetic speech for voice-match tests: a pulse train at a given pitch
through vowel formants, so two "speakers" differ the way real voices do."""
from __future__ import annotations

import io
import wave

import numpy as np
from scipy.signal import lfilter

VOWELS = {"a": (730, 1090, 2440), "i": (270, 2290, 3010), "u": (300, 870, 2240), "e": (530, 1840, 2480),
          "o": (570, 840, 2410)}


def voice(f0: float, scale: float, seed: int, seconds: float = 6.0, rate: int = 16000) -> bytes:
    """WAV bytes of a synthetic speaker (pitch ``f0``, vocal tract ``scale``)."""
    rng = np.random.default_rng(seed)
    out = []
    t = 0.0
    while t < seconds:
        v = str(rng.choice(list(VOWELS)))
        dur = rng.uniform(0.15, 0.4)
        n = int(dur * rate)
        f = f0 * (1 + 0.08 * np.sin(np.linspace(0, rng.uniform(1, 3), n))) * (1 + rng.normal(0, 0.01, n))
        phase = np.cumsum(f / rate)
        y = (np.diff(np.floor(phase), prepend=0) > 0).astype(float)
        for fm, bw in zip(VOWELS[v], (80, 90, 120)):
            r = np.exp(-np.pi * bw / rate)
            th = 2 * np.pi * fm * scale / rate
            y = lfilter([1 - r], [1, -2 * r * np.cos(th), r * r], y)
        out += [y * np.hanning(n), np.zeros(int(rate * rng.uniform(0.02, 0.08)))]
        t += dur
    x = np.concatenate(out)
    x = x / (np.abs(x).max() + 1e-9) * 0.6 + rng.normal(0, 0.003, len(x))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    return buf.getvalue()
