"""HubSpot CRM: where the coworker records what it learns on calls.

When a ``crm.update`` action is approved, the coworker finds or creates the
company (by domain, else name) and the contact (by email), associates them,
and logs a note with the call summary and qualification answers.

Two ways to connect:

* OAuth (``HUBSPOT_CLIENT_ID`` / ``HUBSPOT_CLIENT_SECRET``) from a HubSpot
  public app.
* Paste a private app access token (``pat-...``) with the CRM contact,
  company, and note scopes. Simplest for a single portal.
"""
from __future__ import annotations

import html
import os
import time
from typing import Any
from urllib.parse import urlencode

import requests

from coworker.connectors.base import ConnectorError
from coworker.store import Store, iso

API = "https://api.hubapi.com"
AUTH_URL = "https://app.hubspot.com/oauth/authorize"
SCOPES = [
    "oauth", "crm.objects.contacts.read", "crm.objects.contacts.write",
    "crm.objects.companies.read", "crm.objects.companies.write",
]
TIMEOUT = 20
NOTE_TO_CONTACT = 202
NOTE_TO_COMPANY = 190


def is_configured() -> bool:
    return bool(os.environ.get("HUBSPOT_CLIENT_ID") and os.environ.get("HUBSPOT_CLIENT_SECRET"))


def redirect_uri() -> str:
    default = f"{os.environ.get('BACKEND_URL', 'http://localhost:5000').rstrip('/')}/api/coworker/connections/hubspot/callback"
    return os.environ.get("HUBSPOT_REDIRECT_URI", default)


def auth_url(state: str) -> str:
    return f"{AUTH_URL}?{urlencode({'client_id': os.environ.get('HUBSPOT_CLIENT_ID', ''), 'redirect_uri': redirect_uri(), 'scope': ' '.join(SCOPES), 'state': state})}"


def _token_request(data: dict[str, str]) -> dict[str, Any]:
    resp = requests.post(f"{API}/oauth/v1/token", data={
        "client_id": os.environ.get("HUBSPOT_CLIENT_ID", ""),
        "client_secret": os.environ.get("HUBSPOT_CLIENT_SECRET", ""), **data,
    }, timeout=TIMEOUT)
    body: dict[str, Any] = resp.json() if resp.content else {}
    if resp.status_code >= 400 or not body.get("access_token"):
        code = "reauth_required" if data.get("grant_type") == "refresh_token" else "oauth_failed"
        raise ConnectorError(f"HubSpot OAuth failed: {body.get('message') or resp.status_code}", code)
    return {
        "access_token": body["access_token"], "refresh_token": body.get("refresh_token", ""),
        "expires_at": time.time() + int(body.get("expires_in", 1800)) - 60, "kind": "oauth",
    }


def exchange_code(code: str) -> dict[str, Any]:
    token = _token_request({"grant_type": "authorization_code", "redirect_uri": redirect_uri(), "code": code})
    info = requests.get(f"{API}/oauth/v1/access-tokens/{token['access_token']}", timeout=TIMEOUT)
    meta = info.json() if info.ok and info.content else {}
    token["portal"] = meta.get("hub_domain") or str(meta.get("hub_id") or "HubSpot")
    token["scope"] = " ".join(meta.get("scopes") or SCOPES)
    return token


def verify_private_token(value: str) -> dict[str, Any]:
    token = {"access_token": value, "kind": "private", "expires_at": 0}
    client = HubSpotClient(token)
    client.request("GET", "/crm/v3/objects/contacts", params={"limit": 1})
    details = client.request("GET", "/account-info/v3/details", allow_error=True)
    token["portal"] = str(details.get("portalId") or "HubSpot") if details else "HubSpot"
    return token


def revoke(token: dict[str, Any]) -> None:
    if token.get("kind") == "oauth" and token.get("refresh_token"):
        try:
            requests.delete(f"{API}/oauth/v1/refresh-tokens/{token['refresh_token']}", timeout=TIMEOUT)
        except requests.RequestException:
            pass


