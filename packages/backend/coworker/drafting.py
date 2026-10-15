"""Writing on the user's behalf: email replies, Slack answers, and meeting briefs.

With an Anthropic key, drafts come from Claude, grounded in the thread,
memory, company docs, and the user's style profile. Without one, a
deterministic composer produces sensible, grounded drafts from the same
inputs so the product still works end to end.
"""
from __future__ import annotations

import re
from typing import Any

from coworker import llm, memory, scheduling, security, style
from coworker.store import Store


def first_name(name: str) -> str:
    return (name or "").strip().split(" ")[0] or "there"


def _style(store: Store, user_id: int) -> dict[str, Any]:
    return (store.get_coworker(user_id) or {}).get("style_profile") or {}


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text or "")) if s.strip()]


def doc_answer(store: Store, user_id: int, question: str, max_sentences: int = 2) -> str:
    """Best-matching sentences from the user's docs (pricing, FAQ, ...)."""
    docs = [i for i in store.items(user_id, kind="doc", limit=200) if i.get("body")]
    q_words = {w for w in re.findall(r"[a-z0-9]+", question.lower()) if len(w) > 2} - {
        "the", "and", "what", "does", "can", "you", "for", "our", "are", "any", "there", "with", "this", "that",
        "thanks", "quick", "one", "hi", "hey", "about", "would", "like", "much", "how",
    }
    synonyms = {"size": {"mb", "limit", "large", "upload"}, "limit": {"maximum", "mb", "size"},
                "pricing": {"plan", "seat", "month", "$49", "$99"}, "price": {"plan", "seat"},
                "sso": {"saml", "sso"}, "excel": {"supported", "types"}, "types": {"supported", "pdf"}}
    expanded = set(q_words)
    for w in q_words:
        expanded |= synonyms.get(w, set())
    scored: list[tuple[int, str]] = []
    for d in docs:
        for s in _sentences(d["body"]):
            s_words = set(re.findall(r"[a-z0-9$]+", s.lower()))
            score = len(expanded & s_words)
            if score:
                scored.append((score, s))
    scored.sort(key=lambda x: x[0], reverse=True)
    picked: list[str] = []
    for _, s in scored:
        if s not in picked:
            picked.append(s)
        if len(picked) >= max_sentences:
            break
    return " ".join(picked)


def slot_lines(store: Store, user_id: int, count: int = 3, afternoon: bool = False) -> tuple[str, list[dict[str, str]]]:
    slots = scheduling.free_slots(store, user_id, count=count, prefer_afternoon=afternoon)
    return "\n".join(f"- {s['label']}" for s in slots), slots


def _wrap(store: Store, user_id: int, greeting_name: str, body: str) -> str:
    st = _style(store, user_id)
    coworker = store.get_coworker(user_id) or {}
    greeting = st.get("greeting") or "Hi"
    signoff = st.get("signoff") or "Best"
    body = body.strip()
    if (st.get("exclamation_rate") or 0) < 0.1:
        body = body.replace("!", ".")
    return f"{greeting} {greeting_name},\n\n{body}\n\n{signoff},\n{first_name(coworker.get('owner_name', ''))}"


def compose_reply(
    store: Store,
    user_id: int,
    thread_items: list[dict[str, Any]],
    category: str,
    instruction: str = "",
) -> dict[str, Any]:
    """Draft a reply to the latest inbound message in a thread.

    Returns ``{"to", "subject", "body", "thread_id", "slots", "reasoning"}``.
    """
    inbound = [i for i in thread_items if i["direction"] == "inbound"]
    last = inbound[-1] if inbound else thread_items[-1]
    to = [last["author_email"]] if last["direction"] == "inbound" else [r["email"] for r in last.get("recipients") or []]
    subject = last.get("subject") or ""
    if subject and not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    name = first_name(last.get("author_name") or "")
    if llm.available(user_id):
        try:
            body = _llm_reply(store, user_id, thread_items, category, instruction)
            if body:
                return {"to": to, "subject": subject, "body": body, "thread_id": last["thread_id"], "slots": [],
                        "reasoning": f"Drafted with Claude from the thread, your memory, and your docs ({category})."}
        except Exception:
            pass  # fall back to the deterministic composer
    body, slots, reasoning = _template_body(store, user_id, last, category, instruction)
    return {"to": to, "subject": subject, "body": _wrap(store, user_id, name, body), "thread_id": last["thread_id"],
            "slots": slots, "reasoning": reasoning}


