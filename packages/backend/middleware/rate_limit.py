"""Rate limiting shared across processes.

Uses Redis (``REDIS_URL``) with a fixed window per key, so limits hold
across gunicorn workers and containers. Falls back to an in-process
sliding window when Redis isn't configured or can't be reached, so a Redis
outage never takes public endpoints down.
"""
from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from typing import Any

log = logging.getLogger("rate_limit")

_redis_client: Any = None
_redis_failed_at = 0.0


def _redis() -> Any:
    """Shared client, or None. After a failure, retry at most once a minute."""
    global _redis_client, _redis_failed_at
    url = os.environ.get("RATE_LIMIT_REDIS_URL") or os.environ.get("REDIS_URL", "")
    if not url or os.environ.get("RATE_LIMIT_BACKEND", "redis") == "memory":
        return None
    if _redis_client is not None:
        return _redis_client
    if time.monotonic() - _redis_failed_at < 60 and _redis_failed_at:
        return None
    try:
        import redis

        client = redis.Redis.from_url(url, socket_timeout=0.5, socket_connect_timeout=0.5)
        client.ping()
        _redis_client = client
        return client
    except Exception as exc:
        _redis_failed_at = time.monotonic()
        log.warning("rate limiting falls back to in-process limits: %s", exc)
        return None


def reset_backend() -> None:
    global _redis_client, _redis_failed_at
    _redis_client = None
    _redis_failed_at = 0.0


class RateLimiter:
    def __init__(self, max_calls: int = 60, period: float = 60.0, name: str = "default") -> None:
        self._max_calls = max_calls
        self._period = period
        self._name = name
        self._calls: dict[str, list[float]] = defaultdict(list)

    def _memory_allowed(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - self._period
        self._calls[key] = [t for t in self._calls[key] if t > window_start]
        if len(self._calls[key]) >= self._max_calls:
            return False
        self._calls[key].append(now)
        return True

    def is_allowed(self, key: str) -> bool:
        global _redis_client, _redis_failed_at
        client = _redis()
        if client is None:
            return self._memory_allowed(key)
        window = int(time.time() // self._period)
        rkey = f"rl:{self._name}:{key}:{window}"
        try:
            pipe = client.pipeline()
            pipe.incr(rkey)
            pipe.expire(rkey, int(self._period) + 1)
            count = int(pipe.execute()[0])
            return count <= self._max_calls
        except Exception as exc:
            log.warning("redis rate limit failed, using in-process limits: %s", exc)
            _redis_client = None
            _redis_failed_at = time.monotonic()
            return self._memory_allowed(key)
