"""Verified identities: who a user provably is, according to Google or Microsoft.

A typed-in email (registration, profile) proves nothing. Everything that grants
trust based on an email or domain reads this table instead:

* the pilot admin list,
* claiming a company domain for automatic team joining,
* accepting a team invite automatically at sign-in,
* matching Teams and Google Chat users to their coworker.

Rows are written only after a successful Google or Microsoft sign-in (or connecting
a mailbox), keyed by the provider's stable subject (Google ``sub``, Microsoft object
id). The first verified sign-in to a password account also replaces its password and
ends every existing session. Otherwise, someone who registered a victim's address
first would keep a working password and token after the victim takes the account over.
"""
from __future__ import annotations

from typing import Any

from coworker.store import IntegrityError, Store, iso, parse_iso

MICROSOFT_PERSONAL_TENANT = "9188040d-6c67-4c5b-b112-36a304b66dad"


def record(store: Store, user_id: int, provider: str, subject: str, email: str, managed_domain: str = "",
           tenant: str = "") -> bool:
    """Remember a verified identity. Returns True the first time this user's ``email`` is verified."""
    first = not store.one("SELECT id FROM cw_verified_identities WHERE user_id = %s AND email = %s LIMIT 1",
                          (user_id, email.strip().lower()))
    values = {"user_id": user_id, "email": email.strip().lower()[:255], "managed_domain": managed_domain.strip().lower()[:255],
              "tenant": tenant[:255], "last_seen_at": iso()}
    existing = store.one("SELECT id FROM cw_verified_identities WHERE provider = %s AND subject = %s", (provider, subject))
    if existing:
        store.update("cw_verified_identities", int(existing["id"]), None, values)
    else:
        try:
            store.insert("cw_verified_identities", {"provider": provider, "subject": subject[:255], "created_at": iso(), **values})
        except IntegrityError:  # two sign-ins at once
            pass
    return first


def verified_emails(store: Store, user_id: int) -> set[str]:
    return {r["email"] for r in store.query("SELECT email FROM cw_verified_identities WHERE user_id = %s", (user_id,))}


def managed_domains(store: Store, user_id: int) -> set[str]:
    return {r["managed_domain"] for r in store.query(
        "SELECT managed_domain FROM cw_verified_identities WHERE user_id = %s AND managed_domain != ''", (user_id,))}


def user_for(store: Store, provider: str, subject: str = "", email: str = "") -> int | None:
    """The user a verified provider identity belongs to (by subject, or by email for that provider)."""
    if subject:
        row = store.one("SELECT user_id FROM cw_verified_identities WHERE provider = %s AND subject = %s", (provider, subject))
    else:
        row = store.one("SELECT user_id FROM cw_verified_identities WHERE provider = %s AND email = %s ORDER BY id LIMIT 1",
                        (provider, email.strip().lower()))
    return int(row["user_id"]) if row else None


# -- sessions -----------------------------------------------------------------------------------

def revoke_sessions(store: Store, user_id: int) -> None:
    """Every token issued before now stops working."""
    now = iso()
    try:
        store.insert("cw_auth_epochs", {"user_id": user_id, "tokens_valid_after": now})
    except IntegrityError:
        store.execute("UPDATE cw_auth_epochs SET tokens_valid_after = %s WHERE user_id = %s", (now, user_id))


def token_revoked(store: Store, payload: dict[str, Any]) -> bool:
    try:
        user_id = int(payload.get("sub") or 0)
    except (TypeError, ValueError):
        return False
    row = store.one("SELECT tokens_valid_after FROM cw_auth_epochs WHERE user_id = %s", (user_id,))
    if not row:
        return False
    after = parse_iso(row["tokens_valid_after"])
    issued = payload.get("iat")
    return bool(after and (not issued or issued < int(after.timestamp())))
