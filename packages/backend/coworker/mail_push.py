"""Real-time email: providers tell us about new mail instead of waiting for the poll.

* **Gmail** publishes to a Cloud Pub/Sub topic (``GMAIL_PUBSUB_TOPIC``) after
  ``users.watch``; a push subscription delivers to
  ``/api/coworker/google/push``. Requests are verified with the push
  subscription's OIDC token (``GMAIL_PUSH_AUDIENCE``) or, more simply, a
  shared ``?token=`` (``GMAIL_PUSH_TOKEN``).
* **Outlook** uses Microsoft Graph change notifications on the inbox,
  delivered to ``/api/coworker/microsoft/notify`` and checked against a
  per-user ``clientState``.

Watches and subscriptions are (re)created during the regular sync, so they
renew themselves; the worker's poll keeps running as the fallback.
"""
from __future__ import annotations

import base64
import hmac
import json
import logging
import os
import re
import secrets
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from coworker.store import Store, iso

log = logging.getLogger("coworker.mail_push")

GRAPH_LIFETIME = timedelta(days=3)  # Outlook message subscriptions may last up to ~7 days
RENEW_BEFORE = timedelta(days=1)
RETRY_AFTER = timedelta(hours=1)  # after a failed watch/subscription, keep polling and try again later


def _backing_off(connector: Any, key: str) -> bool:
    from coworker.store import parse_iso

    retry = parse_iso(connector.cursor.get(key))
    return bool(retry and retry > datetime.now(UTC))


def _back_off(connector: Any, key: str) -> None:
    connector.cursor[key] = iso(datetime.now(UTC) + RETRY_AFTER)


def _backend_url() -> str:
    return os.environ.get("BACKEND_URL", "").rstrip("/")


# -- Gmail -------------------------------------------------------------------

def gmail_enabled() -> bool:
    return bool(os.environ.get("GMAIL_PUBSUB_TOPIC")
                and (os.environ.get("GMAIL_PUSH_TOKEN") or os.environ.get("GMAIL_PUSH_AUDIENCE")))


def ensure_gmail_watch(connector: Any) -> None:
    """Start or renew ``users.watch`` (it lapses after 7 days). Never breaks a sync."""
    if not gmail_enabled():
        return
    expires_ms = int(connector.cursor.get("gmail_watch_expires") or 0)
    if expires_ms > (time.time() + RENEW_BEFORE.total_seconds()) * 1000 or _backing_off(connector, "gmail_watch_retry"):
        return
    from coworker.connectors.base import ConnectorError
    from coworker.connectors.google import GMAIL

    try:
        data = connector._request("POST", f"{GMAIL}/watch", json={
            "topicName": os.environ["GMAIL_PUBSUB_TOPIC"], "labelIds": ["INBOX"], "labelFilterBehavior": "INCLUDE",
        })
    except ConnectorError as exc:
        log.warning("gmail watch failed for user %s: %s", connector.user_id, exc)
        _back_off(connector, "gmail_watch_retry")
        return
    connector.cursor["gmail_watch_expires"] = int(data.get("expiration") or 0)


def verify_gmail(headers: Any, args: Any) -> bool:
    audience = os.environ.get("GMAIL_PUSH_AUDIENCE", "")
    if audience:
        auth = str(headers.get("Authorization", ""))
        if not auth.startswith("Bearer "):
            return False
        try:
            from google.auth.transport import requests as google_requests
            from google.oauth2 import id_token

            claims = id_token.verify_oauth2_token(auth[7:], google_requests.Request(), audience=audience)
        except Exception:
            return False
        # Any Google service account can mint a token for any audience, so the sender must be pinned.
        sender = os.environ.get("GMAIL_PUSH_SERVICE_ACCOUNT", "")
        return bool(sender) and claims.get("email") == sender and bool(claims.get("email_verified"))
    token = os.environ.get("GMAIL_PUSH_TOKEN", "")
    return bool(token) and hmac.compare_digest(str(args.get("token", "")), token)


