"""Slack Events API: Slack pushes each new message so the coworker answers in seconds.

Configure the Slack app with Event Subscriptions on, Request URL
``<BACKEND_URL>/api/coworker/slack/events``, and these events subscribed
*on behalf of users*: ``message.im``, ``message.mpim``, ``message.channels``,
``message.groups``. Set ``SLACK_SIGNING_SECRET`` from the app's Basic
Information page. Without it this endpoint rejects everything and the
worker's one-minute poll still picks messages up.

With ``SLACK_BOT_ENABLED=1`` the same endpoint also receives the bot's
``app_mention`` and ``message.im`` events (see ``coworker/slackbot.py``), and
``/slack/interactive`` handles its Approve / Skip buttons.
"""
from __future__ import annotations

import json
import threading
from collections.abc import Callable
from typing import Any

import requests
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


def _soon(name: str, work: Callable[[], Any]) -> None:
    """Run ``work`` off the request (Slack wants a 2xx within 3 seconds), inline in tests."""
    app = current_app._get_current_object()  # type: ignore[attr-defined]

    def target() -> None:
        with app.app_context():
            try:
                work()
            except Exception as exc:  # a failed reply must not take the endpoint down
                app.logger.exception("Slack bot %s failed: %s", name, exc)

    if app.config.get("TESTING") and not app.config.get("COWORKER_SYNC_THREADS"):
        target()
    else:
        threading.Thread(target=target, name=f"coworker-{name}", daemon=True).start()


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
    from coworker import slackbot

    routed = slackbot.route(s, payload.get("team_id", ""), event) if slackbot.enabled() else None
    if routed:
        bot_owner, bot_token = routed
        _soon(f"slackbot-{bot_owner}", lambda: slackbot.handle(store(), bot_owner, bot_token, event))
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


@coworker_bp.post("/slack/interactive")
def slack_interactive() -> Any:
    """Approve / Skip buttons on the bot's messages. Signed like events; form-encoded ``payload``."""
    from coworker import slackbot

    body = request.get_data(cache=True)
    if not slack.verify_signature(body, request.headers.get("X-Slack-Request-Timestamp", ""),
                                  request.headers.get("X-Slack-Signature", "")):
        return error("bad signature", 401, "unauthorized")
    try:
        payload = json.loads(request.form.get("payload", "{}"))
    except ValueError:
        return error("bad payload")
    response_url = str(payload.get("response_url") or "")

    def work() -> None:
        text = slackbot.interact(store(), payload)
        if text and response_url.startswith("https://hooks.slack.com/"):
            requests.post(response_url, json={"replace_original": True, "text": text}, timeout=10)

    _soon("slack-button", work)
    return "", 200
