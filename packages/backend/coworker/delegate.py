"""Things you hand off in one chat message.

* ``join_meeting``: "Join my 2pm with Dana and pitch the pilot." The
  coworker joins (meeting bot when configured; otherwise it runs the call
  in the browser studio), follows your context, and posts the summary
  and a drafted follow-up back into the chat when the call ends.
* ``reply_to_emails``: "Reply to my unanswered leads." It drafts a reply
  for each waiting thread and puts every one in the chat for approval.
  Once sent, the chat shows exactly what went out.
* ``day``: everything the coworker did on a given day, for the Today view
  and "what did you do today?".
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from coworker import drafting, executor, meetings, memory, scheduling
from coworker.store import Store, iso, parse_iso, utcnow

URL_RE = re.compile(r"https://[^\s)>\]]+")
HANDLE_BY_DEFAULT = ("sales_lead", "scheduling", "support", "partner", "candidate", "investor")


class DelegateError(Exception):
    pass


def _match_event(store: Store, user_id: int, hint: str) -> dict[str, Any] | None:
    """Find the calendar event the user means ('my 2pm', 'the Globex QBR', 'with Dana')."""
    events = scheduling.upcoming_events(store, user_id, hours=24 * 7)
    if not events:
        return None
    low = (hint or "").lower()
    best, best_score = None, 0
    for e in events:
        words = {w for w in re.findall(r"[a-z]{3,}", f"{e.get('subject', '')} {' '.join(a.get('name') or a.get('email', '') for a in e.get('recipients') or [])}".lower())}
        score = sum(1 for w in words if w in low)
        if score > best_score:
            best, best_score = e, score
    return best


def join_meeting(store: Store, user_id: int, *, chat_id: int | None, meeting_url: str = "", context: str = "",
                 title: str = "", prospect_name: str = "", company: str = "", prospect_email: str = "") -> dict[str, Any]:
    """Send the coworker to a meeting. Returns {meeting, how, event}."""
    coworker = store.get_coworker(user_id) or {}
    if coworker.get("status") != "active":
        raise DelegateError("Your coworker is paused. Resume it first.")
    event = None
    if not meeting_url:
        event = _match_event(store, user_id, f"{title} {context} {prospect_name} {company}")
        if event:
            loc = (event.get("meta") or {}).get("location") or ""
            meeting_url = (URL_RE.search(loc) or URL_RE.search(event.get("body") or "") or [""])[0] if loc or event.get("body") else ""
            title = title or event.get("subject") or ""
            guest = next((a for a in event.get("recipients") or [] if memory.domain_of(a.get("email", "")) !=
                          memory.company_context(store, user_id)["domain"]), None)
            if guest:
                prospect_name = prospect_name or guest.get("name") or ""
                prospect_email = prospect_email or guest.get("email") or ""
    from coworker.connectors import recall

    use_bot = bool(meeting_url) and recall.is_configured()
    if use_bot:
        meeting = meetings.start(store, user_id, mode="bot", title=title, prospect_name=prospect_name, company=company,
                                 prospect_email=prospect_email, meeting_url=meeting_url, context=context, chat_id=chat_id)
        first = (coworker.get("owner_name") or "").split(" ")[0] or "Your"
        from itsdangerous import URLSafeSerializer

        secret = os.environ.get("JWT_SECRET_KEY", "dev")
        try:
            from flask import current_app, has_app_context

            if has_app_context():
                secret = str(current_app.config.get("JWT_SECRET_KEY") or secret)
        except ImportError:  # pragma: no cover
            pass
        token = URLSafeSerializer(secret, salt="recall-webhook").dumps({"u": user_id, "m": meeting["id"]})
        hook = f"{os.environ.get('BACKEND_URL', 'http://localhost:5000').rstrip('/')}/api/coworker/meetings/recall/webhook?token={token}"
        bot_id = recall.create_bot(meeting_url, f"{first}'s AI coworker (Ourogen)",
                                   meetings.disclosure_line(store, user_id) + " Say 'please leave' and I will.", hook)
        store.update("cw_meetings", meeting["id"], user_id, {"bot_id": bot_id})
        how = "bot"
        from coworker import push

        push.send(store, user_id, f"Your coworker joined: {meeting['title']}", "Tap to watch, whisper, or take over.",
                  {"type": "call", "meetingId": meeting["id"]})
    else:
        # No meeting bot here: run it as a browser call the user (or the guest) can join from the call studio.
        meeting = meetings.start(store, user_id, mode="live_call", title=title, prospect_name=prospect_name,
                                 company=company, prospect_email=prospect_email, meeting_url=meeting_url,
                                 context=context, chat_id=chat_id)
        how = "studio"
    store.log(user_id, "meeting", f"Sent to a meeting from chat: {meeting['title']}", {"meeting_id": meeting["id"], "how": how},
              chat_id=chat_id)
    return {"meeting": store.get("cw_meetings", meeting["id"], user_id) or meeting, "how": how, "event": event}


def run_demo_call(store: Store, user_id: int, *, chat_id: int | None, context: str = "") -> dict[str, Any]:
    """Demo workspace: run a full scripted call so the whole loop is visible."""
    meeting = meetings.start(store, user_id, mode="simulated", persona="northwind", context=context, chat_id=chat_id)
    while True:
        line = meetings.next_prospect_line(store.get("cw_meetings", meeting["id"], user_id) or meeting)
        if not line:
            break
        result = meetings.respond(store, user_id, meeting["id"], line)
        if result.get("ended"):
            break
    finished = meetings.finish(store, user_id, meeting["id"])
    return {"meeting": finished, "how": "demo"}


def reply_to_emails(store: Store, user_id: int, *, chat_id: int | None, category: str = "", limit: int = 5,
                    instruction: str = "", who: str = "") -> list[dict[str, Any]]:
    """Draft and propose a reply for each waiting thread. Returns the actions."""
    rows = memory.needs_reply(store, user_id, include_internal=False)
    if category:
        rows = [r for r in rows if r["category"] == category]
    else:
        rows = [r for r in rows if r["category"] in HANDLE_BY_DEFAULT]
    if who:
        low = who.lower()
        rows = [r for r in rows if low in f"{r.get('from', '')} {r.get('from_email', '')} {r.get('title', '')}".lower()]
    existing = {a["source_item_id"] for a in store.query(
        "SELECT source_item_id FROM cw_actions WHERE user_id = %s AND status IN ('proposed','approved','executing') "
        "AND source_item_id IS NOT NULL", (user_id,))}
    actions = []
    for r in rows[:max(1, min(limit, 15))]:
        if r["id"] in existing:
            continue  # already waiting for approval; never draft the same reply twice
        thread = store.thread(user_id, r["thread_id"])
        draft = drafting.compose_reply(store, user_id, thread, r["category"], instruction)
        actions.append(executor.propose(
            store, user_id, "email.send",
            {"to": draft["to"], "subject": draft["subject"], "body": draft["body"], "thread_id": draft["thread_id"]},
            title=f"Reply to {r.get('from') or draft['to'][0]}: {draft['subject']}"[:200], reasoning=draft["reasoning"],
            source_item_id=r["id"], chat_id=chat_id, requested_in_chat=True,
        ))
    return actions


# -- the day ------------------------------------------------------------------

def _day_bounds(store: Store, user_id: int, date: str | None) -> tuple[datetime, datetime, str]:
    tz: ZoneInfo = scheduling.tz_for(store.get_coworker(user_id) or {})
    local_now = utcnow().astimezone(tz)
    day = datetime.strptime(date, "%Y-%m-%d").date() if date else local_now.date()
    start = datetime(day.year, day.month, day.day, tzinfo=tz)
    return start, start + timedelta(days=1), day.isoformat()


def day(store: Store, user_id: int, date: str | None = None) -> dict[str, Any]:
    """Everything the coworker did (and has waiting) on one day, newest first."""
    start, end, label = _day_bounds(store, user_id, date)
    lo, hi = iso(start), iso(end)
    entries: list[dict[str, Any]] = []
    for m in store.query("SELECT * FROM cw_meetings WHERE user_id = %s AND started_at >= %s AND started_at < %s",
                         (user_id, lo, hi)):
        summary = meetings.summary_of(m) or {}
        entries.append({"kind": "meeting", "id": m["id"], "at": m["started_at"], "title": m["title"],
                        "status": m["status"], "score": summary.get("score"), "hot": summary.get("hot"),
                        "detail": (summary.get("text") or "")[:400], "chatId": (m.get("answers") or {}).get("chat_id")})
    for a in store.query("SELECT * FROM cw_actions WHERE user_id = %s AND ((executed_at >= %s AND executed_at < %s) "
                         "OR (status = 'proposed' AND created_at >= %s AND created_at < %s))", (user_id, lo, hi, lo, hi)):
        p = a.get("payload") or {}
        entries.append({"kind": "action", "id": a["id"], "at": a.get("executed_at") or a["created_at"], "title": a["title"],
                        "status": a["status"], "type": a["type"], "to": p.get("to") or ([f"#{p['channel']}"] if p.get("channel") else []),
                        "detail": (p.get("body") or p.get("text") or "")[:400], "chatId": a.get("chat_id")})
    for row in store.query("SELECT * FROM cw_activity WHERE user_id = %s AND created_at >= %s AND created_at < %s AND kind IN "
                           "('brief','escalation','security','digest')", (user_id, lo, hi)):
        entry = {"kind": row["kind"], "id": row["id"], "at": row["created_at"], "title": row["summary"],
                 "status": "", "detail": "", "chatId": row.get("chat_id")}
        aj = (row.get("detail") or {}).get("autojoin")
        if aj:
            from coworker import autojoin

            entry["autojoin"] = {"eventId": aj["event_id"],
                                 "state": autojoin.state(store, user_id, aj["event_id"], bool(aj.get("will_join")))}
        entries.append(entry)
    entries.sort(key=lambda e: e["at"] or "", reverse=True)
    sent = [e for e in entries if e["kind"] == "action" and e["status"] == "executed"]
    pending = [e for e in entries if e["kind"] == "action" and e["status"] == "proposed"]
    calls = [e for e in entries if e["kind"] == "meeting"]
    upcoming = [{"title": e.get("subject"), "at": e.get("occurred_at"), "id": e.get("id")}
                for e in scheduling.upcoming_events(store, user_id, hours=24)
                if (parse_iso(e.get("occurred_at")) or utcnow()) < end] if label == _day_bounds(store, user_id, None)[2] else []
    def n(count: int, word: str) -> str:
        return f"{count} {word}{'' if count == 1 else 's'}"
    headline = (f"{n(len(sent), 'thing')} done, {n(len(calls), 'call')}, {n(len(pending), 'item')} waiting for you."
                if entries else "Nothing yet today.")
    return {"date": label, "headline": headline, "entries": entries, "upcoming": upcoming,
            "counts": {"done": len(sent), "calls": len(calls), "pending": len(pending)}}
