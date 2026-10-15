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
    external_channel = False
    if payload.get("channel"):
        latest = store.one("SELECT meta FROM cw_items WHERE user_id = %s AND kind = 'slack' AND channel = %s "
                           "ORDER BY occurred_at DESC LIMIT 1", (user_id, payload["channel"]))
        external_channel = bool(((latest or {}).get("meta") or {}).get("shared"))
    return {
        "coworker": coworker,
        "external_channel": external_channel,
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
    from coworker import orgs

    level = orgs.cap_level(store, user_id, action_type, policy.level_for(coworker, action_type, responsibility))
    blocked = orgs.blocked_recipients(store, user_id, _recipients(payload))
    if blocked:
        risks.append({"code": "org_blocked", "message": f"Your organization doesn't allow sending to {', '.join(blocked)}."})
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
    from coworker import governance

    if decision["auto"] and coworker.get("status") == "active" and not governance.needs_employer_ok(store, user_id):
        store.update("cw_actions", action_id, user_id, {"status": "approved", "decided_at": iso(),
                                                        "execute_after": _execute_after(coworker, action_type)})
        store.log(user_id, "auto_approved", f"Auto-approved: {title}", {"level": level}, action_id=action_id)
        run_due(store, user_id)
    else:
        store.log(user_id, "proposed", f"Needs approval: {title}", {"reason": decision["reason"]}, action_id=action_id,
                  chat_id=chat_id)
        if not requested_in_chat:  # the user is looking at the chat already
            from coworker import push

            fresh = store.get("cw_actions", action_id, user_id)
            if fresh:
                push.approval_needed(store, user_id, fresh)
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


def _recipients(payload: dict[str, Any]) -> list[str]:
    return [str(r) for r in (payload.get("to") or []) + (payload.get("cc") or []) + (payload.get("attendees") or [])]


def edit(store: Store, user_id: int, action_id: int, payload_changes: dict[str, Any]) -> dict[str, Any]:
    action = _get_open(store, user_id, action_id)
    if action["status"] != "proposed":
        raise ActionError("Only pending actions can be edited", "conflict")
    allowed = {"to", "cc", "subject", "body", "text", "title", "start", "end", "attendees", "description", "channel",
               "instruction", "autonomy", "name"}
    before = action.get("payload") or {}
    payload = {**before, **{k: v for k, v in payload_changes.items() if k in allowed}}
    if "attachments" in payload_changes:  # files can be removed when editing, never added
        from coworker.attachments import ref_id

        keep = {ref_id(a) for a in payload_changes.get("attachments") or []} - {None}
        payload["attachments"] = [a for a in before.get("attachments") or [] if ref_id(a) in keep]
    store.update("cw_actions", action_id, user_id, {"payload": payload, "edited": 1})
    old_text = str(before.get("body") or before.get("text") or "")
    new_text = str(payload.get("body") or payload.get("text") or "")
    if old_text != new_text:
        import difflib

        changed = round(1 - difflib.SequenceMatcher(None, old_text, new_text).ratio(), 3)
        store.log(user_id, "edited", f"You edited: {action['title']}", {"changed": changed, "type": action["type"]},
                  action_id=action_id)
    updated = store.get("cw_actions", action_id, user_id)
    assert updated is not None
    return updated


def _check_governance(store: Store, user_id: int, coworker: dict[str, Any]) -> None:
    from coworker import governance

    if governance.org_disabled(coworker.get("owner_email") or ""):
        raise ActionError("Your organization has turned off AI coworkers.", "org_disabled")
    if governance.needs_employer_ok(store, user_id):
        raise ActionError("Confirm in Settings that you own the company or your employer allows an AI coworker, "
                          "then approve again.", "employer_authorization")


def approve(store: Store, user_id: int, action_id: int, payload_changes: dict[str, Any] | None = None) -> dict[str, Any]:
    coworker = store.get_coworker(user_id) or {}
    if coworker.get("status") != "active":
        raise ActionError("Your coworker is paused. Resume it to approve actions.", "paused")
    _check_governance(store, user_id, coworker)
    action = _get_open(store, user_id, action_id)
    if action["status"] != "proposed":
        raise ActionError(f"This action is already {action['status']}", "conflict")
    if payload_changes:
        action = edit(store, user_id, action_id, payload_changes)
    from coworker import orgs

    blocked = orgs.blocked_recipients(store, user_id, _recipients(action.get("payload") or {}))
    if blocked:
        raise ActionError(f"Your organization doesn't allow sending to {', '.join(blocked)}. Edit the recipients or reject it.",
                          "org_blocked")
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
        from coworker import attachments

        files = attachments.files_for(store, user_id, payload.get("attachments") or [])
        if action["autonomy"] == "suggest":
            res = ws.create_draft(payload.get("to") or [], payload.get("subject", ""), body, payload.get("thread_id", ""),
                                  files)
            return {"external_id": res.external_id, "draft": True, "undo": res.undo}
        res = ws.send_email(payload.get("to") or [], payload.get("subject", ""), body, payload.get("thread_id", ""),
                            payload.get("cc") or [], files)
        return {"external_id": res.external_id, "thread_id": res.thread_id, "undo": res.undo}
    if kind == "slack.post":
        res = ws.post_slack(payload.get("channel", ""), payload.get("text", ""))
        return {"external_id": res.external_id, "undo": res.undo}
    if kind == "calendar.create":
        res = ws.create_event(payload.get("title", "Meeting"), payload["start"], payload["end"],
                              payload.get("attendees") or [], payload.get("description", ""))
        return {"external_id": res.external_id, "undo": res.undo}
    if kind == "crm.update":
        from coworker.connectors import crm

        found = crm.client_for(store, user_id)
        pushed = found[1].record_call(payload) if found else None  # first, so a failure records nothing
        store.insert("cw_memory", {
            "user_id": user_id, "kind": "crm", "subject": payload.get("company", ""), "title": payload.get("summary", "")[:500],
            "detail": str(payload.get("fields") or {}), "occurred_at": iso(), "created_at": iso(),
        })
        if not found or pushed is None:
            return {"recorded": True}
        provider, client = found
        return {"recorded": True, "crm": {"provider": provider, "label": client.label, **pushed},
                **({"hubspot": pushed} if provider == "hubspot" else {})}
    if kind == "responsibility.create":
        from coworker import responsibilities

        resp = responsibilities.create(store, user_id, payload)
        return {"responsibility_id": resp["id"]}
    raise ActionError(f"Don't know how to execute {kind}")  # pragma: no cover


DOUBLE_REPLY_MINUTES = 30


def _owner_already_replied(store: Store, user_id: int, action: dict[str, Any]) -> bool:
    """True when the user wrote in this email thread themselves after the
    draft was proposed, or within the last few minutes. Sending the
    coworker's draft then would be a double reply."""
    if action["type"] != "email.send":
        return False
    thread_id = (action.get("payload") or {}).get("thread_id")
    if not thread_id:
        return False
    thread = store.thread(user_id, thread_id)
    last_inbound = max((it["occurred_at"] for it in thread if it["direction"] == "inbound"), default="")
    since = max(last_inbound, min(action["created_at"], iso(utcnow() - timedelta(minutes=DOUBLE_REPLY_MINUTES))))
    for it in thread:
        meta = it.get("meta") or {}
        if (it["direction"] == "outbound" and it["occurred_at"] > since and meta.get("sent_by") != "coworker"
                and not meta.get("notification")):
            return True
    return False


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
        if _owner_already_replied(store, user_id, action):
            store.update("cw_actions", action["id"], user_id, {"status": "superseded"})
            store.log(user_id, "superseded", f"Didn't send: {action['title']} (you already replied in that thread)",
                      action_id=action["id"])
            continue
        try:
            result = _execute(store, user_id, action, coworker)
        except (ConnectorError, ActionError, KeyError) as exc:
            code = getattr(exc, "code", "error")
            store.update("cw_actions", action["id"], user_id, {"status": "failed", "error": f"{code}: {exc}"})
            store.log(user_id, "failed", f"Failed: {action['title']} ({exc})", {"code": code}, action_id=action["id"])
            import observability

            observability.alert(f"action-failed:{user_id}:{code}", "An approved coworker action failed",
                                user_id=user_id, action_id=action["id"], code=code)
            failed += 1
            continue
        store.update("cw_actions", action["id"], user_id, {"status": "executed", "executed_at": iso(), "result": result})
        verb = "Saved draft" if result.get("draft") else "Done"
        store.log(user_id, "executed", f"{verb}: {action['title']}", action_id=action["id"], chat_id=action.get("chat_id"))
        if action.get("chat_id") and action["type"] != "responsibility.create":
            from coworker import reports

            reports.post(user_id, action["chat_id"], reports.action_done(action, result))
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
