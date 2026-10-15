"""Coworker profile, demo workspace, memory, and style routes."""
from __future__ import annotations

from typing import Any

from flask import jsonify, request

from api_endpoints.coworker.common import (
    coworker_bp,
    error,
    llm_available,
    owner_profile,
    serialize_coworker,
    store,
    uid,
)
from coworker import memory, style
from coworker.connectors.demo import DemoConnector
from coworker.demo_data import SCENARIOS
from middleware.auth import require_auth

ALLOWED_SETTINGS = {
    "company_name", "company_domain", "timezone", "working_hours", "disclosure_text",
    "disclose_on_approved", "send_delay_seconds", "slack_channels", "meeting_join_policy",
    "recording_consent", "digest_email", "notify_approvals", "model", "weekly_report",
}


def _require_coworker(user_id: int) -> dict[str, Any] | None:
    return store().get_coworker(user_id)


def refresh_knowledge(user_id: int) -> dict[str, Any]:
    """Rebuild memory and style after new content arrives."""
    s = store()
    counts = memory.rebuild(s, user_id)
    profile = style.build_profile(s, user_id)
    existing = (s.get_coworker(user_id) or {}).get("style_profile") or {}
    if existing.get("rules"):
        profile["rules"] = existing["rules"]
        profile["summary"] = style.summarize(profile)
    s.update_coworker(user_id, style_profile=profile)
    return {"memory": counts, "style": profile}


@coworker_bp.get("")
@require_auth
def get_coworker() -> tuple:
    user_id = uid()
    row = _require_coworker(user_id)
    from coworker import voice
    from coworker.connectors import (
        google,
        hubspot,
        microsoft,
        pipedrive,
        recall,
        salesforce,
        slack,
        tavus,
    )

    capabilities = {
        "llm": llm_available(user_id),
        "google": google.is_configured(),
        "microsoft": microsoft.is_configured(),
        "slack_oauth": slack.is_configured(),
        "hubspot_oauth": hubspot.is_configured(),
        "salesforce_oauth": salesforce.is_configured(),
        "pipedrive_oauth": pipedrive.is_configured(),
        "voice": voice.is_configured(),
        "avatar": tavus.is_configured(),
        "meeting_bot": recall.is_configured(),
    }
    if not row:
        return jsonify({"coworker": None, "capabilities": capabilities, "scenarios": _scenarios()}), 200
    return jsonify({
        "coworker": serialize_coworker(row),
        "connections": [_serialize_connection(c) for c in store().list_connections(user_id)],
        "capabilities": capabilities,
        "scenarios": _scenarios(),
    }), 200


def _scenarios() -> list[dict[str, str]]:
    return [{"id": k, "label": v["label"]} for k, v in SCENARIOS.items()]


def _serialize_connection(c: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider": c["provider"], "account": c.get("account_label") or "", "status": c["status"],
        "error": c.get("error") or "", "lastSyncedAt": c.get("last_synced_at"),
        "scopes": c.get("scopes") or "",
    }


@coworker_bp.post("")
@require_auth
def create_coworker() -> tuple:
    """Create the coworker. ``mode`` is ``demo`` (seeded workspace) or ``live``."""
    user_id = uid()
    data = request.get_json(silent=True) or {}
    mode = data.get("mode", "demo")
    if mode not in ("demo", "live"):
        return error("mode must be 'demo' or 'live'")
    name, email = owner_profile(user_id)
    name = (data.get("name") or name or "").strip()
    email = (data.get("email") or email or "").strip().lower()
    from coworker import governance

    if governance.org_disabled(email):
        return error("Your organization has turned off AI coworkers for your account. Ask your admin.", 403, "org_disabled")
    s = store()
    row = s.create_coworker(user_id, name, email, mode=mode)
    if row["mode"] != mode:
        s.update_coworker(user_id, mode=mode)
    seeded = 0
    if mode == "demo":
        seeded = DemoConnector.seed(s, user_id, row["owner_name"] or name, row["owner_email"] or email)
        refresh_knowledge(user_id)
        s.log(user_id, "setup", "Connected the Anote demo workspace", {"items": seeded})
    row = s.get_coworker(user_id) or row
    return jsonify({"coworker": serialize_coworker(row), "seeded": seeded}), 201


