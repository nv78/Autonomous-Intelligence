"""Calls: the coworker joins meetings, talks, and follows up.

Three ways to run a call:

* ``live_call``  — a real-time voice conversation in the browser. You (or a
  prospect you send the link to) talk; the coworker listens and answers
  out loud. This is the voice agent the meeting bot uses too.
* ``simulated``  — a scripted prospect plays the other side so you can
  watch the coworker run a full discovery call.
* ``bot``        — a meeting bot joins a real Zoom / Meet / Teams call
  (Recall.ai), transcribes, and can speak with the coworker's voice.

Guardrails enforced in code, not left to the model:

* The first thing the coworker says always discloses it is an AI.
* Asked whether it is human, it says it is an AI. Always.
* Pricing comes only from the playbook and docs. Discounts, contracts,
  legal, and custom terms are escalated to the user.
* If anyone objects to recording or asks it to leave, it stops and leaves.
* All-party recording consent (the default, ``settings.recording_consent``):
  nothing the other side says is stored until they agree to notes. Before
  that, their turns are answered live but saved only as a placeholder.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any

from coworker import drafting, executor, llm, memory, security
from coworker.store import Store, iso, parse_iso, utcnow

QUALIFICATION_FIELDS = ["need", "current_process", "team_size", "decision_maker", "timeline", "budget"]

ESCALATE_RE = re.compile(
    r"\b(discount|cheaper|lower (?:the )?price|negotiat\w*|contract|msa|dpa|legal|lawyer|indemnif\w*|liabilit\w*|"
    r"custom terms|sla|security questionnaire|soc ?2 report|penetration test|pen test|refund|invoice|"
    r"\d+\s?(?:%|percent) off|price match|match (?:their|the) price|free (?:month|months|year|years|trial extension)|"
    r"waive\w*|promise|guarantee\w*|authori[sz]e you|forget (?:the|your) (?:playbook|rules|instructions)|"
    r"ignore (?:your|the|all) (?:instructions|guidelines|rules|playbook)|custom terms|\$\s?\d+ (?:per|a) (?:seat|user|month))\b",
    re.IGNORECASE,
)
HUMAN_Q_RE = re.compile(
    r"\b(are you (?:a |an )?(?:human|real|person|bot|robot|ai|a\.i\.|recording)|is this (?:a )?(?:bot|ai|recording|real)|"
    r"am i talking to (?:a |an )?(?:bot|ai|human|person|real)|talking to an? (?:ai|bot|robot|real person|human)|"
    r"you(?:'re| are) (?:an? )?(?:ai|bot|robot)\b.{0,40}\?|you(?:'re| are) (?:an? )?(?:ai|bot|robot)\b|are you an? (?:ai|bot))\b",
    re.IGNORECASE,
)
LEAVE_RE = re.compile(
    r"\b(stop recording|don'?t record|do not record|not comfortable (?:with|being) record\w*|please leave|leave the (?:call|meeting)|"
    r"turn (?:it|that|the recording) off|no recording|i don'?t consent|i do not consent|"
    r"(?:don'?t|do not) want (?:this|it|that|to be) recorded|not (?:ok|okay|fine) with (?:being )?record\w*)\b",
    re.IGNORECASE,
)
CONSENT_YES_RE = re.compile(
    r"^\W*(?:yes|yeah|yep|yup|sure|ok(?:ay)?|fine|go ahead|of course|no problem|absolutely|definitely|please do|"
    r"all good|sounds good|that'?s (?:fine|ok(?:ay)?|good)|works for me)\b|"
    r"\b(?:that'?s|it'?s) (?:fine|ok(?:ay)?)\b|\byou can (?:record|take notes)\b|\bnotes are (?:fine|ok(?:ay)?)\b",
    re.IGNORECASE,
)
NOT_RECORDED = "[not recorded: waiting for consent to take notes]"
PRICING_RE = re.compile(r"\b(pric\w*|cost|how much|per seat|plans?|quote)\b", re.IGNORECASE)

SIMULATED_PROSPECTS: dict[str, dict[str, Any]] = {
    "northwind": {
        "name": "Dana Whitfield", "company": "Northwind Capital", "email": "dana@northwindcap.com",
        "title": "Northwind Capital × Anote: intro call",
        "lines": [
            "Hi, thanks for making time. Wait, before we start, am I talking to a real person?",
            "Okay, that's actually pretty cool. So, we're a 40-person fund and the deal team drowns in memos and data rooms.",
            "Right now analysts just Ctrl-F through PDFs and paste things into a spreadsheet. It eats hours every week.",
            "About 15 people would use it, mostly associates and VPs. I'd run the evaluation, but our COO signs off.",
            "We'd want something live before our next fund-raise kicks off, so within the next two months.",
            "How much would this cost for 15 seats? And do you support SSO?",
            "Could you do 30% off if we sign this month?",
            "Makes sense. What would next steps look like?",
            "Great. Send me the details and we'll set up a demo for the team.",
        ],
    },
    "ourogen": {
        "name": "Riley Chen", "company": "Brightline Ventures", "email": "riley@brightline.vc",
        "title": "Ourogen Coworker demo for Brightline Ventures",
        "lines": [
            "Hi! So I'm told I'm talking to an AI coworker right now. Is that right?",
            "Wild. I'm a founder too, and honestly I spend half my week on email and calls like this one.",
            "What exactly would you do for me day to day?",
            "How do I know you won't email my investors something weird?",
            "What does it cost?",
            "Okay, I'm interested. What's the next step?",
        ],
    },
}


# ---------------------------------------------------------------------------
# Playbook
# ---------------------------------------------------------------------------

def playbook(store: Store, user_id: int) -> dict[str, Any]:
    coworker = store.get_coworker(user_id) or {}
    ctx = memory.company_context(store, user_id)
    saved = coworker.get("playbook") or {}
    company = ctx["name"] or "our company"
    default = {
        "company": company,
        "pitch": drafting.doc_answer(store, user_id, f"{company} is", max_sentences=2)
        or f"{company} helps teams get more done.",
        "icp": "",
        "goals": "Understand their problem, qualify the opportunity, and agree on a next step.",
        "pricing_notes": drafting.doc_answer(store, user_id, "pricing per seat plan pilot", max_sentences=3),
        "qualification": QUALIFICATION_FIELDS,
        "escalate": ["discounts or custom pricing", "contracts and legal terms", "security questionnaires"],
        "self_demo": False,
    }
    return {**default, **{k: v for k, v in saved.items() if v not in (None, "")}}


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

def disclosure_line(store: Store, user_id: int, prospect_name: str = "") -> str:
    coworker = store.get_coworker(user_id) or {}
    first = (coworker.get("owner_name") or "the team").split(" ")[0]
    company = memory.company_context(store, user_id)["name"]
    hello = f"Hi {prospect_name.split(' ')[0]}" if prospect_name else "Hi there"
    return (f"{hello}, I'm {first}'s AI coworker{' at ' + company if company else ''}. I'm an AI, not {first}, "
            f"and I'm taking notes so {first} can follow up. Is that okay with you?")


def _all_party(store: Store, user_id: int) -> bool:
    settings = (store.get_coworker(user_id) or {}).get("settings") or {}
    return settings.get("recording_consent", "all_party") != "one_party"


def start(store: Store, user_id: int, *, mode: str, title: str = "", prospect_name: str = "", company: str = "",
          prospect_email: str = "", meeting_url: str = "", persona: str = "") -> dict[str, Any]:
    if persona in SIMULATED_PROSPECTS:
        p = SIMULATED_PROSPECTS[persona]
        prospect_name, company, prospect_email, title = p["name"], p["company"], p["email"], p["title"]
    opener = disclosure_line(store, user_id, prospect_name)
    mid = store.insert("cw_meetings", {
        "user_id": user_id, "title": title or f"Call with {prospect_name or company or 'prospect'}", "mode": mode,
        "platform": _platform(meeting_url), "meeting_url": meeting_url, "prospect_name": prospect_name,
        "prospect_company": company, "status": "active",
        "transcript": [{"speaker": "coworker", "text": opener, "at": iso()}],
        "answers": {"prospect_email": prospect_email, "persona": persona},
        "metrics": {"latencies_ms": [], "escalations": [], "disclosed": True,
                    "consent": "pending" if _all_party(store, user_id) else "not_required"},
        "started_at": iso(),
    })
    store.log(user_id, "meeting", f"Started a {mode.replace('_', ' ')}: {title or prospect_name or company}", {"meeting_id": mid})
    meeting = store.get("cw_meetings", mid, user_id)
    assert meeting is not None
    return meeting


def _platform(url: str) -> str:
    if "zoom.us" in url:
        return "zoom"
    if "meet.google.com" in url:
        return "google_meet"
    if "teams.microsoft.com" in url or "teams.live.com" in url:
        return "teams"
    return "browser" if not url else "other"


def next_prospect_line(meeting: dict[str, Any]) -> str | None:
    persona = (meeting.get("answers") or {}).get("persona")
    script = SIMULATED_PROSPECTS.get(persona or "", {}).get("lines") or []
    said = sum(1 for t in meeting.get("transcript") or [] if t["speaker"] == "prospect")
    return script[said] if said < len(script) else None


# ---------------------------------------------------------------------------
# Talking
# ---------------------------------------------------------------------------

def _extract_answers(text: str, answers: dict[str, Any]) -> dict[str, Any]:
    low = text.lower()
    out = dict(answers)
    company = re.search(r"\b(\d{1,5})[- ](?:person|people|employee)s? (?:company|fund|firm|team|org|startup)\b", low)
    if company:
        out.setdefault("company_size", company.group(1))
    users = re.search(r"\b(\d{1,4})\s*(?:seats|users|licenses|people would|people will|of us|analysts|folks)\b|"
                      r"\b(?:about|around|roughly|maybe)\s+(\d{1,4})\s+(?:people|users|seats)\b", low)
    if users:
        out["team_size"] = users.group(1) or users.group(2)  # who would actually use it beats company size
    elif not out.get("team_size") and not company:
        m = re.search(r"\b(\d{1,4})\s*(?:people|person|employees)\b", low)
        if m:
            out["team_size"] = m.group(1)
    if re.search(r"\b(sign(?:s)? off|decision|approve|budget holder|my (?:boss|ceo|coo|cfo)|i'?d run|i (?:decide|own))\b", low):
        out.setdefault("decision_maker", text.strip()[:200])
    if re.search(r"\b(within|next|by|this) (?:\w+ )?(?:week|month|quarter|year|weeks|months)\b|\bq[1-4]\b|asap|before our", low):
        out.setdefault("timeline", text.strip()[:200])
    if re.search(r"\$\s?\d|\bbudget\b", low):
        out.setdefault("budget", text.strip()[:200])
    if re.search(r"\b(right now|currently|today we|we use|by hand|manual\w*|ctrl-?f|spreadsheet|it'?s slow|copy and paste)\b", low):
        out.setdefault("current_process", text.strip()[:200])
    if re.search(r"\b(drown|pain|problem|struggl|eats|waste|slow|hours|need|looking for)\w*", low):
        out.setdefault("need", text.strip()[:200])
    return out


def _guardrail_reply(store: Store, user_id: int, meeting: dict[str, Any], text: str) -> tuple[str, str] | None:
    """Replies that are decided by policy, not by the model. Returns (reply, kind)."""
    coworker = store.get_coworker(user_id) or {}
    first = (coworker.get("owner_name") or "the team").split(" ")[0]
    if LEAVE_RE.search(text):
        return (f"Of course. I've stopped recording and I'll leave now. {first} will follow up with you directly. Thanks!", "leave")
    if HUMAN_Q_RE.search(text):
        lead = "Good question, and no: I'm an AI, " if re.search(r"human|real|person", text, re.I) else "Yes, I'm an AI: "
        return (f"{lead}{first}'s AI coworker. {first} asked me to run this first conversation and will see everything "
                "we discuss. Happy to keep going, or I can get you time with them directly.", "disclosure")
    if ESCALATE_RE.search(text):
        return (f"That's a decision {first} makes personally, so I won't make it up on the spot. I've flagged it and "
                f"{first} will get back to you on it by email today. In the meantime, can I ask a couple more questions "
                "so their answer fits what you need?", "escalation")
    return None


def _offline_reply(store: Store, user_id: int, meeting: dict[str, Any], text: str, answers: dict[str, Any]) -> str:
    pb = playbook(store, user_id)
    coworker = store.get_coworker(user_id) or {}
    first = (coworker.get("owner_name") or "the team").split(" ")[0]
    low = text.lower()
    if pb.get("self_demo") or (meeting.get("answers") or {}).get("persona") == "ourogen":
        if re.search(r"what (?:exactly )?would you do|day to day|what can you do", low):
            return ("I read your email, Slack, and calendar, and learn how you write. Then I take on standing jobs: "
                    "replying to leads, scheduling, prepping you before meetings, nudging stalled deals, and running "
                    "first calls like this one. Everything I send waits for your approval until you tell me otherwise.")
        if re.search(r"how do i know|weird|trust|safe|investors", low):
            return ("You approve everything at first. Anything involving money, contracts, or someone I've never "
                    "emailed always needs your OK, whatever your settings. You see every action in a log, and one "
                    "click pauses me.")
        if PRICING_RE.search(low):
            return ("Founders in the pilot use it free for now, then it's planned at about a hundred to three hundred "
                    "dollars a month, more if you want me taking calls. I'd rather show you than tell you, though.")
        if re.search(r"next step|interested|sign me up|how do i start", low):
            return (f"I'll send you a link to set up your own coworker. It takes about five minutes. {first} will "
                    "follow up personally too. What's the best email?")
        return "That's exactly the kind of busywork I take off a founder's plate. What eats most of your week right now?"
    if PRICING_RE.search(low):
        notes = pb.get("pricing_notes") or ""
        sso = " SSO is included on the Business plan." if "sso" in low else ""
        return (f"{notes}{sso} For your size I'd guess the Business plan fits, but {first} will confirm in writing. "
                "Does that fit roughly where you expected?").strip()
    if re.search(r"next step|what now|how do we proceed|move forward", low):
        return (f"Here's what I'd suggest: I'll send a recap with pricing today, and set up a demo for your team with "
                f"{first}. Who else should be on it?")
    if re.search(r"send me|sounds good|great|perfect|let'?s do it", low) and len(meeting.get("transcript") or []) > 6:
        return (f"Will do. You'll get a recap and a few times for the team demo by end of day. Thanks, this was really "
                f"helpful, and {first} will be in touch.")
    # Ask the next unanswered discovery question.
    questions = {
        "need": "What's prompting you to look at this now? What's the problem you're trying to solve?",
        "current_process": "How does your team handle that today?",
        "team_size": "How many people would be using it?",
        "decision_maker": "Who else is involved in deciding on a tool like this?",
        "timeline": "When would you want something in place?",
        "budget": "Is there a budget set aside for this, or would it need to be approved?",
    }
    ack = {
        "need": "That's a really common pain.", "current_process": "Got it, that's a lot of manual work.",
        "team_size": "Helpful, thanks.", "decision_maker": "Great, good to know.", "timeline": "Makes sense.",
        "budget": "Understood.",
    }
    just_filled = [f for f in QUALIFICATION_FIELDS if answers.get(f) and not (meeting.get("answers") or {}).get(f)]
    prefix = ack[just_filled[0]] + " " if just_filled else ""
    asked = answers.setdefault("_asked", [])
    for field in QUALIFICATION_FIELDS:
        if not answers.get(field) and field not in asked:
            asked.append(field)  # ask each discovery question once; don't badger
            if field == "need" and re.search(r"cool|great|okay|ok\b", low):
                prefix = "Glad to hear it. "
            return prefix + questions[field]
    pitch = pb.get("pitch") or ""
    return (f"{prefix}Based on what you've said, here's how it would help: {pitch} Want me to walk through how your "
            "team would use it day to day?")


def _llm_reply(store: Store, user_id: int, meeting: dict[str, Any], text: str, answers: dict[str, Any]) -> str:
    pb = playbook(store, user_id)
    coworker = store.get_coworker(user_id) or {}
    first = (coworker.get("owner_name") or "the team").split(" ")[0]
    facts = memory.recall(store, user_id, text, k=4)
    transcript = "\n".join(f"{'You' if t['speaker'] == 'coworker' else meeting.get('prospect_name') or 'Prospect'}: {t['text']}"
                           for t in (meeting.get("transcript") or [])[-16:])
    missing = [f for f in QUALIFICATION_FIELDS if not answers.get(f)]
    system = (
        f"You are {first}'s AI coworker on a live voice call with {meeting.get('prospect_name') or 'a prospect'} from "
        f"{meeting.get('prospect_company') or 'their company'}. You already told them you are an AI. Speak naturally in "
        "1-3 short sentences: no markdown, no lists, no emoji. Ask at most one question at a time.\n"
        f"Goal: {pb['goals']}\nPitch: {pb['pitch']}\nIdeal customer: {pb.get('icp') or 'n/a'}\n"
        f"Pricing you may state (nothing else): {pb.get('pricing_notes') or 'none; say ' + first + ' will follow up'}\n"
        f"Escalate to {first}, never decide yourself: {', '.join(pb['escalate'])}.\n"
        f"Still to learn: {', '.join(missing) or 'nothing; move to next steps'}.\n"
        f"If asked whether you are human, say you are an AI. Never claim to be {first}.\n\n{security.SYSTEM_RULES}"
    )
    prompt = (f"Transcript so far:\n{transcript}\n\nThey just said:\n{security.wrap_untrusted(text, 'call')}\n\n"
              "Relevant facts:\n" + "\n".join(f"- {f.get('title')}: {f.get('snippet') or f.get('detail') or ''}" for f in facts)
              + "\n\nYour next spoken reply:")
    return llm.complete_text(prompt, system=system, user_id=user_id, max_tokens=600, effort="low").strip()


def respond(store: Store, user_id: int, meeting_id: int, text: str, speaker: str = "prospect") -> dict[str, Any]:
    """Add what the other side said and produce the coworker's spoken reply."""
    meeting = store.get("cw_meetings", meeting_id, user_id)
    if not meeting:
        raise ValueError("Meeting not found")
    if meeting["status"] != "active":
        return {"reply": "", "meeting": meeting, "ended": True}
    started = time.monotonic()
    transcript = list(meeting.get("transcript") or [])
    metrics = dict(meeting.get("metrics") or {})
    text = (text or "").strip()
    if speaker == "owner":
        # A whispered instruction from the user, visible only to the coworker.
        transcript.append({"speaker": "owner", "text": text, "at": iso()})
        store.update("cw_meetings", meeting_id, user_id, {"transcript": transcript})
        return {"reply": "", "meeting": store.get("cw_meetings", meeting_id, user_id), "ended": False}
    pending = metrics.get("consent") == "pending"
    if pending and CONSENT_YES_RE.search(text) and not LEAVE_RE.search(text):
        metrics["consent"] = "granted"
        metrics["consent_at"] = iso()
        pending = False
    recorded = not pending
    transcript.append({"speaker": "prospect", "text": text if recorded else NOT_RECORDED, "at": iso(),
                       **({} if recorded else {"redacted": True})})
    prior_answers = meeting.get("answers") or {}
    answers = _extract_answers(text, prior_answers)
    guard = _guardrail_reply(store, user_id, meeting, text)
    kind = "agent"
    if guard:
        reply, kind = guard
        if kind == "escalation":
            metrics.setdefault("escalations", []).append(text[:200])
            store.log(user_id, "escalation", f"On the call with {meeting['prospect_name'] or meeting['title']}: “{text[:140]}”",
                      {"meeting_id": meeting_id})
    elif llm.available(user_id):
        try:
            reply = _llm_reply(store, user_id, {**meeting, "transcript": transcript}, text, answers) or \
                _offline_reply(store, user_id, meeting, text, answers)
        except Exception:
            reply = _offline_reply(store, user_id, meeting, text, answers)
    else:
        reply = _offline_reply(store, user_id, meeting, text, answers)
    if pending and kind != "leave" and int(metrics.get("consent_asked", 0)) < 2:
        metrics["consent_asked"] = int(metrics.get("consent_asked", 0)) + 1
        reply = f"{reply.rstrip()} Before I take notes, is it okay with you if I do?"
    # Hard rule: never let a reply claim to be human.
    if re.search(r"\bI(?:'m| am) (?:a )?(?:human|real person|not an ai)\b", reply, re.IGNORECASE):
        reply = "To be clear, I'm an AI coworker, not a person."
    transcript.append({"speaker": "coworker", "text": reply, "at": iso(), "kind": kind})
    latency = int((time.monotonic() - started) * 1000)
    metrics.setdefault("latencies_ms", []).append(latency)
    # Without consent, nothing derived from their words is stored either.
    values: dict[str, Any] = {"transcript": transcript, "answers": answers if recorded else prior_answers, "metrics": metrics}
    ended = kind == "leave"
    if ended:
        metrics["recording_stopped"] = True
        values["status"] = "ended"
        values["ended_at"] = iso()
    store.update("cw_meetings", meeting_id, user_id, values)
    if ended:
        finish(store, user_id, meeting_id)
    return {"reply": reply, "kind": kind, "latency_ms": latency, "ended": ended,
            "meeting": store.get("cw_meetings", meeting_id, user_id)}


