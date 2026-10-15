"""SCIM 2.0 provisioning: an identity provider (Okta, Microsoft Entra, Google) adds and removes team members.

Base URL: ``<BACKEND_URL>/api/coworker/scim/v2``, with a bearer token an organization admin
creates in **Team → Sign-in → SCIM token** (shown once; only its hash is stored).

* **Create a user**: the person is invited, exactly as if an admin had invited them. They
  join when they accept the invite or first sign in with Google or Microsoft.
* **Deactivate** (``active: false``) **or delete a user**: removed like an admin removal, so
  their coworker is paused and every connection is revoked.
* **Reactivate**: invited again.

Users only. Group push isn't supported, which the major providers allow. Seats sync to
Stripe after each change.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any

from coworker import orgs
from coworker.store import Store

USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
LIST_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:ListResponse"
ERROR_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:Error"
PATCH_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:PatchOp"


class ScimError(Exception):
    def __init__(self, message: str, status: int = 400, scim_type: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.scim_type = scim_type

    def body(self) -> dict[str, Any]:
        out: dict[str, Any] = {"schemas": [ERROR_SCHEMA], "detail": str(self), "status": str(self.status)}
        if self.scim_type:
            out["scimType"] = self.scim_type
        return out


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_token(store: Store, admin_user_id: int) -> str:
    """Create (or rotate) the organization's SCIM token. Returned once."""
    org = orgs._require_admin(store, admin_user_id)
    token = "scim_" + secrets.token_urlsafe(32)
    store.update("cw_orgs", int(org["id"]), None, {"scim_token_hash": _hash(token)})
    store.log(admin_user_id, "org", "Created a new SCIM token (the previous one stops working)")
    return token


def revoke_token(store: Store, admin_user_id: int) -> None:
    org = orgs._require_admin(store, admin_user_id)
    store.update("cw_orgs", int(org["id"]), None, {"scim_token_hash": ""})
    store.log(admin_user_id, "org", "Turned off SCIM provisioning")


def org_for_token(store: Store, auth_header: str) -> dict[str, Any]:
    token = auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else ""
    if not token:
        raise ScimError("Missing bearer token", 401)
    digest = _hash(token)
    for org in store.query("SELECT * FROM cw_orgs WHERE scim_token_hash != ''"):
        if hmac.compare_digest(str(org["scim_token_hash"]), digest):
            return org
    raise ScimError("Invalid token", 401)


def _actor(store: Store, org: dict[str, Any]) -> int:
    """An active admin to act as, for the audit trail and invite emails."""
    row = store.one("SELECT user_id FROM cw_org_members WHERE org_id = %s AND role = 'admin' AND status = 'active' "
                    "AND user_id IS NOT NULL ORDER BY id LIMIT 1", (org["id"],))
    if not row:
        raise ScimError("The organization has no active admin", 409)
    return int(row["user_id"])


def resource(member: dict[str, Any], base_url: str = "") -> dict[str, Any]:
    email = member["email"]
    return {
        "schemas": [USER_SCHEMA], "id": str(member["id"]), "userName": email, "displayName": email,
        "emails": [{"value": email, "primary": True, "type": "work"}], "active": member["status"] != "removed",
        "meta": {"resourceType": "User", **({"location": f"{base_url}/Users/{member['id']}"} if base_url else {})},
    }


def _member(store: Store, org: dict[str, Any], member_id: str) -> dict[str, Any]:
    row = store.one("SELECT * FROM cw_org_members WHERE id = %s AND org_id = %s", (int(member_id) if member_id.isdigit() else -1,
                                                                                 org["id"]))
    if not row:
        raise ScimError("User not found", 404)
    return row


def list_users(store: Store, org: dict[str, Any], filter_: str = "", start: int = 1, count: int = 100) -> dict[str, Any]:
    rows = store.query("SELECT * FROM cw_org_members WHERE org_id = %s ORDER BY id", (org["id"],))
    if filter_:
        import re

        m = re.fullmatch(r'\s*(userName|emails(?:\.value)?|emails\[type eq "work"\]\.value)\s+eq\s+"([^"]*)"\s*', filter_, re.I)
        if not m:
            raise ScimError("Only 'userName eq \"...\"' filters are supported", 400, "invalidFilter")
        rows = [r for r in rows if r["email"] == m.group(2).strip().lower()]
    start, count = max(1, start), max(0, min(count, 200))
    page = rows[start - 1:start - 1 + count]
    return {"schemas": [LIST_SCHEMA], "totalResults": len(rows), "startIndex": start, "itemsPerPage": len(page),
            "Resources": [resource(r) for r in page]}


