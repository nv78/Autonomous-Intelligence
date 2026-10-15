"""The coworker's track record: the pilot success metrics, per user.

* **Acceptance**: approved without edits / all decided proposals, per type.
* **Edit size**: how much of a draft the user changed (0 = untouched,
  1 = rewritten), from the ``edited`` activity entries.
* **Rejections** with the user's reasons (they feed future drafts).
* **Hours saved**: executed work times a conservative minutes-per-task
  estimate. It's an estimate and labeled as one.
* **Calls**: calls run, minutes, escalations, and human interventions.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from coworker.store import Store, iso, utcnow

MINUTES_SAVED = {
    "email.send": 4, "slack.post": 2, "calendar.create": 5, "crm.update": 5, "responsibility.create": 0,
}
BRIEF_MINUTES = 10
DECIDED = ("approved", "executed", "executing", "rejected", "undone", "superseded", "failed")


def track_record(store: Store, user_id: int, days: int = 30) -> dict[str, Any]:
    since = iso(utcnow() - timedelta(days=days))
    actions = store.query("SELECT type, status, edited, autonomy FROM cw_actions WHERE user_id = %s AND created_at >= %s",
                          (user_id, since))
    by_type: dict[str, dict[str, Any]] = {}
    for a in actions:
        t = by_type.setdefault(a["type"], {"proposed": 0, "decided": 0, "unedited": 0, "edited": 0, "rejected": 0,
                                           "expired": 0, "executed": 0, "auto": 0})
        t["proposed"] += 1
        if a["status"] in DECIDED:
            t["decided"] += 1
            if a["status"] == "rejected":
                t["rejected"] += 1
            elif a["edited"]:
                t["edited"] += 1
            else:
                t["unedited"] += 1
        if a["status"] == "expired":
            t["expired"] += 1
        if a["status"] == "executed":
            t["executed"] += 1
            if a["autonomy"] in ("notify", "silent"):
                t["auto"] += 1
    for t in by_type.values():
        t["acceptance"] = round(t["unedited"] / t["decided"], 3) if t["decided"] else None

    activity = store.activity(user_id, limit=5000, since=since)
    edits = [float((a.get("detail") or {}).get("changed", 0)) for a in activity if a["kind"] == "edited"]
    reasons = [str((a.get("detail") or {}).get("feedback") or "") for a in activity if a["kind"] == "rejected"]
    briefs = sum(1 for a in activity if a["kind"] == "brief")

    meetings = store.query("SELECT metrics, started_at, ended_at, transcript FROM cw_meetings WHERE user_id = %s "
                           "AND started_at >= %s", (user_id, since))
    call_minutes = escalations = interventions = 0.0
    for m in meetings:
        metrics = m.get("metrics") or {}
        escalations += len(metrics.get("escalations") or [])
        interventions += sum(1 for t in m.get("transcript") or [] if t.get("speaker") == "owner")
        start, end = m.get("started_at"), m.get("ended_at")
        if start and end:
            from coworker.store import parse_iso

            s_at, e_at = parse_iso(start), parse_iso(end)
            if s_at and e_at:
                call_minutes += max(0.0, (e_at - s_at).total_seconds() / 60)

    minutes = sum(MINUTES_SAVED.get(k, 3) * v["executed"] for k, v in by_type.items()) + briefs * BRIEF_MINUTES + call_minutes
    decided = sum(v["decided"] for v in by_type.values())
    unedited = sum(v["unedited"] for v in by_type.values())
    return {
        "days": days,
        "acceptance": round(unedited / decided, 3) if decided else None,
        "decided": decided,
        "executed": sum(v["executed"] for v in by_type.values()),
        "pending": sum(1 for a in actions if a["status"] == "proposed"),
        "byType": by_type,
        "edits": {"count": len(edits), "avgChanged": round(sum(edits) / len(edits), 3) if edits else None},
        "rejections": {"count": len(reasons), "recentReasons": [r for r in reasons if r][:5]},
        "briefs": briefs,
        "calls": {"count": len(meetings), "minutes": round(call_minutes, 1), "escalations": int(escalations),
                  "interventions": int(interventions)},
        "hoursSaved": round(minutes / 60, 1),
        "hoursSavedNote": "Estimate: minutes per task × tasks done, plus call time.",
    }
