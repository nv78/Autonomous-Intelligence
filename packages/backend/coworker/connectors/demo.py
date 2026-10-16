"""The demo workspace connector.

Seeds a fictional Anote mailbox, Slack, calendar, and docs, and makes
every "send" land back in that workspace as an outbound item, so the
whole delegation loop is visible end to end without touching real
accounts.
"""
from __future__ import annotations

import uuid
from typing import Any

from coworker.connectors.base import SendResult
from coworker.demo_data import SCENARIOS, seed_items
from coworker.store import Store, iso, utcnow


class DemoConnector:
    provider = "demo"

    # -- seeding -----------------------------------------------------------

    @staticmethod
    def seed(store: Store, user_id: int, owner_name: str, owner_email: str) -> int:
        count = 0
        for item in seed_items(owner_name, owner_email, utcnow()):
            if store.add_item(user_id, item):
                count += 1
        store.upsert_connection(
            user_id, "demo", account_label="Anote demo workspace (fictional data)",
            status="connected", last_synced_at=iso(),
        )
        return count

    @staticmethod
    def inject(store: Store, user_id: int, scenario: str) -> int | None:
        spec = SCENARIOS.get(scenario)
        if not spec:
            return None
        item = dict(spec["item"])
        item["external_id"] = f"demo-sim-{scenario}-{uuid.uuid4().hex[:8]}"
        item["occurred_at"] = iso()
        if item["kind"] == "email":
            coworker = store.get_coworker(user_id) or {}
            item["recipients"] = [{"name": coworker.get("owner_name", ""), "email": coworker.get("owner_email", "")}]
        return store.add_item(user_id, item)

    # -- writes ------------------------------------------------------------

    def _owner(self, store: Store, user_id: int) -> dict[str, str]:
        coworker = store.get_coworker(user_id) or {}
        return {"name": coworker.get("owner_name", ""), "email": coworker.get("owner_email", "")}

    def send_email(self, store: Store, user_id: int, *, to: list[str], subject: str, body: str,
                   thread_id: str = "", cc: list[str] | None = None, files: list[Any] | None = None) -> SendResult:
        owner = self._owner(store, user_id)
        ext = f"demo-out-{uuid.uuid4().hex[:10]}"
        thread = thread_id or f"t-{uuid.uuid4().hex[:8]}"
        recipients = [{"name": "", "email": e} for e in to + (cc or [])]
        item_id = store.add_item(user_id, {
            "provider": "gmail", "external_id": ext, "thread_id": thread, "kind": "email",
            "direction": "outbound", "author_name": owner["name"], "author_email": owner["email"],
            "recipients": recipients, "subject": subject, "body": body, "occurred_at": iso(),
            "meta": {"labels": ["SENT"], "sent_by": "coworker", "demo": True,
                     "attachments": [{"filename": f.name, "size": len(f.data)} for f in files or []]},
        })
        return SendResult(external_id=ext, thread_id=thread, undo={"item_id": item_id})

    def create_draft(self, store: Store, user_id: int, *, to: list[str], subject: str, body: str,
                     thread_id: str = "", files: list[Any] | None = None) -> SendResult:
        owner = self._owner(store, user_id)
        ext = f"demo-draft-{uuid.uuid4().hex[:10]}"
        item_id = store.add_item(user_id, {
            "provider": "gmail", "external_id": ext, "thread_id": thread_id or ext, "kind": "draft",
            "direction": "outbound", "author_name": owner["name"], "author_email": owner["email"],
            "recipients": [{"name": "", "email": e} for e in to], "subject": subject, "body": body,
            "occurred_at": iso(), "meta": {"labels": ["DRAFT"], "demo": True},
        })
        return SendResult(external_id=ext, thread_id=thread_id, undo={"item_id": item_id})

    def post_message(self, store: Store, user_id: int, *, channel: str, text: str) -> SendResult:
        owner = self._owner(store, user_id)
        ext = f"demo-slack-out-{uuid.uuid4().hex[:10]}"
        item_id = store.add_item(user_id, {
            "provider": "slack", "external_id": ext, "thread_id": f"slack-{channel}", "kind": "slack",
            "direction": "outbound", "author_name": owner["name"], "author_email": owner["email"],
            "recipients": [], "subject": "", "body": text, "channel": channel, "occurred_at": iso(),
            "meta": {"sent_by": "coworker", "demo": True},
        })
        return SendResult(external_id=ext, thread_id=f"slack-{channel}", undo={"item_id": item_id})

    def create_event(self, store: Store, user_id: int, *, title: str, start: str, end: str,
                     attendees: list[str], description: str = "", add_video: bool = True) -> SendResult:
        owner = self._owner(store, user_id)
        ext = f"demo-evt-{uuid.uuid4().hex[:10]}"
        location = f"https://meet.google.com/demo-{uuid.uuid4().hex[:3]}-{uuid.uuid4().hex[:4]}" if add_video else ""
        item_id = store.add_item(user_id, {
            "provider": "gcal", "external_id": ext, "thread_id": f"event-{ext}", "kind": "event",
            "direction": "outbound", "author_name": owner["name"], "author_email": owner["email"],
            "recipients": [{"name": "", "email": e} for e in attendees], "subject": title,
            "body": description or location, "occurred_at": start,
            "meta": {"start": start, "end": end, "location": location, "created_by": "coworker", "demo": True},
        })
        return SendResult(external_id=ext, thread_id=f"event-{ext}", undo={"item_id": item_id})

    def undo(self, store: Store, user_id: int, action_type: str, undo: dict[str, Any]) -> bool:
        item_id = undo.get("item_id")
        if not item_id:
            return False
        return store.execute("DELETE FROM cw_items WHERE id = %s AND user_id = %s", (item_id, user_id)) > 0

    def sync(self, store: Store, user_id: int) -> int:  # pragma: no cover - demo never syncs remotely
        return 0
