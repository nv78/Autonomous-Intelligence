"""Live Microsoft 365 connector: Outlook mail and calendar over Microsoft Graph.

OAuth uses an Azure (Entra ID) app registration: ``MICROSOFT_CLIENT_ID`` /
``MICROSOFT_CLIENT_SECRET``, tenant ``MICROSOFT_TENANT`` (default ``common``,
which accepts work, school and personal Microsoft accounts).

Like Google, scopes are requested in two steps: ``read`` at onboarding and
``act`` (send mail, write calendar) when a responsibility first needs it.
Microsoft rotates refresh tokens, so every refresh saves the new one.
"""
from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import requests

from coworker.connectors.base import ConnectorError, SendResult, decrypt_token, encrypt_token
from coworker.connectors.google import _strip_html, _strip_quoted
from coworker.store import Store, iso

GRAPH = "https://graph.microsoft.com/v1.0"

SCOPES = {
    "read": ["offline_access", "openid", "email", "profile", "User.Read", "Mail.Read", "Calendars.Read"],
    "act": ["Mail.Send", "Mail.ReadWrite", "Calendars.ReadWrite"],
}
# The Gmail scope names the rest of the app checks, mapped to Graph's.
SCOPE_ALIASES = {"gmail.send": "Mail.Send", "gmail.compose": "Mail.ReadWrite", "calendar.events": "Calendars.ReadWrite"}

BACKFILL_DAYS = int(os.environ.get("COWORKER_BACKFILL_DAYS", "90"))
MAX_MESSAGES_PER_SYNC = int(os.environ.get("COWORKER_MAX_MESSAGES_PER_SYNC", "300"))
TIMEOUT = 20
MESSAGE_FIELDS = ("id,conversationId,internetMessageId,subject,body,from,toRecipients,ccRecipients,"
                  "receivedDateTime,sentDateTime,isDraft,parentFolderId,internetMessageHeaders,hasAttachments")


def _tenant() -> str:
    return os.environ.get("MICROSOFT_TENANT", "common")


def _authority() -> str:
    return f"https://login.microsoftonline.com/{_tenant()}/oauth2/v2.0"


def is_configured() -> bool:
    return bool(os.environ.get("MICROSOFT_CLIENT_ID") and os.environ.get("MICROSOFT_CLIENT_SECRET"))


def redirect_uri() -> str:
    default = f"{os.environ.get('BACKEND_URL', 'http://localhost:5000').rstrip('/')}/api/coworker/connections/microsoft/callback"
    return os.environ.get("MICROSOFT_REDIRECT_URI", default)


def scopes_for(level: str) -> list[str]:
    return SCOPES["read"] + (SCOPES["act"] if level == "act" else [])


def auth_url(state: str, level: str = "read") -> str:
    params = {
        "client_id": os.environ.get("MICROSOFT_CLIENT_ID", ""),
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "response_mode": "query",
        "scope": " ".join(scopes_for(level)),
        "prompt": "select_account",
        "state": state,
    }
    return f"{_authority()}/authorize?{urlencode(params)}"


def _token_request(data: dict[str, str]) -> dict[str, Any]:
    resp = requests.post(f"{_authority()}/token", data={
        "client_id": os.environ.get("MICROSOFT_CLIENT_ID", ""),
        "client_secret": os.environ.get("MICROSOFT_CLIENT_SECRET", ""),
        **data,
    }, timeout=TIMEOUT)
    body: dict[str, Any] = resp.json() if resp.content else {}
    if resp.status_code != 200:
        # invalid_grant: the refresh token expired or was revoked (password change, admin, 90 days idle)
        code = "reauth_required" if body.get("error") in ("invalid_grant", "interaction_required") else "oauth_failed"
        raise ConnectorError(f"Microsoft sign-in failed: {body.get('error_description', resp.text)[:200]}", code)
    body["expires_at"] = time.time() + int(body.get("expires_in", 3600)) - 60
    return body


