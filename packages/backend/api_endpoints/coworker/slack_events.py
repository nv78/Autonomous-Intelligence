"""Slack Events API: Slack pushes each new message so the coworker answers in seconds.

Configure the Slack app with Event Subscriptions on, Request URL
``<BACKEND_URL>/api/coworker/slack/events``, and these events subscribed
*on behalf of users*: ``message.im``, ``message.mpim``, ``message.channels``,
``message.groups``. Set ``SLACK_SIGNING_SECRET`` from the app's Basic
Information page. Without it this endpoint rejects everything and the
worker's one-minute poll still picks messages up.
"""
from __future__ import annotations

import threading
from typing import Any

from flask import current_app, jsonify, request

from api_endpoints.coworker.common import coworker_bp, error, store
from coworker.connectors import slack
from coworker.connectors.base import decrypt_token
from coworker.store import Store
from middleware.rate_limit import RateLimiter

_ip_limiter = RateLimiter(max_calls=1200, period=60, name="slack-events-ip")
_running: set[int] = set()
_running_lock = threading.Lock()


def owners_for(s: Store, team_id: str, slack_user_ids: list[str]) -> list[int]:
    """Our users whose connected Slack identity is one of the event's authorized users."""
    wanted = {u for u in slack_user_ids if u}
    found: list[int] = []
    for row in s.query("SELECT user_id, token_enc FROM cw_connections WHERE provider = 'slack' "
                       "AND status IN ('connected', 'syncing')"):
        token = decrypt_token(row.get("token_enc"))
        if token.get("user_id") in wanted and (not team_id or not token.get("team_id") or token["team_id"] == team_id):
            found.append(int(row["user_id"]))
    return found


def _respond_soon(user_id: int) -> None:
    """Run this user's responsibilities off the request: Slack wants a 2xx within 3 seconds."""
    app = current_app._get_current_object()  # type: ignore[attr-defined]
    with _running_lock:
        if user_id in _running:
            return  # a pass is already running; it will see this message too
        _running.add(user_id)

    def target() -> None:
        try:
            with app.app_context():
                react(store(), user_id)
        finally:
            with _running_lock:
                _running.discard(user_id)

    if app.config.get("TESTING") and not app.config.get("COWORKER_SYNC_THREADS"):
        target()
    else:
        threading.Thread(target=target, name=f"coworker-slack-{user_id}", daemon=True).start()


def react(s: Store, user_id: int) -> list[str]:
    from coworker import governance, notify, responsibilities

    coworker = s.get_coworker(user_id) or {}
    if coworker.get("status") != "active" or governance.org_disabled(coworker.get("owner_email") or ""):
        return []  # paused or turned off: the regular tick handles governance
    results = responsibilities.run_all(s, user_id)
    notify.maybe_notify_approvals(s, user_id)
    return results


@coworker_bp.post("/slack/events")
def slack_events() -> Any:
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()
    if not _ip_limiter.is_allowed(ip):
        return error("rate limited", 429, "rate_limited")
    body = request.get_data(cache=True)
    if not slack.verify_signature(body, request.headers.get("X-Slack-Request-Timestamp", ""),
                                  request.headers.get("X-Slack-Signature", "")):
        return error("bad signature", 401, "unauthorized")
    payload = request.get_json(silent=True) or {}
    if payload.get("type") == "url_verification":
        return jsonify({"challenge": payload.get("challenge", "")}), 200
    if payload.get("type") != "event_callback":
        return jsonify({"ok": True}), 200
    event = payload.get("event") or {}
    authorized = [a.get("user_id", "") for a in payload.get("authorizations") or []]
    s = store()
    stored = 0
    from coworker.connectors.base import Workspace

    for user_id in owners_for(s, payload.get("team_id", ""), authorized):
        connector = Workspace(s, user_id)._live("slack")
        if connector is None:
            continue
        if connector.ingest_event(s, user_id, event):
            stored += 1
            _respond_soon(user_id)
    return jsonify({"ok": True, "stored": stored}), 200
