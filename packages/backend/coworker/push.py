"""Mobile push notifications through Expo's push service.

The mobile app registers its Expo push token (``POST /push/register``).
The coworker pushes when something needs the user:

* an action needs approval: the notification has Approve and Reject
  buttons (the ``approval`` category registered by the app);
* a hot lead or an escalation on a call;
* the coworker joined a call (tap to watch, whisper, or take over);
* the daily digest.

Pushes for approvals are coalesced to at most one per minute per user, and
tokens Expo reports as unregistered are dropped.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any

import requests

from coworker.store import IntegrityError, Store, iso, utcnow

log = logging.getLogger("coworker.push")

EXPO_URL = "https://exp.host/--/api/v2/push/send"
TOKEN_RE = re.compile(r"^(?:Exponent|Expo)PushToken\[[\w-]+\]$")
MAX_TOKENS = 5


def tokens(store: Store, user_id: int) -> list[str]:
    return list(((store.get_coworker(user_id) or {}).get("settings") or {}).get("push_tokens") or [])


def _save(store: Store, user_id: int, values: list[str]) -> None:
    coworker = store.get_coworker(user_id) or {}
    store.update_coworker(user_id, settings={**(coworker.get("settings") or {}), "push_tokens": values[-MAX_TOKENS:]})


def register(store: Store, user_id: int, token: str) -> list[str]:
    if not TOKEN_RE.match(token or ""):
        raise ValueError("Not an Expo push token")
    current = [t for t in tokens(store, user_id) if t != token]
    _save(store, user_id, current + [token])
    return tokens(store, user_id)


def unregister(store: Store, user_id: int, token: str) -> None:
    _save(store, user_id, [t for t in tokens(store, user_id) if t != token])


def send(store: Store, user_id: int, title: str, body: str, data: dict[str, Any] | None = None,
         category: str | None = None) -> int:
    """Push to every device the user registered. Returns how many accepted it."""
    if os.environ.get("COWORKER_PUSH", "1") == "0":
        return 0
    targets = tokens(store, user_id)
    if not targets:
        return 0
    messages = [{"to": t, "title": title[:120], "body": body[:240], "data": data or {}, "sound": "default",
                 **({"categoryId": category} if category else {})} for t in targets]
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if os.environ.get("EXPO_ACCESS_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['EXPO_ACCESS_TOKEN']}"
    try:
        resp = requests.post(EXPO_URL, json=messages, headers=headers, timeout=10)
        results = (resp.json() or {}).get("data") or []
    except (requests.RequestException, ValueError) as exc:
        log.warning("push failed for user %s: %s", user_id, exc)
        return 0
    dead = [t for t, r in zip(targets, results)
            if r.get("status") == "error" and (r.get("details") or {}).get("error") == "DeviceNotRegistered"]
    if dead:
        _save(store, user_id, [t for t in tokens(store, user_id) if t not in dead])
    return sum(1 for r in results if r.get("status") == "ok")


def approval_needed(store: Store, user_id: int, action: dict[str, Any]) -> int:
    """Push for a new proposal, at most once a minute per user."""
    slot = utcnow().strftime("%Y-%m-%dT%H:%M")
    try:
        store.insert("cw_notifications", {"user_id": user_id, "kind": "push_approval", "slot": slot,
                                          "channel": "push", "subject": action["title"][:500], "item_count": 1,
                                          "sent_at": iso()})
    except IntegrityError:
        return 0
    pending = store.one("SELECT COUNT(*) AS n FROM cw_actions WHERE user_id = %s AND status = 'proposed'", (user_id,))
    n = int((pending or {}).get("n") or 1)
    body = (action.get("payload") or {}).get("body") or (action.get("payload") or {}).get("text") or action.get("reasoning") or ""
    title = action["title"] if n <= 1 else f"{action['title']} (+{n - 1} more)"
    return send(store, user_id, title, body.strip().replace("\n", " "),
                {"type": "approval", "actionId": action["id"]}, category="approval")
