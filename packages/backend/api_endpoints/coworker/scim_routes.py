"""SCIM 2.0 for identity providers (see ``coworker/scim.py``), plus the admin's token management."""
from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import jsonify, request

from api_endpoints.coworker.common import coworker_bp, error, store, uid
from coworker import orgs, scim
from middleware.auth import require_auth

SCIM_TYPE = "application/scim+json"


def _scim(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Authenticate the organization's token and turn ScimError into a SCIM error response."""
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            org = scim.org_for_token(store(), request.headers.get("Authorization", ""))
            body, status = fn(org, *args, **kwargs)
        except scim.ScimError as exc:
            body, status = exc.body(), exc.status
        if body is None:
            return "", status
        resp = jsonify(body)
        resp.status_code = status
        resp.mimetype = SCIM_TYPE
        return resp
    return wrapper


@coworker_bp.get("/scim/v2/ServiceProviderConfig")
@_scim
def scim_config(org: dict[str, Any]) -> tuple:
    return scim.SERVICE_PROVIDER_CONFIG, 200


@coworker_bp.get("/scim/v2/Users")
@_scim
def scim_list(org: dict[str, Any]) -> tuple:
    return scim.list_users(store(), org, request.args.get("filter", ""), int(request.args.get("startIndex") or 1),
                           int(request.args.get("count") or 100)), 200


@coworker_bp.post("/scim/v2/Users")
@_scim
def scim_create(org: dict[str, Any]) -> tuple:
    return scim.create_user(store(), org, request.get_json(silent=True) or {}), 201


@coworker_bp.get("/scim/v2/Users/<member_id>")
@_scim
def scim_get(org: dict[str, Any], member_id: str) -> tuple:
    return scim.resource(scim._member(store(), org, member_id)), 200


@coworker_bp.patch("/scim/v2/Users/<member_id>")
@_scim
def scim_patch(org: dict[str, Any], member_id: str) -> tuple:
    return scim.patch_user(store(), org, scim._member(store(), org, member_id), request.get_json(silent=True) or {}), 200


@coworker_bp.put("/scim/v2/Users/<member_id>")
@_scim
def scim_put(org: dict[str, Any], member_id: str) -> tuple:
    return scim.replace_user(store(), org, scim._member(store(), org, member_id), request.get_json(silent=True) or {}), 200


@coworker_bp.delete("/scim/v2/Users/<member_id>")
@_scim
def scim_delete(org: dict[str, Any], member_id: str) -> tuple:
    scim.set_active(store(), org, scim._member(store(), org, member_id), False)
    return None, 204


@coworker_bp.post("/org/scim-token")
@require_auth
def create_scim_token() -> tuple:
    try:
        return jsonify({"token": scim.new_token(store(), uid())}), 201
    except orgs.OrgError as exc:
        return error(str(exc), exc.status, exc.code)


@coworker_bp.delete("/org/scim-token")
@require_auth
def delete_scim_token() -> tuple:
    try:
        scim.revoke_token(store(), uid())
    except orgs.OrgError as exc:
        return error(str(exc), exc.status, exc.code)
    return jsonify({"ok": True}), 200
