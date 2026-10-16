"""Team plan: an organization, its members, and the rules every member's coworker obeys.

* An **organization** has admins and members. Admins invite people by email;
  an invite is a signed link that only the invited address can accept.
* **Policies** set by admins are ceilings that individual settings can't exceed:

  - ``autonomy_ceiling``: ``{action_type: level}``. A member who picks
    "silent" for email is held to, say, "approve".
  - ``blocked_domains``: the coworker never sends to these.
  - ``recording_consent``: forces "all_party" for every member.
  - ``allowed_models``: members can only choose from this list.
  - ``sso_required``: members must sign in with Google or Microsoft; the
    password form refuses them.
  - ``domain_auto_join``: anyone who signs in with Google or Microsoft at the
    organization's domain joins automatically (no invite needed). Only for a
    company domain the turning-on admin's own address is at, and only one
    organization per domain.

* Joining an organization counts as the employer's authorization for its
  domain. Removing a member revokes their connections and pauses their
  coworker.
"""
from __future__ import annotations

import os
from typing import Any

from coworker import policy
from coworker.store import IntegrityError, Store, iso

ROLES = ("admin", "member")
INVITE_SALT = "coworker-org-invite"
INVITE_MAX_AGE = 14 * 86400
PUBLIC_EMAIL_DOMAINS = frozenset({
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com", "msn.com", "yahoo.com", "icloud.com",
    "me.com", "mac.com", "aol.com", "proton.me", "protonmail.com", "gmx.com", "mail.com", "yandex.com", "zoho.com",
})


