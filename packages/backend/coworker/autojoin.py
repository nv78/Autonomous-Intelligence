"""Auto-join: the coworker takes the user's external calls without being asked each time.

A standing "Join my external meetings" responsibility watches the calendar.
For each matching event with a video link:

1. About ``minutes_before`` the start, it opens a chat named after the
   meeting with a prep brief, and tells the user by push and email with a
   one-tap Skip. Anything the user writes in that chat before the call
   becomes context for the call.
2. At the start time, the meeting bot joins (disclosure, consent, then the
   call), and the summary and follow-up post back into that same chat.

Skipping claims the join step, so the bot never joins a skipped meeting.
Without a meeting bot configured, the brief still arrives but nothing joins.
"""
from __future__ import annotations

import os
import re
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

from coworker import drafting, memory
from coworker.store import IntegrityError, Store, iso, parse_iso, utcnow

JOIN_LEAD = timedelta(minutes=2)  # join slightly early, like a person would
JOIN_GRACE = timedelta(minutes=10)  # still join if the worker was a little late
SKIP_SALT = "coworker-autojoin-skip"


def meeting_url(event: dict[str, Any]) -> str:
    from coworker.delegate import URL_RE

    for text in ((event.get("meta") or {}).get("location") or "", event.get("body") or ""):
        found = URL_RE.search(text)
        if found:
            return found.group(0)
    return ""


def _external_guests(store: Store, user_id: int, event: dict[str, Any]) -> list[dict[str, Any]]:
    ctx = memory.company_context(store, user_id)
    owner = (ctx.get("owner_email") or "").lower()
    return [a for a in event.get("recipients") or []
            if (a.get("email") or "").lower() not in ("", owner) and memory.domain_of(a.get("email", "")) != ctx["domain"]]


def matches(store: Store, user_id: int, event: dict[str, Any], spec: dict[str, Any]) -> bool:
    if "T" not in (event.get("occurred_at") or "") or not meeting_url(event):
        return False  # all-day entries and events without a call link
    if spec.get("external_only", True) and not _external_guests(store, user_id, event):
        return False
    keywords = [k.lower() for k in spec.get("keywords") or []]
    return not keywords or any(k in (event.get("subject") or "").lower() for k in keywords)


def _claim(store: Store, user_id: int, resp_id: int, key: str, status: str = "running", summary: str = "") -> int | None:
    try:
        return store.insert("cw_runs", {"user_id": user_id, "responsibility_id": resp_id, "trigger_key": key,
                                        "status": status, "summary": summary, "created_at": iso()})
    except IntegrityError:
        return None


def _run(store: Store, user_id: int, resp_id: int, key: str) -> dict[str, Any] | None:
    return store.one("SELECT * FROM cw_runs WHERE user_id = %s AND responsibility_id = %s AND trigger_key = %s",
                     (user_id, resp_id, key))


def skip_token(user_id: int, event_id: str) -> str:
    from itsdangerous import URLSafeTimedSerializer

    return URLSafeTimedSerializer(_secret(), salt=SKIP_SALT).dumps({"u": int(user_id), "e": event_id})


def read_skip_token(token: str, max_age: int = 2 * 86400) -> tuple[int, str] | None:
    from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

    try:
        data = URLSafeTimedSerializer(_secret(), salt=SKIP_SALT).loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    return int(data["u"]), str(data["e"])


def _secret() -> str:
    try:
        from flask import current_app, has_app_context

        if has_app_context() and current_app.config.get("JWT_SECRET_KEY"):
            return str(current_app.config["JWT_SECRET_KEY"])
    except ImportError:  # pragma: no cover
        pass
    return os.environ.get("JWT_SECRET_KEY", "dev")


def skip_url(user_id: int, event_id: str) -> str:
    base = os.environ.get("BACKEND_URL", "http://localhost:5000").rstrip("/")
    return f"{base}/api/coworker/autojoin/skip/{skip_token(user_id, event_id)}"


def responsibility(store: Store, user_id: int) -> dict[str, Any] | None:
    return store.one("SELECT * FROM cw_responsibilities WHERE user_id = %s AND template = 'auto_join' AND enabled = 1 "
                     "ORDER BY id LIMIT 1", (user_id,))


