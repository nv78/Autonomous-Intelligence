"""Microsoft Teams bot (Azure Bot Service / Bot Framework).

Register an Azure Bot with messaging endpoint ``<BACKEND_URL>/api/coworker/teams/messages``,
turn on the Teams channel, and set ``MICROSOFT_BOT_APP_ID`` / ``MICROSOFT_BOT_APP_PASSWORD``
(``MICROSOFT_BOT_TENANT`` for a single-tenant bot). Install the app in Teams from the manifest
``python -m coworker.connectors.teams manifest`` generates.

Every request carries a Bot Framework JWT, verified against Microsoft's published keys, with
the app id as audience. Replies go to the activity's ``serviceUrl`` with a token from the
bot's own credentials.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from typing import Any

import requests

from coworker import chatbots
from coworker.store import Store

OPENID_CONFIG = "https://login.botframework.com/v1/.well-known/openidconfiguration"
ISSUER = "https://api.botframework.com"
TIMEOUT = 15
_jwks: Any = None
_token: dict[str, Any] = {}


class TeamsError(Exception):
    pass


def is_configured() -> bool:
    return bool(os.environ.get("MICROSOFT_BOT_APP_ID") and os.environ.get("MICROSOFT_BOT_APP_PASSWORD"))


def _jwks_client() -> Any:
    global _jwks
    if _jwks is None:
        from jwt import PyJWKClient

        uri = requests.get(OPENID_CONFIG, timeout=TIMEOUT).json()["jwks_uri"]
        _jwks = PyJWKClient(uri, cache_keys=True)
    return _jwks


def verify(auth_header: str, service_url: str) -> dict[str, Any]:
    """Claims of a valid Bot Framework token for this bot; raises TeamsError otherwise."""
    import jwt

    if not auth_header.startswith("Bearer "):
        raise TeamsError("missing bearer token")
    token = auth_header.removeprefix("Bearer ")
    try:
        key = _jwks_client().get_signing_key_from_jwt(token).key
        claims: dict[str, Any] = jwt.decode(token, key, algorithms=["RS256"], audience=os.environ.get("MICROSOFT_BOT_APP_ID"),
                                            issuer=ISSUER, leeway=300)
    except Exception as exc:
        raise TeamsError(f"invalid token: {exc.__class__.__name__}") from exc
    if claims.get("serviceurl") and claims["serviceurl"].rstrip("/") != service_url.rstrip("/"):
        raise TeamsError("serviceUrl mismatch")
    return claims


def _bot_token() -> str:
    if _token.get("value") and _token.get("expires", 0) > time.time() + 60:
        return str(_token["value"])
    tenant = os.environ.get("MICROSOFT_BOT_TENANT") or "botframework.com"
    resp = requests.post(f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token", timeout=TIMEOUT, data={
        "grant_type": "client_credentials", "client_id": os.environ.get("MICROSOFT_BOT_APP_ID", ""),
        "client_secret": os.environ.get("MICROSOFT_BOT_APP_PASSWORD", ""), "scope": "https://api.botframework.com/.default"})
    if resp.status_code >= 300:
        raise TeamsError(f"bot token failed ({resp.status_code})")
    data = resp.json()
    _token.update(value=data["access_token"], expires=time.time() + int(data.get("expires_in", 3600)))
    return str(data["access_token"])


def _api(method: str, service_url: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    resp = requests.request(method, f"{service_url.rstrip('/')}/v3{path}", json=body, timeout=TIMEOUT,
                            headers={"Authorization": f"Bearer {_bot_token()}"})
    if resp.status_code >= 300:
        raise TeamsError(f"Bot Framework {method} {path} failed ({resp.status_code})")
    return dict(resp.json() or {}) if resp.content else {}


def member_email(activity: dict[str, Any]) -> str:
    """Teams doesn't put the sender's email on messages; ask the conversation's roster."""
    conv = (activity.get("conversation") or {}).get("id", "")
    user = (activity.get("from") or {}).get("id", "")
    member = _api("GET", activity["serviceUrl"], f"/conversations/{conv}/members/{user}")
    return str(member.get("email") or member.get("userPrincipalName") or "").lower()


def approval_card(action: dict[str, Any]) -> dict[str, Any]:
    payload = action.get("payload") or {}
    return {"contentType": "application/vnd.microsoft.card.adaptive", "content": {
        "type": "AdaptiveCard", "version": "1.4", "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "body": [{"type": "TextBlock", "text": action["title"], "weight": "Bolder", "wrap": True},
                 {"type": "TextBlock", "text": str(payload.get("body") or payload.get("text") or "")[:1500], "wrap": True}],
        "actions": [{"type": "Action.Submit", "title": "Approve", "data": {"cw": "approve", "id": action["id"]}},
                    {"type": "Action.Submit", "title": "Skip", "data": {"cw": "reject", "id": action["id"]}}]}}


