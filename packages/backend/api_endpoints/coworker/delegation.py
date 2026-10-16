"""Delegation routes: chat with the coworker, approvals, activity, kill switch,
responsibilities, autonomy, and the periodic tick."""
from __future__ import annotations

import csv
import io
import json
from collections.abc import Generator
from typing import Any

from flask import Response, jsonify, request, stream_with_context

from api_endpoints.coworker.common import coworker_bp, error, store, uid
from coworker import brain, executor, policy, responsibilities
from coworker.store import iso, parse_iso, utcnow
from database.db import (
    create_chat,
    create_message,
    get_chat,
    get_connection,
    get_messages,
    rename_chat,
)
from middleware.auth import require_auth
from services.streaming import sse_event

TICK_MIN_SECONDS = 10
SYNC_MIN_SECONDS = 120


def _coworker_or_404() -> tuple[int, dict[str, Any] | None]:
    user_id = uid()
    return user_id, store().get_coworker(user_id)


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

def marker(data: dict[str, Any]) -> str:
    return f"\n:::cw {json.dumps(data)}\n"


@coworker_bp.post("/chat/stream")
@require_auth
def chat_stream() -> Any:
    user_id, coworker = _coworker_or_404()
    if not coworker:
        return error("Set up your coworker first", 404, "not_found")
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    if not message:
        return error("message is required")
    session_raw = data.get("session_id")
    cnx = get_connection()
    try:
        if session_raw:
            chat_id = int(session_raw)
            row = get_chat(cnx, user_id, chat_id)
            if not row:
                return error("Session not found", 404, "not_found")
            needs_title = row["name"] == "New Chat"
            history = [{"role": m["role"], "content": m["content"]} for m in get_messages(cnx, chat_id)]
        else:
            chat_id = create_chat(cnx, user_id)
            needs_title = True
            history = []
        create_message(cnx, chat_id, "user", message)
    finally:
        cnx.close()

    def generate() -> Generator[str, None, None]:
        if not session_raw:
            yield sse_event("session_id", {"session_id": chat_id})
        parts: list[str] = []
        try:
            from coworker import autojoin

            pending = autojoin.pending_for_chat(store(), user_id, chat_id) if session_raw else None
            turn = (autojoin.chat_turn(store(), user_id, pending, message) if pending
                    else brain.run_turn(store(), user_id, chat_id, message, history))
            for kind, payload in turn:
                if kind == "text":
                    parts.append(payload)
                    yield sse_event("text", {"text": payload})
                elif kind == "tool":
                    parts.append(marker({"t": "tool", **payload}))
                    yield sse_event("tool", payload)
                elif kind == "card":
                    parts.append(marker({"t": payload["type"], **{k: v for k, v in payload.items() if k != "type"}}))
                    if payload["type"] == "action":
                        action = store().get("cw_actions", payload["id"], user_id)
                        yield sse_event("card", {"card": "action", "action": executor.serialize(action) if action else None})
                    else:
                        yield sse_event("card", {"card": payload["type"], **payload})
        except Exception as exc:
            parts.append(f"\n\nSomething went wrong: {exc}")
            yield sse_event("error", {"message": f"Your coworker hit an error: {exc}"})
        content = "".join(parts).strip()
        if content:
            cnx2 = get_connection()
            try:
                create_message(cnx2, chat_id, "assistant", content, "coworker")
                if needs_title:
                    title = message[:60] + ("…" if len(message) > 60 else "")
                    rename_chat(cnx2, user_id, chat_id, title)
                    yield sse_event("title", {"session_id": chat_id, "title": title})
            finally:
                cnx2.close()
        yield sse_event("done", {})

    return Response(stream_with_context(generate()), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"})


# ---------------------------------------------------------------------------
# Actions / approvals
# ---------------------------------------------------------------------------

@coworker_bp.get("/actions")
@require_auth
def list_actions() -> tuple:
    user_id = uid()
    executor.run_due(store(), user_id)
    status = request.args.get("status")
    ids = request.args.get("ids")
    sql = "SELECT * FROM cw_actions WHERE user_id = %s"
    params: list[Any] = [user_id]
    if ids:
        id_list = [int(i) for i in ids.split(",") if i.strip().isdigit()][:100]
        if not id_list:
            return jsonify({"actions": []}), 200
        sql += f" AND id IN ({', '.join(['%s'] * len(id_list))})"
        params += id_list
    elif status:
        sql += " AND status = %s"
        params.append(status)
    sql += " ORDER BY id DESC LIMIT 200"
    rows = store().query(sql, params)
    return jsonify({"actions": [executor.serialize(a) for a in rows]}), 200


def _action_route(fn: Any, action_id: int, *args: Any) -> tuple:
    try:
        action = fn(store(), uid(), action_id, *args)
    except executor.ActionError as exc:
        status = {"not_found": 404, "conflict": 409, "paused": 423}.get(exc.code, 400)
        return error(str(exc), status, exc.code)
    return jsonify({"action": executor.serialize(action)}), 200


@coworker_bp.patch("/actions/<int:action_id>")
@require_auth
def edit_action(action_id: int) -> tuple:
    return _action_route(executor.edit, action_id, (request.get_json(silent=True) or {}).get("payload") or {})


@coworker_bp.post("/actions/<int:action_id>/approve")
@require_auth
def approve_action(action_id: int) -> tuple:
    return _action_route(executor.approve, action_id, (request.get_json(silent=True) or {}).get("payload"))


@coworker_bp.post("/actions/<int:action_id>/reject")
@require_auth
def reject_action(action_id: int) -> tuple:
    return _action_route(executor.reject, action_id, str((request.get_json(silent=True) or {}).get("feedback", "")))


@coworker_bp.post("/actions/<int:action_id>/undo")
@require_auth
def undo_action(action_id: int) -> tuple:
    return _action_route(executor.undo, action_id)


# ---------------------------------------------------------------------------
# Activity, digest, status, kill switch
# ---------------------------------------------------------------------------

@coworker_bp.get("/activity")
@require_auth
def activity() -> Any:
    user_id = uid()
    rows = store().activity(user_id, limit=min(int(request.args.get("limit", 200)), 2000))
    if request.args.get("format") == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["time", "kind", "summary", "action_id", "detail"])
        for r in rows:
            writer.writerow([r["created_at"], r["kind"], r["summary"], r.get("action_id") or "", json.dumps(r.get("detail") or {})])
        return Response(buf.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": "attachment; filename=coworker-activity.csv"})
    return jsonify({"activity": rows}), 200


@coworker_bp.get("/digest")
@require_auth
def get_digest() -> tuple:
    hours = min(int(request.args.get("hours", 24)), 24 * 30)
    return jsonify(responsibilities.digest(store(), uid(), hours=hours)), 200


@coworker_bp.get("/status")
@require_auth
def status() -> tuple:
    user_id, coworker = _coworker_or_404()
    if not coworker:
        return jsonify({"exists": False}), 200
    pending = store().one("SELECT COUNT(*) AS n FROM cw_actions WHERE user_id = %s AND status = 'proposed'", (user_id,))
    attention = store().one(
        "SELECT COUNT(*) AS n FROM cw_activity WHERE user_id = %s AND kind IN ('escalation', 'security') AND created_at >= %s",
        (user_id, iso(utcnow().replace(hour=0, minute=0, second=0, microsecond=0))),
    )
    from coworker import ops

    return jsonify({
        "exists": True, "status": coworker["status"], "mode": coworker["mode"],
        "pending": int((pending or {}).get("n") or 0), "attention": int((attention or {}).get("n") or 0),
        "onboarding": coworker.get("onboarding") or {}, "worker": ops.worker_status(store()),
    }), 200


@coworker_bp.get("/runs")
@require_auth
def list_runs() -> tuple:
    """Recent runs of responsibilities and scheduled tasks: outcome, duration, attempts, errors."""
    from coworker import ops

    return jsonify({"runs": ops.recent_runs(store(), uid(), int(request.args.get("limit") or 50))}), 200


@coworker_bp.post("/pause")
@require_auth
def pause() -> tuple:
    user_id, coworker = _coworker_or_404()
    if not coworker:
        return error("Set up your coworker first", 404, "not_found")
    cancelled = executor.pause(store(), user_id, str((request.get_json(silent=True) or {}).get("reason", "")))
    return jsonify({"status": "paused", "cancelled": cancelled}), 200


@coworker_bp.post("/resume")
@require_auth
def resume() -> tuple:
    user_id, coworker = _coworker_or_404()
    if not coworker:
        return error("Set up your coworker first", 404, "not_found")
    executor.resume(store(), user_id)
    return jsonify({"status": "active"}), 200


@coworker_bp.post("/tick")
@require_auth
def tick() -> tuple:
    """Run the coworker's loop: sync, responsibilities, due actions.

    The web app calls this every ~20s while open; ``python -m coworker.worker``
    does the same in the background for every user.
    """
    user_id, coworker = _coworker_or_404()
    if not coworker:
        return error("Set up your coworker first", 404, "not_found")
    force = bool((request.get_json(silent=True) or {}).get("force"))
    return jsonify(run_tick(user_id, force=force)), 200


def run_tick(user_id: int, force: bool = False, inline_sync: bool = False) -> dict[str, Any]:
    """One pass of the coworker loop. Web requests queue network sync in the
    background; only the worker (``inline_sync=True``) syncs in-process."""
    from coworker import notify, sync_jobs

    s = store()
    coworker = s.get_coworker(user_id) or {}
    settings = coworker.get("settings") or {}
    now = utcnow()
    last = parse_iso(settings.get("last_tick"))
    if not force and last and (now - last).total_seconds() < TICK_MIN_SECONDS:
        return {"skipped": True}
    settings["last_tick"] = iso(now)
    synced: dict[str, Any] = {}
    last_sync = parse_iso(settings.get("last_sync"))
    if coworker.get("mode") == "live" and (force or not last_sync or (now - last_sync).total_seconds() > SYNC_MIN_SECONDS):
        settings["last_sync"] = iso(now)
        job = sync_jobs.request(s, user_id)
        if inline_sync:
            synced = (sync_jobs.run_job(s, int(job["id"])) or {}).get("counts") or {}
            coworker = s.get_coworker(user_id) or coworker
            settings = {**(coworker.get("settings") or {}), "last_tick": iso(now), "last_sync": iso(now)}
        else:
            sync_jobs.start(s, job)
            synced = {"queued": int(job["id"])}
    s.update_coworker(user_id, settings=settings)
    if coworker.get("mode") == "live" and coworker.get("status") == "active":
        from coworker import inbound_email

        inbound_email.scan_mailbox(s, user_id)  # free "email your coworker": you+coworker@ your own mailbox
    from coworker import governance

    if coworker.get("status") == "active" and governance.org_disabled(coworker.get("owner_email") or ""):
        executor.pause(s, user_id, "your organization turned off AI coworkers")
        coworker = s.get_coworker(user_id) or coworker
    if settings.get("pending_voice_deletes"):
        from coworker import twin

        twin.retry_voice_deletes(s, user_id)
        coworker = s.get_coworker(user_id) or coworker
    if notify.handle_stop_replies(s, user_id):
        coworker = s.get_coworker(user_id) or coworker
    results = responsibilities.run_all(s, user_id) if coworker.get("status") == "active" else []
    due = executor.run_due(s, user_id)
    notified = notify.maybe_notify_approvals(s, user_id)
    from coworker import weekly

    weekly.maybe_send(s, user_id)
    return {"synced": synced, "results": results, "notified": notified, **due}


# ---------------------------------------------------------------------------
# Responsibilities
# ---------------------------------------------------------------------------

def _serialize_resp(r: dict[str, Any]) -> dict[str, Any]:
    out = {
        "id": r["id"], "name": r["name"], "template": r["template"], "instruction": r.get("instruction") or "",
        "trigger": r.get("trigger_spec") or {}, "autonomy": r["autonomy"], "escalation": r.get("escalation") or "",
        "enabled": bool(r["enabled"]), "runs": r["runs"], "lastRunAt": r.get("last_run_at"), "createdAt": r["created_at"],
    }
    if r.get("template") == "scheduled":
        from coworker import schedules

        out["schedule"] = schedules.state(store(), int(r["user_id"]), r)
    return out


@coworker_bp.get("/responsibilities")
@require_auth
def list_responsibilities() -> tuple:
    user_id = uid()
    rows = store().query("SELECT * FROM cw_responsibilities WHERE user_id = %s ORDER BY id", (user_id,))
    templates = [{"id": k, "name": v["name"], "description": v["description"], "autonomy": v["autonomy"]}
                 for k, v in responsibilities.TEMPLATES.items()]
    return jsonify({"responsibilities": [_serialize_resp(r) for r in rows], "templates": templates,
                    "suggestions": responsibilities.suggestions(store(), user_id)}), 200


@coworker_bp.post("/responsibilities")
@require_auth
def create_responsibility() -> tuple:
    user_id, coworker = _coworker_or_404()
    if not coworker:
        return error("Set up your coworker first", 404, "not_found")
    data = request.get_json(silent=True) or {}
    template = data.get("template")
    if template and template not in responsibilities.TEMPLATES:
        return error("Unknown template")
    if not template and not data.get("instruction"):
        return error("template or instruction is required")
    if isinstance(data.get("schedule"), dict):
        try:
            spec = responsibilities.scheduled_spec(str(data["instruction"]), data["schedule"], str(data.get("name") or ""))
        except ValueError as exc:
            return error(str(exc))
    else:
        spec = responsibilities.proposal_payload(data["instruction"]) if not template else {"template": template}
    if data.get("autonomy") in policy.LEVELS:
        spec["autonomy"] = data["autonomy"]
    if data.get("name"):
        spec["name"] = data["name"]
    row = responsibilities.create(store(), user_id, spec)
    results = responsibilities.run_one(store(), user_id, row) if data.get("runNow", True) else []
    return jsonify({"responsibility": _serialize_resp(store().get("cw_responsibilities", row["id"], user_id) or row),
                    "results": results}), 201


@coworker_bp.get("/recipes")
@require_auth
def list_recipes() -> tuple:
    """One-click scheduled tasks, with a reason to try each when the user's data suggests it."""
    from coworker import schedules

    return jsonify({"recipes": schedules.recipes(store(), uid())}), 200


@coworker_bp.patch("/responsibilities/<int:resp_id>")
@require_auth
def update_responsibility(resp_id: int) -> tuple:
    user_id = uid()
    data = request.get_json(silent=True) or {}
    values: dict[str, Any] = {}
    if "enabled" in data:
        values["enabled"] = 1 if data["enabled"] else 0
    if data.get("autonomy") in policy.LEVELS:
        values["autonomy"] = data["autonomy"]
    for key in ("name", "instruction", "escalation"):
        if key in data:
            values[key] = str(data[key])[:4000]
    if isinstance(data.get("schedule"), dict):
        from coworker import schedules

        row = store().get("cw_responsibilities", resp_id, user_id)
        if not row or row["template"] != "scheduled":
            return error("Only scheduled tasks have a schedule", 400, "bad_request")
        try:
            values["trigger_spec"] = schedules.clean({**(row.get("trigger_spec") or {}), **data["schedule"]})
        except ValueError as exc:
            return error(str(exc))
    if not values or not store().update("cw_responsibilities", resp_id, user_id, values):
        return error("Not found or nothing to update", 404, "not_found")
    return jsonify({"responsibility": _serialize_resp(store().get("cw_responsibilities", resp_id, user_id) or {})}), 200


@coworker_bp.delete("/responsibilities/<int:resp_id>")
@require_auth
def delete_responsibility(resp_id: int) -> tuple:
    if not store().execute("DELETE FROM cw_responsibilities WHERE id = %s AND user_id = %s", (resp_id, uid())):
        return error("Not found", 404, "not_found")
    return jsonify({"deleted": True}), 200


@coworker_bp.post("/responsibilities/<int:resp_id>/run")
@require_auth
def run_responsibility(resp_id: int) -> tuple:
    user_id = uid()
    row = store().get("cw_responsibilities", resp_id, user_id)
    if not row:
        return error("Not found", 404, "not_found")
    if row["template"] == "scheduled":  # "Run now": don't wait for the next occurrence
        from coworker import schedules

        results = schedules.run(store(), user_id, row, force=True)
    else:
        results = responsibilities.run_one(store(), user_id, row)
    executor.run_due(store(), user_id)
    return jsonify({"results": results}), 200


# ---------------------------------------------------------------------------
# Autonomy
# ---------------------------------------------------------------------------

@coworker_bp.post("/autojoin/<event_id>/skip")
@require_auth
def autojoin_skip(event_id: str) -> tuple:
    from coworker import autojoin

    user_id = uid()
    if not autojoin.responsibility(store(), user_id):
        return error("Auto-join isn't on", 404, "not_found")
    if not autojoin.skip(store(), user_id, event_id):
        return error("Your coworker already joined this meeting", 409, "already_joined")
    return jsonify({"skipped": True}), 200


@coworker_bp.get("/autonomy")
@require_auth
def get_autonomy() -> tuple:
    user_id, coworker = _coworker_or_404()
    from coworker import orgs

    levels = {t: policy.level_for(coworker or {}, t) for t in policy.ACTION_TYPES if t not in policy.ALWAYS_APPROVE}
    ceiling = (orgs.policies(store(), user_id).get("autonomy_ceiling") or {}) if coworker else {}
    suggestions = [sg for t in levels if (sg := policy.earned_autonomy(store(), user_id, t))]
    return jsonify({
        "levels": levels, "options": list(policy.LEVELS),
        "types": {t: v["label"] for t, v in policy.ACTION_TYPES.items() if t not in policy.ALWAYS_APPROVE},
        "suggestions": suggestions,
        "orgCeiling": ceiling,
        "hardFloors": [
            "First contact with someone new", "Pricing, discounts, contracts, or payments",
            "Details from a different conversation", "More than 5 recipients",
            "Anything triggered by a suspicious message", "Deleting data",
        ],
    }), 200


@coworker_bp.put("/autonomy")
@require_auth
def set_autonomy() -> tuple:
    user_id, coworker = _coworker_or_404()
    if not coworker:
        return error("Set up your coworker first", 404, "not_found")
    data = request.get_json(silent=True) or {}
    levels = {k: v for k, v in data.items() if k in policy.ACTION_TYPES and k not in policy.ALWAYS_APPROVE and v in policy.LEVELS}
    if not levels:
        return error("Provide {action_type: level}")
    store().update_coworker(user_id, autonomy={**(coworker.get("autonomy") or {}), **levels})
    store().log(user_id, "autonomy", "Changed autonomy: " + ", ".join(f"{k} → {v}" for k, v in levels.items()))
    return get_autonomy()


# ---------------------------------------------------------------------------
# Onboarding helpers
# ---------------------------------------------------------------------------

@coworker_bp.get("/onboarding/suggestions")
@require_auth
def onboarding_suggestions() -> tuple:
    return jsonify({"suggestions": responsibilities.suggestions(store(), uid())}), 200


# ---------------------------------------------------------------------------
# Governance and track record
# ---------------------------------------------------------------------------

@coworker_bp.get("/governance")
@require_auth
def get_governance() -> tuple:
    from coworker import governance

    return jsonify(governance.status(store(), uid())), 200


@coworker_bp.post("/governance/employer")
@require_auth
def confirm_employer() -> tuple:
    from coworker import governance

    data = request.get_json(silent=True) or {}
    if not data.get("confirm"):
        return error("Confirm that you're allowed to use an AI coworker at work")
    try:
        record = governance.authorize(store(), uid(), str(data.get("basis", "")))
    except ValueError as exc:
        return error(str(exc))
    return jsonify({"employerAuthorized": record, **governance.status(store(), uid())}), 200


@coworker_bp.get("/metrics")
@require_auth
def get_metrics() -> tuple:
    from coworker import metrics

    days = min(max(int(request.args.get("days", 30)), 1), 365)
    return jsonify(metrics.track_record(store(), uid(), days=days)), 200


@coworker_bp.get("/day")
@require_auth
def get_day() -> tuple:
    """Everything the coworker did on one day (YYYY-MM-DD, default today)."""
    from coworker import delegate

    date = request.args.get("date") or None
    if date and not __import__("re").match(r"^\d{4}-\d{2}-\d{2}$", date):
        return error("date must be YYYY-MM-DD")
    return jsonify(delegate.day(store(), uid(), date)), 200


@coworker_bp.post("/push/register")
@require_auth
def register_push() -> tuple:
    from coworker import push

    try:
        devices = push.register(store(), uid(), str((request.get_json(silent=True) or {}).get("token", "")))
    except ValueError as exc:
        return error(str(exc))
    return jsonify({"devices": len(devices)}), 200


@coworker_bp.post("/push/unregister")
@require_auth
def unregister_push() -> tuple:
    from coworker import push

    push.unregister(store(), uid(), str((request.get_json(silent=True) or {}).get("token", "")))
    return jsonify({"ok": True}), 200