def skip(store: Store, user_id: int, event_id: str) -> bool:
    """Don't join this meeting. Returns False if the bot already joined."""
    resp = responsibility(store, user_id)
    if not resp:
        return False
    key = f"autojoin:{event_id}"
    if _claim(store, user_id, int(resp["id"]), key, status="skipped", summary="skipped by you") is None:
        run = _run(store, user_id, int(resp["id"]), key) or {}
        return run.get("status") == "skipped"
    event = store.one("SELECT subject FROM cw_items WHERE user_id = %s AND kind = 'event' AND external_id = %s",
                      (user_id, event_id)) or {}
    store.log(user_id, "meeting", f"Won't join {event.get('subject') or 'that meeting'}: you skipped it", {"event_id": event_id})
    return True


def upcoming(store: Store, user_id: int, minutes_before: int) -> list[dict[str, Any]]:
    now = utcnow()
    return store.query(
        "SELECT * FROM cw_items WHERE user_id = %s AND kind = 'event' AND occurred_at >= %s AND occurred_at < %s "
        "ORDER BY occurred_at", (user_id, iso(now - JOIN_GRACE), iso(now + timedelta(minutes=minutes_before))),
    )


def run(store: Store, user_id: int, resp: dict[str, Any]) -> list[str]:
    from coworker.connectors import recall

    spec = resp.get("trigger_spec") or {}
    minutes_before = int(spec.get("minutes_before", 30))
    out: list[str] = []
    now = utcnow()
    for event in upcoming(store, user_id, minutes_before):
        if not matches(store, user_id, event, spec):
            continue
        start = parse_iso(event["occurred_at"])
        if start is None:
            continue
        until = start - now
        if until > timedelta(0) and _claim(store, user_id, int(resp["id"]), f"autojoin-brief:{event['external_id']}") is not None:
            out.append(_announce(store, user_id, resp, event, can_join=recall.is_configured()))
        if recall.is_configured() and until <= JOIN_LEAD and -until <= JOIN_GRACE:
            joined = _join(store, user_id, resp, event)
            if joined:
                out.append(joined)
    return out


def _announce(store: Store, user_id: int, resp: dict[str, Any], event: dict[str, Any], can_join: bool) -> str:
    from coworker import notify, push, reports

    brief = drafting.meeting_brief(store, user_id, event)
    subject = event.get("subject") or "your meeting"
    when = brief["event"]["label"]
    if can_join:
        plan = (f"I'll join **{subject}** at {when} as your disclosed AI coworker, ask for consent to take notes, "
                "and post the summary and a follow-up draft here when it ends.\n\n"
                "Anything I should push for or avoid? Reply in this chat before the call. "
                f"Changed your mind? [Skip this one]({skip_url(user_id, event['external_id'])}).")
    else:
        plan = ("A meeting bot isn't set up on this server, so I can't join this one for you. "
                "Here's your brief so you walk in prepared.")
    chat_id = reports.new_chat(user_id, f"📞 {subject}"[:120], f"{brief['markdown']}\n\n{plan}")
    claimed = _run(store, user_id, int(resp["id"]), f"autojoin-brief:{event['external_id']}")
    if claimed:
        store.update("cw_runs", int(claimed["id"]), None, {"status": "done", "summary": f"chat:{chat_id or ''}"})
    store.log(user_id, "brief", f"Prep brief ready: {subject}",
              {"brief": brief, "autojoin": {"event_id": event["external_id"], "will_join": can_join}}, chat_id=chat_id)
    if can_join:
        push.send(store, user_id, f"Joining {subject} at {when}", "Your coworker will take this call. Open to add context or skip.",
                  {"type": "autojoin", "eventId": event["external_id"], "chatId": chat_id})
        notify.deliver(store, user_id, f"I'll join {subject} at {when}",
                       f"{brief['markdown']}\n\nI'll join as your disclosed AI coworker and send you the summary after.\n\n"
                       f"Skip this one: {skip_url(user_id, event['external_id'])}")
    return f"Prepared a brief for {subject}" + (" and scheduled to join" if can_join else "")


