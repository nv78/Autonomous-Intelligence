"""Tell the owner when their coworker needs them, by email.

* **Approvals.** New proposals are batched for ``NOTIFY_BATCH_SECONDS``
  (default 5 minutes), then sent as one email that links to the approvals
  page. At most one approval email per ``NOTIFY_MIN_INTERVAL_SECONDS``
  (default 30 minutes) per user. The limit is enforced by a unique key on
  ``cw_notifications`` (user, kind, time slot) as well as by the check, so
  the web app and the worker can't both send.
* **Daily digest.** Sent when ``settings.digest_email`` is on.

Delivery: the owner's own Gmail (to themselves) when the coworker has send
access, else the server relay in ``SMTP_URL``. In demo mode the email lands
in the demo inbox instead of being sent. ``settings.notify_approvals =
false`` turns approval emails off.
"""
from __future__ import annotations

import logging
import os
import smtplib
import ssl
import uuid
from datetime import timedelta
from email.message import EmailMessage
from typing import Any
from urllib.parse import unquote, urlparse

from coworker.store import IntegrityError, Store, iso, parse_iso, utcnow

log = logging.getLogger("coworker.notify")

SUBJECT_PREFIX = "[Ourogen]"
SENDER = "notifications@ourogen.ai"


def _batch_seconds() -> int:
    return int(os.environ.get("NOTIFY_BATCH_SECONDS", "300"))


def _interval_seconds() -> int:
    return int(os.environ.get("NOTIFY_MIN_INTERVAL_SECONDS", "1800"))


def _app_url(path: str) -> str:
    return os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/") + path


# -- delivery ----------------------------------------------------------------

def _smtp_send(to: str, subject: str, body: str) -> None:
    url = urlparse(os.environ["SMTP_URL"])
    msg = EmailMessage()
    msg["From"] = os.environ.get("SMTP_FROM", f"Ourogen <{SENDER}>")
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    secure = url.scheme == "smtps"
    port = url.port or (465 if secure else 587)
    host = url.hostname or "localhost"
    server: smtplib.SMTP = (smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=20)
                            if secure else smtplib.SMTP(host, port, timeout=20))
    with server:
        if not secure:
            server.starttls(context=ssl.create_default_context())
        if url.username:
            server.login(unquote(url.username), unquote(url.password or ""))
        server.send_message(msg)


def deliver(store: Store, user_id: int, subject: str, body: str) -> str:
    """Send an email to the owner. Returns the channel used, or '' if none."""
    from coworker.connectors.base import ConnectorError, Workspace

    coworker = store.get_coworker(user_id) or {}
    owner = coworker.get("owner_email") or ""
    subject = f"{SUBJECT_PREFIX} {subject}"
    if coworker.get("mode", "demo") != "live":
        store.add_item(user_id, {
            "provider": "gmail", "external_id": f"notify-{uuid.uuid4().hex[:12]}", "thread_id": f"notify-{uuid.uuid4().hex[:8]}",
            "kind": "email", "direction": "inbound", "author_name": "Ourogen", "author_email": SENDER,
            "recipients": [{"name": coworker.get("owner_name") or "", "email": owner}], "subject": subject, "body": body,
            "occurred_at": iso(), "meta": {"labels": ["INBOX", "CATEGORY_UPDATES"], "notification": True, "demo": True},
        })
        return "demo"
    if not owner:
        return ""
    mailbox = Workspace(store, user_id).email_connector()
    if mailbox is not None and mailbox.has_scope("gmail.send"):
        channel = "gmail" if mailbox.provider == "google" else "outlook"
        try:
            mailbox.send_email(store, user_id, to=[owner], subject=subject, body=body)
            return channel
        except ConnectorError as exc:
            log.warning("%s notification failed for user %s: %s", channel, user_id, exc)
    if os.environ.get("SMTP_URL"):
        try:
            _smtp_send(owner, subject, body)
            return "smtp"
        except Exception as exc:
            log.warning("smtp notification failed for user %s: %s", user_id, exc)
    return ""


def is_notification(item: dict[str, Any]) -> bool:
    """Our own notification emails, which the coworker must never act on."""
    return bool((item.get("meta") or {}).get("notification")) or str(item.get("subject") or "").startswith(SUBJECT_PREFIX)


# -- approvals ---------------------------------------------------------------

def _last(store: Store, user_id: int, kind: str) -> dict[str, Any] | None:
    return store.one("SELECT * FROM cw_notifications WHERE user_id = %s AND kind = %s ORDER BY id DESC LIMIT 1",
                     (user_id, kind))


def _record(store: Store, user_id: int, kind: str, slot: str, subject: str, count: int) -> int | None:
    """Reserve the slot before sending. None means someone else already has it."""
    try:
        return store.insert("cw_notifications", {
            "user_id": user_id, "kind": kind, "slot": slot, "subject": subject[:500], "item_count": count, "sent_at": iso(),
        })
    except IntegrityError:
        return None


