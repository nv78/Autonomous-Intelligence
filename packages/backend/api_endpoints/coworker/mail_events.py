"""Push endpoints for real-time email (see ``coworker/mail_push.py``).

Both answer fast and do the work off the request: sync that mailbox, then
run the user's responsibilities, so a new lead gets a draft in seconds.
"""
from __future__ import annotations

import threading
from typing import Any

from flask import Response, current_app, jsonify, request

from api_endpoints.coworker import slack_events
from api_endpoints.coworker.common import coworker_bp, error, store
from coworker import mail_push
from middleware.rate_limit import RateLimiter

_ip_limiter = RateLimiter(max_calls=1200, period=60, name="mail-push-ip")
_running: set[tuple[int, str]] = set()
_running_lock = threading.Lock()


def refresh(user_id: int, provider: str) -> None:
    """Sync one mailbox and react, at most one pass per user and provider at a time."""
    app = current_app._get_current_object()  # type: ignore[attr-defined]
    key = (user_id, provider)
    with _running_lock:
        if key in _running:
            return
        _running.add(key)

    def target() -> None:
        try:
            with app.app_context():
                from coworker.connectors.base import Workspace

                s = store()
                Workspace(s, user_id).sync(providers=(provider,))
                slack_events.react(s, user_id)
        finally:
            with _running_lock:
                _running.discard(key)

    if app.config.get("TESTING") and not app.config.get("COWORKER_SYNC_THREADS"):
        target()
    else:
        threading.Thread(target=target, name=f"coworker-mail-{provider}-{user_id}", daemon=True).start()


def _limited() -> bool:
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()
    return not _ip_limiter.is_allowed(ip)


@coworker_bp.post("/google/push")
def gmail_push() -> Any:
    if _limited():
        return error("rate limited", 429, "rate_limited")
    if not mail_push.gmail_enabled():
        return error("Gmail push isn't configured", 404, "not_found")
    if not mail_push.verify_gmail(request.headers, request.args):
        return error("unauthorized", 401, "unauthorized")
    users = mail_push.users_for_gmail(store(), mail_push.parse_gmail(request.get_json(silent=True) or {}))
    for user_id in users:
        refresh(user_id, "google")
    return jsonify({"ok": True, "users": len(users)}), 200  # any 2xx acks the Pub/Sub message


@coworker_bp.post("/microsoft/notify")
def graph_notify() -> Any:
    token = request.args.get("validationToken")
    if token is not None:  # Graph checks the endpoint when a subscription is created
        return Response(token, status=200, mimetype="text/plain")
    if _limited():
        return error("rate limited", 429, "rate_limited")
    payload = request.get_json(silent=True) or {}
    users = mail_push.users_for_graph(store(), list(payload.get("value") or []))
    for user_id in users:
        refresh(user_id, "microsoft")
    return jsonify({"ok": True, "users": len(users)}), 202
