"""Standing responsibilities and the engine that runs them.

A responsibility is a job the user hands off once ("handle first replies
to inbound sales leads"). Each one has a trigger, an autonomy level, and
an escalation rule. ``run_all`` checks every enabled responsibility
against new events and creates actions or briefs. Runs are idempotent:
the ``cw_runs`` unique key means the same email never produces two
replies, even with several workers.
"""
from __future__ import annotations

import re
from datetime import timedelta
from typing import Any

from coworker import drafting, executor, memory, scheduling, security
from coworker.store import IntegrityError, Store, iso, utcnow

TEMPLATES: dict[str, dict[str, Any]] = {
    "inbound_leads": {
        "name": "Reply to inbound sales leads",
        "description": "Draft a first reply to new sales inquiries: answer pricing from your docs and offer demo times.",
        "instruction": "Handle first replies to inbound sales leads. Offer a demo with open times and answer pricing questions from our pricing doc.",
        "trigger": {"type": "email", "category": "sales_lead"},
        "autonomy": "approve",
    },
    "scheduling": {
        "name": "Handle scheduling requests",
        "description": "When someone asks to meet or reschedule, offer open times from your calendar.",
        "instruction": "Reply to scheduling and rescheduling requests with open times inside my working hours.",
        "trigger": {"type": "email", "category": "scheduling"},
        "autonomy": "approve",
    },
    "support": {
        "name": "Answer customer support questions",
        "description": "Answer product questions from your docs; escalate anything the docs don't cover.",
        "instruction": "Answer customer product questions using our product FAQ. Escalate anything the docs don't answer.",
        "trigger": {"type": "email", "category": "support"},
        "autonomy": "approve",
    },
    "auto_join": {
        "name": "Join my external meetings",
        "description": "Before each external video call: a prep brief in its own chat with a Skip link. Then it joins as "
                       "your disclosed AI coworker and posts the summary and follow-up there.",
        "instruction": "Join my external meetings for me. Introduce yourself as my AI coworker, find out what they need "
                       "and their timeline, and escalate pricing, contracts, or anything you're unsure about to me.",
        "trigger": {"type": "calendar_join", "minutes_before": 30, "external_only": True, "keywords": []},
        "autonomy": "notify",
    },
    "meeting_prep": {
        "name": "Prep me for every meeting",
        "description": "Before each meeting with someone outside the company, post a brief: who, history, open items, agenda.",
        "instruction": "Before each external meeting, brief me on who they are, our history, open items, and an agenda.",
        "trigger": {"type": "calendar", "hours_before": 48},
        "autonomy": "silent",
    },
    "stale_deals": {
        "name": "Nudge stalled deals",
        "description": "When a proposal or deal thread goes quiet, draft a friendly follow-up.",
        "instruction": "If a deal thread where I wrote last goes quiet for 4 days, draft a short, friendly nudge.",
        "trigger": {"type": "stale", "days": 4},
        "autonomy": "approve",
    },
    "slack_answers": {
        "name": "Answer teammates on Slack",
        "description": "Answer questions in your DMs from memory and docs; say you'll check when unsure.",
        "instruction": "Answer teammates' questions in my Slack DMs from what you know. If you're not sure, tell them you'll check with me.",
        "trigger": {"type": "slack"},
        "autonomy": "approve",
    },
    "meeting_followup": {
        "name": "Follow up after meetings",
        "description": "After a meeting your coworker attended, send the recap and next steps.",
        "instruction": "After each meeting you attend for me, draft the follow-up email with the summary and next steps.",
        "trigger": {"type": "transcript"},
        "autonomy": "approve",
    },
    "daily_digest": {
        "name": "Daily digest",
        "description": "An end-of-day summary of what your coworker handled and what needs you.",
        "instruction": "At the end of each day, summarize what you handled and what needs me.",
        "trigger": {"type": "daily"},
        "autonomy": "silent",
    },
}