def _email_of(body: dict[str, Any]) -> str:
    emails = body.get("emails") or []
    primary = next((e.get("value") for e in emails if isinstance(e, dict) and e.get("primary")), None)
    value = str(body.get("userName") or primary or (emails[0].get("value") if emails and isinstance(emails[0], dict) else "") or "")
    return value.strip().lower()


def create_user(store: Store, org: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
    email = _email_of(body)
    if "@" not in email:
        raise ScimError("userName must be an email address", 400, "invalidValue")
    existing = store.one("SELECT * FROM cw_org_members WHERE org_id = %s AND email = %s", (org["id"], email))
    if existing and existing["status"] != "removed":
        raise ScimError(f"{email} already exists", 409, "uniqueness")
    if body.get("active") is False:
        raise ScimError("Create the user active; deactivate it afterwards", 400, "invalidValue")
    try:
        orgs.invite(store, _actor(store, org), email, "member")
    except orgs.OrgError as exc:
        raise ScimError(str(exc), exc.status) from exc
    _synced(store, org)
    row = store.one("SELECT * FROM cw_org_members WHERE org_id = %s AND email = %s", (org["id"], email))
    assert row is not None
    return resource(row)


def set_active(store: Store, org: dict[str, Any], member: dict[str, Any], active: bool) -> dict[str, Any]:
    if active and member["status"] == "removed":
        try:
            orgs.invite(store, _actor(store, org), member["email"], member.get("role") or "member")
        except orgs.OrgError as exc:
            raise ScimError(str(exc), exc.status) from exc
    elif not active and member["status"] != "removed":
        try:
            orgs.remove(store, _actor(store, org), int(member["id"]))
        except orgs.OrgError as exc:
            raise ScimError(str(exc), exc.status) from exc
    _synced(store, org)
    fresh = store.one("SELECT * FROM cw_org_members WHERE id = %s", (member["id"],))
    assert fresh is not None
    return resource(fresh)


def patch_user(store: Store, org: dict[str, Any], member: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
    """Okta and Entra send ``{"op": "replace", "path": "active", "value": false}`` or ``{"op": "Replace", "value": {"active": false}}``."""
    active: bool | None = None
    for op in body.get("Operations") or []:
        if str(op.get("op", "")).lower() not in ("replace", "add"):
            continue
        value = op.get("value")
        if str(op.get("path") or "").lower() == "active":
            active = value if isinstance(value, bool) else str(value).lower() == "true"
        elif isinstance(value, dict) and "active" in value:
            active = value["active"] if isinstance(value["active"], bool) else str(value["active"]).lower() == "true"
    return set_active(store, org, member, active) if active is not None else resource(member)


def replace_user(store: Store, org: dict[str, Any], member: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
    if _email_of(body) and _email_of(body) != member["email"]:
        raise ScimError("Changing a user's email isn't supported; deactivate and create a new user", 400, "mutability")
    return set_active(store, org, member, body.get("active", True) is not False)


def _synced(store: Store, org: dict[str, Any]) -> None:
    from coworker import billing

    try:
        billing.sync_seats(store, org)
    except Exception as exc:  # billing must never block provisioning; Stripe reconciles on the next change
        store.log(int(org["owner_user_id"]), "billing", f"Couldn't update Team seats in Stripe: {exc}")


SERVICE_PROVIDER_CONFIG = {
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
    "patch": {"supported": True}, "bulk": {"supported": False, "maxOperations": 0, "maxPayloadSize": 0},
    "filter": {"supported": True, "maxResults": 200}, "changePassword": {"supported": False},
    "sort": {"supported": False}, "etag": {"supported": False},
    "authenticationSchemes": [{"type": "oauthbearertoken", "name": "Bearer token", "primary": True,
                               "description": "Token from Ourogen → Team → Sign-in → SCIM token"}],
}
