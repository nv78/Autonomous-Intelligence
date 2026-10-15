"""Billing, pilot applications, and data-export routes."""
from __future__ import annotations

import os
import re
from typing import Any

import requests
from flask import jsonify, request

from api_endpoints.coworker.common import coworker_bp, error, frontend_url, store, uid
from coworker import billing
from coworker.store import iso
from middleware.auth import require_auth
from middleware.rate_limit import RateLimiter

_pilot_limiter = RateLimiter(max_calls=5, period=3600, name="pilot")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PILOT_FIELDS = ("teamSize", "emailsPerDay", "meetingsPerWeek", "handOff", "tools", "notes", "utm")


@coworker_bp.get("/billing")
@require_auth
def get_billing() -> tuple:
    user_id = uid()
    if not store().get_coworker(user_id):
        return error("Set up your coworker first", 404, "not_found")
    return jsonify(billing.summary(store(), user_id)), 200


@coworker_bp.post("/billing/checkout")
@require_auth
def coworker_checkout() -> tuple:
    """Kept for older clients: same as changing plan."""
    return change_plan()


@coworker_bp.post("/billing/change")
@require_auth
def change_plan() -> tuple:
    """Upgrade, downgrade, or cancel. Returns a Checkout URL when there's no subscription yet."""
    plan = str((request.get_json(silent=True) or {}).get("plan", ""))
    if plan == "pilot":
        return error("The founder pilot is by invitation")
    try:
        result = billing.change_plan(store(), uid(), plan)
    except billing.PlanError as exc:
        code = 501 if "isn't configured" in str(exc) else 400
        return error(str(exc), code, "not_configured" if code == 501 else "bad_request")
    return jsonify({**result, "billing": billing.summary(store(), uid())}), 200


@coworker_bp.post("/billing/portal")
@require_auth
def billing_portal() -> tuple:
    try:
        url = billing.portal_url(store(), uid(), f"{frontend_url()}/app/coworker/settings")
    except billing.PlanError as exc:
        return error(str(exc))
    return jsonify({"url": url}), 200


@coworker_bp.get("/export")
@require_auth
def export_data() -> tuple:
    """Everything the coworker stored about the user (data portability)."""
    user_id = uid()
    s = store()
    tables = ("cw_coworkers", "cw_connections", "cw_people", "cw_memory", "cw_responsibilities", "cw_actions",
              "cw_activity", "cw_meetings", "cw_consents", "cw_usage")
    out: dict[str, Any] = {}
    for t in tables:
        rows = s.query(f"SELECT * FROM {t} WHERE user_id = %s", (user_id,))
        for r in rows:
            r.pop("token_enc", None)
        out[t] = rows
    out["cw_items_count"] = len(s.items(user_id, limit=100000))
    return jsonify(out), 200


@coworker_bp.delete("/data")
@require_auth
def delete_all() -> tuple:
    """Delete the coworker and everything it stored (connections revoked first)."""
    user_id = uid()
    s = store()
    from coworker import twin
    from coworker.connectors import crm, google, microsoft, slack
    from coworker.connectors.base import decrypt_token

    for row in s.list_connections(user_id):
        token = decrypt_token(row.get("token_enc"))
        if row["provider"] == "google":
            google.revoke(token)
        elif row["provider"] == "slack":
            slack.revoke(token)
        elif row["provider"] in crm.PROVIDERS:
            crm.revoke(row["provider"], token)
        elif row["provider"] == "microsoft":
            microsoft.revoke(token)
    twin.revoke(s, user_id)
    for t in ("cw_items", "cw_people", "cw_memory", "cw_responsibilities", "cw_runs", "cw_actions", "cw_activity",
              "cw_meetings", "cw_consents", "cw_twin_assets", "cw_usage", "cw_connections", "cw_coworkers"):
        s.execute(f"DELETE FROM {t} WHERE user_id = %s", (user_id,))
    return jsonify({"deleted": True}), 200


# ---------------------------------------------------------------------------
# Founder pilot applications (public; posted by the ourogen.ai landing page)
# ---------------------------------------------------------------------------

@coworker_bp.post("/pilot/applications")
def pilot_application() -> tuple:
    data = request.get_json(silent=True) or {}
    if data.get("website"):  # honeypot field, invisible to people
        return jsonify({"ok": True}), 201
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()
    if not _pilot_limiter.is_allowed(ip):
        return error("Too many submissions. Try again later.", 429, "rate_limited")
    email = str(data.get("email", "")).strip().lower()
    if not EMAIL_RE.match(email):
        return error("A valid work email is required")
    answers = {k: data.get(k) for k in PILOT_FIELDS if data.get(k) not in (None, "", [])}
    app_id = store().insert("cw_pilot_applications", {
        "name": str(data.get("name", ""))[:255], "email": email[:255], "company": str(data.get("company", ""))[:255],
        "role": str(data.get("role", ""))[:255], "answers": answers, "source": str(data.get("source", "landing"))[:255],
        "created_at": iso(),
    })
    hook = os.environ.get("PILOT_SLACK_WEBHOOK_URL")
    if hook:
        try:
            requests.post(hook, json={"text": (
                f":rocket: New pilot application: *{data.get('name', '')}* ({email}), {data.get('role', '')} at "
                f"{data.get('company', '')}. Hand off first: {', '.join(answers.get('handOff') or []) or 'n/a'}."
            )}, timeout=5)
        except requests.RequestException:
            pass
    return jsonify({"ok": True, "id": app_id, "bookingUrl": os.environ.get("PILOT_BOOKING_URL", "")}), 201


def _is_pilot_admin(user_id: int) -> bool:
    """PILOT_ADMIN_EMAILS, matched against addresses Google or Microsoft verified (sign in with one once)."""
    from coworker import identity

    admins = {e.strip().lower() for e in os.environ.get("PILOT_ADMIN_EMAILS", "").split(",") if e.strip()}
    return bool(admins & identity.verified_emails(store(), user_id))


@coworker_bp.get("/pilot/applications")
@require_auth
def list_pilot_applications() -> tuple:
    """Internal: only users listed in PILOT_ADMIN_EMAILS can read applications."""
    if not _is_pilot_admin(uid()):
        return error("Not allowed", 403, "forbidden")
    rows = store().query("SELECT * FROM cw_pilot_applications ORDER BY id DESC LIMIT 500")
    return jsonify({"applications": rows}), 200


@coworker_bp.get("/admin/vendors")
@require_auth
def vendor_status() -> tuple:
    """Internal: read-only checks of every configured vendor (admins only)."""
    from coworker import vendor_check

    if not _is_pilot_admin(uid()):
        return error("Not allowed", 403, "forbidden")
    return jsonify({"vendors": vendor_check.run_all()}), 200