def exchange_code(code: str) -> dict[str, Any]:
    return _token_request({"code": code, "redirect_uri": redirect_uri(), "grant_type": "authorization_code"})


def fetch_account_email(access_token: str) -> str:
    resp = requests.get(f"{GRAPH}/me", params={"$select": "mail,userPrincipalName"},
                        headers={"Authorization": f"Bearer {access_token}"}, timeout=TIMEOUT)
    if resp.status_code != 200:
        return ""
    me = resp.json()
    return str(me.get("mail") or me.get("userPrincipalName") or "").lower()


def revoke(token: dict[str, Any]) -> None:
    """Graph has no per-app token revocation; dropping our copy is what disconnect does.
    Users can also remove the app at https://myapps.microsoft.com."""


def _address(entry: dict[str, Any] | None) -> dict[str, str]:
    addr = (entry or {}).get("emailAddress") or {}
    return {"name": addr.get("name", ""), "email": (addr.get("address") or "").lower()}


def _to_utc(value: str) -> str:
    """Graph returns '2026-10-15T14:00:00.0000000' (UTC when asked) or with a Z."""
    if not value:
        return ""
    clean = value.replace("Z", "")[:19]
    return iso(datetime.fromisoformat(clean).replace(tzinfo=UTC))


def _graph_time(value: str) -> dict[str, str]:
    """Our ISO timestamps -> Graph's {dateTime, timeZone} in UTC."""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return {"dateTime": dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": "UTC"}


def parse_message(msg: dict[str, Any], account_email: str, sent_folder: str = "") -> dict[str, Any]:
    sender = _address(msg.get("from"))
    recipients = [_address(r) for r in (msg.get("toRecipients") or []) + (msg.get("ccRecipients") or [])]
    body = msg.get("body") or {}
    text = body.get("content", "")
    if body.get("contentType", "").lower() == "html":
        text = _strip_html(text)
    outbound = bool((sent_folder and msg.get("parentFolderId") == sent_folder)
                    or (account_email and sender["email"] == account_email.lower()))
    headers = {h.get("name", "").lower(): h.get("value", "") for h in msg.get("internetMessageHeaders") or []}
    when = msg.get("receivedDateTime") or msg.get("sentDateTime") or ""
    return {
        "provider": "outlook",
        "external_id": msg["id"],
        "thread_id": msg.get("conversationId") or msg["id"],
        "kind": "draft" if msg.get("isDraft") else "email",
        "direction": "outbound" if outbound else "inbound",
        "author_name": sender["name"] or sender["email"],
        "author_email": sender["email"],
        "recipients": [r for r in recipients if r["email"]],
        "subject": (msg.get("subject") or "")[:500],
        "body": _strip_quoted(text)[:20000],
        "occurred_at": iso(datetime.fromisoformat(when.replace("Z", "+00:00"))) if when else iso(),
        "meta": {
            "message_id": msg.get("internetMessageId", ""),
            "list_unsubscribe": bool(headers.get("list-unsubscribe")),
            "labels": ["SENT"] if outbound else ["INBOX"],
        },
    }


class MicrosoftConnector:
    provider = "microsoft"

    def __init__(self, store: Store, user_id: int, token: dict[str, Any], cursor: dict[str, Any],
                 account_email: str = "") -> None:
        self.store = store
        self.user_id = user_id
        self.token = token
        self.cursor = cursor
        self.account_email = account_email

    @classmethod
    def from_row(cls, store: Store, row: dict[str, Any]) -> MicrosoftConnector:
        cursor = row.get("sync_cursor") or {}
        if isinstance(cursor, str):
            try:
                cursor = json.loads(cursor)
            except ValueError:
                cursor = {}
        return cls(store, int(row["user_id"]), decrypt_token(row.get("token_enc")), cursor,
                   row.get("account_label", ""))

    # -- auth --------------------------------------------------------------

    def has_scope(self, scope: str) -> bool:
        wanted = SCOPE_ALIASES.get(scope, scope).lower()
        return wanted in {s.lower().rsplit("/", 1)[-1] for s in str(self.token.get("scope", "")).split()}

    def _access_token(self) -> str:
        if self.token.get("expires_at", 0) > time.time() and self.token.get("access_token"):
            return str(self.token["access_token"])
        refresh = self.token.get("refresh_token")
        if not refresh:
            raise ConnectorError("Outlook access expired. Please reconnect.", "reauth_required")
        fresh = _token_request({"refresh_token": refresh, "grant_type": "refresh_token",
                                "scope": str(self.token.get("scope", "")) or " ".join(SCOPES["read"])})
        self.token.update(fresh)  # includes the rotated refresh_token
        self.store.upsert_connection(self.user_id, "microsoft", token_enc=encrypt_token(self.token))
        return str(self.token["access_token"])

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        url = path if path.startswith("http") else f"{GRAPH}{path}"
        extra_headers = kwargs.pop("headers", {})
        for attempt in range(3):
            headers = {"Authorization": f"Bearer {self._access_token()}", **extra_headers}
            resp = requests.request(method, url, headers=headers, timeout=TIMEOUT, **kwargs)
            if resp.status_code == 401 and attempt == 0:
                self.token["expires_at"] = 0
                continue
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(min(int(resp.headers.get("Retry-After", 2 ** attempt)), 10))
                continue
            if resp.status_code == 401:
                raise ConnectorError("Microsoft rejected our token. Please reconnect.", "reauth_required")
            if resp.status_code == 403:
                raise ConnectorError("Ourogen needs permission to do this. Reconnect Outlook with send access.",
                                     "needs_scope")
            if resp.status_code >= 400:
                raise ConnectorError(f"Microsoft Graph error {resp.status_code}: {resp.text[:200]}",
                                     "not_found" if resp.status_code in (404, 410) else "provider_error")
            if not resp.content:
                return {}
            data: dict[str, Any] = resp.json()
            return data
        raise ConnectorError("Microsoft Graph kept failing; will retry later.")  # pragma: no cover

    # -- sync --------------------------------------------------------------

    def sync(self, store: Store, user_id: int) -> int:
        if not self.account_email:
            self.account_email = fetch_account_email(self._access_token())
        count = self._sync_mail(store, user_id) + self._sync_calendar(store, user_id)
        from coworker import mail_push

        mail_push.ensure_graph_subscription(self)
        store.upsert_connection(user_id, "microsoft", sync_cursor=json.dumps(self.cursor))
        return count

    def _sent_folder(self) -> str:
        if not self.cursor.get("sent_folder"):
            try:
                self.cursor["sent_folder"] = self._request("GET", "/me/mailFolders/sentitems", params={"$select": "id"}).get("id", "")
            except ConnectorError:
                return ""
        return str(self.cursor.get("sent_folder", ""))

    def _sync_mail(self, store: Store, user_id: int) -> int:
        since = self.cursor.get("mail_since") or iso(datetime.now(UTC) - timedelta(days=BACKFILL_DAYS))
        sent_folder = self._sent_folder()
        url: str | None = "/me/messages"
        params: dict[str, Any] | None = {
            "$filter": f"receivedDateTime ge {since}", "$orderby": "receivedDateTime desc",
            "$top": 50, "$select": MESSAGE_FIELDS,
        }
        newest = since
        count = seen = 0
        while url and seen < MAX_MESSAGES_PER_SYNC:
            data = self._request("GET", url, params=params, headers={"Prefer": 'outlook.body-content-type="text"'})
            for msg in data.get("value", []):
                seen += 1
                newest = max(newest, msg.get("receivedDateTime") or newest)
                item = parse_message(msg, self.account_email, sent_folder)
                if store.add_item(user_id, item):
                    count += 1
                    if msg.get("hasAttachments"):
                        self._ingest_attachments(store, user_id, item)
            url, params = data.get("@odata.nextLink"), None  # the next link carries the query
        self.cursor["mail_since"] = newest
        return count

    def _ingest_attachments(self, store: Store, user_id: int, item: dict[str, Any]) -> None:
        from coworker import attachments

        try:
            listed = self._request("GET", f"/me/messages/{item['external_id']}/attachments",
                                   params={"$select": "id,name,contentType,size,isInline"}).get("value", [])
        except ConnectorError:
            return
        files = [a for a in listed if a.get("@odata.type", "").endswith("fileAttachment") and not a.get("isInline")]
        for a in files[:attachments.MAX_PER_MESSAGE]:
            att = {"id": a["id"], "filename": a.get("name", ""), "mime": a.get("contentType", ""), "size": int(a.get("size") or 0)}
            if not attachments.supported(att["filename"], att["size"]):
                continue
            try:
                data = self.attachment_bytes(item["external_id"], att["id"])
            except ConnectorError:
                continue
            attachments.ingest(store, user_id, item, att, data)

    def attachment_bytes(self, message_id: str, attachment_id: str) -> bytes:
        from coworker.attachments import b64decode_any

        data = self._request("GET", f"/me/messages/{message_id}/attachments/{attachment_id}")
        return b64decode_any(str(data.get("contentBytes") or ""))

    def _attach(self, draft_id: str, files: list[Any] | None) -> None:
        import base64

        for f in files or []:
            self._request("POST", f"/me/messages/{draft_id}/attachments", json={
                "@odata.type": "#microsoft.graph.fileAttachment", "name": f.name,
                "contentType": f.mime, "contentBytes": base64.b64encode(f.data).decode(),
            })

    def _sync_calendar(self, store: Store, user_id: int) -> int:
        now = datetime.now(UTC)
        params: dict[str, Any] = {
            "startDateTime": iso(now - timedelta(days=14)), "endDateTime": iso(now + timedelta(days=21)),
            "$top": 250, "$orderby": "start/dateTime",
            "$select": "id,subject,start,end,attendees,organizer,location,onlineMeeting,webLink,isCancelled",
        }
        data = self._request("GET", "/me/calendarView", params=params, headers={"Prefer": 'outlook.timezone="UTC"'})
        count = 0
        for ev in data.get("value", []):
            if ev.get("isCancelled"):
                continue
            start = _to_utc((ev.get("start") or {}).get("dateTime", ""))
            end = _to_utc((ev.get("end") or {}).get("dateTime", ""))
            if not start:
                continue
            organizer = _address(ev.get("organizer"))
            attendees = [a for a in (_address(x) for x in ev.get("attendees") or [])
                         if a["email"] and a["email"] != (self.account_email or "").lower()]
            location = ((ev.get("onlineMeeting") or {}).get("joinUrl")
                        or (ev.get("location") or {}).get("displayName", ""))
            item = {
                "provider": "outlook_cal", "external_id": ev["id"], "thread_id": f"event-{ev['id']}", "kind": "event",
                "direction": "inbound", "author_name": organizer["name"], "author_email": organizer["email"],
                "recipients": attendees, "subject": ev.get("subject") or "(no title)", "body": location,
                "occurred_at": start,
                "meta": {"start": start, "end": end, "location": location, "html_link": ev.get("webLink", "")},
            }
            existing = store.one("SELECT id FROM cw_items WHERE user_id = %s AND provider = 'outlook_cal' AND external_id = %s",
                                 (user_id, ev["id"]))
            if existing:
                store.update("cw_items", existing["id"], user_id, {k: item[k] for k in ("subject", "occurred_at", "meta", "recipients")})
            elif store.add_item(user_id, item):
                count += 1
        return count

    # -- writes ------------------------------------------------------------

    def _last_in_thread(self, store: Store, user_id: int, thread_id: str) -> str:
        rows = store.thread(user_id, thread_id) if thread_id else []
        last = next((r for r in reversed(rows) if r.get("kind") == "email" and r.get("provider") == "outlook"), None)
        return str(last["external_id"]) if last else ""

    @staticmethod
    def _recipients(emails: list[str]) -> list[dict[str, Any]]:
        return [{"emailAddress": {"address": e}} for e in emails]

    def _compose(self, store: Store, user_id: int, to: list[str], subject: str, body: str,
                 thread_id: str, cc: list[str] | None) -> dict[str, Any]:
        """A draft in the user's mailbox, threaded as a reply when we know the conversation."""
        fields = {"subject": subject, "body": {"contentType": "Text", "content": body},
                  "toRecipients": self._recipients(to), "ccRecipients": self._recipients(cc or [])}
        reply_to = self._last_in_thread(store, user_id, thread_id)
        if reply_to:
            try:
                draft = self._request("POST", f"/me/messages/{reply_to}/createReplyAll")
                self._request("PATCH", f"/me/messages/{draft['id']}", json=fields)
                return draft
            except ConnectorError as exc:
                if exc.code != "not_found":
                    raise  # message was deleted on their side: fall through to a fresh email
        return self._request("POST", "/me/messages", json=fields)

    def send_email(self, store: Store, user_id: int, *, to: list[str], subject: str, body: str,
                   thread_id: str = "", cc: list[str] | None = None, files: list[Any] | None = None) -> SendResult:
        if not self.has_scope("Mail.Send"):
            raise ConnectorError("Ourogen needs permission to send email. Reconnect Outlook with send access.",
                                 "needs_scope")
        draft = self._compose(store, user_id, to, subject, body, thread_id, cc)
        self._attach(draft["id"], files)
        self._request("POST", f"/me/messages/{draft['id']}/send")
        return SendResult(external_id=draft.get("id", ""), thread_id=draft.get("conversationId") or thread_id)

    def create_draft(self, store: Store, user_id: int, *, to: list[str], subject: str, body: str,
                     thread_id: str = "", files: list[Any] | None = None) -> SendResult:
        draft = self._compose(store, user_id, to, subject, body, thread_id, None)
        self._attach(draft["id"], files)
        return SendResult(external_id=draft.get("id", ""), thread_id=thread_id, undo={"draft_id": draft.get("id", "")})

    def create_event(self, store: Store, user_id: int, *, title: str, start: str, end: str,
                     attendees: list[str], description: str = "", add_video: bool = True) -> SendResult:
        body: dict[str, Any] = {
            "subject": title, "body": {"contentType": "Text", "content": description},
            "start": _graph_time(start), "end": _graph_time(end),
            "attendees": [{"emailAddress": {"address": e}, "type": "required"} for e in attendees],
        }
        if add_video:
            body.update({"isOnlineMeeting": True, "onlineMeetingProvider": "teamsForBusiness"})
        try:
            ev = self._request("POST", "/me/events", json=body)
        except ConnectorError:
            if not add_video:
                raise
            # Personal Microsoft accounts can't create Teams meetings; book it without one.
            body.pop("isOnlineMeeting")
            body.pop("onlineMeetingProvider")
            ev = self._request("POST", "/me/events", json=body)
        return SendResult(external_id=ev.get("id", ""), undo={"event_id": ev.get("id", "")})

    def undo(self, store: Store, user_id: int, action_type: str, undo: dict[str, Any]) -> bool:
        if undo.get("event_id"):
            self._request("POST", f"/me/events/{undo['event_id']}/cancel", json={"comment": "Cancelled"})
            return True
        if undo.get("draft_id"):
            self._request("DELETE", f"/me/messages/{undo['draft_id']}")
            return True
        return False  # sent mail can't be recalled; the executor's send delay is the undo window
