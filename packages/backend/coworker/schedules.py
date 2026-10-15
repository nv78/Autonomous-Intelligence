"""Scheduled tasks: recurring jobs the coworker runs on its own.

"Every weekday at 8:30 tell me what's on my plate", "every Monday at 9 post
the pipeline in #sales", "on the 1st of each month email clients with
overdue invoices". A scheduled task is a responsibility with template
``scheduled`` and a trigger like::

    {"type": "schedule", "freq": "weekly", "days": ["mon"], "time": "09:00",
     "deliver": ["chat", "email"], "chat_id": 12}

``freq`` is ``daily``, ``weekdays``, ``weekly`` (``days``), ``monthly``
(``day``, clamped to the month's last day) or ``hourly`` (``every_hours``).
Times are in the owner's time zone, so 9am stays 9am across DST.

Each occurrence runs once: the claim key is ``sched:<occurrence UTC>`` in
``cw_runs``, so several workers can tick safely. An occurrence missed by up
to ``GRACE`` (worker restart, deploy) still runs; older ones are skipped.

A run sends the task's instruction through the same reasoning loop and
tools as chat (``channels.ask``). Write actions go through the executor at
the task's autonomy level and the organization's ceilings, so "approve"
tasks leave a card to approve and "notify" tasks just do it. The result is
posted to the task's own chat, and optionally emailed or pushed.
"""
from __future__ import annotations

import calendar
import re
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from coworker.store import Store, iso, parse_iso, utcnow

GRACE = timedelta(hours=2)
MAX_ATTEMPTS = 3
RETRY_AFTER = (timedelta(minutes=2), timedelta(minutes=10))  # before attempts 2 and 3
FREQS = ("daily", "weekdays", "weekly", "monthly", "hourly")
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
DAY_NAMES = {"monday": "mon", "tuesday": "tue", "wednesday": "wed", "thursday": "thu", "friday": "fri",
             "saturday": "sat", "sunday": "sun", "mon": "mon", "tue": "tue", "tues": "tue", "wed": "wed",
             "thu": "thu", "thur": "thu", "thurs": "thu", "fri": "fri", "sat": "sat", "sun": "sun"}
DELIVERY = ("chat", "email", "push", "sms")
_DAY = r"(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tues?|wed|thu(?:rs?)?|fri|sat|sun)"


# -- the schedule itself ---------------------------------------------------------------

def clean(raw: dict[str, Any]) -> dict[str, Any]:
    """A valid trigger spec from user or model input. Raises ValueError when it can't be one."""
    freq = str(raw.get("freq") or "").lower()
    if freq not in FREQS:
        raise ValueError("freq must be one of " + ", ".join(FREQS))
    hh, mm = _hm(str(raw.get("time") or "09:00"))
    spec: dict[str, Any] = {"type": "schedule", "freq": freq, "time": f"{hh:02d}:{mm:02d}"}
    if freq == "weekly":
        days = [_day(str(d)) for d in raw.get("days") or []]
        spec["days"] = [d for d in DAYS if d in days] or ["mon"]
    if freq == "monthly":
        spec["day"] = min(31, max(1, int(raw.get("day") or 1)))
    if freq == "hourly":
        spec["every_hours"] = min(24, max(1, int(raw.get("every_hours") or 1)))
    deliver = [d for d in raw.get("deliver") or ["chat"] if d in DELIVERY]
    spec["deliver"] = deliver if "chat" in deliver else ["chat", *deliver]
    if raw.get("chat_id"):
        spec["chat_id"] = int(raw["chat_id"])
    return spec


def _day(word: str) -> str:
    word = word.strip().lower()
    return DAY_NAMES.get(word) or DAY_NAMES.get(word.rstrip("s")) or ""


def _hm(value: str) -> tuple[int, int]:
    m = re.fullmatch(r"\s*(\d{1,2})(?::(\d{2}))?\s*", value)
    if not m or int(m.group(1)) > 23 or int(m.group(2) or 0) > 59:
        raise ValueError("time must be HH:MM (24-hour)")
    return int(m.group(1)), int(m.group(2) or 0)


