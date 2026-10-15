"""Live Slack connector, acting with a *user* token so the coworker can read
the user's DMs and channels and reply as their disclosed AI.

Two ways to connect:

* OAuth v2 (``SLACK_CLIENT_ID`` / ``SLACK_CLIENT_SECRET``). Slack requires
  an HTTPS redirect URL, so local testing usually goes through a tunnel.
* Paste a user token (``xoxp-...``) from a Slack app you installed to your
  own workspace. Simplest for a personal prototype.

New messages arrive two ways: the worker polls ``conversations.history``
every minute, and, when the Slack app subscribes to events on behalf of
users (``SLACK_SIGNING_SECRET`` set), Slack pushes each message to
``/api/coworker/slack/events`` so the coworker can answer in seconds.

Every message the coworker posts is prefixed with a visible marker so
teammates can tell it apart from the human.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

import requests

from coworker.connectors.base import ConnectorError, SendResult, decrypt_token
from coworker.store import Store, iso

API = "https://slack.com/api"
AUTH_URL = "https://slack.com/oauth/v2/authorize"
USER_SCOPES = [
    "channels:history", "groups:history", "im:history", "mpim:history",
    "channels:read", "groups:read", "im:read", "users:read", "users:read.email",
    "chat:write",
]
TIMEOUT = 20
AI_PREFIX = ":robot_face: _via Ourogen (AI coworker)_"


def is_configured() -> bool:
    return bool(os.environ.get("SLACK_CLIENT_ID") and os.environ.get("SLACK_CLIENT_SECRET"))


def redirect_uri() -> str:
    default = f"{os.environ.get('BACKEND_URL', 'http://localhost:5000').rstrip('/')}/api/coworker/connections/slack/callback"
    return os.environ.get("SLACK_REDIRECT_URI", default)


def auth_url(state: str) -> str:
    return f"{AUTH_URL}?{urlencode({'client_id': os.environ.get('SLACK_CLIENT_ID', ''), 'user_scope': ','.join(USER_SCOPES), 'redirect_uri': redirect_uri(), 'state': state})}"


def _call(method: str, token: str, http: str = "GET", **params: Any) -> dict[str, Any]:
    for attempt in range(3):
        if http == "GET":
            resp = requests.get(f"{API}/{method}", params=params, headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT)
        else:
            resp = requests.post(f"{API}/{method}", json=params, headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT)
        if resp.status_code == 429 and attempt < 2:
            time.sleep(min(int(resp.headers.get("Retry-After", "1")), 5))
            continue
        data: dict[str, Any] = resp.json() if resp.content else {}
        if not data.get("ok"):
            err = data.get("error", f"http_{resp.status_code}")
            code = "reauth_required" if err in ("invalid_auth", "token_revoked", "not_authed", "account_inactive") else "provider_error"
            raise ConnectorError(f"Slack {method} failed: {err}", code)
        return data
    raise ConnectorError(f"Slack {method} rate limited")  # pragma: no cover


def exchange_code(code: str) -> dict[str, Any]:
    resp = requests.post(f"{API}/oauth.v2.access", data={
        "client_id": os.environ.get("SLACK_CLIENT_ID", ""),
        "client_secret": os.environ.get("SLACK_CLIENT_SECRET", ""),
        "code": code, "redirect_uri": redirect_uri(),
    }, timeout=TIMEOUT)
    data = resp.json() if resp.content else {}
    if not data.get("ok"):
        raise ConnectorError(f"Slack OAuth failed: {data.get('error', 'unknown')}", "oauth_failed")
    user = data.get("authed_user") or {}
    return {
        "access_token": user.get("access_token", ""), "scope": user.get("scope", ""),
        "user_id": user.get("id", ""), "team": (data.get("team") or {}).get("name", ""),
        "team_id": (data.get("team") or {}).get("id", ""),
    }


def verify_token(token: str) -> dict[str, Any]:
    info = _call("auth.test", token)
    return {"access_token": token, "user_id": info.get("user_id", ""), "team": info.get("team", ""),
            "team_id": info.get("team_id", ""), "scope": ""}


def events_enabled() -> bool:
    return bool(os.environ.get("SLACK_SIGNING_SECRET"))


def verify_signature(body: bytes, timestamp: str, signature: str, now: float | None = None) -> bool:
    """Slack signs every event request with the app's signing secret (v0 HMAC-SHA256)."""
    secret = os.environ.get("SLACK_SIGNING_SECRET", "")
    if not secret or not timestamp or not signature:
        return False
    try:
        if abs((now or time.time()) - int(timestamp)) > 300:  # replayed or very late
            return False
    except ValueError:
        return False
    base = b"v0:" + timestamp.encode() + b":" + body
    expected = "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def message_item(me: str, cid: str, channel_name: str, is_dm: bool, shared: bool,
                 m: dict[str, Any], author: dict[str, str]) -> dict[str, Any]:
    text = m.get("text", "")
    return {
        "provider": "slack", "external_id": f"{cid}:{m['ts']}", "thread_id": f"slack-{channel_name}",
        "kind": "slack", "direction": "outbound" if m.get("user") == me else "inbound",
        "author_name": author["name"], "author_email": author["email"], "recipients": [],
        "body": text, "channel": channel_name,
        "occurred_at": iso(datetime.fromtimestamp(float(m["ts"]), UTC)),
        "meta": {"dm": is_dm, "mentions_owner": is_dm or f"<@{me}>" in text, "channel_id": cid, "ts": m["ts"],
                 "shared": shared},
    }


def revoke(token: dict[str, Any]) -> None:
    if token.get("access_token"):
        try:
            _call("auth.revoke", token["access_token"])
        except (ConnectorError, requests.RequestException):
            pass