def _template_body(store: Store, user_id: int, last: dict[str, Any], category: str,
                   instruction: str) -> tuple[str, list[dict[str, str]], str]:
    text = f"{last.get('subject', '')}\n{last.get('body', '')}"
    lower = text.lower()
    ctx = memory.company_context(store, user_id)
    company = ctx["name"] or "us"
    if instruction:
        body = instruction.strip()
        body = body[0].upper() + body[1:]
        if not body.endswith((".", "?", "!")):
            body += "."
        return body, [], "Wrote the reply you asked for."
    if category == "sales_lead":
        lines, slots = slot_lines(store, user_id)
        parts = [f"Thanks for reaching out, and great to hear from you. I'd be glad to show you how {company} works."]
        if any(w in lower for w in ("pricing", "price", "cost", "seats")):
            pricing = doc_answer(store, user_id, "pricing per seat plan sso", max_sentences=2)
            if pricing:
                parts.append(f"On pricing: {pricing}")
        if "sso" in lower:
            sso = doc_answer(store, user_id, "sso saml", max_sentences=1)
            if sso:
                parts.append(sso)
        parts.append(f"Would any of these work for a 30-minute demo?\n{lines}" if lines else
                     "What times work for a 30-minute demo next week?")
        return "\n\n".join(parts), slots, "New sales lead: offered a demo with open times from your calendar, and answered pricing from your pricing doc."
    if category in ("scheduling", "partner", "candidate"):
        lines, slots = slot_lines(store, user_id, afternoon="afternoon" in lower)
        intro = {"scheduling": "Of course, happy to find a time.",
                 "partner": "Thanks for following up. I'd be glad to talk about it.",
                 "candidate": "Thanks for reaching out, I'd love to chat."}[category]
        body = f"{intro} Would any of these work?\n{lines}" if lines else f"{intro} What times work for you?"
        return body, slots, "Scheduling request: offered open slots from your calendar within working hours."
    if category == "support":
        answer = doc_answer(store, user_id, text)
        body = (f"Thanks for flagging this. {answer}\n\nLet me know if that doesn't solve it and we'll dig in."
                if answer else "Thanks for flagging this. I'm looking into it and will get back to you shortly.")
        return body, [], "Support question: answered from your product docs." if answer else "Support question: no doc answer found, so I acknowledged and flagged it."
    if category == "investor":
        deals = [d for d in memory.learned_summary(store, user_id)["deals"] if d["relationship"] in ("prospect", "customer")]
        pipeline = "\n".join(f"- {d['company']}: {d['last'] or 'in progress'}" for d in deals[:4]) or "- [add pipeline]"
        body = ("Thanks for checking in. Quick update:\n\n- Revenue: [add this quarter's number]\n"
                f"- Pipeline:\n{pipeline}\n- Hiring: talking with candidates for the founding engineer role\n\n"
                "Happy to go deeper before your partner meeting.")
        return body, [], "Investor update: filled the pipeline from your active deals and left revenue for you to add."
    return "Thanks for the note. Will take a look and follow up.", [], "Acknowledged the message."


def _llm_reply(store: Store, user_id: int, thread_items: list[dict[str, Any]], category: str, instruction: str) -> str:
    coworker = store.get_coworker(user_id) or {}
    ctx = memory.company_context(store, user_id)
    st = _style(store, user_id)
    last_inbound = next((i for i in reversed(thread_items) if i["direction"] == "inbound"), thread_items[-1])
    thread_text = "\n\n".join(
        f"From: {i['author_name']} <{i['author_email']}> ({i['occurred_at'][:10]})\nSubject: {i['subject']}\n"
        + (security.wrap_untrusted(i['body'] or '', 'email') if i["direction"] == "inbound" else (i["body"] or ""))
        for i in thread_items[-8:]
    )
    facts = memory.recall(store, user_id, f"{last_inbound.get('subject', '')} {last_inbound.get('body', '')}", k=5)
    docs = doc_answer(store, user_id, last_inbound.get("body") or "", max_sentences=4)
    lines, _ = slot_lines(store, user_id)
    examples = style.examples_for(store, user_id, last_inbound.get("body") or "", k=2)
    system = (
        f"You draft emails for {coworker.get('owner_name')} at {ctx['name']}. Write exactly what they would send: "
        f"their voice, their facts. Style: {st.get('summary', '')}\n\n{security.SYSTEM_RULES}\n"
        "Only state facts found in the thread, the facts list, or the company docs. Never invent prices, dates, "
        "or commitments; if something is unknown, leave a [bracketed placeholder]. Reply with the email body "
        "only (greeting through sign-off), no subject line, no commentary."
    )
    prompt = (
        f"Thread (oldest first):\n{thread_text}\n\nCategory: {category}\n"
        f"Instruction from {first_name(coworker.get('owner_name', ''))}: {instruction or 'Write the best reply.'}\n\n"
        f"Company docs:\n{docs or '(none relevant)'}\n\nRelated memory:\n"
        + "\n".join(f"- {f.get('title')}: {f.get('snippet') or f.get('detail') or ''}" for f in facts)
        + f"\n\nOpen calendar slots you may offer:\n{lines or '(none)'}\n\nExamples of their writing:\n"
        + "\n---\n".join(examples)
    )
    return llm.complete_text(prompt, system=system, user_id=user_id, effort="medium").strip()