def _matches(spec: dict[str, Any], d: date) -> bool:
    freq = spec["freq"]
    if freq in ("daily", "hourly"):
        return True
    if freq == "weekdays":
        return d.weekday() < 5
    if freq == "weekly":
        return DAYS[d.weekday()] in (spec.get("days") or ["mon"])
    last = calendar.monthrange(d.year, d.month)[1]
    return d.day == min(int(spec.get("day") or 1), last)


def _candidates(spec: dict[str, Any], tz: ZoneInfo, start: date, days: int) -> list[datetime]:
    """Occurrence instants (UTC) on local dates ``start`` .. ``start + days``."""
    hh, mm = _hm(spec["time"])
    out: list[datetime] = []
    for offset in range(days + 1):
        d = start + timedelta(days=offset)
        if not _matches(spec, d):
            continue
        if spec["freq"] == "hourly":
            step = int(spec.get("every_hours") or 1)
            times = [time(h, mm) for h in range(0, 24) if h % step == hh % step]
        else:
            times = [time(hh, mm)]
        out += [datetime.combine(d, t, tzinfo=tz).astimezone(ZoneInfo("UTC")) for t in times]
    return sorted(set(out))


def next_run(spec: dict[str, Any], tz: ZoneInfo, after: datetime | None = None) -> datetime | None:
    after = after or utcnow()
    local = after.astimezone(tz).date()
    for when in _candidates(spec, tz, local - timedelta(days=1), 400 if spec["freq"] == "monthly" else 9):
        if when > after:
            return when
    return None


def due(spec: dict[str, Any], tz: ZoneInfo, now: datetime | None = None, not_before: datetime | None = None) -> datetime | None:
    """The latest occurrence at or before ``now`` that's still inside the grace window, if any."""
    now = now or utcnow()
    floor = max(now - GRACE, not_before) if not_before else now - GRACE
    local = now.astimezone(tz).date()
    hits = [w for w in _candidates(spec, tz, local - timedelta(days=1), 1) if floor <= w <= now]
    return hits[-1] if hits else None


def describe(spec: dict[str, Any]) -> str:
    hh, mm = _hm(spec.get("time") or "09:00")
    at = time(hh, mm).strftime("%I:%M %p").lstrip("0").replace(":00 ", " ")
    freq = spec.get("freq")
    if freq == "hourly":
        n = int(spec.get("every_hours") or 1)
        return "Every hour" if n == 1 else f"Every {n} hours"
    if freq == "weekdays":
        return f"Every weekday at {at}"
    if freq == "weekly":
        names = [calendar.day_name[DAYS.index(d)] for d in spec.get("days") or ["mon"]]
        listed = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
        return f"Every {listed} at {at}"
    if freq == "monthly":
        day = int(spec.get("day") or 1)
        suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return f"On the {day}{suffix} of every month at {at}"
    return f"Every day at {at}"


# -- natural language --------------------------------------------------------------------

_TIME_RE = re.compile(r"\b(?:at|@)\s*(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)?\b|\b(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)\b"
                      r"|\b(?:at\s+)?(noon|midday|midnight)\b", re.I)
_PARTS_OF_DAY = {"morning": (8, 0), "afternoon": (14, 0), "evening": (18, 0), "night": (20, 0)}


def parse(text: str) -> dict[str, Any] | None:
    """A schedule from "every Monday at 9am …", or None when the text isn't a recurring request."""
    low = text.lower()
    spec: dict[str, Any] | None = None
    if m := re.search(r"\bevery\s+(\d{1,2})\s+hours?\b", low):
        spec = {"freq": "hourly", "every_hours": int(m.group(1))}
    elif re.search(r"\b(?:every|each)\s+hour\b|\bhourly\b", low):
        spec = {"freq": "hourly", "every_hours": 1}
    elif re.search(r"\b(?:every|each|on)\s+weekdays?\b|\bweekdays\b|\bmonday\s+(?:through|to|thru|-)\s+friday\b", low):
        spec = {"freq": "weekdays"}
    elif m := re.search(rf"\b(every|each|on)\s+((?:{_DAY}s?\b(?:\s*(?:,|and|&)\s*)?)+)", low):
        # "every Friday" / "on Fridays" recur; "on Friday" is a one-off
        if m.group(1) != "on" or re.search(rf"{_DAY}s\b", m.group(2)):
            spec = {"freq": "weekly", "days": [_day(d) for d in re.findall(rf"{_DAY}s?\b", m.group(2))]}
    if spec is None and (m := re.search(r"\b(?:on\s+)?the\s+(\d{1,2})(?:st|nd|rd|th)\s+(?:of\s+)?(?:every|each)\s+month\b"
                                        r"|\b(?:every|each)\s+month\s+on\s+the\s+(\d{1,2})(?:st|nd|rd|th)?\b", low)):
        spec = {"freq": "monthly", "day": int(m.group(1) or m.group(2))}
    elif spec is None and re.search(r"\b(?:every|each)\s+month\b|\bmonthly\b|\bfirst of (?:the|every|each) month\b", low):
        spec = {"freq": "monthly", "day": 1}
    elif spec is None and re.search(r"\b(?:every|each)\s+week\b|\bweekly\b", low):
        spec = {"freq": "weekly", "days": ["mon"]}
    elif spec is None and re.search(r"\b(?:every|each)\s+(?:day|morning|afternoon|evening|night)\b|\bdaily\b|\bnightly\b", low):
        spec = {"freq": "daily"}
    if spec is None:
        return None
    spec["time"] = _parse_time(low)
    return clean(spec)