class SlackConnector:
    provider = "slack"

    def __init__(self, store: Store, user_id: int, token: dict[str, Any], cursor: dict[str, Any]) -> None:
        self.store = store
        self.user_id = user_id
        self.token = token
        self.cursor = cursor
        self._users: dict[str, dict[str, str]] = {}

    @classmethod
    def from_row(cls, store: Store, row: dict[str, Any]) -> SlackConnector:
        cursor = row.get("sync_cursor") or {}
        if isinstance(cursor, str):
            try:
                cursor = json.loads(cursor)
            except ValueError:
                cursor = {}
        return cls(store, int(row["user_id"]), decrypt_token(row.get("token_enc")), cursor)

    @property
    def _tok(self) -> str:
        return str(self.token.get("access_token", ""))

    def _user(self, uid: str) -> dict[str, str]:
        if uid not in self._users:
            try:
                profile = _call("users.info", self._tok, user=uid).get("user", {})
                self._users[uid] = {
                    "name": profile.get("real_name") or profile.get("name", uid),
                    "email": ((profile.get("profile") or {}).get("email") or "").lower(),
                }
            except ConnectorError:
                self._users[uid] = {"name": uid, "email": ""}
        return self._users[uid]

    def sync(self, store: Store, user_id: int) -> int:
        me = self.token.get("user_id", "")
        convs = _call("conversations.list", self._tok, types="public_channel,private_channel,im",
                      exclude_archived="true", limit=200).get("channels", [])
        oldest_default = str(time.time() - 14 * 86400)
        count = 0
        for conv in convs[:60]:
            if not (conv.get("is_member") or conv.get("is_im")):
                continue
            cid = conv["id"]
            is_dm = bool(conv.get("is_im"))
            channel_name = f"dm-{self._user(conv.get('user', ''))['name'].split()[0].lower()}" if is_dm else conv.get("name", cid)
            oldest = self.cursor.get(cid, oldest_default)
            try:
                history = _call("conversations.history", self._tok, channel=cid, oldest=oldest, limit=100)
            except ConnectorError:
                continue
            newest = oldest
            shared = bool(conv.get("is_ext_shared") or conv.get("is_shared"))
            for m in history.get("messages", []):
                if m.get("subtype"):
                    continue
                item = message_item(me, cid, channel_name, is_dm, shared, m, self._user(m.get("user", "")))
                if store.add_item(user_id, item):
                    count += 1
                newest = max(newest, m["ts"])
            self.cursor[cid] = newest
        store.upsert_connection(user_id, "slack", sync_cursor=json.dumps(self.cursor))
        return count

    def ingest_event(self, store: Store, user_id: int, event: dict[str, Any]) -> int | None:
        """Store one pushed ``message`` event exactly as a sync would; None if skipped or seen."""
        if event.get("type") != "message" or event.get("subtype") or not event.get("ts") or not event.get("channel"):
            return None  # edits, deletes, joins, bot posts
        if AI_PREFIX in (event.get("text") or ""):
            return None  # our own replies, echoed back
        cid = event["channel"]
        is_dm = event.get("channel_type") == "im"
        shared = False
        if is_dm:
            other = event.get("user", "") if event.get("user") != self.token.get("user_id") else ""
            channel_name = self._dm_name(store, user_id, cid, other)
        else:
            try:
                info = _call("conversations.info", self._tok, channel=cid).get("channel", {})
            except ConnectorError:
                info = {}
            channel_name = info.get("name", cid)
            shared = bool(info.get("is_ext_shared") or info.get("is_shared"))
        item = message_item(self.token.get("user_id", ""), cid, channel_name, is_dm, shared, event,
                            self._user(event.get("user", "")))
        return store.add_item(user_id, item)

    def _dm_name(self, store: Store, user_id: int, cid: str, other: str) -> str:
        """Same name the poller gives this DM, so threads line up."""
        row = store.one("SELECT channel FROM cw_items WHERE user_id = %s AND provider = 'slack' AND meta LIKE %s "
                        "ORDER BY id DESC LIMIT 1", (user_id, f'%"channel_id": "{cid}"%'))
        if row and row.get("channel"):
            return str(row["channel"])
        if not other:
            try:
                other = _call("conversations.info", self._tok, channel=cid).get("channel", {}).get("user", "")
            except ConnectorError:
                other = ""
        return f"dm-{self._user(other)['name'].split()[0].lower()}" if other else f"dm-{cid.lower()}"

    def _channel_id(self, store: Store, user_id: int, channel: str) -> str:
        row = store.one(
            "SELECT meta FROM cw_items WHERE user_id = %s AND provider = 'slack' AND channel = %s ORDER BY id DESC LIMIT 1",
            (user_id, channel),
        )
        meta = (row or {}).get("meta") or {}
        return str(meta.get("channel_id") or channel)

    def post_message(self, store: Store, user_id: int, *, channel: str, text: str) -> SendResult:
        cid = self._channel_id(store, user_id, channel)
        data = _call("chat.postMessage", self._tok, http="POST", channel=cid, text=f"{AI_PREFIX}\n{text}")
        return SendResult(external_id=data.get("ts", ""), thread_id=f"slack-{channel}",
                          undo={"channel_id": data.get("channel", cid), "ts": data.get("ts", "")})

    def undo(self, store: Store, user_id: int, action_type: str, undo: dict[str, Any]) -> bool:
        if undo.get("ts") and undo.get("channel_id"):
            _call("chat.delete", self._tok, http="POST", channel=undo["channel_id"], ts=undo["ts"])
            return True
        return False