def maybe_notify_approvals(store: Store, user_id: int) -> int:
    """Email the owner about new approvals if the batch window has passed.
    Returns how many actions the email covered (0 when nothing was sent)."""
    coworker = store.get_coworker(user_id) or {}
    if (coworker.get("settings") or {}).get("notify_approvals") is False or coworker.get("status") != "active":
        return 0
    now = utcnow()
    last = _last(store, user_id, "approvals")
    last_at = parse_iso(last["sent_at"]) if last else None
    interval = _interval_seconds()
    if last_at and (now - last_at).total_seconds() < interval:
        return 0
    pending = store.query(
        "SELECT id, title, created_at FROM cw_actions WHERE user_id = %s AND status = 'proposed' AND created_at > %s "
        "ORDER BY created_at, id", (user_id, last["sent_at"] if last else ""),
    )
    if not pending:
        return 0
    oldest = parse_iso(pending[0]["created_at"])
    if oldest and (now - oldest).total_seconds() < _batch_seconds():
        return 0  # keep batching
    n = len(pending)
    subject = f"{n} action{'s' if n != 1 else ''} waiting for your approval"
    slot = str(int(now.timestamp()) // max(interval, 1))
    row_id = _record(store, user_id, "approvals", slot, subject, n)
    if row_id is None:
        return 0
    from api_endpoints.coworker.email_actions import action_url

    lines = [f"• {p['title']}\n  Review and approve: {action_url(user_id, int(p['id']))}" for p in pending[:15]]
    if n > 15:
        lines.append(f"…and {n - 15} more")
    body = (f"Hi {(coworker.get('owner_name') or 'there').split(' ')[0]},\n\n"
            f"Your AI coworker has {subject.lower()}:\n\n" + "\n".join(lines) +
            f"\n\nReview them: {_app_url('/app/coworker/approvals')}\n\n"
            "Proposals expire if nobody approves them. Reply STOP to pause your coworker. "
            "Turn these emails off in Settings → Notifications.\n")
    channel = deliver(store, user_id, subject, body)
    from coworker import sms

    if sms.notify_approvals(store, user_id, pending):
        channel = f"{channel}+sms" if channel else "sms"
    from coworker import telegram

    if telegram.notify_approvals(store, user_id, pending):
        channel = f"{channel}+telegram" if channel else "telegram"
    store.update("cw_notifications", row_id, user_id, {"channel": channel or "none"})
    if channel:
        store.log(user_id, "notification", f"Emailed you about {n} pending approval{'s' if n != 1 else ''}")
    return n if channel else 0


# -- digest ------------------------------------------------------------------

def send_digest(store: Store, user_id: int, digest: dict[str, Any]) -> str:
    coworker = store.get_coworker(user_id) or {}
    if not (coworker.get("settings") or {}).get("digest_email"):
        return ""
    day = utcnow().strftime("%Y-%m-%d")
    row_id = _record(store, user_id, "digest", day, "Your daily digest", len(digest.get("executed") or []))
    if row_id is None:
        return ""

    def section(title: str, items: list[str]) -> str:
        return f"\n{title}\n" + "\n".join(f"• {i}" for i in items) + "\n" if items else ""

    body = (digest["headline"] + "\n" + section("Done", digest.get("executed") or [])
            + section("Waiting for you", digest.get("pending") or [])
            + section("Needs your attention", digest.get("attention") or [])
            + section("Briefs", digest.get("briefs") or [])
            + f"\nOpen your coworker: {_app_url('/app/coworker/activity')}\n"
            + "Reply STOP to pause your coworker.\n")
    from coworker import push

    push.send(store, user_id, "Your coworker's day", digest["headline"], {"type": "today"})
    channel = deliver(store, user_id, "Your daily digest", body)
    store.update("cw_notifications", row_id, user_id, {"channel": channel or "none"})
    return channel


def history(store: Store, user_id: int, since_hours: int = 24 * 7) -> list[dict[str, Any]]:
    since = iso(utcnow() - timedelta(hours=since_hours))
    return store.query("SELECT kind, channel, subject, item_count, sent_at FROM cw_notifications "
                       "WHERE user_id = %s AND sent_at >= %s ORDER BY id DESC", (user_id, since))


# -- reply STOP ---------------------------------------------------------------

def _first_line(body: str) -> str:
    for line in (body or "").splitlines():
        line = line.strip()
        if line and not line.startswith(">"):
            return line
    return ""


def handle_stop_replies(store: Store, user_id: int) -> bool:
    """Pause the coworker when the owner replies STOP to a notification email."""
    from coworker import executor

    coworker = store.get_coworker(user_id) or {}
    owner = (coworker.get("owner_email") or "").lower()
    if not owner:
        return False
    since = iso(utcnow() - timedelta(days=3))
    rows = store.query(
        "SELECT id, subject, body FROM cw_items WHERE user_id = %s AND kind = 'email' AND LOWER(author_email) = %s "
        "AND occurred_at >= %s AND subject LIKE %s ORDER BY id", (user_id, owner, since, f"%{SUBJECT_PREFIX}%"),
    )
    paused = False
    for r in rows:
        if _first_line(r["body"]).strip(" .!").upper() != "STOP":
            continue
        try:
            store.insert("cw_runs", {"user_id": user_id, "responsibility_id": 0, "trigger_key": f"stop:{r['id']}",
                                     "status": "done", "created_at": iso()})
        except IntegrityError:
            continue  # already handled this reply
        if (store.get_coworker(user_id) or {}).get("status") == "active":
            executor.pause(store, user_id, "you replied STOP to a notification email")
            paused = True
    return paused
