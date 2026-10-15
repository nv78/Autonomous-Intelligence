"""Tools the coworker agent can call from chat.

Read tools return data (inbound content wrapped as untrusted). Write tools
never act directly: they create proposals through ``executor.propose``,
which applies autonomy levels, hard floors, and risk checks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from coworker import (
    drafting,
    executor,
    memory,
    policy,
    responsibilities,
    scheduling,
    security,
    style,
)
from coworker.store import Store, iso, parse_iso, utcnow


@dataclass
class ToolContext:
    store: Store
    user_id: int
    chat_id: int | None = None
    cards: list[dict[str, Any]] = field(default_factory=list)


def _obj(props: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


S = {"type": "string"}
INT = {"type": "integer"}
SL = {"type": "array", "items": {"type": "string"}}

DEFINITIONS: list[dict[str, Any]] = [
    {"name": "search_memory", "description": "Search everything the coworker knows (email, Slack, meetings, docs, decisions). Returns cited snippets.",
     "input_schema": _obj({"query": S}, ["query"])},
    {"name": "who_is", "description": "Look up a person: company, role, relationship to the user, and recent interactions.",
     "input_schema": _obj({"name": S}, ["name"])},
    {"name": "account_status", "description": "Where things stand with a company or person: last message, who owes a reply, open asks, next meeting, past decisions.",
     "input_schema": _obj({"name": S}, ["name"])},
    {"name": "list_needs_reply", "description": "Email threads waiting on the user, triaged by category (sales_lead, scheduling, support, investor, candidate, partner, internal, fyi).",
     "input_schema": _obj({"category": S}, [])},
    {"name": "read_thread", "description": "Read a full email or Slack thread by thread_id.",
     "input_schema": _obj({"thread_id": S}, ["thread_id"])},
    {"name": "calendar", "description": "The user's calendar for the next N days.",
     "input_schema": _obj({"days": INT}, [])},
    {"name": "find_free_slots", "description": "Open times inside the user's working hours, across different days.",
     "input_schema": _obj({"duration_minutes": INT, "days_ahead": INT, "count": INT}, [])},
    {"name": "draft_reply", "description": "Draft a reply to the latest message in a thread, in the user's voice, grounded in memory and docs. Returns text only; use send_email to propose sending.",
     "input_schema": _obj({"thread_id": S, "instruction": S}, ["thread_id"])},
    {"name": "send_email", "description": "Propose sending an email. It goes to the user's approval inbox unless their autonomy settings allow it. Include thread_id when replying.",
     "input_schema": _obj({"to": SL, "subject": S, "body": S, "thread_id": S, "cc": SL}, ["to", "subject", "body"])},
    {"name": "post_slack", "description": "Propose posting a Slack message (channel name like 'sales' or a DM like 'dm-maya').",
     "input_schema": _obj({"channel": S, "text": S}, ["channel", "text"])},
    {"name": "schedule_meeting", "description": "Propose sending a calendar invite. start is ISO-8601 UTC.",
     "input_schema": _obj({"title": S, "attendees": SL, "start": S, "duration_minutes": INT, "description": S}, ["title", "attendees", "start"])},
    {"name": "meeting_brief", "description": "Prep brief for an upcoming meeting (the next external one if no query).",
     "input_schema": _obj({"query": S}, [])},
    {"name": "propose_responsibility", "description": "Propose taking on a standing responsibility (e.g. 'reply to inbound leads'). The user confirms it as a card.",
     "input_schema": _obj({"request": S}, ["request"])},
    {"name": "list_responsibilities", "description": "Responsibilities the coworker currently owns.",
     "input_schema": _obj({}, [])},
    {"name": "pending_approvals", "description": "Actions waiting for the user's approval.",
     "input_schema": _obj({}, [])},
    {"name": "remember_preference", "description": "Save a writing or working preference the user just stated (e.g. 'never use exclamation points').",
     "input_schema": _obj({"rule": S}, ["rule"])},
]


def _card(ctx: ToolContext, action: dict[str, Any]) -> dict[str, Any]:
    card = {"type": "action", "id": action["id"]}
    ctx.cards.append(card)
    return card


def _action_result(action: dict[str, Any]) -> dict[str, Any]:
    status = action["status"]
    if status == "proposed":
        note = "Waiting for the user's approval in chat and the approval inbox. Tell the user it's ready for review; do not say it was sent."
    elif status == "executed":
        note = "Done (allowed by the user's autonomy settings)."
    else:
        note = f"Status: {status}."
    return {"action_id": action["id"], "status": status, "note": note, "risks": action.get("risk") or []}


def run(name: str, args: dict[str, Any], ctx: ToolContext) -> tuple[Any, str]:
    """Execute a tool. Returns (result for the model, one-line summary for the UI)."""
    s, uid = ctx.store, ctx.user_id
    if name == "search_memory":
        hits = memory.recall(s, uid, args.get("query", ""), k=6)
        for h in hits:
            if h.get("snippet") and h.get("direction") == "inbound":
                h["snippet"] = security.wrap_untrusted(h["snippet"], h.get("provider") or "item")
        return hits, f"Searched memory for “{args.get('query', '')}” ({len(hits)} results)"
    if name == "who_is":
        found = memory.who_is(s, uid, args.get("name", ""))
        return found or {"found": False}, f"Looked up {args.get('name', '')}"
    if name == "account_status":
        st = memory.account_status(s, uid, args.get("name", ""))
        return st, f"Checked status with {st.get('company') or args.get('name', '')}"
    if name == "list_needs_reply":
        rows = memory.needs_reply(s, uid)
        if args.get("category"):
            rows = [r for r in rows if r["category"] == args["category"]]
        for r in rows:
            r["snippet"] = security.wrap_untrusted(r.get("snippet") or "", "email")
        return rows[:15], f"Checked what needs a reply ({len(rows)} threads)"
    if name == "read_thread":
        thread = s.thread(uid, args.get("thread_id", ""))
        out = [{
            "id": t["id"], "from": f"{t['author_name']} <{t['author_email']}>", "date": t["occurred_at"],
            "subject": t["subject"], "direction": t["direction"],
            "body": security.wrap_untrusted(t["body"] or "", t["provider"]) if t["direction"] == "inbound" else t["body"],
        } for t in thread[-12:]]
        return out, f"Read thread ({len(out)} messages)"
    if name == "calendar":
        days = int(args.get("days") or 7)
        now = utcnow()
        tz = scheduling.tz_for(s.get_coworker(uid) or {})
        events = s.query(
            "SELECT * FROM cw_items WHERE user_id = %s AND kind = 'event' AND occurred_at >= %s AND occurred_at < %s ORDER BY occurred_at",
            (uid, iso(now - timedelta(hours=1)), iso(now + timedelta(days=days))),
        )
        out = []
        for e in events:
            when = parse_iso(e["occurred_at"])
            out.append({"id": e["id"], "title": e["subject"], "when": scheduling.label(when, tz) if when else e["occurred_at"],
                        "start": e["occurred_at"], "attendees": [a.get("email") for a in e.get("recipients") or []],
                        "location": (e.get("meta") or {}).get("location", "")})
        return out, f"Checked your calendar ({len(out)} events)"
    if name == "find_free_slots":
        slots = scheduling.free_slots(s, uid, int(args.get("duration_minutes") or 30), int(args.get("days_ahead") or 7),
                                      int(args.get("count") or 3))
        return slots, f"Found {len(slots)} open slots"
    if name == "draft_reply":
        thread = s.thread(uid, args.get("thread_id", ""))
        if not thread:
            return {"error": "thread not found"}, "Thread not found"
        last_in = next((t for t in reversed(thread) if t["direction"] == "inbound"), thread[-1])
        category = memory.classify(last_in, memory.company_context(s, uid))
        draft = drafting.compose_reply(s, uid, thread, category, args.get("instruction", ""))
        return draft, f"Drafted a reply to {last_in['author_name']}"
    if name == "send_email":
        payload = {k: args[k] for k in ("to", "cc", "subject", "body", "thread_id") if args.get(k)}
        source = None
        if payload.get("thread_id"):
            thread = s.thread(uid, payload["thread_id"])
            source = next((t["id"] for t in reversed(thread) if t["direction"] == "inbound"), None)
        action = executor.propose(s, uid, "email.send", payload, title=f"Email {', '.join(payload['to'])}: {payload['subject']}",
                                  reasoning=args.get("reasoning", "You asked for this in chat."), source_item_id=source,
                                  chat_id=ctx.chat_id, requested_in_chat=True)
        _card(ctx, action)
        return _action_result(action), f"Prepared an email to {', '.join(payload['to'])}"
    if name == "post_slack":
        channel = str(args.get("channel", "")).lstrip("#")
        action = executor.propose(s, uid, "slack.post", {"channel": channel, "text": args.get("text", "")},
                                  title=f"Slack #{channel}", reasoning="You asked for this in chat.", chat_id=ctx.chat_id,
                                  requested_in_chat=True)
        _card(ctx, action)
        return _action_result(action), f"Prepared a Slack message to #{channel}"
    if name == "schedule_meeting":
        start = parse_iso(args.get("start"))
        if not start:
            return {"error": "start must be ISO-8601"}, "Couldn't read the meeting time"
        end = start + timedelta(minutes=int(args.get("duration_minutes") or 30))
        payload = {"title": args.get("title", "Meeting"), "attendees": args.get("attendees") or [], "start": iso(start),
                   "end": iso(end), "description": args.get("description", "")}
        tz = scheduling.tz_for(s.get_coworker(uid) or {})
        action = executor.propose(s, uid, "calendar.create", payload,
                                  title=f"Invite {', '.join(payload['attendees'])}: {payload['title']} ({scheduling.label(start, tz)})",
                                  reasoning="You asked for this in chat.", chat_id=ctx.chat_id, requested_in_chat=True)
        _card(ctx, action)
        return _action_result(action), "Prepared a calendar invite"
    if name == "meeting_brief":
        event = _find_event(s, uid, args.get("query", ""))
        if not event:
            return {"error": "no matching upcoming meeting"}, "No matching meeting found"
        brief = drafting.meeting_brief(s, uid, event)
        ctx.cards.append({"type": "brief", "title": event["subject"]})
        return brief, f"Prepared a brief for {event['subject']}"
    if name == "propose_responsibility":
        spec = responsibilities.proposal_payload(args.get("request", ""))
        action = executor.propose(s, uid, "responsibility.create", spec, title=f"New responsibility: {spec['name']}",
                                  reasoning=spec["description"], chat_id=ctx.chat_id, requested_in_chat=True)
        _card(ctx, action)
        return {**_action_result(action), "spec": spec}, f"Proposed a responsibility: {spec['name']}"
    if name == "list_responsibilities":
        rows = s.query("SELECT id, name, template, autonomy, enabled, runs FROM cw_responsibilities WHERE user_id = %s", (uid,))
        return rows, f"Listed responsibilities ({len(rows)})"
    if name == "pending_approvals":
        rows = s.query("SELECT id, type, title, created_at FROM cw_actions WHERE user_id = %s AND status = 'proposed' ORDER BY id DESC",
                       (uid,))
        return rows, f"Checked pending approvals ({len(rows)})"
    if name == "remember_preference":
        coworker = s.get_coworker(uid) or {}
        profile = style.add_rule(coworker.get("style_profile") or {}, args.get("rule", ""))
        s.update_coworker(uid, style_profile=profile)
        return {"saved": True}, "Saved your preference"
    return {"error": f"unknown tool {name}"}, f"Unknown tool {name}"


def _find_event(s: Store, uid: int, query: str) -> dict[str, Any] | None:
    ctx = memory.company_context(s, uid)
    events = scheduling.upcoming_events(s, uid, hours=24 * 14)
    q = query.lower().strip()
    if q:
        for e in events:
            hay = f"{e['subject']} {' '.join((a.get('name') or '') + ' ' + (a.get('email') or '') for a in e.get('recipients') or [])}".lower()
            if any(tok in hay for tok in q.split() if len(tok) > 2):
                return e
    for e in events:
        if any(memory.domain_of(a.get("email", "")) not in (ctx["domain"], "") for a in e.get("recipients") or []):
            return e
    return events[0] if events else None


def labels() -> dict[str, str]:
    return {k: v["label"] for k, v in policy.ACTION_TYPES.items()}