def _parse_time(low: str) -> str:
    for m in _TIME_RE.finditer(low):
        if m.group(7):
            return "00:00" if m.group(7) == "midnight" else "12:00"
        hh = int(m.group(1) or m.group(4))
        mm = int(m.group(2) or m.group(5) or 0)
        ampm = (m.group(3) or m.group(6) or "").replace(".", "")
        if hh > 23 or mm > 59 or (ampm and hh > 12):
            continue
        if ampm == "pm" and hh < 12:
            hh += 12
        elif ampm == "am" and hh == 12:
            hh = 0
        elif not ampm and 1 <= hh <= 6:
            hh += 12  # "at 4" means 4pm for work tasks
        return f"{hh:02d}:{mm:02d}"
    for word, (hh, mm) in _PARTS_OF_DAY.items():
        if re.search(rf"\b{word}\b", low):
            return f"{hh:02d}:{mm:02d}"
    if re.search(r"\bend of (?:the )?day\b", low):
        return "17:00"
    return "09:00"


def strip_schedule(text: str) -> str:
    """The instruction without its schedule words, so a run doesn't try to schedule itself again."""
    out = re.sub(r"\b(?:every|each)\s+month\s+on\s+the\s+\d{1,2}(?:st|nd|rd|th)?\b"
                 r"|\b(?:every|each)\s+(?:\d{1,2}\s+hours?|hour|weekdays?|day|morning|afternoon|evening|night|week|month)\b"
                 rf"|\b(?:every|each|on)\s+(?:{_DAY}s?\b(?:\s*(?:,|and|&)\s*)?)+"
                 r"|\b(?:on\s+)?the\s+\d{1,2}(?:st|nd|rd|th)\s+(?:of\s+)?(?:every|each)\s+month\b"
                 r"|^\s*(?:hourly|daily|nightly|weekly|monthly)\b"  # "Daily at 7, …" (but keep "my weekly update")
                 r"|\bmonday\s+(?:through|to|thru|-)\s+friday\b", " ", text, flags=re.I)
    out = _TIME_RE.sub(" ", out)
    out = re.sub(r"\s+([,.!?])", r"\1", re.sub(r"\s{2,}", " ", out)).strip(" ,.-")
    return out[:1].upper() + out[1:] if out else text.strip()


def name_for(instruction: str) -> str:
    words = instruction.strip().rstrip(".").split()
    return " ".join(words[:8]) + ("…" if len(words) > 8 else "") if words else "Scheduled task"


# -- running -----------------------------------------------------------------------------

def _tz(store: Store, user_id: int) -> ZoneInfo:
    from coworker import scheduling

    return scheduling.tz_for(store.get_coworker(user_id) or {})


def state(store: Store, user_id: int, resp: dict[str, Any]) -> dict[str, Any]:
    """For the UI: the schedule in words, the next run, and recent runs."""
    spec = resp.get("trigger_spec") or {}
    try:
        nxt = next_run(spec, _tz(store, user_id)) if resp.get("enabled") else None
    except (KeyError, ValueError):
        return {"description": "Invalid schedule", "nextRun": None, "runs": []}
    runs = store.query("SELECT trigger_key, status, summary, created_at FROM cw_runs WHERE responsibility_id = %s "
                       "AND user_id = %s ORDER BY id DESC LIMIT 5", (resp["id"], user_id))
    return {"description": describe(spec), "nextRun": iso(nxt) if nxt else None, "deliver": spec.get("deliver") or ["chat"],
            "chatId": spec.get("chat_id"), "runs": [{"at": r["created_at"], "status": r["status"], "summary": r.get("summary") or ""}
                                                    for r in runs], "usage": usage(store, user_id, int(resp["id"]))}


