"""Connector interface and the per-user workspace router."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from coworker.store import Store, get_store, iso

PROVIDERS = ("google", "microsoft", "slack")


class ConnectorError(Exception):
    """A provider call failed. ``code`` lets the UI react (e.g. reconnect)."""

    def __init__(self, message: str, code: str = "provider_error") -> None:
        super().__init__(message)
        self.code = code


@dataclass
class SendResult:
    external_id: str
    thread_id: str = ""
    undo: dict[str, Any] = field(default_factory=dict)


class Connector(Protocol):
    provider: str

    def sync(self, store: Store, user_id: int) -> int: ...


LABELS = {"google": "Google", "slack": "Slack", "microsoft": "Outlook", "hubspot": "HubSpot"}


def _tell_owner_to_reconnect(store: Store, user_id: int, provider: str) -> None:
    """A connection's access expired: until the owner reconnects, nothing from it is read or sent."""
    from coworker import notify, push

    name = LABELS.get(provider, provider.title())
    body = (f"Your coworker lost access to {name}, so it has stopped reading and sending there. "
            f"Reconnect it here: {notify._app_url('/coworker/settings')}")
    try:
        push.send(store, user_id, f"Reconnect {name}", f"Your coworker lost access to {name}.",
                  data={"url": "/coworker/settings"})
        notify.deliver(store, user_id, f"Reconnect {name}", body)
    except Exception:  # never let an alert break the sync loop
        pass
    store.log(user_id, "connection.reauth", f"{name} needs to be reconnected", {"provider": provider})


class Workspace:
    """Routes reads and writes for one user to demo or live connectors."""

    def __init__(self, store: Store, user_id: int) -> None:
        self.store = store
        self.user_id = user_id
        self.coworker = store.get_coworker(user_id) or {}
        self.mode = self.coworker.get("mode") or "demo"

    # -- which backend --------------------------------------------------

    def _live(self, provider: str) -> Any | None:
        if self.mode != "live":
            return None
        row = self.store.get_connection_row(self.user_id, provider)
        if not row or row.get("status") not in ("connected", "syncing"):
            return None
        if provider == "google":
            from coworker.connectors.google import GoogleConnector

            return GoogleConnector.from_row(self.store, row)
        if provider == "microsoft":
            from coworker.connectors.microsoft import MicrosoftConnector

            return MicrosoftConnector.from_row(self.store, row)
        if provider == "slack":
            from coworker.connectors.slack import SlackConnector

            return SlackConnector.from_row(self.store, row)
        return None  # pragma: no cover

    def _demo(self) -> Any:
        from coworker.connectors.demo import DemoConnector

        return DemoConnector()

    def email_connector(self) -> Any | None:
        """The live mailbox the coworker reads and sends from: Gmail, else Outlook."""
        return self._live("google") or self._live("microsoft")

    def _for_email(self) -> Any:
        return self.email_connector() or self._demo()

    def _for_slack(self) -> Any:
        return self._live("slack") or self._demo()

    # -- sync ------------------------------------------------------------

    def sync(self, providers: tuple[str, ...] = PROVIDERS) -> dict[str, int]:
        counts: dict[str, int] = {}
        if self.mode != "live":
            return counts
        for provider in providers:
            connector = self._live(provider)
            if not connector:
                continue
            before = (self.store.get_connection_row(self.user_id, provider) or {}).get("status")
            self.store.upsert_connection(self.user_id, provider, status="syncing")
            try:
                counts[provider] = connector.sync(self.store, self.user_id)
                self.store.upsert_connection(
                    self.user_id, provider, status="connected", error="", last_synced_at=iso()
                )
            except ConnectorError as exc:
                status = "reauth_required" if exc.code == "reauth_required" else "error"
                self.store.upsert_connection(self.user_id, provider, status=status, error=str(exc))
                if status == "reauth_required" and before != "reauth_required":
                    _tell_owner_to_reconnect(self.store, self.user_id, provider)
                if status == "error":  # reauth is the user's to fix; other errors are ours
                    import observability

                    observability.alert(f"sync-error:{provider}:{self.user_id}", f"{provider} sync failed",
                                        user_id=self.user_id, error=str(exc)[:200])
        return counts

    # -- actions ---------------------------------------------------------

    def send_email(self, to: list[str], subject: str, body: str, thread_id: str = "",
                   cc: list[str] | None = None, files: list[Any] | None = None) -> SendResult:
        result: SendResult = self._for_email().send_email(
            self.store, self.user_id, to=to, subject=subject, body=body, thread_id=thread_id, cc=cc or [], files=files or []
        )
        return result

    def create_draft(self, to: list[str], subject: str, body: str, thread_id: str = "",
                     files: list[Any] | None = None) -> SendResult:
        result: SendResult = self._for_email().create_draft(
            self.store, self.user_id, to=to, subject=subject, body=body, thread_id=thread_id, files=files or []
        )
        return result

    def post_slack(self, channel: str, text: str) -> SendResult:
        result: SendResult = self._for_slack().post_message(self.store, self.user_id, channel=channel, text=text)
        return result

    def create_event(self, title: str, start: str, end: str, attendees: list[str],
                     description: str = "", add_video: bool = True) -> SendResult:
        result: SendResult = self._for_email().create_event(
            self.store, self.user_id, title=title, start=start, end=end, attendees=attendees,
            description=description, add_video=add_video,
        )
        return result

    def undo(self, action_type: str, undo: dict[str, Any]) -> bool:
        target = self._for_slack() if action_type.startswith("slack.") else self._for_email()
        return bool(target.undo(self.store, self.user_id, action_type, undo))

    def calendar(self, start: str, end: str) -> list[dict[str, Any]]:
        """Calendar events between two ISO timestamps (synced items)."""
        rows = self.store.query(
            "SELECT * FROM cw_items WHERE user_id = %s AND kind = 'event' AND occurred_at >= %s "
            "AND occurred_at < %s ORDER BY occurred_at",
            (self.user_id, start, end),
        )
        return rows


def workspace_for(user_id: int, store: Store | None = None) -> Workspace:
    return Workspace(store or get_store(), user_id)


def encrypt_token(data: dict[str, Any]) -> str:
    from services.provider_keys import encrypt_key

    return encrypt_key(json.dumps(data))


def decrypt_token(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    from services.provider_keys import decrypt_key

    try:
        decoded: dict[str, Any] = json.loads(decrypt_key(value))
    except Exception:
        return {}
    return decoded