@coworker_bp.patch("")
@require_auth
def update_coworker() -> tuple:
    user_id = uid()
    row = _require_coworker(user_id)
    if not row:
        return error("Set up your coworker first", 404, "not_found")
    data = request.get_json(silent=True) or {}
    values: dict[str, Any] = {}
    if "displayName" in data:
        values["display_name"] = str(data["displayName"])[:255]
    if "persona" in data:
        values["persona"] = str(data["persona"])[:4000]
    if "mode" in data and data["mode"] in ("demo", "live"):
        values["mode"] = data["mode"]
    if "onboarding" in data and isinstance(data["onboarding"], dict):
        values["onboarding"] = {**(row.get("onboarding") or {}), **data["onboarding"]}
    if "settings" in data and isinstance(data["settings"], dict):
        clean = {k: v for k, v in data["settings"].items() if k in ALLOWED_SETTINGS}
        if "model" in clean:
            from coworker import llm

            choice = next((m for m in llm.models_for(user_id) if m["id"] == clean["model"]), None)
            if not choice:
                return error("Unknown model")
            if not choice["available"]:
                return error(f"Add your {choice['provider'].title()} API key in Settings to use {choice['label']}.",
                             400, "key_required")
        values["settings"] = {**(row.get("settings") or {}), **clean}
    store().update_coworker(user_id, **values)
    return jsonify({"coworker": serialize_coworker(store().get_coworker(user_id) or row)}), 200


@coworker_bp.post("/demo/simulate")
@require_auth
def simulate() -> tuple:
    """Drop a scripted event into the demo workspace (new lead, phishing, ...)."""
    user_id = uid()
    row = _require_coworker(user_id)
    if not row:
        return error("Set up your coworker first", 404, "not_found")
    if row["mode"] != "demo":
        return error("Simulations only run in the demo workspace")
    scenario = (request.get_json(silent=True) or {}).get("scenario", "")
    item_id = DemoConnector.inject(store(), user_id, scenario)
    if not item_id:
        return error(f"Unknown scenario '{scenario}'")
    memory.rebuild(store(), user_id)
    store().log(user_id, "simulation", f"Simulated: {SCENARIOS[scenario]['label']}", {"item_id": item_id})
    return jsonify({"itemId": item_id}), 201


@coworker_bp.post("/demo/reset")
@require_auth
def reset_demo() -> tuple:
    user_id = uid()
    row = _require_coworker(user_id)
    if not row or row["mode"] != "demo":
        return error("Reset only applies to the demo workspace")
    s = store()
    for table in ("cw_items", "cw_people", "cw_memory", "cw_actions", "cw_runs", "cw_activity", "cw_meetings"):
        s.execute(f"DELETE FROM {table} WHERE user_id = %s", (user_id,))
    seeded = DemoConnector.seed(s, user_id, row["owner_name"], row["owner_email"])
    refresh_knowledge(user_id)
    return jsonify({"seeded": seeded}), 200


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

@coworker_bp.post("/memory/rebuild")
@require_auth
def rebuild_memory() -> tuple:
    user_id = uid()
    if not _require_coworker(user_id):
        return error("Set up your coworker first", 404, "not_found")
    result = refresh_knowledge(user_id)
    if llm_available(user_id) and (request.get_json(silent=True) or {}).get("enrich"):
        from coworker.llm import complete_text

        result["enriched"] = memory.enrich_people_with_llm(store(), user_id, lambda p: complete_text(p, user_id=user_id))
    return jsonify(result), 200


@coworker_bp.get("/memory/learned")
@require_auth
def learned() -> tuple:
    user_id = uid()
    row = _require_coworker(user_id)
    if not row:
        return error("Set up your coworker first", 404, "not_found")
    summary = memory.learned_summary(store(), user_id)
    summary["style"] = row.get("style_profile") or {}
    return jsonify(summary), 200


@coworker_bp.get("/memory/people")
@require_auth
def list_people() -> tuple:
    return jsonify({"people": store().people(uid())}), 200


@coworker_bp.patch("/memory/people/<int:person_id>")
@require_auth
def edit_person(person_id: int) -> tuple:
    user_id = uid()
    data = request.get_json(silent=True) or {}
    values = {k: str(v)[:255] for k, v in data.items() if k in ("name", "company", "role", "relationship", "notes")}
    if not values:
        return error("Nothing to update")
    values["user_edited"] = 1  # type: ignore[assignment]
    if not store().update("cw_people", person_id, user_id, values):
        return error("Not found", 404, "not_found")
    return jsonify({"person": store().get("cw_people", person_id, user_id)}), 200