def match_template(text: str) -> str:
    t = text.lower()
    rules = [
        ("auto_join", r"\b(?:join|attend|take|cover|sit in on)\b.{0,30}\b(?:all|every|each|any)\b.{0,40}\b(?:meetings?|calls?)\b"
                      r"|\b(?:from now on|going forward|always)\b.{0,40}\b(?:join|attend|take|cover)\b.{0,40}\b(?:meetings?|calls?)\b"),
        ("daily_digest", r"digest|end of (?:the )?day|daily summary|summari[sz]e (?:my|the) day"),
        ("meeting_followup", r"after (?:each |every |my )?(?:meeting|call)s?|follow[- ]?up after|recap"),
        ("meeting_prep", r"\bprep|brief me|before (?:each |every |my )?(?:meeting|call)"),
        ("stale_deals", r"stal\w*|nudge|gone quiet|go quiet|chase|follow[- ]?up on (?:deals|proposals)"),
        ("slack_answers", r"slack|teammates?|team questions|dms?\b"),
        ("support", r"support|customer questions|product questions|faq"),
        ("scheduling", r"schedul|calendar|meeting requests|book(?:ing)? (?:time|meetings)|reschedul"),
        ("inbound_leads", r"lead|sales|inbound|prospect|demo requests?|pricing questions"),
    ]
    for template, pattern in rules:
        if re.search(pattern, t):
            return template
    return "custom"


def create(store: Store, user_id: int, spec: dict[str, Any]) -> dict[str, Any]:
    template = spec.get("template") or "custom"
    base = TEMPLATES.get(template, {})
    rid = store.insert("cw_responsibilities", {
        "user_id": user_id,
        "name": (spec.get("name") or base.get("name") or "Custom responsibility")[:255],
        "template": template if template in TEMPLATES or template == "scheduled" else "custom",
        "instruction": spec.get("instruction") or base.get("instruction", ""),
        "trigger_spec": spec.get("trigger") or base.get("trigger") or {"type": "email", "keywords": _keywords(spec.get("instruction", ""))},
        "tools": spec.get("tools") or [],
        "autonomy": spec.get("autonomy") or base.get("autonomy", "approve"),
        "escalation": spec.get("escalation") or "Escalate to me when you're unsure, when money or contracts are involved, or when someone asks for a human.",
        "enabled": 1, "runs": 0, "created_at": iso(),
    })
    store.log(user_id, "responsibility", f"Took on a new responsibility: {spec.get('name') or base.get('name', '')}")
    row = store.get("cw_responsibilities", rid, user_id)
    assert row is not None
    return row


def _keywords(instruction: str) -> list[str]:
    stop = {"the", "and", "from", "with", "that", "this", "when", "then", "they", "them", "your", "mine", "into", "about",
            "handle", "reply", "replies", "please", "every", "each", "should", "would"}
    return [w for w in re.findall(r"[a-z]{4,}", instruction.lower()) if w not in stop][:8]


def scheduled_spec(instruction: str, schedule: dict[str, Any], name: str = "") -> dict[str, Any]:
    from coworker import schedules

    trigger = schedules.clean(schedule)
    return {
        "template": "scheduled",
        "name": (name or schedules.name_for(instruction))[:255],
        "instruction": instruction.strip(),
        "trigger": trigger,
        "autonomy": "approve",
        "escalation": "Escalate to me when you're unsure, when money or contracts are involved, or when someone asks for a human.",
        "description": f"{schedules.describe(trigger)}: {instruction.strip()}",
    }