def slack_answer(store: Store, user_id: int, question: str) -> dict[str, Any]:
    """Answer a teammate's question from memory and docs, or say it needs the user."""
    decisions = [r for r in memory.recall(store, user_id, question, k=4) if r["type"] == "decision"]
    doc = doc_answer(store, user_id, question)
    coworker = store.get_coworker(user_id) or {}
    owner = first_name(coworker.get("owner_name", ""))
    if llm.available(user_id):
        try:
            facts = memory.recall(store, user_id, question, k=6)
            text = llm.complete_text(
                f"A teammate asked on Slack:\n{security.wrap_untrusted(question, 'slack')}\n\nFacts:\n"
                + "\n".join(f"- {f.get('title')}: {f.get('detail') or f.get('snippet') or ''}" for f in facts)
                + f"\n\nDocs: {doc or '(none)'}\n\nAnswer in 1-3 short sentences using only these facts. If the facts "
                  f"don't answer it, reply exactly: NEEDS_{owner.upper()}",
                system=f"You are {owner}'s AI coworker answering a teammate on Slack.\n{security.SYSTEM_RULES}",
                user_id=user_id, effort="low",
            ).strip()
            if text and not text.startswith("NEEDS_"):
                return {"text": text, "confident": True}
            return {"text": f"Good question. I'll check with {owner} and get back to you.", "confident": False}
        except Exception:
            pass
    if decisions:
        d = decisions[0]
        rationale = f" {d['detail']}" if d.get("detail") else ""
        return {"text": f"From {owner}'s notes ({(d.get('date') or '')[:10]}): {d['title']}{rationale}", "confident": True}
    if doc:
        return {"text": doc, "confident": True}
    return {"text": f"Good question. I'll check with {owner} and get back to you.", "confident": False}


def meeting_brief(store: Store, user_id: int, event: dict[str, Any]) -> dict[str, Any]:
    """Who they are, what's happened, open items, and a suggested agenda."""
    coworker = store.get_coworker(user_id) or {}
    owner_email = (coworker.get("owner_email") or "").lower()
    ctx = memory.company_context(store, user_id)
    attendees = [a for a in event.get("recipients") or [] if (a.get("email") or "").lower() != owner_email]
    external = [a for a in attendees if memory.domain_of(a.get("email", "")) != ctx["domain"]]
    people = []
    statuses: dict[str, Any] = {}
    for a in external or attendees:
        p = store.person_by_email(user_id, a.get("email", "")) or {"name": a.get("name") or a.get("email"), "email": a.get("email"),
                                                                     "company": "", "role": "", "relationship": "contact"}
        people.append({k: p.get(k) for k in ("name", "email", "company", "role", "relationship")})
        key = p.get("company") or p.get("email")
        if key and key not in statuses:
            statuses[key] = memory.account_status(store, user_id, key)
    tz = scheduling.tz_for(coworker)
    start = (event.get("meta") or {}).get("start") or event["occurred_at"]
    from coworker.store import parse_iso

    when = parse_iso(start)
    agenda = []
    open_items: list[str] = []
    for status in statuses.values():
        if not status.get("found"):
            continue
        open_items += status.get("open_asks") or []
        if status.get("waiting_on") == "them" and status.get("last_message"):
            open_items.append(f"Follow up on: {status['last_message']['title']}")
        for d in status.get("decisions") or []:
            open_items.append(f"Past decision: {d['title']}")
    title_lower = (event.get("subject") or "").lower()
    if "security" in title_lower:
        agenda = ["Walk through security posture and SOC 2 timeline", "Answer CISO questions", "Agree on next step to signature"]
    elif "qbr" in title_lower:
        agenda = ["Usage and outcomes this quarter", "Open issues and requests", "Renewal and expansion"]
    elif "intro" in title_lower or "chat" in title_lower:
        agenda = ["Introductions and background", "What they're looking for", "Next steps"]
    else:
        agenda = ["Goals for the meeting", "Discussion", "Next steps and owners"]
    brief: dict[str, Any] = {
        "event": {"id": event["id"], "title": event.get("subject"), "start": start,
                  "label": scheduling.label(when, tz) if when else start, "location": (event.get("meta") or {}).get("location", "")},
        "people": people,
        "accounts": [
            {"company": k, "relationship": v.get("relationship"), "waitingOn": v.get("waiting_on"),
             "daysSinceLast": v.get("days_since_last"), "history": [h["title"] for h in (v.get("history") or [])][-4:]}
            for k, v in statuses.items() if v.get("found")
        ],
        "openItems": open_items[:6],
        "agenda": agenda,
    }
    lines = [f"**Prep brief: {brief['event']['title']}** ({brief['event']['label']})", ""]
    for p in people:
        role = f", {p['role']}" if p.get("role") else ""
        company = f" at {p['company']}" if p.get("company") else ""
        lines.append(f"- **{p['name']}**{role}{company} ({p['relationship']})")
    for acc in brief["accounts"]:
        waiting = {"them": "waiting on them", "you": "waiting on you"}.get(acc["waitingOn"] or "", "")
        lines.append(f"\n**{acc['company']}**: {waiting}, last touch {acc['daysSinceLast']} days ago")
        for h in acc["history"]:
            lines.append(f"  - {h}")
    if open_items:
        lines.append("\n**Open items**")
        lines += [f"- {o}" for o in open_items[:6]]
    lines.append("\n**Suggested agenda**")
    lines += [f"{i + 1}. {a}" for i, a in enumerate(agenda)]
    brief["markdown"] = "\n".join(lines)
    return brief
