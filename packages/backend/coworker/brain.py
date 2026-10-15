"""The coworker's reasoning loop for chat.

``run_turn`` yields UI events as the coworker works:

* ``("tool", {...})``   a tool call with a one-line summary
* ``("text", "...")``   reply text
* ``("card", {...})``   an action card (approval) or a brief

With an Anthropic key it runs a manual tool-use loop against Claude. The
assistant content blocks are passed back exactly as received, so thinking
and fallback blocks round-trip correctly. Without a key, an offline
planner maps the common delegation requests onto the same tools, so the
product is fully testable with no API access.
"""
from __future__ import annotations

import json
import re
from collections.abc import Generator
from typing import Any

from coworker import drafting, llm, memory, responsibilities, scheduling, security, tools
from coworker.store import Store, utcnow

MAX_ITERATIONS = 10
Event = tuple[str, Any]


def system_prompt(store: Store, user_id: int) -> str:
    coworker = store.get_coworker(user_id) or {}
    ctx = memory.company_context(store, user_id)
    owner = coworker.get("owner_name") or "the user"
    first = owner.split(" ")[0]
    tz = scheduling.tz_for(coworker)
    now = utcnow().astimezone(tz)
    st = (coworker.get("style_profile") or {}).get("summary", "")
    feedback = [m["title"] for m in store.memories(user_id, kind="feedback")[:8]]
    mode = "a fictional demo workspace" if coworker.get("mode") == "demo" else "their real accounts"
    return f"""You are {coworker.get('display_name') or f"{first}'s AI coworker"}, the AI coworker of {owner} at {ctx['name'] or 'their company'}.
{first} talks to you in this chat to hand off work. You have access to {first}'s email, Slack, calendar, docs, and memory of past work ({mode}).

How you work:
- Do the work, don't just describe it. Look things up with tools before answering questions about people, deals, or threads.
- Write tools (send_email, post_slack, schedule_meeting, propose_responsibility) create proposals. Most wait for {first}'s approval as a card in this chat. Never say something was sent unless the tool result says it was executed.
- When {first} asks you to take something off their plate going forward ("from now on", "handle", "every time"), use propose_responsibility.
- "Join my call / go to the meeting / take my 2pm" means join_meeting, with {first}'s instructions as context. You'll post the summary here afterward.
- "Join all my external calls / take every intro call from now on" is a standing job: use propose_responsibility (it auto-joins matching meetings, with a brief and a skip link before each).
- "Reply to my emails / leads / customers" means reply_to_emails: one draft per waiting thread, each a card here. Once sent, this chat shows exactly what went out.
- "What did you do today?" means my_day.
- Cite where facts come from (who said it and when). If you don't know, say so; never invent prices, dates, or commitments.
- You always act as {first}'s disclosed AI. Never claim to be {first} or a human.
- Keep replies short and skimmable. Use the user's first name sparingly.

{first}'s writing style (use it for anything you draft in their voice): {st or 'not learned yet; write plainly and briefly.'}
Feedback {first} gave on past drafts: {'; '.join(feedback) or 'none yet'}
{(coworker.get('persona') or '').strip()}

Today is {now.strftime('%A, %B %d, %Y')}, {now.strftime('%I:%M %p').lstrip('0')} {now.tzname()} ({tz.key}).

{security.SYSTEM_RULES}"""


def strip_markers(content: str) -> str:
    return "\n".join(line for line in content.splitlines() if not line.startswith(":::cw ")).strip()


def run_turn(store: Store, user_id: int, chat_id: int | None, message: str,
             history: list[dict[str, str]] | None = None) -> Generator[Event, None, None]:
    ctx = tools.ToolContext(store=store, user_id=user_id, chat_id=chat_id)
    if llm.available(user_id):
        yield from _llm_turn(ctx, message, history or [])
    else:
        yield from _offline_turn(ctx, message)


# ---------------------------------------------------------------------------
# Claude tool-use loop
# ---------------------------------------------------------------------------