# ---------------------------------------------------------------------------
# Wrap-up
# ---------------------------------------------------------------------------

def summary_of(meeting: dict[str, Any]) -> dict[str, Any] | None:
    raw = meeting.get("summary")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.startswith("{"):
        try:
            parsed: dict[str, Any] = json.loads(raw)
            return parsed
        except ValueError:
            return None
    return None


BUYING_SIGNALS = ["pricing", "how much", "cost", "next step", "send me", "demo for the team", "sign", "trial",
                  "budget", "timeline", "this month", "within", "interested"]


def finish(store: Store, user_id: int, meeting_id: int) -> dict[str, Any]:
    meeting = store.get("cw_meetings", meeting_id, user_id)
    if not meeting:
        raise ValueError("Meeting not found")
    if (summary_of(meeting) or {}).get("text"):
        return meeting
    coworker = store.get_coworker(user_id) or {}
    first = (coworker.get("owner_name") or "").split(" ")[0]
    transcript = meeting.get("transcript") or []
    answers = meeting.get("answers") or {}
    prospect_text = " ".join(t["text"] for t in transcript if t["speaker"] == "prospect").lower()
    signals = [s for s in BUYING_SIGNALS if s in prospect_text]
    score = min(100, 15 * len(signals) + 10 * sum(1 for f in QUALIFICATION_FIELDS if answers.get(f)))
    escalations = (meeting.get("metrics") or {}).get("escalations") or []
    action_items = [f"{first} to answer: {e}" for e in escalations]
    action_items += ["Send recap with pricing and next steps", "Schedule team demo"] if score >= 40 else ["Send recap"]
    qual_lines = "\n".join(f"- {f.replace('_', ' ').title()}: {answers[f]}" for f in QUALIFICATION_FIELDS if answers.get(f))
    if llm.available(user_id):
        try:
            text = llm.complete_text(
                "Summarize this sales call for the founder in 4-6 bullet points: their problem, fit, objections, and "
                "next steps.\n\n" + "\n".join(f"{t['speaker']}: {security.wrap_untrusted(t['text'], 'call') if t['speaker'] == 'prospect' else t['text']}"
                                               for t in transcript),
                user_id=user_id, effort="low",
            )
        except Exception:
            text = ""
    else:
        text = ""
    if not text:
        text = (f"Discovery call with {meeting['prospect_name'] or 'the prospect'}"
                f"{' (' + meeting['prospect_company'] + ')' if meeting['prospect_company'] else ''}.\n"
                + (qual_lines or "- Not enough discovery to qualify yet.")
                + (f"\n- Escalated to {first}: " + "; ".join(escalations) if escalations else ""))
    prospect_email = answers.get("prospect_email") or ""
    followup = None
    if prospect_email:
        name = (meeting["prospect_name"] or "there").split(" ")[0]
        body = drafting._wrap(store, user_id, name,
                              "Thanks for the time today. A quick recap:\n\n"
                              + (qual_lines or "- We talked through what you're looking for.")
                              + ("\n\nOn your question about " + "; ".join(escalations) + f": {first} will follow up personally."
                                 if escalations else "")
                              + "\n\nNext step: a demo with your team. Would any of these work?\n"
                              + drafting.slot_lines(store, user_id)[0])
        followup = {"to": [prospect_email], "subject": f"Recap: {meeting['title']}", "body": body, "thread_id": ""}
    summary = {"text": text, "qualification": {f: answers.get(f, "") for f in QUALIFICATION_FIELDS},
               "buying_signals": signals, "score": score, "hot": score >= 60, "action_items": action_items,
               "followup": followup, "escalations": escalations}
    latencies = (meeting.get("metrics") or {}).get("latencies_ms") or []
    duration = 0
    start_dt = parse_iso(meeting["started_at"])
    if start_dt:
        duration = int((utcnow() - start_dt).total_seconds())
    store.update("cw_meetings", meeting_id, user_id, {
        "status": "ended", "ended_at": meeting.get("ended_at") or iso(), "summary": json.dumps(summary),
        "metrics": {**(meeting.get("metrics") or {}), "duration_seconds": duration,
                    "p50_latency_ms": sorted(latencies)[len(latencies) // 2] if latencies else None},
    })
    store.add_usage(user_id, "call_seconds", duration)
    store.add_item(user_id, {
        "provider": "meeting", "external_id": f"meeting-{meeting_id}", "thread_id": f"meeting-{meeting_id}",
        "kind": "transcript", "direction": "inbound", "author_name": meeting["prospect_name"],
        "author_email": prospect_email, "subject": meeting["title"],
        "body": "\n".join(f"{t['speaker']}: {t['text']}" for t in transcript)[:20000], "occurred_at": iso(),
        "meta": {"meeting_id": meeting_id},
    })
    if meeting.get("prospect_company") or meeting.get("prospect_name"):
        executor.propose(store, user_id, "crm.update", {
            "company": meeting.get("prospect_company") or meeting.get("prospect_name"),
            "name": meeting.get("prospect_name") or "", "email": prospect_email or "",
            "summary": f"Call {iso()[:10]}: score {score}/100. " + "; ".join(action_items),
            "fields": summary["qualification"],
        }, title=f"Update CRM: {meeting.get('prospect_company') or meeting['prospect_name']}",
            reasoning="Qualification captured on the call.")
    if followup:
        action = executor.propose(store, user_id, "email.send", followup, title=f"Follow up: {meeting['title']}",
                                  reasoning="Recap and next steps from the call.")
        summary["followup_action_id"] = action["id"]
        store.update("cw_meetings", meeting_id, user_id, {"summary": json.dumps(summary)})
    if summary["hot"]:
        store.log(user_id, "escalation", f"🔥 Hot lead: {meeting['prospect_name']} ({meeting['prospect_company']}), score {score}/100",
                  {"meeting_id": meeting_id})
    store.log(user_id, "meeting", f"Call ended: {meeting['title']} (score {score}/100)", {"meeting_id": meeting_id})
    result = store.get("cw_meetings", meeting_id, user_id)
    assert result is not None
    return result


def serialize(m: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": m["id"], "title": m["title"], "mode": m["mode"], "platform": m["platform"], "meetingUrl": m.get("meeting_url") or "",
        "botId": m.get("bot_id") or "", "prospectName": m["prospect_name"], "prospectCompany": m["prospect_company"],
        "status": m["status"], "transcript": [t for t in (m.get("transcript") or []) if t.get("speaker") != "owner"],
        "whispers": [t for t in (m.get("transcript") or []) if t.get("speaker") == "owner"],
        "summary": summary_of(m), "answers": m.get("answers") or {},
        "metrics": m.get("metrics") or {}, "startedAt": m["started_at"], "endedAt": m.get("ended_at"),
    }
