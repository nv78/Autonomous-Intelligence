"""Employer authorization and org-wide controls.

* **Employer authorization.** When the coworker runs on a work account (a
  company email domain, not gmail.com and friends), the user confirms that
  they own the company or their employer allows an AI coworker to act for
  them. Until they do, it can read and draft but won't send anything.
* **Org-wide disable.** ``COWORKER_DISABLED_DOMAINS`` (comma-separated)
  blocks the coworker for every account on those domains: an employer that
  asks us to turn it off for their company gets that in one setting. Their
  users can't create a coworker, and existing ones are paused.
"""
from __future__ import annotations

import os
from typing import Any

from coworker.memory import PUBLIC_DOMAINS
from coworker.store import Store, iso

BASES = ("owner", "permitted")


def _domain(email: str) -> str:
    return email.split("@")[-1].lower().strip() if "@" in (email or "") else ""


def disabled_domains() -> set[str]:
    return {d.strip().lower() for d in os.environ.get("COWORKER_DISABLED_DOMAINS", "").split(",") if d.strip()}


def org_disabled(email: str) -> bool:
    return _domain(email) in disabled_domains()


def work_domain(store: Store, user_id: int) -> str:
    """The company domain the coworker acts in, or '' for personal accounts."""
    coworker = store.get_coworker(user_id) or {}
    emails = [coworker.get("owner_email") or ""]
    google = store.get_connection_row(user_id, "google")
    if google:
        emails.insert(0, google.get("account_label") or "")
    for e in emails:
        d = _domain(e)
        if d and d not in PUBLIC_DOMAINS:
            return d
    return ""


def needs_employer_ok(store: Store, user_id: int) -> bool:
    coworker = store.get_coworker(user_id) or {}
    if coworker.get("mode") != "live":
        return False
    domain = work_domain(store, user_id)
    granted = (coworker.get("settings") or {}).get("employer_authorized") or {}
    return bool(domain) and granted.get("domain") != domain


def authorize(store: Store, user_id: int, basis: str) -> dict[str, Any]:
    if basis not in BASES:
        raise ValueError(f"basis must be one of {', '.join(BASES)}")
    coworker = store.get_coworker(user_id) or {}
    domain = work_domain(store, user_id)
    record = {"domain": domain, "basis": basis, "at": iso()}
    store.update_coworker(user_id, settings={**(coworker.get("settings") or {}), "employer_authorized": record})
    who = "you own the company" if basis == "owner" else "your employer allows it"
    store.log(user_id, "governance", f"Confirmed an AI coworker is allowed at {domain or 'your account'} ({who})", record)
    return record


def status(store: Store, user_id: int) -> dict[str, Any]:
    coworker = store.get_coworker(user_id) or {}
    return {
        "workDomain": work_domain(store, user_id),
        "needsEmployerAuthorization": needs_employer_ok(store, user_id),
        "employerAuthorized": (coworker.get("settings") or {}).get("employer_authorized"),
        "orgDisabled": org_disabled(coworker.get("owner_email") or ""),
    }