def run(store: Store, user_id: int, resp: dict[str, Any], force: bool = False) -> list[str]:
    """Run the task if an occurrence is due (or now, with ``force``). Returns what happened, for the activity log."""
    from coworker import responsibilities

    if (store.get_coworker(user_id) or {}).get("status") != "active":
        return []  # paused: the kill switch stops scheduled work too
    spec = resp.get("trigger_spec") or {}
    try:
        when = utcnow() if force else due(spec, _tz(store, user_id), not_before=parse_iso(resp.get("created_at") or ""))
    except (KeyError, ValueError):
        return []
    if when is None:
        return []
    key = f"{'manual' if force else 'sched'}:{iso(when)}"
    run_id = responsibilities._claim(store, user_id, resp, key) or _retry(store, user_id, resp, key)
    if not run_id:
        return []
    from coworker import llm

    with llm.metering() as usage:
        try:
            answer = execute(store, user_id, resp)
        except Exception as exc:  # one failed run must not stop the others; it's visible in the task's history
            _failed(store, user_id, resp, run_id, exc)
            return []
    responsibilities._finish(store, run_id, answer["summary"][:500], usage=usage)
    return [f"Ran '{resp['name']}'"]


def _retry(store: Store, user_id: int, resp: dict[str, Any], key: str) -> int | None:
    """Take a failed occurrence back for another attempt once its backoff has passed (atomic, like a claim)."""
    row = store.one("SELECT * FROM cw_runs WHERE user_id = %s AND responsibility_id = %s AND trigger_key = %s",
                    (user_id, resp["id"], key))
    if not row or row["status"] != "retry":
        return None
    attempts = int(row.get("attempts") or 1)
    finished = parse_iso(row.get("finished_at") or "")
    if attempts >= MAX_ATTEMPTS or (finished and utcnow() - finished < RETRY_AFTER[min(attempts, len(RETRY_AFTER)) - 1]):
        return None
    taken = store.execute("UPDATE cw_runs SET status = 'running', attempts = %s, started_at = %s, finished_at = NULL "
                          "WHERE id = %s AND status = 'retry' AND attempts = %s", (attempts + 1, iso(), row["id"], attempts))
    return int(row["id"]) if taken else None


def _failed(store: Store, user_id: int, resp: dict[str, Any], run_id: int, exc: Exception) -> None:
    from coworker import responsibilities

    row = store.get("cw_runs", run_id) or {}
    attempts = int(row.get("attempts") or 1)
    if attempts < MAX_ATTEMPTS:
        responsibilities._finish(store, run_id, f"attempt {attempts} failed; retrying", "retry", str(exc))
        return
    responsibilities._finish(store, run_id, f"failed after {attempts} attempts: {exc}"[:500], "failed", str(exc))
    store.log(user_id, "escalation", f"Scheduled task '{resp['name']}' failed {attempts} times: {exc}",
              {"responsibility_id": resp["id"]})
    import observability
    from coworker import notify, push

    observability.alert(f"task_failed:{resp['id']}", "A scheduled task failed every attempt", user_id=user_id,
                        responsibility_id=resp["id"], error=str(exc)[:300])
    body = (f"Your scheduled task “{resp['name']}” ({describe(resp.get('trigger_spec') or {}).lower()}) failed "
            f"{attempts} times:\n\n{exc}\n\nIt will try again at its next scheduled time. Run it now or edit it in "
            "Coworker → Responsibilities.")
    try:
        notify.deliver(store, user_id, f"Scheduled task failed: {resp['name']}", body)
        push.send(store, user_id, "A scheduled task failed", resp["name"])
    except Exception as notify_exc:  # telling the owner must not raise from the worker loop
        observability.capture(notify_exc, where="schedules.notify_failure")


