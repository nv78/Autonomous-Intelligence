"""Team plan: organization, members, invites, and policies (see ``coworker/orgs.py``)."""
from __future__ import annotations

from typing import Any

from flask import jsonify, request

from api_endpoints.coworker.common import coworker_bp, error, owner_profile, store, uid
from coworker import billing, orgs
from coworker.billing import PlanError
from middleware.auth import require_auth


def _fail(exc: orgs.OrgError) -> tuple:
    return error(str(exc), exc.status, exc.code)


def _seats_changed(user_id: int) -> None:
    org = orgs.org_for(store(), user_id)
    if org:
        try:
            billing.sync_seats(store(), org)
        except Exception as exc:  # billing must never block team management; Stripe reconciles on the next change
            store().log(user_id, "billing", f"Couldn't update Team seats in Stripe: {exc}")


@coworker_bp.get("/org")
@require_auth
def get_org() -> tuple:
    return jsonify({"org": orgs.overview(store(), uid())}), 200


@coworker_bp.post("/org")
@require_auth
def create_org() -> tuple:
    user_id = uid()
    data = request.get_json(silent=True) or {}
    try:
        billing.require(store(), user_id, "admin")
    except PlanError as exc:
        return error(f"{exc} Teams need the Team plan.", 402, "plan_required")
    _, email = owner_profile(user_id)
    coworker = store().get_coworker(user_id) or {}
    try:
        orgs.create(store(), user_id, str(data.get("name", "")), str(data.get("domain", "")),
                    email or coworker.get("owner_email") or "")
    except orgs.OrgError as exc:
        return _fail(exc)
    return jsonify({"org": orgs.overview(store(), user_id)}), 201


@coworker_bp.patch("/org")
@require_auth
def update_org() -> tuple:
    data = request.get_json(silent=True) or {}
    try:
        orgs.update(store(), uid(), data.get("name"), data.get("policies") if isinstance(data.get("policies"), dict) else None,
                    domain=str(data["domain"]) if "domain" in data else None)
    except orgs.OrgError as exc:
        return _fail(exc)
    return jsonify({"org": orgs.overview(store(), uid())}), 200


@coworker_bp.post("/org/invites")
@require_auth
def invite_member() -> tuple:
    data = request.get_json(silent=True) or {}
    try:
        sent = orgs.invite(store(), uid(), str(data.get("email", "")), str(data.get("role", "member")))
    except orgs.OrgError as exc:
        return _fail(exc)
    _seats_changed(uid())
    return jsonify({"invite": sent, "org": orgs.overview(store(), uid())}), 201


@coworker_bp.post("/org/join/<token>")
@require_auth
def join_org(token: str) -> tuple:
    user_id = uid()
    _, email = owner_profile(user_id)
    coworker = store().get_coworker(user_id) or {}
    try:
        orgs.accept(store(), user_id, email or coworker.get("owner_email") or "", token)
    except orgs.OrgError as exc:
        return _fail(exc)
    return jsonify({"org": orgs.overview(store(), user_id)}), 200


@coworker_bp.patch("/org/members/<int:member_id>")
@require_auth
def change_member(member_id: int) -> tuple:
    try:
        orgs.set_role(store(), uid(), member_id, str((request.get_json(silent=True) or {}).get("role", "")))
    except orgs.OrgError as exc:
        return _fail(exc)
    return jsonify({"org": orgs.overview(store(), uid())}), 200


@coworker_bp.delete("/org/members/<int:member_id>")
@require_auth
def remove_member(member_id: int) -> tuple:
    user_id = uid()
    try:
        result = orgs.remove(store(), user_id, member_id)
    except orgs.OrgError as exc:
        return _fail(exc)
    _seats_changed(user_id)
    return jsonify({**result, "org": orgs.overview(store(), user_id)}), 200


@coworker_bp.post("/org/leave")
@require_auth
def leave_org() -> Any:
    user_id = uid()
    org = orgs.org_for(store(), user_id)
    try:
        orgs.leave(store(), user_id)
    except orgs.OrgError as exc:
        return _fail(exc)
    if org:
        try:
            billing.sync_seats(store(), org)
        except Exception:  # pragma: no cover
            pass
    return jsonify({"org": None}), 200
