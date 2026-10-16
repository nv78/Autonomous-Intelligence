"""Autonomy levels and approval rules.

Each action type has an autonomy level the user controls:

* ``suggest`` — the coworker prepares it; the user sends it themselves
  (approving an email in this mode saves a Gmail draft instead of sending).
* ``approve`` — one-click approval, then the coworker does it. **Default.**
* ``notify``  — the coworker acts, then tells the user.
* ``silent``  — the coworker acts; it only shows up in the activity log.

**Hard floors** sit underneath: any risk flag from
``security.assess_outbound`` (first contact with someone new, money or
contract terms, data from another thread, bulk sends, suspicious trigger,
deletion) forces approval no matter what level is configured. Floors are
enforced here on the server, not in the UI.
"""
from __future__ import annotations

from typing import Any

from coworker.store import Store

LEVELS = ("suggest", "approve", "notify", "silent")
DEFAULT_LEVEL = "approve"

ACTION_TYPES: dict[str, dict[str, Any]] = {
    "email.send": {"label": "Send email", "external": True},
    "slack.post": {"label": "Post on Slack", "external": True},
    "calendar.create": {"label": "Send calendar invite", "external": True},
    "crm.update": {"label": "Update CRM", "external": False},
    "responsibility.create": {"label": "Take on a responsibility", "external": False},
}

# Configuration changes always need the user's explicit yes.
ALWAYS_APPROVE = {"responsibility.create"}
EARNED_AUTONOMY_STREAK = 20


def level_for(coworker: dict[str, Any], action_type: str, responsibility: dict[str, Any] | None = None) -> str:
    if responsibility and responsibility.get("autonomy") in LEVELS:
        return str(responsibility["autonomy"])
    autonomy = coworker.get("autonomy") or {}
    level = autonomy.get(action_type, DEFAULT_LEVEL)
    return level if level in LEVELS else DEFAULT_LEVEL


def decide(action_type: str, level: str, risks: list[dict[str, str]]) -> dict[str, Any]:
    """Return {"auto": bool, "reason": str} for a proposed action."""
    if action_type in ALWAYS_APPROVE:
        return {"auto": False, "reason": "Changes what your coworker is responsible for."}
    if risks:
        return {"auto": False, "reason": "Needs your approval: " + " ".join(r["message"] for r in risks)}
    if level in ("suggest", "approve"):
        return {"auto": False, "reason": "Your autonomy setting for this kind of action is "
                                         f"'{level}'."}
    return {"auto": True, "reason": f"Allowed by your autonomy setting ('{level}')."}


def earned_autonomy(store: Store, user_id: int, action_type: str) -> dict[str, Any] | None:
    """Suggest raising autonomy after a streak of unedited approvals.

    The coworker only ever *suggests* this; it never raises its own level.
    """
    coworker = store.get_coworker(user_id) or {}
    current = level_for(coworker, action_type)
    if current not in ("suggest", "approve"):
        return None
    rows = store.query(
        "SELECT status, edited FROM cw_actions WHERE user_id = %s AND type = %s AND status IN "
        "('executed', 'rejected', 'cancelled') ORDER BY id DESC LIMIT %s",
        (user_id, action_type, EARNED_AUTONOMY_STREAK),
    )
    if len(rows) < EARNED_AUTONOMY_STREAK or any(r["status"] != "executed" or r["edited"] for r in rows):
        return None
    nxt = LEVELS[LEVELS.index(current) + 1]
    return {
        "actionType": action_type, "from": current, "to": nxt,
        "message": f"You approved the last {EARNED_AUTONOMY_STREAK} '{ACTION_TYPES[action_type]['label']}' "
                   f"actions without edits. Want to move this to '{nxt}'?",
    }