def proposal_payload(text: str) -> dict[str, Any]:
    """Turn a chat request into a responsibility spec for the user to confirm."""
    from coworker import schedules

    template = match_template(text)
    schedule = schedules.parse(text) if template != "auto_join" else None
    if schedule:  # recurring work on a clock: "every Monday at 9am post the pipeline in #sales"
        return scheduled_spec(schedules.strip_schedule(text), schedule)
    base = TEMPLATES.get(template, {})
    trigger = base.get("trigger") or {"type": "email", "keywords": _keywords(text)}
    if template == "auto_join":
        low = text.lower()
        kinds = [k for k in ("intro", "demo", "discovery", "sales", "qbr", "interview", "onboarding", "kickoff") if k in low]
        trigger = {**trigger, "keywords": kinds, "external_only": "internal" not in low and "all my meetings" not in low}
    return {
        "template": template,
        "name": base.get("name") or text.strip().rstrip(".")[:80],
        "instruction": base.get("instruction") or text.strip(),
        "trigger": trigger,
        "autonomy": base.get("autonomy", "approve"),
        "escalation": "Escalate to me when you're unsure, when money or contracts are involved, or when someone asks for a human.",
        "description": base.get("description") or "Custom responsibility. I'll flag matching messages for you.",
    }


def _claim(store: Store, user_id: int, resp: dict[str, Any], key: str) -> int | None:
    try:
        return store.insert("cw_runs", {"user_id": user_id, "responsibility_id": resp["id"], "trigger_key": key,
                                        "status": "running", "created_at": iso(), "started_at": iso()})
    except IntegrityError:
        return None


def _finish(store: Store, run_id: int, summary: str, status: str = "done", error: str = "",
            usage: dict[str, Any] | None = None) -> None:
    values: dict[str, Any] = {"status": status, "summary": summary, "finished_at": iso()}
    if usage:
        values["tokens"] = int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0))
        values["cost_micros"] = None if usage.get("cost_usd") is None else int(round(usage["cost_usd"] * 1_000_000))
    if error:
        values["error"] = error[:2000]
    store.update("cw_runs", run_id, None, values)


def _since(resp: dict[str, Any]) -> str:
    """Look back a week before the responsibility was created, so it can act on recent backlog."""
    from coworker.store import parse_iso

    created = parse_iso(resp["created_at"]) or utcnow()
    return iso(created - timedelta(days=7))


def _email_responsibility(store: Store, user_id: int, resp: dict[str, Any], category: str) -> list[str]:
    out: list[str] = []
    since = _since(resp)
    for pending in memory.needs_reply(store, user_id):
        if pending["category"] != category or (pending["date"] or "") < since:
            continue
        item = store.get("cw_items", pending["id"], user_id)
        if not item:
            continue
        run_id = _claim(store, user_id, resp, f"{pending['thread_id']}:{item['id']}")
        if not run_id:
            continue
        if security.is_suspicious(item.get("body") or ""):
            store.log(user_id, "security", f"Didn't reply to a suspicious message from {item['author_email']}: "
                      "it looks like a phishing or prompt-injection attempt.", {"item_id": item["id"]})
            _finish(store, run_id, "skipped: suspicious", "skipped")
            continue
        draft = drafting.compose_reply(store, user_id, store.thread(user_id, item["thread_id"]), category)
        action = executor.propose(
            store, user_id, "email.send",
            {"to": draft["to"], "subject": draft["subject"], "body": draft["body"], "thread_id": draft["thread_id"]},
            title=f"Reply to {item['author_name']}: {item['subject']}", reasoning=draft["reasoning"],
            source_item_id=item["id"], responsibility=resp,
        )
        _finish(store, run_id, f"action {action['id']}")
        out.append(f"Drafted a reply to {item['author_name']}")
    return out


def _meeting_prep(store: Store, user_id: int, resp: dict[str, Any]) -> list[str]:
    out: list[str] = []
    hours = int((resp.get("trigger_spec") or {}).get("hours_before", 48))
    ctx = memory.company_context(store, user_id)
    owner = ctx["owner_email"]
    for event in scheduling.upcoming_events(store, user_id, hours=hours):
        external = [a for a in event.get("recipients") or []
                    if (a.get("email") or "").lower() != owner and memory.domain_of(a.get("email", "")) != ctx["domain"]]
        if not external:
            continue
        run_id = _claim(store, user_id, resp, f"event:{event['external_id']}")
        if not run_id:
            continue
        brief = drafting.meeting_brief(store, user_id, event)
        store.log(user_id, "brief", f"Prep brief ready: {event['subject']}", {"brief": brief})
        _finish(store, run_id, "brief posted")
        out.append(f"Prepared a brief for {event['subject']}")
    return out


