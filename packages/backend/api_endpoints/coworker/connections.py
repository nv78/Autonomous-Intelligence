"""Connect, sync, and disconnect Google, Microsoft 365 (Outlook), Slack, and HubSpot."""
from __future__ import annotations

import os
from typing import Any

from flask import current_app, jsonify, redirect, request
from itsdangerous import BadSignature, URLSafeTimedSerializer

from api_endpoints.coworker.common import coworker_bp, error, frontend_url, store, uid
from api_endpoints.coworker.core import refresh_knowledge
from coworker.connectors import google, hubspot, microsoft, slack
from coworker.connectors.base import ConnectorError, decrypt_token, encrypt_token
from middleware.auth import require_auth

STATE_MAX_AGE = 600


def _serializer() -> URLSafeTimedSerializer:
    secret = current_app.config.get("JWT_SECRET_KEY") or os.environ.get("JWT_SECRET_KEY", "dev")
    return URLSafeTimedSerializer(str(secret), salt="coworker-oauth")


def _state(user_id: int, provider: str, level: str = "read") -> str:
    return _serializer().dumps({"uid": user_id, "p": provider, "l": level})


def _read_state(value: str, provider: str) -> dict[str, Any] | None:
    try:
        data: dict[str, Any] = _serializer().loads(value, max_age=STATE_MAX_AGE)
    except BadSignature:
        return None
    return data if data.get("p") == provider else None


def _back(provider: str, ok: bool, message: str = "") -> Any:
    target = os.environ.get("COWORKER_CONNECT_RETURN_PATH", "/app/onboarding")
    qs = f"connected={provider}" if ok else f"connect_error={provider}&message={message[:120]}"
    return redirect(f"{frontend_url()}{target}?{qs}")


@coworker_bp.get("/connections")
@require_auth
def list_connections() -> tuple:
    from api_endpoints.coworker.core import _serialize_connection

    return jsonify({"connections": [_serialize_connection(c) for c in store().list_connections(uid())]}), 200


# -- Google -----------------------------------------------------------------

@coworker_bp.post("/connections/google/start")
@require_auth
def google_start() -> tuple:
    if not google.is_configured():
        return error("Google isn't configured on this server. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
                     501, "not_configured")
    level = (request.get_json(silent=True) or {}).get("level", "read")
    if level not in ("read", "act"):
        return error("level must be 'read' or 'act'")
    return jsonify({"url": google.auth_url(_state(uid(), "google", level), level)}), 200


@coworker_bp.get("/connections/google/callback")
def google_callback() -> Any:
    state = _read_state(request.args.get("state", ""), "google")
    if not state:
        return _back("google", False, "invalid or expired state")
    if request.args.get("error"):
        return _back("google", False, request.args["error"])
    try:
        token = google.exchange_code(request.args.get("code", ""))
    except ConnectorError as exc:
        return _back("google", False, str(exc))
    user_id = int(state["uid"])
    s = store()
    previous = decrypt_token((s.get_connection_row(user_id, "google") or {}).get("token_enc"))
    if not token.get("refresh_token") and previous.get("refresh_token"):
        token["refresh_token"] = previous["refresh_token"]
    email = google.fetch_account_email(token.get("access_token", ""))
    s.upsert_connection(user_id, "google", account_label=email, token_enc=encrypt_token(token),
                        scopes=token.get("scope", ""), status="connected", error="")
    coworker = s.get_coworker(user_id)
    if coworker and coworker["mode"] != "live":
        _switch_to_live(user_id)
    s.log(user_id, "connection", f"Connected Google ({email})", {"level": state.get("l")})
    return _back("google", True)


def _switch_to_live(user_id: int) -> None:
    """Leaving the demo: drop demo content so it never mixes with real data."""
    s = store()
    for table in ("cw_items", "cw_people", "cw_memory", "cw_actions", "cw_runs"):
        s.execute(f"DELETE FROM {table} WHERE user_id = %s", (user_id,))
    s.delete_connection(user_id, "demo")
    s.update_coworker(user_id, mode="live")


