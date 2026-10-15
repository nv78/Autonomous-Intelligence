"""Proposing, approving, and executing the coworker's actions.

Every external action goes through ``propose``. The model never executes
anything directly: it can only create proposals, and this module decides
(via ``policy`` and ``security``) whether a proposal waits for the user or
runs on its own.

Approved email sends wait ``send_delay_seconds`` (default 20s live, 0s demo)
before going out, which is what makes "Undo" possible for Gmail.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from coworker import policy, security
from coworker.connectors.base import ConnectorError, workspace_for
from coworker.store import Store, iso, utcnow

PROPOSAL_TTL_HOURS = 72
OPEN_STATUSES = ("proposed", "approved")


class ActionError(Exception):
    def __init__(self, message: str, code: str = "bad_request") -> None:
        super().__init__(message)
        self.code = code


def _owner_first(coworker: dict[str, Any]) -> str:
    return (coworker.get("owner_name") or "the user").split(" ")[0]


def disclosure(coworker: dict[str, Any]) -> str:
    text = (coworker.get("settings") or {}).get("disclosure_text")
    first = _owner_first(coworker)
    return text or f"Sent by {first}'s AI coworker (Ourogen) on {first}'s behalf."


def _context(store: Store, user_id: int, payload: dict[str, Any], source_item_id: int | None) -> dict[str, Any]:
    coworker = store.get_coworker(user_id) or {}
    known = {p["email"] for p in store.people(user_id, include_hidden=True)}
    thread_id = payload.get("thread_id") or ""
    source = store.get("cw_items", source_item_id, user_id) if source_item_id else None
    if source and not thread_id:
        thread_id = source.get("thread_id") or ""
    thread = store.thread(user_id, thread_id) if thread_id else []
    participants: set[str] = set()
    for it in thread:
        participants.add((it.get("author_email") or "").lower())
        participants |= {(r.get("email") or "").lower() for r in it.get("recipients") or []}
    participants.discard("")
    others = store.query(
        "SELECT body FROM cw_items WHERE user_id = %s AND thread_id != %s AND kind IN ('email','slack') "
        "ORDER BY occurred_at DESC LIMIT 300",
        (user_id, thread_id),
    )
    return {
        "coworker": coworker,
        "known_emails": known,
        "thread_participants": participants,
        "trigger_text": (source or {}).get("body") or "",
        "thread_text": "\n".join((t.get("body") or "") for t in thread),
        "other_threads_text": "\n".join((o.get("body") or "") for o in others),
    }


def propose(
    store: Store,
    user_id: int,
    action_type: str,
    payload: dict[str, Any],
    *,
    title: str,
    reasoning: str = "",
    source_item_id: int | None = None,
    responsibility: dict[str, Any] | None = None,
    chat_id: int | None = None,
    requested_in_chat: bool = False,
) -> dict[str, Any]:
    if action_type not in policy.ACTION_TYPES:
        raise ActionError(f"Unknown action type {action_type}")
    ctx = _context(store, user_id, payload, source_item_id)
    coworker = ctx.pop("coworker")
    risks = []
    if policy.ACTION_TYPES[action_type]["external"]:
        risks = security.assess_outbound(
            action_type, payload, owner_email=coworker.get("owner_email", ""), requested_in_chat=requested_in_chat, **ctx,
        )
    level = policy.level_for(coworker, action_type, responsibility)
    decision = policy.decide(action_type, level, risks)
    action_id = store.insert("cw_actions", {
        "user_id": user_id, "type": action_type, "status": "proposed", "title": title[:500], "payload": payload,
        "reasoning": reasoning, "autonomy": level, "approval_reason": decision["reason"], "risk": risks,
        "source_item_id": source_item_id, "responsibility_id": (responsibility or {}).get("id"), "chat_id": chat_id,
        "expires_at": iso(utcnow() + timedelta(hours=PROPOSAL_TTL_HOURS)), "created_at": iso(),
    })
    if any(r["code"] == "suspicious_trigger" for r in risks):
        store.log(user_id, "security", "Flagged a suspicious message and held the related action for review",
                  {"risks": risks}, action_id=action_id)
    if decision["auto"] and coworker.get("status") == "active":
        store.update("cw_actions", action_id, user_id, {"status": "approved", "decided_at": iso(),
                                                        "execute_after": _execute_after(coworker, action_type)})
        store.log(user_id, "auto_approved", f"Auto-approved: {title}", {"level": level}, action_id=action_id)
        run_due(store, user_id)
    else:
        store.log(user_id, "proposed", f"Needs approval: {title}", {"reason": decision["reason"]}, action_id=action_id,
                  chat_id=chat_id)
    action = store.get("cw_actions", action_id, user_id)
    assert action is not None
    return action


def _execute_after(coworker: dict[str, Any], action_type: str) -> str:
    settings = coworker.get("settings") or {}
    default = 0 if coworker.get("mode") == "demo" else 20
    delay = int(settings.get("send_delay_seconds", default)) if action_type == "email.send" else 0
    return iso(utcnow() + timedelta(seconds=delay))


def _get_open(store: Store, user_id: int, action_id: int) -> dict[str, Any]:
    action = store.get("cw_actions", action_id, user_id)
    if not action:
        raise ActionError("Action not found", "not_found")
    return action


def edit(store: Store, user_id: int, action_id: int, payload_changes: dict[str, Any]) -> dict[str, Any]:
    action = _get_open(store, user_id, action_id)
    if action["status"] != "proposed":
        raise ActionError("Only pending actions can be edited", "conflict")
    allowed = {"to", "cc", "subject", "body", "text", "title", "start", "end", "attendees", "description", "channel",
               "instruction", "autonomy", "name"}
    payload = {**(action.get("payload") or {}), **{k: v for k, v in payload_changes.items() if k in allowed}}
    store.update("cw_actions", action_id, user_id, {"payload": payload, "edited": 1})
    updated = store.get("cw_actions", action_id, user_id)
    assert updated is not None
    return updated


def approve(store: Store, user_id: int, action_id: int, payload_changes: dict[str, Any] | None = None) -> dict[str, Any]:
    coworker = store.get_coworker(user_id) or {}
    if coworker.get("status") != "active":
        raise ActionError("Your coworker is paused. Resume it to approve actions.", "paused")
    action = _get_open(store, user_id, action_id)
    if action["status"] != "proposed":
        raise ActionError(f"This action is already {action['status']}", "conflict")
    if payload_changes:
        action = edit(store, user_id, action_id, payload_changes)
    if payload_changes and policy.ACTION_TYPES[action["type"]]["external"]:
        # Re-check risk on the edited content; edits can't silently widen what gets sent.
        ctx = _context(store, user_id, action["payload"] or {}, action.get("source_item_id"))
        ctx.pop("coworker")
        risks = security.assess_outbound(action["type"], action["payload"] or {}, owner_email=coworker.get("owner_email", ""),
                                         requested_in_chat=True, **ctx)
        store.update("cw_actions", action_id, user_id, {"risk": risks})
    store.update("cw_actions", action_id, user_id, {
        "status": "approved", "decided_at": iso(), "execute_after": _execute_after(coworker, action["type"]),
    })
    store.log(user_id, "approved", f"Approved: {action['title']}", action_id=action_id)
    run_due(store, user_id)
    result = store.get("cw_actions", action_id, user_id)
    assert result is not None
    return result


def reject(store: Store, user_id: int, action_id: int, feedback: str = "") -> dict[str, Any]:
    action = _get_open(store, user_id, action_id)
    if action["status"] != "proposed":
        raise ActionError(f"This action is already {action['status']}", "conflict")
    store.update("cw_actions", action_id, user_id, {"status": "rejected", "decided_at": iso(), "feedback": feedback[:2000]})
    if feedback.strip():
        store.insert("cw_memory", {
            "user_id": user_id, "kind": "feedback", "subject": action["type"], "title": feedback[:500],
            "detail": action["title"], "occurred_at": iso(), "created_at": iso(),
        })
    store.log(user_id, "rejected", f"Rejected: {action['title']}", {"feedback": feedback}, action_id=action_id)
    result = store.get("cw_actions", action_id, user_id)
    assert result is not None
    return result


def undo(store: Store, user_id: int, action_id: int) -> dict[str, Any]:
    action = _get_open(store, user_id, action_id)
    if action["status"] == "approved":
        store.update("cw_actions", action_id, user_id, {"status": "cancelled"})
        store.log(user_id, "undone", f"Cancelled before sending: {action['title']}", action_id=action_id)
    elif action["status"] == "executed":
        undo_info = (action.get("result") or {}).get("undo") or {}
        try:
            done = workspace_for(user_id, store).undo(action["type"], undo_info)
        except ConnectorError as exc:
            raise ActionError(str(exc), exc.code) from exc
        if not done:
            raise ActionError("This can't be undone anymore (sent email can't be recalled).", "cannot_undo")
        store.update("cw_actions", action_id, user_id, {"status": "undone"})
        store.log(user_id, "undone", f"Undid: {action['title']}", action_id=action_id)
    else:
        raise ActionError(f"Can't undo an action that is {action['status']}", "conflict")
    result = store.get("cw_actions", action_id, user_id)
    assert result is not None
    return result


def _execute(store: Store, user_id: int, action: dict[str, Any], coworker: dict[str, Any]) -> dict[str, Any]:
    payload = dict(action.get("payload") or {})
    ws = workspace_for(user_id, store)
    footer_needed = action["autonomy"] in ("notify", "silent") or (coworker.get("settings") or {}).get("disclose_on_approved", True)
    kind = action["type"]
    if kind == "email.send":
        body = payload.get("body", "")
        if footer_needed and disclosure(coworker) not in body:
            body = f"{body.rstrip()}\n\n--\n{disclosure(coworker)}"
        if action["autonomy"] == "suggest":
            res = ws.create_draft(payload.get("to") or [], payload.get("subject", ""), body, payload.get("thread_id", ""))
            return {"external_id": res.external_id, "draft": True, "undo": res.undo}
        res = ws.send_email(payload.get("to") or [], payload.get("subject", ""), body, payload.get("thread_id", ""),
                            payload.get("cc") or [])
        return {"external_id": res.external_id, "thread_id": res.thread_id, "undo": res.undo}
    if kind == "slack.post":
        res = ws.post_slack(payload.get("channel", ""), payload.get("text", ""))
        return {"external_id": res.external_id, "undo": res.undo}
    if kind == "calendar.create":
        res = ws.create_event(payload.get("title", "Meeting"), payload["start"], payload["end"],
                              payload.get("attendees") or [], payload.get("description", ""))
        return {"external_id": res.external_id, "undo": res.undo}
    if kind == "crm.update":
        store.insert("cw_memory", {
            "user_id": user_id, "kind": "crm", "subject": payload.get("company", ""), "title": payload.get("summary", "")[:500],
            "detail": str(payload.get("fields") or {}), "occurred_at": iso(), "created_at": iso(),
        })
        return {"recorded": True}
    if kind == "responsibility.create":
        from coworker import responsibilities

        resp = responsibilities.create(store, user_id, payload)
        return {"responsibility_id": resp["id"]}
    raise ActionError(f"Don't know how to execute {kind}")  # pragma: no cover


def run_due(store: Store, user_id: int) -> dict[str, int]:
    """Execute approved actions whose send delay passed; expire stale proposals."""
    coworker = store.get_coworker(user_id) or {}
    now = iso()
    expired = store.execute(
        "UPDATE cw_actions SET status = 'expired' WHERE user_id = %s AND status = 'proposed' AND expires_at < %s",
        (user_id, now),
    )
    if coworker.get("status") != "active":
        return {"executed": 0, "failed": 0, "expired": expired}
    due = store.query(
        "SELECT * FROM cw_actions WHERE user_id = %s AND status = 'approved' AND (execute_after IS NULL OR execute_after <= %s) ORDER BY id",
        (user_id, now),
    )
    executed = failed = 0
    for action in due:
        # Claim the row first so two workers can't both execute it.
        if not store.execute("UPDATE cw_actions SET status = 'executing' WHERE id = %s AND status = 'approved'", (action["id"],)):
            continue
        try:
            result = _execute(store, user_id, action, coworker)
        except (ConnectorError, ActionError, KeyError) as exc:
            code = getattr(exc, "code", "error")
            store.update("cw_actions", action["id"], user_id, {"status": "failed", "error": f"{code}: {exc}"})
            store.log(user_id, "failed", f"Failed: {action['title']} ({exc})", {"code": code}, action_id=action["id"])
            failed += 1
            continue
        store.update("cw_actions", action["id"], user_id, {"status": "executed", "executed_at": iso(), "result": result})
        verb = "Saved draft" if result.get("draft") else "Done"
        store.log(user_id, "executed", f"{verb}: {action['title']}", action_id=action["id"], chat_id=action.get("chat_id"))
        executed += 1
    return {"executed": executed, "failed": failed, "expired": expired}


def pause(store: Store, user_id: int, reason: str = "") -> int:
    """Kill switch: stop everything and cancel actions queued to execute."""
    store.update_coworker(user_id, status="paused")
    cancelled = store.execute(
        "UPDATE cw_actions SET status = 'cancelled' WHERE user_id = %s AND status IN ('approved', 'executing')",
        (user_id,),
    )
    store.log(user_id, "paused", f"Coworker paused{': ' + reason if reason else ''}. Cancelled {cancelled} queued actions.")
    return cancelled


def resume(store: Store, user_id: int) -> None:
    store.update_coworker(user_id, status="active")
    store.log(user_id, "resumed", "Coworker resumed")


def serialize(action: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": action["id"], "type": action["type"], "status": action["status"], "title": action["title"],
        "payload": action.get("payload") or {}, "reasoning": action.get("reasoning") or "",
        "autonomy": action["autonomy"], "approvalReason": action.get("approval_reason") or "",
        "risks": action.get("risk") or [], "sourceItemId": action.get("source_item_id"),
        "responsibilityId": action.get("responsibility_id"), "chatId": action.get("chat_id"),
        "edited": bool(action.get("edited")), "feedback": action.get("feedback") or "",
        "result": action.get("result") or {}, "error": action.get("error") or "",
        "executeAfter": action.get("execute_after"), "expiresAt": action.get("expires_at"),
        "createdAt": action["created_at"], "decidedAt": action.get("decided_at"), "executedAt": action.get("executed_at"),
        "label": policy.ACTION_TYPES.get(action["type"], {}).get("label", action["type"]),
    }