def execute(store: Store, user_id: int, resp: dict[str, Any]) -> dict[str, Any]:
    from coworker import channels

    spec = dict(resp.get("trigger_spec") or {})
    prompt = (f"This is a scheduled run of your task “{resp['name']}” ({describe(spec).lower()}). Do it now and report "
              f"the result briefly. Don't create or change responsibilities.\n\nTask: {resp['instruction']}")
    answer = channels.ask(store, user_id, prompt, chat_id=spec.get("chat_id"), chat_name=f"⏰ {resp['name']}",
                          responsibility=resp, show_prompt=f"⏰ Scheduled run: {resp['instruction']}")
    if answer["chat_id"] and answer["chat_id"] != spec.get("chat_id"):
        store.update("cw_responsibilities", resp["id"], user_id, {"trigger_spec": {**spec, "chat_id": answer["chat_id"]}})
    deliver = spec.get("deliver") or ["chat"]
    subject = f"{resp['name']}: {answer['summary'][:80]}"
    if "email" in deliver:
        from coworker import notify

        notify.deliver(store, user_id, subject, answer["text"])
    if "push" in deliver:
        from coworker import push

        push.send(store, user_id, resp["name"], answer["summary"][:180], {"chatId": answer["chat_id"]})
    if "sms" in deliver:
        from coworker import sms

        sms.notify(store, user_id, f"{resp['name']}: {answer['text']}", "tasks")
    return answer


# -- usage per task -------------------------------------------------------------------------------

READ_MINUTES = 5  # a report or briefing the owner would otherwise have put together themselves


def usage(store: Store, user_id: int, resp_id: int, days: int = 30) -> dict[str, Any]:
    """Runs, model spend, actions, and an estimate of time saved for one task over ``days``."""
    from coworker import metrics

    since = iso(utcnow() - timedelta(days=days))
    runs = store.query("SELECT status, tokens, cost_micros FROM cw_runs WHERE user_id = %s AND responsibility_id = %s "
                       "AND created_at >= %s", (user_id, resp_id, since))
    actions = store.query("SELECT type, status FROM cw_actions WHERE user_id = %s AND responsibility_id = %s AND created_at >= %s",
                          (user_id, resp_id, since))
    done = [r for r in runs if r["status"] == "done"]
    priced = all(r.get("cost_micros") is not None for r in done)
    executed = [a for a in actions if a["status"] == "executed"]
    minutes = len(done) * READ_MINUTES + sum(metrics.MINUTES_SAVED.get(a["type"], 3) for a in executed)
    return {
        "days": days, "runs": len(done), "failed": sum(1 for r in runs if r["status"] == "failed"),
        "tokens": sum(int(r.get("tokens") or 0) for r in runs),
        "costUsd": round(sum(int(r.get("cost_micros") or 0) for r in runs) / 1_000_000, 2) if priced else None,
        "actions": len(actions), "executed": len(executed), "hoursSaved": round(minutes / 60, 1),
    }


def spend(store: Store, user_id: int, days: int = 30) -> float:
    """Model spend on all of a user's scheduled runs (unpriced runs count as 0)."""
    row = store.one("SELECT SUM(cost_micros) AS c FROM cw_runs WHERE user_id = %s AND created_at >= %s",
                    (user_id, iso(utcnow() - timedelta(days=days))))
    return round(int((row or {}).get("c") or 0) / 1_000_000, 2)


# -- recipes ----------------------------------------------------------------------------------------