def _stale_deals(store: Store, user_id: int, resp: dict[str, Any]) -> list[str]:
    out: list[str] = []
    days = int((resp.get("trigger_spec") or {}).get("days", 4))
    for stale in memory.stale_threads(store, user_id, days=days):
        run_id = _claim(store, user_id, resp, f"stale:{stale['thread_id']}:{stale['id']}")
        if not run_id:
            continue
        thread = store.thread(user_id, stale["thread_id"])
        last = thread[-1]
        to = [r["email"] for r in last.get("recipients") or []]
        names = [r.get("name") or "" for r in last.get("recipients") or []]
        person = store.person_by_email(user_id, to[0]) if to else None
        name = drafting.first_name((person or {}).get("name") or (names[0] if names else ""))
        subject = last["subject"] if last["subject"].lower().startswith("re:") else f"Re: {last['subject']}"
        body = drafting._wrap(store, user_id, name,
                              "Just checking in on this. Any questions I can answer to help things along? "
                              "Happy to set up a quick call if that's easier.")
        action = executor.propose(
            store, user_id, "email.send", {"to": to, "subject": subject, "body": body, "thread_id": stale["thread_id"]},
            title=f"Nudge {name}: {last['subject']}",
            reasoning=f"You wrote last and nobody has replied in {days}+ days.", source_item_id=last["id"], responsibility=resp,
        )
        _finish(store, run_id, f"action {action['id']}")
        out.append(f"Drafted a follow-up to {name}")
    return out


def _slack_answers(store: Store, user_id: int, resp: dict[str, Any]) -> list[str]:
    out: list[str] = []
    since = _since(resp)
    latest: dict[str, dict[str, Any]] = {}
    for it in store.items(user_id, kind="slack", since=since, limit=500):
        latest.setdefault(it["channel"], it)
    for channel, it in latest.items():
        meta = it.get("meta") or {}
        if it["direction"] != "inbound" or not meta.get("dm") or "?" not in (it.get("body") or ""):
            continue
        run_id = _claim(store, user_id, resp, f"slack:{it['external_id']}")
        if not run_id:
            continue
        if security.is_suspicious(it.get("body") or ""):
            _finish(store, run_id, "skipped: suspicious", "skipped")
            continue
        answer = drafting.slack_answer(store, user_id, it["body"])
        action = executor.propose(
            store, user_id, "slack.post", {"channel": channel, "text": answer["text"]},
            title=f"Answer {it['author_name']} on Slack", source_item_id=it["id"], responsibility=resp,
            reasoning="Answered from your memory and docs." if answer["confident"] else "Not sure, so I'm telling them I'll check with you.",
        )
        if not answer["confident"]:
            store.log(user_id, "escalation", f"{it['author_name']} asked something I couldn't answer: {it['body'][:140]}",
                      {"item_id": it["id"]}, action_id=action["id"])
        _finish(store, run_id, f"action {action['id']}")
        out.append(f"Answered {it['author_name']} on Slack")
    return out