@coworker_bp.delete("/memory/people/<int:person_id>")
@require_auth
def forget_person(person_id: int) -> tuple:
    if not store().update("cw_people", person_id, uid(), {"hidden": 1}):
        return error("Not found", 404, "not_found")
    return jsonify({"forgotten": True}), 200


@coworker_bp.get("/memory/timeline")
@require_auth
def timeline() -> tuple:
    user_id = uid()
    kind = request.args.get("kind")
    rows = store().memories(user_id, kind=kind)
    subject = (request.args.get("subject") or "").lower()
    if subject:
        rows = [r for r in rows if subject in (r.get("subject") or "").lower()]
    return jsonify({"entries": rows[:300]}), 200


@coworker_bp.delete("/memory/<int:memory_id>")
@require_auth
def forget_memory(memory_id: int) -> tuple:
    if not store().update("cw_memory", memory_id, uid(), {"hidden": 1}):
        return error("Not found", 404, "not_found")
    return jsonify({"forgotten": True}), 200


@coworker_bp.get("/memory/recall")
@require_auth
def recall() -> tuple:
    q = request.args.get("q", "")
    if not q.strip():
        return error("q is required")
    return jsonify({"results": memory.recall(store(), uid(), q)}), 200


@coworker_bp.get("/memory/status")
@require_auth
def status_of() -> tuple:
    name = request.args.get("name", "")
    if not name.strip():
        return error("name is required")
    return jsonify(memory.account_status(store(), uid(), name)), 200


@coworker_bp.get("/items/<int:item_id>")
@require_auth
def get_item(item_id: int) -> tuple:
    user_id = uid()
    item = store().get("cw_items", item_id, user_id)
    if not item:
        return error("Not found", 404, "not_found")
    thread = store().thread(user_id, item["thread_id"]) if item.get("thread_id") else [item]
    return jsonify({"item": item, "thread": thread}), 200


@coworker_bp.get("/inbox")
@require_auth
def inbox() -> tuple:
    """The synced mailbox with the coworker's triage applied."""
    user_id = uid()
    s = store()
    ctx = memory.company_context(s, user_id)
    latest: dict[str, dict[str, Any]] = {}
    for it in s.items(user_id, kind="email", limit=1000):
        latest.setdefault(it["thread_id"], it)
    threads = [
        {**memory.cite({"type": "item", **it}), "category": memory.classify(it, ctx) if it["direction"] == "inbound" else "sent",
         "awaitingReply": it["direction"] == "inbound" and not memory.is_noise(it)}
        for it in latest.values()
    ]
    threads.sort(key=lambda t: t["date"] or "", reverse=True)
    return jsonify({"threads": threads[:200]}), 200


# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------

@coworker_bp.get("/style")
@require_auth
def get_style() -> tuple:
    row = _require_coworker(uid())
    return jsonify({"style": (row or {}).get("style_profile") or {}}), 200


@coworker_bp.post("/style/rules")
@require_auth
def add_style_rule() -> tuple:
    user_id = uid()
    row = _require_coworker(user_id)
    if not row:
        return error("Set up your coworker first", 404, "not_found")
    rule = str((request.get_json(silent=True) or {}).get("rule", "")).strip()
    if not rule:
        return error("rule is required")
    profile = style.add_rule(row.get("style_profile") or {}, rule[:300])
    store().update_coworker(user_id, style_profile=profile)
    return jsonify({"style": profile}), 200


@coworker_bp.delete("/style/rules")
@require_auth
def clear_style_rules() -> tuple:
    user_id = uid()
    row = _require_coworker(user_id)
    profile = {**((row or {}).get("style_profile") or {}), "rules": []}
    profile["summary"] = style.summarize(profile)
    store().update_coworker(user_id, style_profile=profile)
    return jsonify({"style": profile}), 200


@coworker_bp.get("/models")
@require_auth
def list_models() -> tuple:
    """Models the coworker can run on, and which ones this user has keys for."""
    from coworker import llm

    return jsonify({"models": llm.models_for(uid()), "default": llm.DEFAULT_MODEL}), 200
