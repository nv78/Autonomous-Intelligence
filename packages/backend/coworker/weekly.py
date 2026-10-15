"""The weekly report: what the coworker did, and what to hand it next.

Every Monday morning (the user's time zone) each active coworker sends its
owner a short report by email and push:

* hours saved (an estimate, labeled as one), emails sent, calls taken,
  approval rate and how it moved;
* up to two one-tap suggestions, each a signed link that shows a
  confirmation page before changing anything:
  - **more autonomy** where the user keeps approving drafts unedited;
  - **a new responsibility** the user's own data says would help.

Users turn it off in Settings (``settings.weekly_report = false``).
"""
from __future__ import annotations

import os
from datetime import timedelta
from typing import Any

from coworker import metrics, policy, responsibilities
from coworker.store import Store, iso, utcnow

MIN_DECIDED = 8  # a streak this long without edits is worth suggesting "send without asking"
SEND_HOUR = 8
SALT = "coworker-weekly"


def _secret() -> str:
    from coworker.autojoin import _secret as secret

    return secret()


def token(user_id: int, suggestion: dict[str, Any]) -> str:
    from itsdangerous import URLSafeTimedSerializer

    return URLSafeTimedSerializer(_secret(), salt=SALT).dumps({"u": int(user_id), "s": suggestion})