def _join(store: Store, user_id: int, resp: dict[str, Any], event: dict[str, Any]) -> str | None:
    from coworker import delegate, push, reports
    from coworker.connectors.base import ConnectorError

    key = f"autojoin:{event['external_id']}"
    run_id = _claim(store, user_id, int(resp["id"]), key)
    if run_id is None:
        return None  # already joined, or the user skipped it
    brief_run = _run(store, user_id, int(resp["id"]), f"autojoin-brief:{event['external_id']}") or {}
    summary = str(brief_run.get("summary") or "")
    chat_id = int(summary[5:]) if summary.startswith("chat:") and summary[5:].isdigit() else None
    guests = _external_guests(store, user_id, event)
    context = "\n".join(filter(None, [resp.get("instruction") or "", _chat_context(user_id, chat_id)]))
    try:
        result = delegate.join_meeting(store, user_id, chat_id=chat_id, meeting_url=meeting_url(event), context=context,
                                       title=event.get("subject") or "", prospect_name=(guests[0].get("name") or "") if guests else "",
                                       prospect_email=(guests[0].get("email") or "") if guests else "")
    except (delegate.DelegateError, ConnectorError) as exc:
        store.update("cw_runs", run_id, None, {"status": "failed", "summary": str(exc)[:500]})
        store.log(user_id, "escalation", f"Couldn't join {event.get('subject')}: {exc}", {"event_id": event["external_id"]})
        push.send(store, user_id, f"Couldn't join {event.get('subject')}", str(exc)[:200], {"type": "autojoin_failed"})
        reports.post(user_id, chat_id, f"I couldn't join: {exc}. You may want to take this one yourself.")
        return None
    store.update("cw_runs", run_id, None, {"status": "done", "summary": f"meeting:{result['meeting']['id']}"})
    reports.post(user_id, chat_id, f"Joining now. {reports.marker({'type': 'meeting', 'id': result['meeting']['id']})}")
    return f"Joined {event.get('subject')}"


def _chat_context(user_id: int, chat_id: int | None) -> str:
    """What the user wrote in the meeting's chat before the call."""
    if not chat_id:
        return ""
    try:
        from database.db import get_connection, get_messages

        cnx = get_connection()
        try:
            notes = [m["content"] for m in get_messages(cnx, chat_id) if m.get("role") == "user"]
        finally:
            cnx.close()
    except Exception:
        return ""
    return ("Notes from the user for this call: " + " ".join(notes))[:2000] if notes else ""


SKIP_RE = re.compile(r"\b(?:skip|cancel|don'?t join|do not join|no need to join|i'?ll (?:take|join|do) (?:it|this|that)"
                     r"|i will (?:take|join|do) (?:it|this|that)|leave it)\b", re.I)


def pending_for_chat(store: Store, user_id: int, chat_id: int) -> dict[str, Any] | None:
    """The upcoming auto-join this chat was opened for, until the bot has joined (or it was skipped)."""
    row = store.one("SELECT * FROM cw_runs WHERE user_id = %s AND trigger_key LIKE %s AND summary = %s ORDER BY id DESC LIMIT 1",
                    (user_id, "autojoin-brief:%", f"chat:{chat_id}"))
    if not row:
        return None
    event_id = row["trigger_key"].split(":", 1)[1]
    if _run(store, user_id, int(row["responsibility_id"]), f"autojoin:{event_id}"):
        return None  # joined, skipped, or failed: the chat is an ordinary chat again
    return {"event_id": event_id, "responsibility_id": int(row["responsibility_id"])}


def chat_turn(store: Store, user_id: int, pending: dict[str, Any], message: str) -> Iterator[tuple[str, Any]]:
    """Replies in a meeting's chat before the call: notes for the call, or a skip."""
    if SKIP_RE.search(message):
        skip(store, user_id, pending["event_id"])
        yield ("text", "Okay, I won't join this one. The brief above is yours to keep.")
        return
    yield ("text", "Got it. I'll bring that into the call. Anything else, add it here before it starts.")


def state(store: Store, user_id: int, event_id: str, will_join: bool = True) -> str:
    """scheduled · joined · skipped · failed · brief_only, for the Today view."""
    if not will_join:
        return "brief_only"
    resp = responsibility(store, user_id)
    run = _run(store, user_id, int(resp["id"]), f"autojoin:{event_id}") if resp else None
    if not run:
        return "scheduled" if resp else "brief_only"
    return {"skipped": "skipped", "failed": "failed"}.get(run["status"], "joined")