def parse_gmail(body: dict[str, Any]) -> str:
    """The mailbox a Pub/Sub push is about ('' if malformed)."""
    try:
        data = json.loads(base64.b64decode((body.get("message") or {}).get("data") or ""))
    except (ValueError, TypeError):
        return ""
    return str(data.get("emailAddress") or "").lower() if isinstance(data, dict) else ""


def users_for_gmail(store: Store, email: str) -> list[int]:
    if not email:
        return []
    rows = store.query("SELECT user_id FROM cw_connections WHERE provider = 'google' AND LOWER(account_label) = %s "
                       "AND status IN ('connected', 'syncing')", (email.lower(),))
    return [int(r["user_id"]) for r in rows]


# -- Outlook (Microsoft Graph) ----------------------------------------------

def graph_enabled() -> bool:
    return _backend_url().startswith("https://")  # Graph only delivers to public https endpoints


def _graph_time(when: datetime) -> str:
    return when.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.0000000Z")


def ensure_graph_subscription(connector: Any) -> None:
    """Create or renew the inbox subscription. Never breaks a sync."""
    if not graph_enabled():
        return
    from coworker.connectors.base import ConnectorError
    from coworker.store import parse_iso

    now = datetime.now(UTC)
    sub = connector.cursor.get("graph_sub") or {}
    expires = parse_iso(sub.get("expires"))
    if (sub.get("id") and expires and expires - now > RENEW_BEFORE) or _backing_off(connector, "graph_sub_retry"):
        return
    new_expiry = now + GRAPH_LIFETIME
    try:
        if sub.get("id"):
            try:
                connector._request("PATCH", f"/subscriptions/{sub['id']}", json={"expirationDateTime": _graph_time(new_expiry)})
                connector.cursor["graph_sub"] = {**sub, "expires": iso(new_expiry)}
                return
            except ConnectorError as exc:
                if exc.code != "not_found":
                    raise
        client_state = secrets.token_urlsafe(24)
        created = connector._request("POST", "/subscriptions", json={
            "changeType": "created",
            "notificationUrl": f"{_backend_url()}/api/coworker/microsoft/notify",
            "resource": "me/mailFolders('Inbox')/messages",
            "expirationDateTime": _graph_time(new_expiry),
            "clientState": client_state,
        })
    except ConnectorError as exc:
        log.warning("graph subscription failed for user %s: %s", connector.user_id, exc)
        _back_off(connector, "graph_sub_retry")
        return
    connector.cursor["graph_sub"] = {"id": created.get("id", ""), "expires": iso(new_expiry), "client_state": client_state}


GUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
MAX_GRAPH_NOTIFICATIONS = 100


def users_for_graph(store: Store, notifications: list[dict[str, Any]]) -> list[int]:
    """Users whose subscription id and clientState both match a notification."""
    found: list[int] = []
    seen: set[str] = set()
    for n in notifications[:MAX_GRAPH_NOTIFICATIONS]:
        if not isinstance(n, dict):
            continue
        sub_id, state = str(n.get("subscriptionId") or ""), str(n.get("clientState") or "")
        if not state or not GUID_RE.fullmatch(sub_id) or sub_id in seen:
            continue  # Graph subscription ids are GUIDs; anything else (e.g. "%") never reaches the query
        seen.add(sub_id)
        for row in store.query("SELECT user_id, sync_cursor FROM cw_connections WHERE provider = 'microsoft' "
                               "AND status IN ('connected', 'syncing') AND sync_cursor LIKE %s", (f"%{sub_id}%",)):
            try:
                cursor = json.loads(row.get("sync_cursor") or "{}")
            except ValueError:
                continue
            sub = cursor.get("graph_sub") or {}
            if sub.get("id") == sub_id and hmac.compare_digest(str(sub.get("client_state") or ""), state):
                if int(row["user_id"]) not in found:
                    found.append(int(row["user_id"]))
    return found