class OrgError(Exception):
    def __init__(self, message: str, code: str = "invalid", status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


# -- lookups -------------------------------------------------------------------

def membership(store: Store, user_id: int) -> dict[str, Any] | None:
    return store.one("SELECT * FROM cw_org_members WHERE user_id = %s AND status = 'active' ORDER BY id LIMIT 1", (user_id,))


def org_for(store: Store, user_id: int) -> dict[str, Any] | None:
    m = membership(store, user_id)
    return store.get("cw_orgs", int(m["org_id"])) if m else None


def policies(store: Store, user_id: int) -> dict[str, Any]:
    org = org_for(store, user_id)
    return dict((org or {}).get("policies") or {})


def _require_admin(store: Store, user_id: int) -> dict[str, Any]:
    m = membership(store, user_id)
    if not m:
        raise OrgError("You're not in an organization.", "not_found", 404)
    if m["role"] != "admin":
        raise OrgError("Only organization admins can do that.", "forbidden", 403)
    org = store.get("cw_orgs", int(m["org_id"]))
    assert org is not None
    return org


# -- enforcement hooks (called from policy, executor, meetings, llm) ------------

def cap_level(store: Store, user_id: int, action_type: str, level: str) -> str:
    """The stricter of the member's level and the organization's ceiling."""
    ceiling = (policies(store, user_id).get("autonomy_ceiling") or {}).get(action_type)
    if ceiling in policy.LEVELS and policy.LEVELS.index(ceiling) < policy.LEVELS.index(level):
        return str(ceiling)
    return level


def blocked_recipients(store: Store, user_id: int, recipients: list[str]) -> list[str]:
    from email.utils import parseaddr

    blocked = {str(d).strip().lower().lstrip("@").rstrip(".") for d in policies(store, user_id).get("blocked_domains") or []} - {""}
    out = []
    for r in recipients:
        domain = parseaddr(str(r))[1].rsplit("@", 1)[-1].strip().lower().rstrip(".")
        if any(domain == b or domain.endswith("." + b) for b in blocked):  # mail.competitor.com is competitor.com
            out.append(r)
    return out


def forces_all_party_consent(store: Store, user_id: int) -> bool:
    return policies(store, user_id).get("recording_consent") == "all_party"


def allowed_models(store: Store, user_id: int) -> list[str]:
    return [str(m) for m in policies(store, user_id).get("allowed_models") or []]


# -- organization lifecycle ------------------------------------------------------

def create(store: Store, user_id: int, name: str, domain: str = "", email: str = "") -> dict[str, Any]:
    if membership(store, user_id):
        raise OrgError("You're already in an organization.", "conflict", 409)
    name = name.strip()[:255]
    if not name:
        raise OrgError("Give your organization a name.")
    org_id = store.insert("cw_orgs", {"name": name, "domain": domain.strip().lower().lstrip("@")[:255],
                                      "owner_user_id": user_id, "policies": {}, "created_at": iso()})
    store.insert("cw_org_members", {"org_id": org_id, "user_id": user_id, "email": email.lower(), "role": "admin",
                                    "status": "active", "invited_at": iso(), "joined_at": iso()})
    store.log(user_id, "org", f"Created the organization {name}")
    org = store.get("cw_orgs", org_id)
    assert org is not None
    return org


def update(store: Store, user_id: int, name: str | None = None, new_policies: dict[str, Any] | None = None,
           domain: str | None = None) -> dict[str, Any]:
    org = _require_admin(store, user_id)
    values: dict[str, Any] = {}
    if name is not None and name.strip():
        values["name"] = name.strip()[:255]
    if domain is not None:
        values["domain"] = _clean_domain(domain)
    if new_policies is not None:
        values["policies"] = clean_policies(new_policies)
    if (values.get("policies") or org.get("policies") or {}).get("domain_auto_join"):
        _check_auto_join(store, user_id, org, values.get("domain", org.get("domain") or ""))
    if values:
        store.update("cw_orgs", int(org["id"]), None, values)
        store.log(user_id, "org", "Updated organization policies" if "policies" in values else "Renamed the organization",
                  {"policies": values.get("policies")})
    fresh = store.get("cw_orgs", int(org["id"]))
    assert fresh is not None
    return fresh


def clean_policies(raw: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    ceiling = raw.get("autonomy_ceiling") or {}
    if isinstance(ceiling, dict):
        out["autonomy_ceiling"] = {k: v for k, v in ceiling.items()
                                   if k in policy.ACTION_TYPES and k not in policy.ALWAYS_APPROVE and v in policy.LEVELS}
    domains = raw.get("blocked_domains") or []
    if isinstance(domains, str):
        domains = domains.replace(",", "\n").splitlines()
    out["blocked_domains"] = sorted({str(d).strip().lower().lstrip("@") for d in domains if str(d).strip()})[:200]
    if raw.get("recording_consent") in ("all_party", ""):
        out["recording_consent"] = raw["recording_consent"]
    models = raw.get("allowed_models") or []
    out["allowed_models"] = [str(m) for m in models if isinstance(m, str)][:20]
    out["sso_required"] = bool(raw.get("sso_required"))
    out["domain_auto_join"] = bool(raw.get("domain_auto_join"))
    return out


def _clean_domain(domain: str) -> str:
    return domain.strip().lower().lstrip("@")[:255]


def _check_auto_join(store: Store, user_id: int, org: dict[str, Any], domain: str) -> None:
    """Auto-join hands membership to anyone at the domain, so the domain must really be the company's."""
    if not domain:
        raise OrgError("Set your company domain before turning on automatic joining.")
    if domain in PUBLIC_EMAIL_DOMAINS:
        raise OrgError(f"{domain} is a public email provider, so automatic joining would let anyone in.")
    from coworker import identity

    if domain not in identity.managed_domains(store, user_id):
        raise OrgError(f"To turn on automatic joining, sign in with your @{domain} Google Workspace or Microsoft work "
                       "account first: that's how we know the domain is yours.", "forbidden", 403)
    others = store.query("SELECT id, policies FROM cw_orgs WHERE domain = %s AND id != %s", (domain, org["id"]))
    if any((o.get("policies") or {}).get("domain_auto_join") for o in others):
        raise OrgError(f"Another organization already has automatic joining for {domain}.", "conflict", 409)


# -- invites ---------------------------------------------------------------------

def _secret() -> str:
    from coworker.autojoin import _secret as secret

    return secret()


def invite_token(org_id: int, email: str) -> str:
    from itsdangerous import URLSafeTimedSerializer

    return URLSafeTimedSerializer(_secret(), salt=INVITE_SALT).dumps({"o": int(org_id), "e": email.lower()})


def invite_url(org_id: int, email: str) -> str:
    base = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
    return f"{base}/app/join/{invite_token(org_id, email)}"


def invite(store: Store, user_id: int, email: str, role: str = "member") -> dict[str, Any]:
    org = _require_admin(store, user_id)
    email = email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise OrgError("Enter a valid email address.")
    if role not in ROLES:
        raise OrgError("role must be admin or member")
    existing = store.one("SELECT * FROM cw_org_members WHERE org_id = %s AND email = %s", (org["id"], email))
    if existing and existing["status"] == "active":
        raise OrgError(f"{email} is already a member.", "conflict", 409)
    if existing:
        store.update("cw_org_members", int(existing["id"]), None,
                     {"status": "invited", "role": role, "invited_by": user_id, "invited_at": iso()})
    else:
        try:
            store.insert("cw_org_members", {"org_id": org["id"], "email": email, "role": role, "status": "invited",
                                            "invited_by": user_id, "invited_at": iso()})
        except IntegrityError as exc:  # pragma: no cover - raced with another invite
            raise OrgError(f"{email} was just invited.", "conflict", 409) from exc
    url = invite_url(int(org["id"]), email)
    _send_invite(store, user_id, org, email, url)
    store.log(user_id, "org", f"Invited {email} to {org['name']} as {role}")
    return {"email": email, "role": role, "url": url}


def _send_invite(store: Store, user_id: int, org: dict[str, Any], email: str, url: str) -> str:
    """From the admin's own mailbox when it can send; else the SMTP relay; else the admin shares the link."""
    from coworker import notify
    from coworker.connectors.base import ConnectorError, Workspace

    coworker = store.get_coworker(user_id) or {}
    inviter = coworker.get("owner_name") or "Your teammate"
    subject = f"{inviter} invited you to {org['name']} on Ourogen"
    body = (f"{inviter} invited you to join {org['name']} on Ourogen, where each of you gets an AI coworker that "
            f"handles email, meetings, and follow-ups under your team's rules.\n\nAccept: {url}\n\n"
            "The link works for 14 days and only for this email address.")
    mailbox = Workspace(store, user_id).email_connector() if coworker.get("mode") == "live" else None
    if mailbox is not None and mailbox.has_scope("gmail.send"):
        try:
            mailbox.send_email(store, user_id, to=[email], subject=subject, body=body)
            return "mailbox"
        except ConnectorError:
            pass
    if os.environ.get("SMTP_URL"):
        try:
            notify._smtp_send(email, subject, body)
            return "smtp"
        except Exception:
            pass
    return ""


def read_invite(token: str) -> tuple[int, str] | None:
    from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

    try:
        data = URLSafeTimedSerializer(_secret(), salt=INVITE_SALT).loads(token, max_age=INVITE_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    return int(data["o"]), str(data["e"])


def accept(store: Store, user_id: int, user_email: str, token: str) -> dict[str, Any]:
    loaded = read_invite(token)
    if not loaded:
        raise OrgError("This invite has expired. Ask your admin for a new one.", "expired", 410)
    org_id, email = loaded
    if user_email.lower() != email:
        raise OrgError(f"This invite is for {email}. Sign in with that address to accept it.", "forbidden", 403)
    row = store.one("SELECT * FROM cw_org_members WHERE org_id = %s AND email = %s", (org_id, email))
    if not row or row["status"] == "removed":
        raise OrgError("This invite was withdrawn.", "not_found", 404)
    current = membership(store, user_id)
    if current and int(current["org_id"]) != org_id:
        raise OrgError("You're already in another organization. Leave it first.", "conflict", 409)
    store.update("cw_org_members", int(row["id"]), None, {"user_id": user_id, "status": "active", "joined_at": iso()})
    org = store.get("cw_orgs", org_id)
    assert org is not None
    _joined(store, user_id, org, email)
    return org


def _joined(store: Store, user_id: int, org: dict[str, Any], email: str) -> None:
    coworker = store.get_coworker(user_id)
    if coworker:  # the organization is the employer's authorization for its domain
        store.update_coworker(user_id, settings={**(coworker.get("settings") or {}), "employer_authorized": {
            "domain": org.get("domain") or email.split("@")[-1], "basis": "organization", "org_id": org["id"], "at": iso()}})
    store.log(user_id, "org", f"Joined {org['name']}")


# -- single sign-on ------------------------------------------------------------------

def on_sso_login(store: Store, user_id: int, email: str, managed_domain: str) -> dict[str, Any] | None:
    """After a Google or Microsoft sign-in: accept a pending invite for this address, or join the
    domain's organization if it has automatic joining on.

    ``managed_domain`` is the domain the identity provider says the company
    controls (Google Workspace ``hd``, or the Microsoft tenant's UPN domain).
    A verified address isn't enough: a personal account registered on a work
    address outlives the job. Returns the organization joined, or None.
    """
    email = email.strip().lower()
    domain = email.split("@")[-1]
    if "@" not in email or membership(store, user_id):
        return None
    invited = next((r for r in store.query(
        "SELECT m.*, o.domain AS org_domain FROM cw_org_members m JOIN cw_orgs o ON o.id = m.org_id "
        "WHERE m.email = %s AND m.status = 'invited' ORDER BY m.id", (email,))
        if managed_domain and r.get("org_domain") == managed_domain.strip().lower() == domain), None)
    if invited:  # the company's own org invited its own managed account: signing in accepts it. Others accept the link.
        store.update("cw_org_members", int(invited["id"]), None, {"user_id": user_id, "status": "active", "joined_at": iso()})
        org = store.get("cw_orgs", int(invited["org_id"]))
        assert org is not None
        _joined(store, user_id, org, email)
        return org
    if domain in PUBLIC_EMAIL_DOMAINS or managed_domain.strip().lower() != domain:
        return None
    org = next((o for o in store.query("SELECT * FROM cw_orgs WHERE domain = %s ORDER BY id", (domain,))
                if (o.get("policies") or {}).get("domain_auto_join")), None)
    if not org:
        return None
    row = store.one("SELECT * FROM cw_org_members WHERE org_id = %s AND email = %s", (org["id"], email))
    if row and row["status"] == "removed":
        return None  # an admin removed this person; don't let them walk back in
    if row:
        store.update("cw_org_members", int(row["id"]), None, {"user_id": user_id, "status": "active", "joined_at": iso()})
    else:
        store.insert("cw_org_members", {"org_id": org["id"], "user_id": user_id, "email": email, "role": "member",
                                        "status": "active", "invited_at": iso(), "joined_at": iso()})
    _joined(store, user_id, org, email)
    return org


def sso_required(store: Store, email: str) -> bool:
    """Whether this address belongs to an organization that only allows Google/Microsoft sign-in."""
    rows = store.query("SELECT o.policies FROM cw_org_members m JOIN cw_orgs o ON o.id = m.org_id "
                       "WHERE m.email = %s AND m.status = 'active'", (email.strip().lower(),))
    return any((r.get("policies") or {}).get("sso_required") for r in rows)


# -- members ----------------------------------------------------------------------

def set_role(store: Store, user_id: int, member_id: int, role: str) -> None:
    org = _require_admin(store, user_id)
    if role not in ROLES:
        raise OrgError("role must be admin or member")
    member = store.one("SELECT * FROM cw_org_members WHERE id = %s AND org_id = %s", (member_id, org["id"]))
    if not member:
        raise OrgError("Member not found", "not_found", 404)
    if role != "admin" and member["role"] == "admin" and _admin_count(store, int(org["id"])) <= 1:
        raise OrgError("An organization needs at least one admin.", "conflict", 409)
    store.update("cw_org_members", member_id, None, {"role": role})
    store.log(user_id, "org", f"Made {member['email']} {'an admin' if role == 'admin' else 'a member'}")


def _admin_count(store: Store, org_id: int) -> int:
    row = store.one("SELECT COUNT(*) AS n FROM cw_org_members WHERE org_id = %s AND role = 'admin' AND status = 'active'",
                    (org_id,))
    return int((row or {}).get("n") or 0)


def remove(store: Store, user_id: int, member_id: int) -> dict[str, Any]:
    """Remove a member: their coworker is paused and every connection revoked."""
    org = _require_admin(store, user_id)
    member = store.one("SELECT * FROM cw_org_members WHERE id = %s AND org_id = %s", (member_id, org["id"]))
    if not member or member["status"] == "removed":
        raise OrgError("Member not found", "not_found", 404)
    if member["role"] == "admin" and member["status"] == "active" and _admin_count(store, int(org["id"])) <= 1:
        raise OrgError("An organization needs at least one admin.", "conflict", 409)
    store.update("cw_org_members", member_id, None, {"status": "removed"})
    revoked: list[str] = []
    if member.get("user_id") and member["status"] == "active":
        from coworker import admin

        result = admin.revoke_all(store, int(member["user_id"]))
        revoked = result["revoked"]
        store.log(int(member["user_id"]), "org", f"Removed from {org['name']}: access revoked and coworker paused")
    store.log(user_id, "org", f"Removed {member['email']} from {org['name']}")
    return {"removed": member["email"], "revoked": revoked}


def leave(store: Store, user_id: int) -> None:
    m = membership(store, user_id)
    if not m:
        raise OrgError("You're not in an organization.", "not_found", 404)
    if m["role"] == "admin" and _admin_count(store, int(m["org_id"])) <= 1:
        raise OrgError("Make someone else an admin before you leave.", "conflict", 409)
    store.update("cw_org_members", int(m["id"]), None, {"status": "removed"})
    store.log(user_id, "org", "Left the organization")


def seats(store: Store, org_id: int) -> int:
    row = store.one("SELECT COUNT(*) AS n FROM cw_org_members WHERE org_id = %s AND status IN ('active', 'invited')", (org_id,))
    return int((row or {}).get("n") or 0)


def overview(store: Store, user_id: int) -> dict[str, Any] | None:
    """The organization as the caller may see it: members and usage for admins."""
    m = membership(store, user_id)
    if not m:
        return None
    org = store.get("cw_orgs", int(m["org_id"]))
    assert org is not None
    is_admin = m["role"] == "admin"
    rows = store.query("SELECT * FROM cw_org_members WHERE org_id = %s AND status != 'removed' ORDER BY id", (org["id"],))
    members = []
    for r in rows:
        entry: dict[str, Any] = {"id": r["id"], "email": r["email"], "role": r["role"], "status": r["status"],
                                 "joinedAt": r.get("joined_at")}
        if is_admin and r.get("user_id") and r["status"] == "active":
            entry["usage"] = _usage(store, int(r["user_id"]))
        members.append(entry)
    return {
        "id": org["id"], "name": org["name"], "domain": org.get("domain") or "", "role": m["role"],
        "policies": org.get("policies") or {}, "members": members, "seats": seats(store, int(org["id"])),
        "scim": bool(org.get("scim_token_hash")),
    }


def _usage(store: Store, user_id: int) -> dict[str, Any]:
    from coworker import metrics

    tr = metrics.track_record(store, user_id, days=30)
    coworker = store.get_coworker(user_id) or {}
    from coworker import schedules

    return {"status": coworker.get("status") or "not set up", "executed": tr["executed"], "acceptance": tr["acceptance"],
            "hoursSaved": tr["hoursSaved"], "callMinutes": tr["calls"]["minutes"], "pending": tr["pending"],
            "taskSpendUsd": schedules.spend(store, user_id)}
