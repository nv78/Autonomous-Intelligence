"""Live Google connector: Gmail, Calendar, and Drive over the REST APIs.

OAuth uses the same Google Cloud client as "Sign in with Google"
(``GOOGLE_CLIENT_ID`` / ``GOOGLE_CLIENT_SECRET``) with a second redirect
URI for the coworker (``GOOGLE_COWORKER_REDIRECT_URI``).

Scopes are requested incrementally: ``read`` at onboarding, and ``act``
(send mail, write calendar) the first time a responsibility needs it.
"""
from __future__ import annotations

import base64
import os
import re
import time
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from email.utils import getaddresses, parseaddr
from typing import Any
from urllib.parse import urlencode

import requests

from coworker.connectors.base import ConnectorError, SendResult, decrypt_token, encrypt_token
from coworker.store import Store, iso

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GMAIL = "https://gmail.googleapis.com/gmail/v1/users/me"
CALENDAR = "https://www.googleapis.com/calendar/v3/calendars/primary"
DRIVE = "https://www.googleapis.com/drive/v3"

SCOPES = {
    "read": [
        "openid", "email", "profile",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ],
    "act": [
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/calendar.events",
    ],
}

BACKFILL_DAYS = int(os.environ.get("COWORKER_BACKFILL_DAYS", "90"))
MAX_MESSAGES_PER_SYNC = int(os.environ.get("COWORKER_MAX_MESSAGES_PER_SYNC", "300"))
TIMEOUT = 20


def is_configured() -> bool:
    return bool(os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET"))


def redirect_uri() -> str:
    default = f"{os.environ.get('BACKEND_URL', 'http://localhost:5000').rstrip('/')}/api/coworker/connections/google/callback"
    return os.environ.get("GOOGLE_COWORKER_REDIRECT_URI", default)


def scopes_for(level: str) -> list[str]:
    return SCOPES["read"] + (SCOPES["act"] if level == "act" else [])


def auth_url(state: str, level: str = "read") -> str:
    params = {
        "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": " ".join(scopes_for(level)),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def exchange_code(code: str) -> dict[str, Any]:
    resp = requests.post(TOKEN_URL, data={
        "code": code,
        "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
        "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
        "redirect_uri": redirect_uri(),
        "grant_type": "authorization_code",
    }, timeout=TIMEOUT)
    if resp.status_code != 200:
        raise ConnectorError(f"Google token exchange failed: {resp.text[:200]}", "oauth_failed")
    token: dict[str, Any] = resp.json()
    token["expires_at"] = time.time() + int(token.get("expires_in", 3600)) - 60
    return token


def fetch_account_email(access_token: str) -> str:
    resp = requests.get(USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}, timeout=TIMEOUT)
    if resp.status_code != 200:
        return ""
    return str(resp.json().get("email", ""))


def revoke(token: dict[str, Any]) -> None:
    value = token.get("refresh_token") or token.get("access_token")
    if value:
        try:
            requests.post(REVOKE_URL, params={"token": value}, timeout=TIMEOUT)
        except requests.RequestException:
            pass


def _b64url_decode(data: str) -> str:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode()).decode("utf-8", errors="replace")


