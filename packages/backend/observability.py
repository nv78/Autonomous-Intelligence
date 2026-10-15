"""Error tracking and operational alerts.

Set ``SENTRY_DSN`` to send backend and worker errors to Sentry (or any
Sentry-compatible service). Without it, everything here only logs.

``alert()`` reports things that aren't exceptions but need a person: an
approved action that failed to send, or a sync that errored. They go to
Sentry as warnings and, when ``ALERT_SLACK_WEBHOOK_URL`` is set, to Slack.
Alerts are throttled per key so a persistent failure doesn't flood.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

log = logging.getLogger("observability")

_initialised = False
_last_alert: dict[str, float] = {}
ALERT_COOLDOWN_SECONDS = 15 * 60


def init(component: str) -> bool:
    """Start Sentry once per process. Returns whether it's active."""
    global _initialised
    dsn = os.environ.get("SENTRY_DSN", "")
    if _initialised or not dsn:
        return _initialised
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
    except ImportError:  # pragma: no cover - dependency is in requirements.txt
        log.warning("SENTRY_DSN is set but sentry-sdk isn't installed")
        return False
    sentry_sdk.init(
        dsn=dsn,
        environment=os.environ.get("APP_ENV", "local"),
        release=os.environ.get("GIT_SHA") or None,
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0")),
        send_default_pii=False,  # never ship email bodies or tokens
        integrations=[FlaskIntegration()],
    )
    sentry_sdk.set_tag("component", component)
    _initialised = True
    return True


def capture(exc: BaseException, **context: Any) -> None:
    log.error("%s: %s", type(exc).__name__, exc, extra={"context": context})
    if not _initialised:
        return
    import sentry_sdk

    with sentry_sdk.new_scope() as scope:
        for k, v in context.items():
            scope.set_extra(k, v)
        sentry_sdk.capture_exception(exc)


def alert(key: str, message: str, **context: Any) -> bool:
    """Report an operational problem. Returns False when throttled."""
    now = time.monotonic()
    if now - _last_alert.get(key, -1e9) < ALERT_COOLDOWN_SECONDS:
        return False
    _last_alert[key] = now
    log.warning("alert %s: %s %s", key, message, context)
    if _initialised:
        import sentry_sdk

        with sentry_sdk.new_scope() as scope:
            for k, v in context.items():
                scope.set_extra(k, v)
            sentry_sdk.capture_message(message, level="warning")
    hook = os.environ.get("ALERT_SLACK_WEBHOOK_URL", "")
    if hook:
        try:
            import requests

            detail = ", ".join(f"{k}={v}" for k, v in context.items())
            requests.post(hook, json={"text": f":warning: {message}" + (f" ({detail})" if detail else "")}, timeout=5)
        except Exception as exc:  # alerts must never break the caller
            log.warning("slack alert failed: %s", exc)
    return True