def _llm_turn(ctx: tools.ToolContext, message: str, history: list[dict[str, str]]) -> Generator[Event, None, None]:
    system = system_prompt(ctx.store, ctx.user_id)
    messages: list[dict[str, Any]] = []
    for h in history[-20:]:
        content = strip_markers(h.get("content", ""))
        if content and h.get("role") in ("user", "assistant"):
            if messages and messages[-1]["role"] == h["role"]:
                messages[-1]["content"] += "\n\n" + content
            else:
                messages.append({"role": h["role"], "content": content})
    if messages and messages[0]["role"] != "user":
        messages.pop(0)
    if messages and messages[-1]["role"] == "user":
        messages[-1]["content"] += "\n\n" + message
    else:
        messages.append({"role": "user", "content": message})

    for _ in range(MAX_ITERATIONS):
        response = llm.create_message(system=system, messages=messages, tools=tools.DEFINITIONS, user_id=ctx.user_id)
        stop = response.get("stop_reason")
        if stop == "refusal":
            yield ("text", "I can't help with that request.")
            return
        blocks: list[dict[str, Any]] = response.get("content", [])
        messages.append({"role": "assistant", "content": blocks})
        tool_results = []
        for block in blocks:
            if block.get("type") == "text" and block.get("text"):
                yield ("text", block["text"])
            elif block.get("type") == "tool_use":
                name, args = block["name"], block.get("input") or {}
                if not isinstance(args, dict):
                    tool_results.append({"type": "tool_result", "tool_use_id": block["id"], "is_error": True,
                                         "content": "Invalid tool input; send a JSON object."})
                    continue
                before = len(ctx.cards)
                try:
                    result, summary = tools.run(name, args, ctx)
                    is_error = isinstance(result, dict) and "error" in result
                except Exception as exc:  # a tool failure must not kill the turn
                    result, summary, is_error = {"error": str(exc)}, f"{name} failed", True
                yield ("tool", {"name": name, "summary": summary})
                for card in ctx.cards[before:]:
                    yield ("card", card)
                if name == "meeting_brief" and not is_error:
                    yield ("text", "\n\n" + result.get("markdown", "") + "\n\n")
                tool_results.append({"type": "tool_result", "tool_use_id": block["id"],
                                     "content": json.dumps(result, default=str)[:30000], "is_error": is_error})
        if stop == "tool_use" and tool_results:
            messages.append({"role": "user", "content": tool_results})
            continue
        if stop == "pause_turn":
            continue
        if stop == "max_tokens":
            yield ("text", "\n\n(I ran out of room in that answer. Ask me to continue.)")
        return
    yield ("text", "\n\nI stopped after several steps. Tell me how you'd like to proceed.")


# ---------------------------------------------------------------------------
# Offline planner
# ---------------------------------------------------------------------------

def _call(ctx: tools.ToolContext, name: str, args: dict[str, Any]) -> Generator[Event, None, Any]:
    before = len(ctx.cards)
    result, summary = tools.run(name, args, ctx)
    yield ("tool", {"name": name, "summary": summary})
    for card in ctx.cards[before:]:
        yield ("card", card)
    return result


def _date(value: str | None) -> str:
    return (value or "")[:10]


def _extract_name(message: str, pattern: str) -> str:
    m = re.search(pattern, message, re.IGNORECASE)
    if not m:
        return ""
    name = m.group("name").strip(" ?.!,'\"")
    return re.sub(r"\b(?:the|a|an|my|our|deal|account|team|thread|email|emails|please)\b", "", name, flags=re.I).strip(" ,")


def _person_thread(ctx: tools.ToolContext, who: str) -> dict[str, Any] | None:
    people = memory.find_people(ctx.store, ctx.user_id, who) or memory.company_people(ctx.store, ctx.user_id, who)
    for p in people:
        rows = ctx.store.query(
            "SELECT * FROM cw_items WHERE user_id = %s AND kind = 'email' AND (author_email = %s OR recipients LIKE %s) "
            "ORDER BY occurred_at DESC LIMIT 1",
            (ctx.user_id, p["email"], f"%{p['email']}%"),
        )
        if rows:
            return rows[0]
    return None


AUTOJOIN_RE = re.compile(
    r"\b(?:join|attend|take|cover|sit in on)\b.{0,30}\b(?:all|every|each|any)\b.{0,40}\b(?:meetings?|calls?)\b"
    r"|\b(?:from now on|going forward|always)\b.{0,40}\b(?:join|attend|take|cover)\b.{0,40}\b(?:meetings?|calls?)\b"
)