class HubSpotClient:
    label = "HubSpot"

    def __init__(self, token: dict[str, Any], on_refresh: Any = None) -> None:
        self.token = token
        self.on_refresh = on_refresh

    def _access(self) -> str:
        if self.token.get("kind") == "oauth" and self.token.get("expires_at", 0) <= time.time():
            if not self.token.get("refresh_token"):
                raise ConnectorError("HubSpot access expired. Please reconnect.", "reauth_required")
            fresh = _token_request({"grant_type": "refresh_token", "refresh_token": self.token["refresh_token"]})
            self.token = {**self.token, **fresh, "refresh_token": fresh.get("refresh_token") or self.token["refresh_token"]}
            if self.on_refresh:
                self.on_refresh(self.token)
        return str(self.token.get("access_token", ""))

    def request(self, method: str, path: str, allow_error: bool = False, **kwargs: Any) -> dict[str, Any]:
        for attempt in range(3):
            resp = requests.request(method, f"{API}{path}", headers={"Authorization": f"Bearer {self._access()}"},
                                    timeout=TIMEOUT, **kwargs)
            if resp.status_code == 429 and attempt < 2:
                time.sleep(min(float(resp.headers.get("Retry-After", "1")), 5))
                continue
            body: dict[str, Any] = resp.json() if resp.content else {}
            if resp.status_code >= 400:
                if allow_error:
                    return {}
                code = "reauth_required" if resp.status_code == 401 else "provider_error"
                raise ConnectorError(f"HubSpot {method} {path} failed: {body.get('message') or resp.status_code}", code)
            return body
        raise ConnectorError("HubSpot rate limited", "rate_limited")  # pragma: no cover

    def _find(self, obj: str, prop: str, value: str) -> str:
        if not value:
            return ""
        found = self.request("POST", f"/crm/v3/objects/{obj}/search", json={
            "filterGroups": [{"filters": [{"propertyName": prop, "operator": "EQ", "value": value}]}], "limit": 1,
        })
        results = found.get("results") or []
        return str(results[0]["id"]) if results else ""

    def _upsert(self, obj: str, object_id: str, props: dict[str, str]) -> str:
        props = {k: v for k, v in props.items() if v}
        if object_id:
            if props:
                self.request("PATCH", f"/crm/v3/objects/{obj}/{object_id}", json={"properties": props})
            return object_id
        return str(self.request("POST", f"/crm/v3/objects/{obj}", json={"properties": props})["id"])

    def record_call(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Upsert company and contact, associate them, and log a note."""
        email = str(payload.get("email") or "").lower()
        domain = str(payload.get("domain") or (email.split("@")[-1] if "@" in email else "")).lower()
        company_name = str(payload.get("company") or "")
        company_id = self._find("companies", "domain", domain) if domain else ""
        if not company_id and company_name:
            company_id = self._find("companies", "name", company_name)
        if company_name or domain:
            company_id = self._upsert("companies", company_id, {"name": company_name, "domain": domain})
        contact_id = ""
        if email:
            first, _, last = str(payload.get("name") or "").partition(" ")
            contact_id = self._upsert("contacts", self._find("contacts", "email", email),
                                      {"email": email, "firstname": first, "lastname": last, "company": company_name})
            if company_id:
                self.request("PUT", f"/crm/v4/objects/contact/{contact_id}/associations/default/company/{company_id}")
        fields = payload.get("fields") or {}
        rows = "".join(f"<li><b>{html.escape(str(k).replace('_', ' ').title())}:</b> {html.escape(str(v))}</li>"
                       for k, v in fields.items() if v not in (None, "", []))
        body = (f"<p>{html.escape(str(payload.get('summary') or 'Call notes'))}</p>"
                + (f"<ul>{rows}</ul>" if rows else "")
                + "<p><i>Logged by Ourogen (AI coworker).</i></p>")
        associations = [
            {"to": {"id": oid}, "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": tid}]}
            for oid, tid in ((contact_id, NOTE_TO_CONTACT), (company_id, NOTE_TO_COMPANY)) if oid
        ]
        note = self.request("POST", "/crm/v3/objects/notes", json={
            "properties": {"hs_timestamp": iso(), "hs_note_body": body}, "associations": associations,
        })
        return {"company_id": company_id, "contact_id": contact_id, "note_id": str(note.get("id", ""))}


def client_for(store: Store, user_id: int) -> HubSpotClient | None:
    from coworker.connectors.base import decrypt_token, encrypt_token

    row = store.get_connection_row(user_id, "hubspot")
    if not row or row.get("status") not in ("connected", "syncing"):
        return None

    def save(token: dict[str, Any]) -> None:
        store.upsert_connection(user_id, "hubspot", token_enc=encrypt_token(token))

    return HubSpotClient(decrypt_token(row.get("token_enc")), on_refresh=save)
