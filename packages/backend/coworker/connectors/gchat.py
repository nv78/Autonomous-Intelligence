"""Google Chat app (HTTP endpoint).

In Google Cloud, enable the Google Chat API and configure the app with:
- connection: HTTP endpoint URL ``<BACKEND_URL>/api/coworker/gchat/events``;
- authentication audience: the project number.

Set ``GOOGLE_CHAT_AUDIENCE`` to that project number.

Google signs each request with a token from ``chat@system.gserviceaccount.com``, verified
here. The reply is the HTTP response itself. If a turn takes longer than ``SYNC_SECONDS``, the
user is told the answer is waiting in their Ourogen chat.
"""
from __future__ import annotations

import concurrent.futures
import os
from typing import Any

from coworker import chatbots
from coworker.store import Store

CHAT_ISSUER = "chat@system.gserviceaccount.com"
CHAT_CERTS = "https://www.googleapis.com/service_accounts/v1/metadata/x509/chat@system.gserviceaccount.com"
SYNC_SECONDS = 25
_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="gchat")


class GChatError(Exception):
    pass


def is_configured() -> bool:
    return bool(os.environ.get("GOOGLE_CHAT_AUDIENCE"))


def verify(auth_header: str) -> dict[str, Any]:
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    if not auth_header.startswith("Bearer "):
        raise GChatError("missing bearer token")
    try:
        claims: dict[str, Any] = id_token.verify_token(auth_header.removeprefix("Bearer "), google_requests.Request(),
                                                       audience=os.environ.get("GOOGLE_CHAT_AUDIENCE"), certs_url=CHAT_CERTS)
    except Exception as exc:
        raise GChatError(f"invalid token: {exc.__class__.__name__}") from exc
    if claims.get("iss") != CHAT_ISSUER:
        raise GChatError("wrong issuer")
    return claims


def _message(text: str, thread: str = "", actions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    msg: dict[str, Any] = {"text": text}
    if thread:
        msg["thread"] = {"name": thread}
    if actions:
        msg["cardsV2"] = [{"cardId": f"action-{a['id']}", "card": {
            "header": {"title": a["title"][:200]},
            "sections": [{"widgets": [
                {"textParagraph": {"text": str((a.get("payload") or {}).get("body") or (a.get("payload") or {}).get("text") or "")[:1500]}},
                {"buttonList": {"buttons": [
                    {"text": "Approve", "onClick": {"action": {"function": "cw_approve", "parameters": [{"key": "id", "value": str(a["id"])}]}}},
                    {"text": "Skip", "onClick": {"action": {"function": "cw_reject", "parameters": [{"key": "id", "value": str(a["id"])}]}}},
                ]}},
            ]}]}} for a in actions]
    return msg


def _clicked(event: dict[str, Any]) -> tuple[str, int]:
    common = event.get("common") or {}
    action = event.get("action") or {}
    fn = common.get("invokedFunction") or action.get("actionMethodName") or ""
    params = common.get("parameters") or {p.get("key"): p.get("value") for p in action.get("parameters") or []}
    return fn, int(params.get("id") or 0)


def handle(store: Store, event: dict[str, Any]) -> dict[str, Any]:
    """The JSON response for one Google Chat event."""
    kind = event.get("type")
    user = event.get("user") or {}
    email = str(user.get("email") or "").lower()
    domain = email.split("@")[-1]
    owner = chatbots.owner_for_google(store, email)
    if owner is not None:
        dm = (event.get("space") or {}).get("type") in ("DM", "DIRECT_MESSAGE") or (event.get("space") or {}).get("singleUserBotDm")
        chatbots.remember(store, "gchat", user.get("name", email), owner, domain, email,
                          {"space": (event.get("space") or {}).get("name", "")} if dm else None)
    if kind == "ADDED_TO_SPACE":
        return {"text": "Hi! I'm an Ourogen AI coworker. @mention me with a question, or DM me to hand off work."}
    if kind == "CARD_CLICKED":
        fn, action_id = _clicked(event)
        if owner is None or not action_id or store.get("cw_actions", action_id, owner) is None:
            return {"text": "Only the person this coworker works for can approve this."}
        verb = "approve" if fn == "cw_approve" else "reject"
        return {"actionResponse": {"type": "UPDATE_MESSAGE"}, "text": chatbots.decide(store, owner, verb, action_id)}
    if kind != "MESSAGE":
        return {}
    message = event.get("message") or {}
    if not chatbots.claim(store, owner or 0, f"gchat:{message.get('name', '')}"):
        return {}
    thread = (message.get("thread") or {}).get("name", "")
    text = (message.get("argumentText") or message.get("text") or "").strip()
    if not text:
        return _message("Ask me something, or tell me what to do.", thread)
    if owner is not None:
        key = f"gchat:{(event.get('space') or {}).get('name', '')}:{thread}"
        future = _pool.submit(_in_app_context(chatbots.command), store, owner, "gchat", key, text)
        try:
            out = future.result(timeout=SYNC_SECONDS)
        except concurrent.futures.TimeoutError:
            return _message("This one is taking a moment. The answer will be in your Ourogen chat “💬 Google Chat”.", thread)
        return _message(out["text"], thread, out["actions"])
    candidates = chatbots.owners_in(store, "gchat", domain)
    if not candidates:
        return _message("I'm an Ourogen AI coworker, but I'm not linked to anyone at your company yet.", thread)
    target = int(candidates[0]["user_id"])
    out = chatbots.teammate(store, target, user.get("displayName") or email, text,
                            external=not domain or bool((event.get("space") or {}).get("externalUserAllowed")))
    if out["owner_note"]:
        from coworker import notify

        notify.deliver(store, target, "A teammate asked your coworker on Google Chat", out["owner_note"])
    return _message(out["text"], thread)


def _in_app_context(fn: Any) -> Any:
    """Run ``fn`` in a worker thread with the Flask app context of the caller (the store reads config)."""
    try:
        from flask import current_app

        app = current_app._get_current_object()  # type: ignore[attr-defined]
    except RuntimeError:
        return fn

    def wrapped(*args: Any) -> Any:
        with app.app_context():
            return fn(*args)

    return wrapped