def _meeting_followup(store: Store, user_id: int, resp: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for meeting in store.query(
        "SELECT * FROM cw_meetings WHERE user_id = %s AND status = 'ended' AND started_at >= %s", (user_id, _since(resp))
    ):
        run_id = _claim(store, user_id, resp, f"meeting:{meeting['id']}")
        if not run_id:
            continue
        from coworker.meetings import summary_of

        summary = summary_of(meeting) or {}
        follow = summary.get("followup")
        if not follow or summary.get("followup_action_id"):
            _finish(store, run_id, "no follow-up drafted", "skipped")
            continue
        action = executor.propose(
            store, user_id, "email.send", follow, title=f"Follow up: {meeting['title']}",
            reasoning="Recap and next steps from the meeting your coworker attended.", responsibility=resp,
        )
        _finish(store, run_id, f"action {action['id']}")
        out.append(f"Drafted the follow-up for {meeting['title']}")
    return out


def _custom(store: Store, user_id: int, resp: dict[str, Any]) -> list[str]:
    """Custom responsibilities flag matching inbound messages for the user."""
    out: list[str] = []
    keywords = (resp.get("trigger_spec") or {}).get("keywords") or []
    if not keywords:
        return out
    for pending in memory.needs_reply(store, user_id):
        text = f"{pending.get('title', '')} {pending.get('snippet', '')}".lower()
        if (pending["date"] or "") < _since(resp) or not any(k in text for k in keywords):
            continue
        run_id = _claim(store, user_id, resp, f"custom:{pending['id']}")
        if not run_id:
            continue
        store.log(user_id, "escalation", f"'{resp['name']}' matched a message from {pending['from']}: {pending['title']}",
                  {"item_id": pending["id"]})
        _finish(store, run_id, "flagged")
        out.append(f"Flagged a message from {pending['from']}")
    return out


def _daily_digest(store: Store, user_id: int, resp: dict[str, Any]) -> list[str]:
    from coworker import scheduling as sched

    coworker = store.get_coworker(user_id) or {}
    local = utcnow().astimezone(sched.tz_for(coworker))
    if local.hour < 17:
        return []
    run_id = _claim(store, user_id, resp, f"digest:{local.strftime('%Y-%m-%d')}")
    if not run_id:
        return []
    d = digest(store, user_id, hours=24)
    store.log(user_id, "digest", d["headline"], {"digest": d})
    from coworker import notify

    notify.send_digest(store, user_id, d)
    _finish(store, run_id, d["headline"])
    return ["Posted the daily digest"]


def _scheduled(store: Store, user_id: int, resp: dict[str, Any]) -> list[str]:
    from coworker import schedules

    return schedules.run(store, user_id, resp)


def _auto_join(store: Store, user_id: int, resp: dict[str, Any]) -> list[str]:
    from coworker import autojoin

    return autojoin.run(store, user_id, resp)


HANDLERS = {
    "inbound_leads": lambda s, u, r: _email_responsibility(s, u, r, "sales_lead"),
    "scheduling": lambda s, u, r: _email_responsibility(s, u, r, "scheduling"),
    "support": lambda s, u, r: _email_responsibility(s, u, r, "support"),
    "auto_join": _auto_join,
    "meeting_prep": _meeting_prep,
    "stale_deals": _stale_deals,
    "slack_answers": _slack_answers,
    "meeting_followup": _meeting_followup,
    "daily_digest": _daily_digest,
    "scheduled": _scheduled,
    "custom": _custom,
}


def run_one(store: Store, user_id: int, resp: dict[str, Any]) -> list[str]:
    coworker = store.get_coworker(user_id) or {}
    if coworker.get("status") != "active" or not resp.get("enabled"):
        return []
    results = HANDLERS.get(resp["template"], _custom)(store, user_id, resp)
    store.update("cw_responsibilities", resp["id"], user_id, {
        "runs": int(resp.get("runs") or 0) + len(results), "last_run_at": iso(),
    })
    return results


def run_all(store: Store, user_id: int) -> list[str]:
    results: list[str] = []
    for resp in store.query("SELECT * FROM cw_responsibilities WHERE user_id = %s AND enabled = 1 ORDER BY id", (user_id,)):
        results += run_one(store, user_id, resp)
    return results


def digest(store: Store, user_id: int, hours: int = 24) -> dict[str, Any]:
    since = iso(utcnow() - timedelta(hours=hours))
    acts = store.activity(user_id, limit=1000, since=since)
    executed = [a for a in acts if a["kind"] == "executed"]
    pending = store.query("SELECT id, title FROM cw_actions WHERE user_id = %s AND status = 'proposed' ORDER BY id DESC",
                          (user_id,))
    briefs = [a for a in acts if a["kind"] == "brief"]
    escalations = [a for a in acts if a["kind"] in ("escalation", "security")]
    sent = sum(1 for a in executed if "Reply" in a["summary"] or "Nudge" in a["summary"] or "Follow" in a["summary"])
    def n(count: int, word: str) -> str:
        return f"{count} {word}{'' if count == 1 else 's'}"

    headline = (f"Handled {n(len(executed), 'action')} ({n(sent, 'email')}), prepared {n(len(briefs), 'brief')}. "
                f"{len(pending)} waiting for your approval, {len(escalations)} need your attention.")
    return {
        "headline": headline,
        "executed": [a["summary"] for a in executed][:20],
        "pending": [p["title"] for p in pending][:20],
        "briefs": [a["summary"] for a in briefs][:10],
        "attention": [a["summary"] for a in escalations][:10],
        "since": since,
    }


def suggestions(store: Store, user_id: int) -> list[dict[str, Any]]:
    """What to take off the user's plate first, generated from their data."""
    have = {r["template"] for r in store.query("SELECT template FROM cw_responsibilities WHERE user_id = %s", (user_id,))}
    pending = memory.needs_reply(store, user_id)
    counts: dict[str, int] = {}
    for p in pending:
        counts[p["category"]] = counts.get(p["category"], 0) + 1
    stale = memory.stale_threads(store, user_id)
    ctx = memory.company_context(store, user_id)
    meetings = [e for e in scheduling.upcoming_events(store, user_id, hours=72)
                if any(memory.domain_of(a.get("email", "")) not in (ctx["domain"], "") for a in e.get("recipients") or [])]
    dms = [i for i in store.items(user_id, kind="slack", limit=200)
           if (i.get("meta") or {}).get("dm") and i["direction"] == "inbound" and "?" in (i.get("body") or "")]
    out = []

    def add(template: str, why: str, n: int) -> None:
        if template not in have and n:
            out.append({"template": template, "name": TEMPLATES[template]["name"], "why": why, "count": n,
                        "description": TEMPLATES[template]["description"]})

    def n(count: int, one: str, many: str) -> str:
        return f"{count} {one if count == 1 else many}"

    leads, waiting, support = counts.get("sales_lead", 0), counts.get("scheduling", 0), counts.get("support", 0)
    add("inbound_leads", f"You have {n(leads, 'unanswered sales inquiry', 'unanswered sales inquiries')}.", leads)
    add("stale_deals", f"{n(len(stale), 'deal thread has', 'deal threads have')} gone quiet since you last wrote.", len(stale))
    add("scheduling", f"{n(waiting, 'person is', 'people are')} waiting on a time to meet.", waiting)
    add("meeting_prep", f"You have {n(len(meetings), 'external meeting', 'external meetings')} in the next 3 days.", len(meetings))
    add("support", f"{n(support, 'customer asked a product question', 'customers asked product questions')}.", support)
    from coworker import autojoin
    from coworker.connectors import recall

    if recall.is_configured():
        joinable = [e for e in meetings if autojoin.meeting_url(e)]
        add("auto_join", f"{n(len(joinable), 'external video call', 'external video calls')} in the next 3 days I could take for you.",
            len(joinable))
    add("slack_answers", f"{n(len(dms), 'teammate asked you a question', 'teammates asked you questions')} on Slack.", len(dms))
    # Lead with jobs that produce a draft to approve: that's the fastest "first win".
    priority = {"inbound_leads": 0, "scheduling": 1, "support": 2, "stale_deals": 3, "slack_answers": 4, "auto_join": 5,
                "meeting_prep": 6}
    out.sort(key=lambda s: (priority.get(s["template"], 9), -s["count"]))
    return out