def read_token(value: str, max_age: int = 14 * 86400) -> tuple[int, dict[str, Any]] | None:
    from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

    try:
        data = URLSafeTimedSerializer(_secret(), salt=SALT).loads(value, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    return int(data["u"]), dict(data["s"])


def link(user_id: int, suggestion: dict[str, Any]) -> str:
    base = os.environ.get("BACKEND_URL", "http://localhost:5000").rstrip("/")
    return f"{base}/api/coworker/weekly/apply/{token(user_id, suggestion)}"


def _autonomy_suggestions(store: Store, user_id: int) -> list[dict[str, Any]]:
    coworker = store.get_coworker(user_id) or {}
    out = []
    for action_type, info in policy.ACTION_TYPES.items():
        if action_type in policy.ALWAYS_APPROVE or policy.level_for(coworker, action_type) != "approve":
            continue
        rows = store.query("SELECT status, edited FROM cw_actions WHERE user_id = %s AND type = %s AND status IN "
                           "('executed', 'rejected', 'undone') AND created_at >= %s ORDER BY id DESC LIMIT 50",
                           (user_id, action_type, iso(utcnow() - timedelta(days=30))))
        if len(rows) >= MIN_DECIDED and all(r["status"] == "executed" and not r["edited"] for r in rows):
            out.append({"kind": "autonomy", "action_type": action_type, "level": "notify",
                        "text": f"You approved all {len(rows)} '{info['label'].lower()}' drafts this month without "
                                "changing a word. Let me do those without asking, and tell you after? "
                                "(New contacts, money and contracts still always ask.)"})
    return out


def report(store: Store, user_id: int) -> dict[str, Any]:
    week = metrics.track_record(store, user_id, days=7)
    month = metrics.track_record(store, user_id, days=30)
    emails = (week["byType"].get("email.send") or {}).get("executed", 0)
    suggestions = _autonomy_suggestions(store, user_id)[:1]
    for s in responsibilities.suggestions(store, user_id)[:1]:
        suggestions.append({"kind": "responsibility", "template": s["template"],
                            "text": f"{s['why']} Want me to take on “{s['name']}”?"})
    return {
        "hours": week["hoursSaved"], "executed": week["executed"], "emails": emails, "calls": week["calls"]["count"],
        "acceptance": week["acceptance"], "acceptance30": month["acceptance"], "pending": week["pending"],
        "suggestions": suggestions[:2],
    }


def render(store: Store, user_id: int, data: dict[str, Any]) -> tuple[str, str]:
    """(headline, plain-text email body)."""
    coworker = store.get_coworker(user_id) or {}
    first = (coworker.get("owner_name") or "").split(" ")[0] or "there"
    headline = (f"I saved you about {data['hours']:g} hours this week: {data['emails']} email{'s' if data['emails'] != 1 else ''} "
                f"sent, {data['calls']} call{'s' if data['calls'] != 1 else ''} taken.")
    lines = [f"Hi {first},", "", headline, ""]
    if data["acceptance"] is not None:
        trend = ""
        if data["acceptance30"] is not None and data["acceptance"] != data["acceptance30"]:
            trend = " (up" if data["acceptance"] > data["acceptance30"] else " (down"
            trend += f" from {round(data['acceptance30'] * 100)}% over the month)"
        lines.append(f"You approved {round(data['acceptance'] * 100)}% of my drafts without edits{trend}.")
    if data["pending"]:
        lines.append(f"{data['pending']} still waiting for you: {_app('/app/coworker/approvals')}")
    for s in data["suggestions"]:
        lines += ["", s["text"], f"Yes, do it: {link(user_id, s)}"]
    lines += ["", f"Everything I did: {_app('/app/coworker/today')}",
              "Hours saved is an estimate from the work done. Turn this email off in Settings."]
    return headline, "\n".join(lines)


def _app(path: str) -> str:
    return os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/") + path


def maybe_send(store: Store, user_id: int) -> str:
    """Send this week's report once, Monday after SEND_HOUR local. Returns the channel or ''."""
    from coworker import notify, push, scheduling

    coworker = store.get_coworker(user_id) or {}
    if coworker.get("status") != "active" or (coworker.get("settings") or {}).get("weekly_report") is False:
        return ""
    local = utcnow().astimezone(scheduling.tz_for(coworker))
    if local.weekday() != 0 or local.hour < SEND_HOUR:
        return ""
    slot = f"{local.isocalendar().year}-W{local.isocalendar().week:02d}"
    if store.one("SELECT id FROM cw_notifications WHERE user_id = %s AND kind = 'weekly' AND slot = %s", (user_id, slot)):
        return ""  # checked every tick on Monday; only build the report once
    data = report(store, user_id)
    if not data["executed"] and not data["calls"] and not data["suggestions"]:
        return ""  # a quiet week: nothing worth an email
    row_id = notify._record(store, user_id, "weekly", slot, "Your week with your coworker", data["executed"])
    if row_id is None:
        return ""
    headline, body = render(store, user_id, data)
    push.send(store, user_id, "Your week with your coworker", headline, {"type": "today"})
    channel = notify.deliver(store, user_id, "Your week with your coworker", body)
    store.update("cw_notifications", row_id, user_id, {"channel": channel or "none"})
    store.log(user_id, "notification", headline, {"weekly": data})
    return channel


def apply(store: Store, user_id: int, suggestion: dict[str, Any]) -> str:
    """Carry out a one-tap suggestion. Returns what happened, for the confirmation page."""
    if suggestion.get("kind") == "autonomy":
        action_type, level = suggestion.get("action_type"), suggestion.get("level")
        if action_type not in policy.ACTION_TYPES or action_type in policy.ALWAYS_APPROVE or level not in ("notify",):
            return "That suggestion isn't valid any more."
        coworker = store.get_coworker(user_id) or {}
        store.update_coworker(user_id, autonomy={**(coworker.get("autonomy") or {}), action_type: level})
        label = policy.ACTION_TYPES[action_type]["label"].lower()
        store.log(user_id, "autonomy", f"Changed autonomy from the weekly report: {action_type} → {level}")
        return f"Done. I'll {label} without asking and tell you after. New contacts, money and contracts still ask first."
    if suggestion.get("kind") == "responsibility":
        template = suggestion.get("template")
        if template not in responsibilities.TEMPLATES:
            return "That suggestion isn't valid any more."
        if store.one("SELECT id FROM cw_responsibilities WHERE user_id = %s AND template = %s AND enabled = 1",
                     (user_id, template)):
            return "I'm already doing that."
        resp = responsibilities.create(store, user_id, {"template": template})
        return f"Done. I've taken on “{resp['name']}”. You'll approve what it drafts until you say otherwise."
    return "That suggestion isn't valid any more."