def _offline_turn(ctx: tools.ToolContext, message: str) -> Generator[Event, None, None]:
    m = message.strip()
    low = m.lower()
    s, uid = ctx.store, ctx.user_id
    first = ((s.get_coworker(uid) or {}).get("owner_name") or "").split(" ")[0]

    # 0. Standing instruction to take meetings ("join all my external calls")
    if AUTOJOIN_RE.search(low):
        result = yield from _call(ctx, "propose_responsibility", {"request": m})
        spec = result["spec"]
        yield ("text", f"Here's how I understood that. Confirm the card and I'll start with your next matching meeting.\n\n"
                       f"**{spec['name']}**: {spec['description']}\n\n"
                       "Before each one I'll post a prep brief in its own chat with a one-tap **Skip**, then join as your "
                       "disclosed AI coworker and post the summary there when it ends.")
        return

    # 0a. Send the coworker to a meeting
    if re.search(r"\b(join|attend|take|sit in on|go to|cover)\b.{0,40}\b(meeting|call|zoom|meet|teams|standup|qbr|demo)\b", low) \
            or re.search(r"https://\S*(zoom\.us|meet\.google|teams\.microsoft)", low):
        url = (re.search(r"https://\S+", m) or [""])[0]
        cm = re.search(r"\b(?:and|to)\s+((?:pitch|ask|tell|explain|cover|find out|qualify|push|focus|walk|demo|get)\b.+)$", m, re.I)
        context = cm.group(1).strip() if cm else m
        result = yield from _call(ctx, "join_meeting", {"meeting_url": url, "title": m, "context": context})
        if result.get("error"):
            yield ("text", result["error"])
            return
        how = result["how"]
        if how == "demo":
            yield ("text", "Done. I ran the call (demo workspace: a scripted prospect played Dana from Northwind). "
                           "I opened by saying I'm an AI, followed your context, and escalated anything I can't decide. "
                           "The summary and a drafted follow-up are just below.")
        elif how == "bot":
            yield ("text", "I'm joining now as your disclosed AI coworker. I'll post the summary and a drafted follow-up "
                           "here when the call ends. You can watch live from **Coworker → Calls**.")
        else:
            yield ("text", "There's no meeting bot on this server, so I set the call up in the call studio. Open it "
                           "(**Coworker → Calls**) and I'll talk there. The summary will land in this chat.")
        return

    # 0b. Reply to emails in bulk
    em = re.search(r"\b(?:reply|respond|answer|get back)\b.{0,30}\b(?:my |all |the |unanswered |unread |waiting |inbound )*"
                   r"(?P<what>emails?|inbox|leads?|support (?:emails?|questions)|scheduling (?:emails?|requests)|customers?)\b", low)
    if em:
        what = em.group("what")
        category = ("sales_lead" if what.startswith("lead") else "support" if "support" in what or what.startswith("customer")
                    else "scheduling" if "scheduling" in what else "")
        actions = yield from _call(ctx, "reply_to_emails", {"category": category, "limit": 5})
        if not actions:
            yield ("text", "Nothing is waiting on a reply right now (or I've already drafted those, check your approvals).")
        else:
            yield ("text", f"I drafted {len(actions)} repl{'y' if len(actions) == 1 else 'ies'} in your voice. Approve, edit, "
                           "or reject each one below. After they're sent I'll post exactly what went out here.")
        return

    # 0c. What did you do today?
    if re.search(r"\b(what did you do|what have you done|my day|today'?s (?:work|summary|recap)|recap (?:my|the) day|"
                 r"what happened today|daily (?:recap|summary))\b", low):
        d = yield from _call(ctx, "my_day", {})
        if not d["entries"]:
            yield ("text", "Nothing yet today.")
        else:
            lines = [f"**{d['headline']}**", ""]
            for e in d["entries"][:12]:
                icon = {"meeting": "📞", "brief": "📋", "escalation": "🙋", "security": "🛡️"}.get(e["kind"],
                        "✅" if e.get("status") == "executed" else "📝")
                lines.append(f"- {icon} {e['title']}")
            yield ("text", "\n".join(lines) + "\n\nOpen **Coworker → Today** for details.")
        return

    # 1. Standing responsibilities
    if re.search(r"\b(from now on|going forward|every time|whenever|each time|take over|take care of|own )|"
                 r"^(?:please )?handle\b|\bhandle (?:all|my|every|any|first|inbound|the)\b", low):
        result = yield from _call(ctx, "propose_responsibility", {"request": m})
        spec = result["spec"]
        yield ("text", f"Here's how I understood that. Confirm the card and I'll start right away.\n\n"
                       f"**{spec['name']}**: {spec['description']}\n\n"
                       f"I'll ask for your approval before anything goes out (autonomy: *{spec['autonomy']}*). "
                       "You can loosen that later.")
        return

    # 2. Remember a preference
    if re.match(r"^(remember|note) (that )?|^(always|never) ", low):
        rule = re.sub(r"^(remember|note)( that)?\s*", "", m, flags=re.I)
        yield from _call(ctx, "remember_preference", {"rule": rule})
        yield ("text", f"Got it. I'll follow that from now on: *{rule}*")
        return

    # 3. Approvals
    if re.search(r"\b(pending|approvals?|waiting for me|needs? my (?:ok|approval))\b", low):
        rows = yield from _call(ctx, "pending_approvals", {})
        if not rows:
            yield ("text", "Nothing is waiting for your approval right now.")
        else:
            yield ("text", "Waiting for your approval:\n\n" + "\n".join(f"- {r['title']}" for r in rows[:10]) +
                   "\n\nOpen **Coworker → Approvals** to review them.")
        return

    # 4. Meeting prep
    if re.search(r"\b(prep|prepare|brief)\b", low) and re.search(r"\b(meeting|call|me|tomorrow|next)\b", low):
        query = _extract_name(m, r"(?:with|for) (?P<name>[\w .'-]+?)(?:\?|$| tomorrow| today| next)") or ""
        brief = yield from _call(ctx, "meeting_brief", {"query": query})
        yield ("text", brief.get("markdown") if isinstance(brief, dict) and brief.get("markdown") else "I couldn't find an upcoming meeting to prep.")
        return

    # 5. Calendar
    if re.search(r"\b(calendar|schedule (?:today|tomorrow|this week)|what'?s on my|my week|meetings? (?:today|tomorrow|this week))\b", low) \
            and not re.search(r"\bschedule (?:a|an|time|meeting|call)\b", low):
        events = yield from _call(ctx, "calendar", {"days": 7})
        if not events:
            yield ("text", "Your calendar is clear for the next 7 days.")
        else:
            yield ("text", "Coming up:\n\n" + "\n".join(f"- **{e['when']}**: {e['title']}" for e in events[:12]))
        return

    # 6. Scheduling with someone
    who = _extract_name(m, r"\b(?:schedule|book|set up|find (?:a )?time|find time)\b.*?\bwith (?P<name>[\w .'-]+?)(?:\?|$|\.| next| this| tomorrow| for)")
    if who:
        thread = _person_thread(ctx, who)
        if thread:
            draft = yield from _call(ctx, "draft_reply", {"thread_id": thread["thread_id"],
                                                          "instruction": ""})
            body = draft["body"]
            if not draft.get("slots"):
                slot_text, _ = drafting.slot_lines(s, uid)
                name = drafting.first_name(thread["author_name"] if thread["direction"] == "inbound" else who)
                body = drafting._wrap(s, uid, name, f"Would any of these work for a quick call?\n{slot_text}")
            yield from _call(ctx, "send_email", {"to": draft["to"], "subject": draft["subject"], "body": body,
                                                 "thread_id": thread["thread_id"]})
            yield ("text", f"I drafted a reply to {thread['author_name'] if thread['direction'] == 'inbound' else who} offering open times "
                           "from your calendar. Approve it below and I'll send it.")
        else:
            slots = yield from _call(ctx, "find_free_slots", {})
            yield ("text", f"I couldn't find an email thread with {who}. Here are open times you could offer:\n\n"
                   + "\n".join(f"- {sl['label']}" for sl in slots) + "\n\nTell me their email and I'll send an invite.")
        return

    # 7. Reply / follow up / nudge someone
    who = _extract_name(m, r"\b(?:reply to|respond to|answer|write back to|get back to|draft (?:a )?(?:reply|response|email|note) to|"
                           r"email|follow up with|nudge|ping)\s+(?P<name>[\w .'-]+?)(?:\s+(?:saying|that|and tell|to say|telling|with|about)\b|\?|$|\.|,)")
    if who and not re.search(r"\bslack\b", low):
        instruction = ""
        im = re.search(r"\b(?:saying|that|and tell (?:them|her|him)|to say|telling (?:them|her|him))\b\s+(.+)$", m, re.I)
        if im:
            instruction = im.group(1).strip()
        thread = _person_thread(ctx, who)
        if not thread:
            yield ("text", f"I couldn't find a conversation with {who}. Who do you mean? An email address works too.")
            return
        if re.search(r"\b(follow up|nudge|ping)\b", low) and thread["direction"] == "outbound":
            name = drafting.first_name((memory.find_people(s, uid, who) or [{}])[0].get("name") or who)
            body = drafting._wrap(s, uid, name, instruction or "Just checking in on this. Any questions I can answer to help things along?")
            subject = thread["subject"] if thread["subject"].lower().startswith("re:") else f"Re: {thread['subject']}"
            to = [r["email"] for r in thread.get("recipients") or []]
            yield from _call(ctx, "send_email", {"to": to, "subject": subject, "body": body, "thread_id": thread["thread_id"]})
            yield ("text", f"You wrote last on **{thread['subject']}** ({_date(thread['occurred_at'])}) and haven't heard back, "
                           "so I drafted a short nudge. Approve it below to send.")
            return
        draft = yield from _call(ctx, "draft_reply", {"thread_id": thread["thread_id"], "instruction": instruction})
        yield from _call(ctx, "send_email", {"to": draft["to"], "subject": draft["subject"], "body": draft["body"],
                                             "thread_id": draft["thread_id"]})
        yield ("text", f"Drafted a reply to **{thread['author_name']}** on *{thread['subject']}*. {draft['reasoning']} "
                       "Review and approve it below.")
        return

    # 8. Slack message
    sm = re.search(r"\b(?:tell|message|slack|dm|let)\s+(?P<name>\w+)(?: know)?(?: on slack)?\s+(?:that|:|to say)?\s*(?P<text>.+)$", m, re.I)
    if sm and re.search(r"\b(slack|dm|tell|let \w+ know)\b", low):
        name = sm.group("name").lower()
        text = sm.group("text").strip()
        yield from _call(ctx, "post_slack", {"channel": f"dm-{name}", "text": text[0].upper() + text[1:]})
        yield ("text", f"I'll message {name.title()} on Slack once you approve the card below.")
        return

    # 9. Inbox triage
    if re.search(r"\b(inbox|unread|needs? (?:a |my )?(?:reply|response)|what should i (?:reply|respond)|triage|who'?s waiting)\b", low):
        rows = yield from _call(ctx, "list_needs_reply", {})
        if not rows:
            yield ("text", "You're all caught up. Nothing is waiting on a reply.")
            return
        labels = {"sales_lead": "Sales lead", "scheduling": "Scheduling", "support": "Customer support", "investor": "Investor",
                  "candidate": "Candidate", "partner": "Partner", "internal": "Team", "fyi": "FYI", "customer": "Customer"}
        lines = [f"- **{labels.get(r['category'], r['category'])}**: {r['from']}, *{r['title']}* ({_date(r['date'])})" for r in rows]
        yield ("text", f"{len(rows)} threads are waiting on you:\n\n" + "\n".join(lines) +
               "\n\nWant me to draft replies? Say “reply to Dana”, or “handle inbound sales leads from now on”.")
        return

    # 10. Decisions
    dm = re.search(r"\bwhat did we (?:decide|say|agree)\b(?: (?:about|on|with))? (?P<name>.+?)\??$", low)
    if dm:
        hits = yield from _call(ctx, "search_memory", {"query": f"decided {dm.group('name')}"})
        decisions = [h for h in hits if h["type"] == "decision"]
        if decisions:
            d = decisions[0]
            yield ("text", f"On {_date(d['date'])} you wrote: “{d['title']}”" + (f" {d['detail']}" if d.get("detail") else ""))
        elif hits:
            yield ("text", "I didn't find an explicit decision, but here's the most relevant context:\n\n" + _hit_lines(hits))
        else:
            yield ("text", "I don't have anything on that yet.")
        return

    # 11. Who is
    who = _extract_name(m, r"\bwho(?:'s| is)\s+(?P<name>[\w .'-]+)")
    if who:
        found = yield from _call(ctx, "who_is", {"name": who})
        if not found or not found.get("person"):
            yield ("text", f"I don't know anyone named {who} yet.")
            return
        p = found["person"]
        lines = [f"**{p['name']}** ({p['email']}): {p.get('role') or 'role unknown'}"
                 f"{' at ' + p['company'] if p.get('company') else ''}. Relationship: {p['relationship']}, "
                 f"{p['interactions']} interactions, last on {_date(p.get('last_contact_at'))}."]
        if found.get("recent"):
            lines.append("\nRecent:\n" + "\n".join(f"- {_date(r['date'])}: {r['title']}" for r in found["recent"]))
        yield ("text", "\n".join(lines))
        return

    # 12. Status of an account
    name = _extract_name(m, r"\b(?:status (?:of|with|on)|what'?s (?:going on|happening|the latest|up) with|where (?:are we|do we stand|things stand) with|"
                            r"update on|latest (?:on|with)|how'?s)\s+(?P<name>[\w .'&-]+)")
    if name:
        st = yield from _call(ctx, "account_status", {"name": name})
        if not st.get("found"):
            yield ("text", f"I don't have any history with {name}.")
            return
        waiting = {"them": "You're waiting on them", "you": "They're waiting on you"}.get(st.get("waiting_on") or "", "")
        lines = [f"**{st['company']}** ({st['relationship']}). {waiting}; last message {st.get('days_since_last')} days ago."]
        if st.get("last_message"):
            lm = st["last_message"]
            lines.append(f"\nLast: *{lm['title']}* from {lm['from']} on {_date(lm['date'])}: “{lm['snippet'][:200]}”")
        if st.get("open_asks"):
            lines.append("\nOpen questions:\n" + "\n".join(f"- {q}" for q in st["open_asks"]))
        if st.get("next_meeting"):
            lines.append(f"\nNext meeting: **{st['next_meeting']['title']}** on {_date(st['next_meeting']['date'])}.")
        for d in st.get("decisions") or []:
            lines.append(f"\nDecision ({_date(d['date'])}): {d['title']}")
        if st.get("waiting_on") == "them" and (st.get("days_since_last") or 0) >= 4:
            lines.append(f"\nWant me to nudge them? Say “follow up with {st['people'][0]['name'].split()[0]}”.")
        yield ("text", "\n".join(lines))
        return

    # 13. Fallback: search memory
    hits = yield from _call(ctx, "search_memory", {"query": m})
    if hits:
        yield ("text", "Here's what I found:\n\n" + _hit_lines(hits[:5]) +
               ("\n\n_Running without an AI model key, so I can search and draft but can't reason freely. "
                "Add ANTHROPIC_API_KEY for full answers._"))
    else:
        yield ("text", f"I'm not sure how to help with that yet{', ' + first if first else ''}. Try “what needs a reply?”, "
                       "“what's going on with Acme?”, “reply to Dana”, or “handle inbound sales leads from now on”.")


def _hit_lines(hits: list[dict[str, Any]]) -> str:
    lines = []
    for h in hits:
        if h["type"] == "decision":
            lines.append(f"- **Decision** ({_date(h['date'])}): {h['title']}")
        else:
            snippet = re.sub(r"<[^>]+>", "", h.get("snippet") or "")[:160]
            lines.append(f"- **{h.get('title') or h.get('provider')}** from {h.get('from')} ({_date(h['date'])}): {snippet}")
    return "\n".join(lines)


def responsibility_names() -> dict[str, str]:
    return {k: v["name"] for k, v in responsibilities.TEMPLATES.items()}