def reply(activity: dict[str, Any], text: str, actions: list[dict[str, Any]] | None = None) -> None:
    conv = (activity.get("conversation") or {}).get("id", "")
    body: dict[str, Any] = {"type": "message", "text": text, "textFormat": "markdown", "replyToId": activity.get("id")}
    if actions:
        body["attachments"] = [approval_card(a) for a in actions]
    _api("POST", activity["serviceUrl"], f"/conversations/{conv}/activities/{activity.get('id', '')}", body)


def send(conversation: dict[str, Any], text: str) -> None:
    """A new message in a stored conversation (the owner's 1:1 chat with the bot)."""
    _api("POST", conversation["serviceUrl"], f"/conversations/{conversation['id']}/activities",
         {"type": "message", "text": text, "textFormat": "markdown"})


def _clean(text: str) -> str:
    return re.sub(r"<at>.*?</at>", "", text or "").strip()


def handle(store: Store, activity: dict[str, Any]) -> str:
    """Answer one Teams activity. Returns what happened (for logs and tests)."""
    if activity.get("type") != "message":
        return "ignored"
    conv = activity.get("conversation") or {}
    tenant = str(conv.get("tenantId") or (activity.get("channelData") or {}).get("tenant", {}).get("id") or "")
    sender = activity.get("from") or {}
    email = member_email(activity)
    owner = chatbots.owner_by_email(store, email)
    if owner is not None:
        personal = conv.get("conversationType") == "personal"
        chatbots.remember(store, "teams", sender.get("id", ""), owner, tenant, email,
                          {"serviceUrl": activity["serviceUrl"], "id": conv.get("id", "")} if personal else None)
    if not chatbots.claim(store, owner or 0, f"teams:{activity.get('id', '')}"):
        return "duplicate"
    value = activity.get("value") or {}
    if isinstance(value, dict) and value.get("cw") in ("approve", "reject"):
        if owner is None or (store.get("cw_actions", int(value.get("id") or 0), owner) is None):
            reply(activity, "Only the person this coworker works for can approve this.")
            return "refused button"
        reply(activity, chatbots.decide(store, owner, value["cw"], int(value["id"])))
        return "button"
    text = _clean(activity.get("text", ""))
    if not text:
        return "empty"
    if owner is not None:
        out = chatbots.command(store, owner, "teams", f"teams:{conv.get('id', '')}", text)
        reply(activity, out["text"], out["actions"])
        return "command"
    mentioned = {((e.get("mentioned") or {}).get("id")) for e in activity.get("entities") or [] if e.get("type") == "mention"}
    candidates = chatbots.owners_in(store, "teams", tenant)
    target = next((c for c in candidates if c["external_id"] in mentioned), candidates[0] if candidates else None)
    if target is None:
        reply(activity, "I'm an Ourogen AI coworker, but I'm not linked to anyone in this organization yet.")
        return "unlinked"
    asker = sender.get("name") or email or "A teammate"
    out = chatbots.teammate(store, int(target["user_id"]), asker, text)
    reply(activity, out["text"])
    if out["owner_note"]:
        try:
            if not target.get("conversation"):
                raise TeamsError("the owner hasn't messaged the bot directly yet")
            send(target["conversation"], out["owner_note"])
        except TeamsError:
            from coworker import notify

            notify.deliver(store, int(target["user_id"]), "A teammate asked your coworker on Teams", out["owner_note"])
    return "teammate"


def manifest(backend_url: str, app_id: str, name: str = "Ourogen") -> dict[str, Any]:
    """Teams app manifest. Zip it with color.png (192×192) and outline.png (32×32) and upload in Teams."""
    host = backend_url.split("://", 1)[-1].split("/")[0]
    return {
        "$schema": "https://developer.microsoft.com/en-us/json-schemas/teams/v1.17/MicrosoftTeams.schema.json",
        "manifestVersion": "1.17", "version": "1.0.0", "id": app_id,
        "developer": {"name": "Ourogen", "websiteUrl": "https://ourogen.ai", "privacyUrl": "https://ourogen.ai/privacy",
                      "termsOfUseUrl": "https://ourogen.ai/terms"},
        "name": {"short": name, "full": f"{name} AI coworker"},
        "description": {"short": "Your AI coworker in Teams.",
                        "full": "Ask your AI coworker questions or hand off work. Teammates can @mention it too."},
        "icons": {"color": "color.png", "outline": "outline.png"}, "accentColor": "#212121",
        "bots": [{"botId": app_id, "scopes": ["personal", "team", "groupChat"], "supportsFiles": False, "isNotificationOnly": False}],
        "permissions": ["identity", "messageTeamMembers"], "validDomains": [host],
    }


if __name__ == "__main__":  # pragma: no cover
    if len(sys.argv) > 1 and sys.argv[1] == "manifest":
        print(json.dumps(manifest(os.environ.get("BACKEND_URL", "https://chat.ourogen.ai"),
                                  os.environ.get("MICROSOFT_BOT_APP_ID", "<MICROSOFT_BOT_APP_ID>")), indent=2))
    else:
        raise SystemExit("usage: python -m coworker.connectors.teams manifest")