RECIPES: list[dict[str, Any]] = [
    {"id": "morning_briefing", "name": "Morning briefing", "category": "Daily",
     "instruction": "Tell me what's on my plate today: meetings with prep notes, emails waiting on me, and anything overdue.",
     "schedule": {"freq": "weekdays", "time": "08:00"},
     "sample": "3 meetings today. Prep for Northwind at 11 is below. 4 emails are waiting on you; Dana's is the oldest."},
    {"id": "inbox_sweep", "name": "Inbox sweep", "category": "Daily",
     "instruction": "Reply to my emails that are waiting on me.", "schedule": {"freq": "weekdays", "time": "10:00"},
     "sample": "Drafted 5 replies (2 leads, 2 scheduling, 1 support). They're waiting for your approval."},
    {"id": "end_of_day", "name": "End-of-day wrap", "category": "Daily",
     "instruction": "Wrap up my day: what got done, what's still waiting on me, and what's first tomorrow.",
     "schedule": {"freq": "weekdays", "time": "17:30"},
     "sample": "Done: 6 emails sent, 2 calls. Waiting on you: Globex pricing question. First tomorrow: Acme kickoff."},
    {"id": "pipeline_report", "name": "Weekly pipeline report", "category": "Weekly",
     "instruction": "Summarize my open deals: what moved this week, what is stuck, and who I should follow up with.",
     "schedule": {"freq": "weekly", "days": ["mon"], "time": "09:00"},
     "sample": "Moved: Northwind to pilot. Stuck: Globex (no reply in 9 days). Follow up with Kevin and Priya."},
    {"id": "status_update", "name": "Friday status update", "category": "Weekly",
     "instruction": "Draft my weekly status update to my team: what got done, what is next, and blockers.",
     "schedule": {"freq": "weekly", "days": ["fri"], "time": "16:00"},
     "sample": "Draft ready: 3 wins, 2 next steps, 1 blocker (legal review). Approve to send to the team."},
    {"id": "follow_up_check", "name": "Follow-up check", "category": "Weekly",
     "instruction": "List people I haven't followed up with this week and draft a short nudge to each.",
     "schedule": {"freq": "weekly", "days": ["thu"], "time": "14:00"},
     "sample": "4 threads went quiet after you wrote. Drafted a nudge to each for your approval."},
    {"id": "meeting_digest", "name": "Meeting notes digest", "category": "Weekly",
     "instruction": "Summarize this week's meetings: decisions, action items with owners, and follow-ups still unsent.",
     "schedule": {"freq": "weekly", "days": ["fri"], "time": "15:00"},
     "sample": "5 meetings. Decisions: pilot starts Nov 1. Action items: 7 (3 yours). 1 follow-up still unsent."},
    {"id": "month_review", "name": "Month-start review", "category": "Monthly",
     "instruction": "Recap last month: meetings held, deals moved, emails handled, and time I saved.",
     "schedule": {"freq": "monthly", "day": 1, "time": "09:00"},
     "sample": "October: 22 meetings, 3 deals moved, 140 emails handled, about 19 hours saved."},
    {"id": "investor_update", "name": "Investor update draft", "category": "Monthly",
     "instruction": "Draft my monthly investor update from last month: highlights, metrics I mentioned, lowlights, and asks.",
     "schedule": {"freq": "monthly", "day": 2, "time": "10:00"},
     "sample": "Draft ready with 4 highlights, 2 lowlights, and 2 asks. Review and send from the card."},
    {"id": "overdue_invoices", "name": "Overdue invoice reminders", "category": "Monthly",
     "instruction": "Find clients with overdue invoices in my email and draft a polite reminder to each.",
     "schedule": {"freq": "monthly", "day": 1, "time": "10:00"},
     "sample": "2 clients have invoices past due. Drafted a friendly reminder to each."},
]


def recipes(store: Store, user_id: int) -> list[dict[str, Any]]:
    """The gallery, with a reason to try each one when the user's own data suggests it."""
    from coworker import memory, scheduling

    have = {r["name"] for r in store.query("SELECT name FROM cw_responsibilities WHERE user_id = %s", (user_id,))}
    waiting = len(memory.needs_reply(store, user_id))
    stale = len(memory.stale_threads(store, user_id))
    meetings = len(scheduling.upcoming_events(store, user_id, hours=24 * 7))
    held = int((store.one("SELECT COUNT(*) AS n FROM cw_meetings WHERE user_id = %s AND started_at >= %s",
                          (user_id, iso(utcnow() - timedelta(days=14)))) or {}).get("n") or 0)
    why = {
        "inbox_sweep": f"{waiting} emails are waiting on you right now." if waiting >= 3 else "",
        "morning_briefing": f"You have {meetings} meetings in the next week." if meetings >= 3 else "",
        "follow_up_check": f"{stale} threads went quiet after you wrote." if stale >= 2 else "",
        "meeting_digest": f"Your coworker was in {held} meetings in the last two weeks." if held >= 2 else "",
    }
    out = []
    for r in RECIPES:
        spec = clean(r["schedule"])
        out.append({**r, "schedule": spec, "when": describe(spec), "enabled": r["name"] in have, "why": why.get(r["id"], "")})
    out.sort(key=lambda r: (r["enabled"], not r["why"]))
    return out