# -- Microsoft 365 (Outlook mail + calendar) ---------------------------------

@coworker_bp.post("/connections/microsoft/start")
@require_auth
def microsoft_start() -> tuple:
    if not microsoft.is_configured():
        return error("Outlook isn't configured on this server. Set MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET.",
                     501, "not_configured")
    level = (request.get_json(silent=True) or {}).get("level", "read")
    if level not in ("read", "act"):
        return error("level must be 'read' or 'act'")
    return jsonify({"url": microsoft.auth_url(_state(uid(), "microsoft", level), level)}), 200


@coworker_bp.get("/connections/microsoft/callback")
def microsoft_callback() -> Any:
    state = _read_state(request.args.get("state", ""), "microsoft")
    if not state:
        return _back("microsoft", False, "invalid or expired state")
    if request.args.get("error"):
        return _back("microsoft", False, request.args.get("error_description") or request.args["error"])
    try:
        token = microsoft.exchange_code(request.args.get("code", ""))
    except ConnectorError as exc:
        return _back("microsoft", False, str(exc))
    user_id = int(state["uid"])
    s = store()
    email = microsoft.fetch_account_email(token.get("access_token", ""))
    s.upsert_connection(user_id, "microsoft", account_label=email, token_enc=encrypt_token(token),
                        scopes=token.get("scope", ""), status="connected", error="")
    coworker = s.get_coworker(user_id)
    if coworker and coworker["mode"] != "live":
        _switch_to_live(user_id)
    s.log(user_id, "connection", f"Connected Outlook ({email})", {"level": state.get("l")})
    return _back("microsoft", True)


# -- Slack ------------------------------------------------------------------

@coworker_bp.post("/connections/slack/start")
@require_auth
def slack_start() -> tuple:
    if not slack.is_configured():
        return error("Slack OAuth isn't configured. Paste a user token instead, or set SLACK_CLIENT_ID and "
                     "SLACK_CLIENT_SECRET.", 501, "not_configured")
    return jsonify({"url": slack.auth_url(_state(uid(), "slack"))}), 200


@coworker_bp.get("/connections/slack/callback")
def slack_callback() -> Any:
    state = _read_state(request.args.get("state", ""), "slack")
    if not state:
        return _back("slack", False, "invalid or expired state")
    try:
        token = slack.exchange_code(request.args.get("code", ""))
    except ConnectorError as exc:
        return _back("slack", False, str(exc))
    _save_slack(int(state["uid"]), token)
    return _back("slack", True)


@coworker_bp.post("/connections/slack/token")
@require_auth
def slack_token() -> tuple:
    """Connect Slack by pasting a user OAuth token (xoxp-...)."""
    value = str((request.get_json(silent=True) or {}).get("token", "")).strip()
    if not value.startswith("xoxp-"):
        return error("Paste a Slack *user* token that starts with xoxp-")
    try:
        token = slack.verify_token(value)
    except ConnectorError as exc:
        return error(str(exc), 400, exc.code)
    _save_slack(uid(), token)
    return jsonify({"connected": True, "team": token.get("team", "")}), 200


def _save_slack(user_id: int, token: dict[str, Any]) -> None:
    s = store()
    s.upsert_connection(user_id, "slack", account_label=token.get("team", ""), token_enc=encrypt_token(token),
                        scopes=token.get("scope", ""), status="connected", error="")
    coworker = s.get_coworker(user_id)
    if coworker and coworker["mode"] != "live":
        _switch_to_live(user_id)
    s.log(user_id, "connection", f"Connected Slack ({token.get('team', '')})")


# -- Disconnect & sync ------------------------------------------------------

# -- HubSpot ----------------------------------------------------------------