def _strip_html(html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    text = re.sub(r"(?i)<br\s*/?>|</p>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"[ \t]+", " ", text).strip()


def extract_body(payload: dict[str, Any]) -> str:
    """Prefer text/plain; fall back to stripped text/html."""
    plain: list[str] = []
    html: list[str] = []

    def walk(part: dict[str, Any]) -> None:
        mime = part.get("mimeType", "")
        data = (part.get("body") or {}).get("data")
        if data and mime == "text/plain":
            plain.append(_b64url_decode(data))
        elif data and mime == "text/html":
            html.append(_b64url_decode(data))
        for child in part.get("parts", []) or []:
            walk(child)

    walk(payload)
    if plain:
        return "\n".join(plain).strip()
    if html:
        return _strip_html("\n".join(html))
    return ""


def _strip_quoted(body: str) -> str:
    """Drop the quoted reply chain so memory isn't flooded with repeats."""
    lines = []
    for line in body.splitlines():
        if re.match(r"^On .+ wrote:$", line.strip()) or line.startswith(">"):
            break
        lines.append(line)
    return "\n".join(lines).strip() or body


def attachments_of(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """File parts of a Gmail message: [{id, filename, mime, size}]."""
    found: list[dict[str, Any]] = []

    def walk(part: dict[str, Any]) -> None:
        body = part.get("body") or {}
        if part.get("filename") and body.get("attachmentId"):
            found.append({"id": body["attachmentId"], "filename": part["filename"], "mime": part.get("mimeType", ""),
                          "size": int(body.get("size") or 0)})
        for child in part.get("parts", []) or []:
            walk(child)

    walk(payload)
    return found


def parse_message(msg: dict[str, Any], account_email: str) -> dict[str, Any]:
    headers = {h["name"].lower(): h["value"] for h in (msg.get("payload") or {}).get("headers", [])}
    from_name, from_email = parseaddr(headers.get("from", ""))
    recipients = [
        {"name": n, "email": e.lower()}
        for n, e in getaddresses([headers.get("to", ""), headers.get("cc", "")]) if e
    ]
    labels = msg.get("labelIds", []) or []
    outbound = "SENT" in labels or (account_email and from_email.lower() == account_email.lower())
    ts = int(msg.get("internalDate", "0")) / 1000 or time.time()
    return {
        "provider": "gmail",
        "external_id": msg["id"],
        "thread_id": msg.get("threadId", msg["id"]),
        "kind": "draft" if "DRAFT" in labels else "email",
        "direction": "outbound" if outbound else "inbound",
        "author_name": from_name or from_email,
        "author_email": from_email.lower(),
        "recipients": recipients,
        "subject": headers.get("subject", "")[:500],
        "body": _strip_quoted(extract_body(msg.get("payload") or {}))[:20000],
        "occurred_at": iso(datetime.fromtimestamp(ts, UTC)),
        "meta": {
            "labels": labels,
            "sent": "SENT" in labels,  # Gmail's own label: really sent from this account, not just a matching From
            "message_id": headers.get("message-id", ""),
            "references": headers.get("references", ""),
            "list_unsubscribe": bool(headers.get("list-unsubscribe")),
            "attachments": attachments_of(msg.get("payload") or {}),
        },
    }


def build_mime(sender: str, to: list[str], subject: str, body: str, cc: list[str] | None = None,
               in_reply_to: str = "", references: str = "", files: list[Any] | None = None) -> str:
    msg = EmailMessage()
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    if sender:
        msg["From"] = sender
    msg["Subject"] = subject
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = f"{references} {in_reply_to}".strip()
    msg.set_content(body)
    for f in files or []:
        maintype, _, subtype = (f.mime or "application/octet-stream").partition("/")
        msg.add_attachment(f.data, maintype=maintype or "application", subtype=subtype or "octet-stream", filename=f.name)
    return base64.urlsafe_b64encode(msg.as_bytes()).decode()


class GoogleConnector:
    provider = "google"

    def __init__(self, store: Store, user_id: int, token: dict[str, Any], cursor: dict[str, Any],
                 account_email: str = "") -> None:
        self.store = store
        self.user_id = user_id
        self.token = token
        self.cursor = cursor
        self.account_email = account_email

    @classmethod
    def from_row(cls, store: Store, row: dict[str, Any]) -> GoogleConnector:
        cursor = row.get("sync_cursor") or {}
        if isinstance(cursor, str):
            import json

            try:
                cursor = json.loads(cursor)
            except ValueError:
                cursor = {}
        return cls(store, int(row["user_id"]), decrypt_token(row.get("token_enc")), cursor,
                   row.get("account_label", ""))

    # -- auth --------------------------------------------------------------

    def has_scope(self, scope: str) -> bool:
        return scope in str(self.token.get("scope", ""))

    def _access_token(self) -> str:
        if self.token.get("expires_at", 0) > time.time() and self.token.get("access_token"):
            return str(self.token["access_token"])
        refresh = self.token.get("refresh_token")
        if not refresh:
            raise ConnectorError("Google access expired. Please reconnect.", "reauth_required")
        resp = requests.post(TOKEN_URL, data={
            "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
            "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
            "refresh_token": refresh,
            "grant_type": "refresh_token",
        }, timeout=TIMEOUT)
        if resp.status_code != 200:
            raise ConnectorError("Google refresh failed. Please reconnect.", "reauth_required")
        fresh = resp.json()
        self.token.update(fresh)
        self.token["expires_at"] = time.time() + int(fresh.get("expires_in", 3600)) - 60
        self.store.upsert_connection(self.user_id, "google", token_enc=encrypt_token(self.token))
        return str(self.token["access_token"])

    def _request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        for attempt in range(3):
            headers = {"Authorization": f"Bearer {self._access_token()}"}
            resp = requests.request(method, url, headers=headers, timeout=TIMEOUT, **kwargs)
            if resp.status_code == 401 and attempt == 0:
                self.token["expires_at"] = 0
                continue
            if resp.status_code in (429, 500, 502, 503) and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            if resp.status_code == 401:
                raise ConnectorError("Google rejected our token. Please reconnect.", "reauth_required")
            if resp.status_code == 403 and "insufficient" in resp.text.lower():
                raise ConnectorError("Ourogen needs permission to do this. Reconnect Google with send access.",
                                     "needs_scope")
            if resp.status_code >= 400:
                raise ConnectorError(f"Google API error {resp.status_code}: {resp.text[:200]}",
                                     "not_found" if resp.status_code in (404, 410) else "provider_error")
            if not resp.content:
                return {}
            data: dict[str, Any] = resp.json()
            return data
        raise ConnectorError("Google API kept failing; will retry later.")  # pragma: no cover

    # -- sync --------------------------------------------------------------

    def sync(self, store: Store, user_id: int) -> int:
        count = self._sync_gmail(store, user_id)
        count += self._sync_calendar(store, user_id)
        count += self._sync_drive(store, user_id)
        from coworker import mail_push

        mail_push.ensure_gmail_watch(self)
        import json

        store.upsert_connection(user_id, "google", sync_cursor=json.dumps(self.cursor))
        return count

    def _message_ids_full(self) -> list[str]:
        """Backfill: newest first, so the onboarding view fills in quickly."""
        ids: list[str] = []
        page_token = None
        query = f"newer_than:{BACKFILL_DAYS}d -in:chats"
        while len(ids) < MAX_MESSAGES_PER_SYNC:
            params: dict[str, Any] = {"q": query, "maxResults": 100}
            if page_token:
                params["pageToken"] = page_token
            data = self._request("GET", f"{GMAIL}/messages", params=params)
            ids += [m["id"] for m in data.get("messages", [])]
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        return ids[:MAX_MESSAGES_PER_SYNC]

    def _message_ids_incremental(self, history_id: str) -> list[str] | None:
        ids: list[str] = []
        page_token = None
        while True:
            params: dict[str, Any] = {"startHistoryId": history_id, "historyTypes": "messageAdded"}
            if page_token:
                params["pageToken"] = page_token
            try:
                data = self._request("GET", f"{GMAIL}/history", params=params)
            except ConnectorError as exc:
                if exc.code == "not_found":
                    return None  # history too old: fall back to a full sync
                raise
            for h in data.get("history", []):
                ids += [m["message"]["id"] for m in h.get("messagesAdded", [])]
            page_token = data.get("nextPageToken")
            if not page_token:
                return ids

    def _sync_gmail(self, store: Store, user_id: int) -> int:
        profile = self._request("GET", f"{GMAIL}/profile")
        self.account_email = profile.get("emailAddress", self.account_email)
        history_id = self.cursor.get("gmail_history_id")
        ids = self._message_ids_incremental(history_id) if history_id else None
        if ids is None:
            ids = self._message_ids_full()
        count = 0
        for mid in ids:
            if store.one("SELECT id FROM cw_items WHERE user_id = %s AND provider = 'gmail' AND external_id = %s",
                         (user_id, mid)):
                continue
            msg = self._request("GET", f"{GMAIL}/messages/{mid}", params={"format": "full"})
            item = parse_message(msg, self.account_email)
            if store.add_item(user_id, item):
                count += 1
                self._ingest_attachments(store, user_id, item)
        self.cursor["gmail_history_id"] = profile.get("historyId", history_id)
        return count

    def _ingest_attachments(self, store: Store, user_id: int, item: dict[str, Any]) -> None:
        from coworker import attachments

        for att in (item.get("meta") or {}).get("attachments", [])[:attachments.MAX_PER_MESSAGE]:
            if not attachments.supported(att["filename"], att.get("size", 0)):
                continue
            try:
                data = self.attachment_bytes(item["external_id"], att["id"])
            except ConnectorError:
                continue
            attachments.ingest(store, user_id, item, att, data)

    def attachment_bytes(self, message_id: str, attachment_id: str) -> bytes:
        from coworker.attachments import b64decode_any

        data = self._request("GET", f"{GMAIL}/messages/{message_id}/attachments/{attachment_id}")
        return b64decode_any(str(data.get("data") or ""))

    def _sync_calendar(self, store: Store, user_id: int) -> int:
        now = datetime.now(UTC)
        params = {
            "timeMin": (now - timedelta(days=14)).isoformat(),
            "timeMax": (now + timedelta(days=21)).isoformat(),
            "singleEvents": "true", "orderBy": "startTime", "maxResults": 250,
        }
        data = self._request("GET", f"{CALENDAR}/events", params=params)
        count = 0
        for ev in data.get("items", []):
            start = (ev.get("start") or {}).get("dateTime") or (ev.get("start") or {}).get("date")
            end = (ev.get("end") or {}).get("dateTime") or (ev.get("end") or {}).get("date")
            if not start:
                continue
            start_iso = iso(datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(UTC)) if "T" in start else start
            end_iso = iso(datetime.fromisoformat(end.replace("Z", "+00:00")).astimezone(UTC)) if end and "T" in end else end
            attendees = [
                {"name": a.get("displayName", ""), "email": a.get("email", "").lower()}
                for a in ev.get("attendees", []) if not a.get("self")
            ]
            location = ev.get("hangoutLink") or ev.get("location", "")
            item = {
                "provider": "gcal", "external_id": ev["id"], "thread_id": f"event-{ev['id']}", "kind": "event",
                "direction": "inbound", "author_name": (ev.get("organizer") or {}).get("displayName", ""),
                "author_email": (ev.get("organizer") or {}).get("email", ""), "recipients": attendees,
                "subject": ev.get("summary", "(no title)"), "body": location, "occurred_at": start_iso,
                "meta": {"start": start_iso, "end": end_iso, "location": location, "html_link": ev.get("htmlLink", "")},
            }
            existing = store.one("SELECT id FROM cw_items WHERE user_id = %s AND provider = 'gcal' AND external_id = %s",
                                 (user_id, ev["id"]))
            if existing:
                store.update("cw_items", existing["id"], user_id, {k: item[k] for k in ("subject", "occurred_at", "meta", "recipients")})
            elif store.add_item(user_id, item):
                count += 1
        return count

    def _sync_drive(self, store: Store, user_id: int) -> int:
        params = {
            "q": "mimeType='application/vnd.google-apps.document' and trashed=false",
            "orderBy": "modifiedTime desc", "pageSize": 20, "fields": "files(id,name,modifiedTime)",
        }
        try:
            data = self._request("GET", f"{DRIVE}/files", params=params)
        except ConnectorError:
            return 0  # Drive is optional context; never block email/calendar sync on it
        count = 0
        for f in data.get("files", []):
            if store.one("SELECT id FROM cw_items WHERE user_id = %s AND provider = 'drive' AND external_id = %s",
                         (user_id, f["id"])):
                continue
            headers = {"Authorization": f"Bearer {self._access_token()}"}
            resp = requests.get(f"{DRIVE}/files/{f['id']}/export", params={"mimeType": "text/plain"},
                                headers=headers, timeout=TIMEOUT)
            if resp.status_code != 200:
                continue
            if store.add_item(user_id, {
                "provider": "drive", "external_id": f["id"], "thread_id": f"doc-{f['id']}", "kind": "doc",
                "subject": f.get("name", ""), "body": resp.text[:20000],
                "occurred_at": f.get("modifiedTime", iso()).replace("+00:00", "Z"), "meta": {},
            }):
                count += 1
        return count

    # -- writes ------------------------------------------------------------

    def _reply_headers(self, store: Store, user_id: int, thread_id: str) -> tuple[str, str, str]:
        rows = store.thread(user_id, thread_id) if thread_id else []
        last = next((r for r in reversed(rows) if r.get("kind") == "email"), None)
        if not last:
            return "", "", ""
        meta = last.get("meta") or {}
        return meta.get("message_id", ""), meta.get("references", ""), last.get("thread_id", "")

    def send_email(self, store: Store, user_id: int, *, to: list[str], subject: str, body: str,
                   thread_id: str = "", cc: list[str] | None = None, files: list[Any] | None = None) -> SendResult:
        if not self.has_scope("gmail.send"):
            raise ConnectorError("Ourogen needs permission to send email. Reconnect Google with send access.",
                                 "needs_scope")
        in_reply_to, references, gmail_thread = self._reply_headers(store, user_id, thread_id)
        raw = build_mime(self.account_email, to, subject, body, cc, in_reply_to, references, files)
        payload: dict[str, Any] = {"raw": raw}
        if gmail_thread:
            payload["threadId"] = gmail_thread
        sent = self._request("POST", f"{GMAIL}/messages/send", json=payload)
        return SendResult(external_id=sent.get("id", ""), thread_id=sent.get("threadId", thread_id))

    def create_draft(self, store: Store, user_id: int, *, to: list[str], subject: str, body: str,
                     thread_id: str = "", files: list[Any] | None = None) -> SendResult:
        in_reply_to, references, gmail_thread = self._reply_headers(store, user_id, thread_id)
        message: dict[str, Any] = {"raw": build_mime(self.account_email, to, subject, body, None, in_reply_to, references,
                                                     files)}
        if gmail_thread:
            message["threadId"] = gmail_thread
        draft = self._request("POST", f"{GMAIL}/drafts", json={"message": message})
        return SendResult(external_id=draft.get("id", ""), thread_id=thread_id, undo={"draft_id": draft.get("id", "")})

    def create_event(self, store: Store, user_id: int, *, title: str, start: str, end: str,
                     attendees: list[str], description: str = "", add_video: bool = True) -> SendResult:
        body: dict[str, Any] = {
            "summary": title, "description": description,
            "start": {"dateTime": start}, "end": {"dateTime": end},
            "attendees": [{"email": e} for e in attendees],
        }
        if add_video:
            body["conferenceData"] = {"createRequest": {"requestId": f"ourogen-{int(time.time())}"}}
        ev = self._request("POST", f"{CALENDAR}/events", params={"conferenceDataVersion": 1, "sendUpdates": "all"}, json=body)
        return SendResult(external_id=ev.get("id", ""), undo={"event_id": ev.get("id", "")})

    def undo(self, store: Store, user_id: int, action_type: str, undo: dict[str, Any]) -> bool:
        if undo.get("event_id"):
            self._request("DELETE", f"{CALENDAR}/events/{undo['event_id']}", params={"sendUpdates": "all"})
            return True
        if undo.get("draft_id"):
            self._request("DELETE", f"{GMAIL}/drafts/{undo['draft_id']}")
            return True
        return False  # sent Gmail messages cannot be recalled; see the send delay in the executor