def _save_hubspot(user_id: int, token: dict[str, Any]) -> None:
    s = store()
    s.upsert_connection(user_id, "hubspot", account_label=token.get("portal", "HubSpot"), token_enc=encrypt_token(token),
                        scopes=token.get("scope", ""), status="connected", error="")
    s.log(user_id, "connection", f"Connected HubSpot ({token.get('portal', '')})")


@coworker_bp.post("/connections/hubspot/start")
@require_auth
def hubspot_start() -> tuple:
    if not hubspot.is_configured():
        return error("HubSpot OAuth isn't configured. Paste a private app token instead, or set HUBSPOT_CLIENT_ID and "
                     "HUBSPOT_CLIENT_SECRET.", 501, "not_configured")
    return jsonify({"url": hubspot.auth_url(_state(uid(), "hubspot"))}), 200


@coworker_bp.get("/connections/hubspot/callback")
def hubspot_callback() -> Any:
    state = _read_state(request.args.get("state", ""), "hubspot")
    if not state:
        return _back("hubspot", False, "invalid or expired state")
    try:
        token = hubspot.exchange_code(request.args.get("code", ""))
    except ConnectorError as exc:
        return _back("hubspot", False, str(exc))
    _save_hubspot(int(state["uid"]), token)
    return _back("hubspot", True)


@coworker_bp.post("/connections/hubspot/token")
@require_auth
def hubspot_token() -> tuple:
    value = str((request.get_json(silent=True) or {}).get("token", "")).strip()
    if not value.startswith("pat-"):
        return error("Paste a HubSpot private app token (it starts with pat-)")
    if not store().get_coworker(uid()):
        return error("Set up your coworker first", 404, "not_found")
    try:
        token = hubspot.verify_private_token(value)
    except ConnectorError as exc:
        return error(str(exc), 400, "invalid_token")
    _save_hubspot(uid(), token)
    return jsonify({"connected": True, "portal": token["portal"]}), 200


@coworker_bp.delete("/connections/<provider>")
@require_auth
def disconnect(provider: str) -> tuple:
    user_id = uid()
    s = store()
    row = s.get_connection_row(user_id, provider)
    if not row:
        return error("Not connected", 404, "not_found")
    token = decrypt_token(row.get("token_enc"))
    if provider == "google":
        google.revoke(token)
        purged = sum(s.delete_items(user_id, p) for p in ("gmail", "gcal", "drive"))
    elif provider == "microsoft":
        microsoft.revoke(token)
        purged = sum(s.delete_items(user_id, p) for p in ("outlook", "outlook_cal"))
    elif provider == "slack":
        slack.revoke(token)
        purged = s.delete_items(user_id, "slack")
    elif provider == "hubspot":
        hubspot.revoke(token)
        purged = 0  # nothing synced from HubSpot; records stay in the user's CRM
    else:
        purged = s.delete_items(user_id)
    s.delete_connection(user_id, provider)
    refresh_knowledge(user_id)
    s.log(user_id, "connection", f"Disconnected {provider} and deleted {purged} synced items")
    return jsonify({"disconnected": True, "purged": purged}), 200


@coworker_bp.post("/sync")
@require_auth
def sync() -> tuple:
    """Queue a sync and return at once; poll ``GET /sync/status`` for progress."""
    from coworker import sync_jobs

    user_id = uid()
    s = store()
    coworker = s.get_coworker(user_id)
    if not coworker:
        return error("Set up your coworker first", 404, "not_found")
    if coworker.get("mode") != "live":
        knowledge = refresh_knowledge(user_id) if request.args.get("rebuild") else None
        return jsonify({"queued": False, **sync_jobs.status(s, user_id), "memory": (knowledge or {}).get("memory")}), 200
    job = sync_jobs.request(s, user_id, rebuild=bool(request.args.get("rebuild")))
    sync_jobs.start(s, job)
    return jsonify({"queued": True, **sync_jobs.status(s, user_id)}), 202


@coworker_bp.get("/sync/status")
@require_auth
def sync_status() -> tuple:
    from coworker import sync_jobs

    return jsonify(sync_jobs.status(store(), uid())), 200
