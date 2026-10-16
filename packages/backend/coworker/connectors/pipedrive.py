"""Pipedrive CRM: log calls as notes on the Person and Organization.

Two ways to connect:

* OAuth (``PIPEDRIVE_CLIENT_ID`` / ``PIPEDRIVE_CLIENT_SECRET``) from a
  Pipedrive Marketplace app.
* Paste a personal API token (Settings → Personal preferences → API in
  Pipedrive). Simplest for a single company.

An approved ``crm.update`` finds or creates the Organization (by name) and
the Person (by email), then adds a note with the summary and answers.
"""
from __future__ import annotations

import html
import os
import time
from typing import Any
from urllib.parse import urlencode

import requests

from coworker.connectors.base import ConnectorError

OAUTH = "https://oauth.pipedrive.com/oauth"
API = "https://api.pipedrive.com/v1"
TIMEOUT = 20


def is_configured() -> bool:
    return bool(os.environ.get("PIPEDRIVE_CLIENT_ID") and os.environ.get("PIPEDRIVE_CLIENT_SECRET"))


def redirect_uri() -> str:
    default = f"{os.environ.get('BACKEND_URL', 'http://localhost:5000').rstrip('/')}/api/coworker/connections/pipedrive/callback"
    return os.environ.get("PIPEDRIVE_REDIRECT_URI", default)


def auth_url(state: str) -> str:
    return f"{OAUTH}/authorize?" + urlencode({"client_id": os.environ.get("PIPEDRIVE_CLIENT_ID", ""),
                                               "redirect_uri": redirect_uri(), "state": state})


def _auth() -> tuple[str, str]:
    return os.environ.get("PIPEDRIVE_CLIENT_ID", ""), os.environ.get("PIPEDRIVE_CLIENT_SECRET", "")


def _token(data: dict[str, str]) -> dict[str, Any]:
    resp = requests.post(f"{OAUTH}/token", data=data, auth=_auth(), timeout=TIMEOUT)
    body: dict[str, Any] = resp.json() if resp.content else {}
    if resp.status_code >= 400 or not body.get("access_token"):
        code = "reauth_required" if data.get("grant_type") == "refresh_token" else "oauth_failed"
        raise ConnectorError(f"Pipedrive sign-in failed: {body.get('message') or resp.status_code}", code)
    return {"kind": "oauth", "access_token": body["access_token"], "refresh_token": body.get("refresh_token", ""),
            "api_domain": body.get("api_domain", ""), "expires_at": time.time() + int(body.get("expires_in", 3600)) - 60}


def exchange_code(code: str) -> dict[str, Any]:
    token = _token({"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri()})
    token["company"] = PipedriveClient(token).company()
    return token


def verify_api_token(value: str) -> dict[str, Any]:
    token: dict[str, Any] = {"kind": "api_token", "api_token": value}
    token["company"] = PipedriveClient(token).company()
    return token


def revoke(token: dict[str, Any]) -> None:
    if token.get("kind") == "oauth" and token.get("refresh_token"):
        try:
            requests.post(f"{OAUTH}/revoke", data={"token": token["refresh_token"], "token_type_hint": "refresh_token"},
                          auth=_auth(), timeout=TIMEOUT)
        except requests.RequestException:
            pass


class PipedriveClient:
    label = "Pipedrive"

    def __init__(self, token: dict[str, Any], on_refresh: Any = None) -> None:
        self.token = token
        self.on_refresh = on_refresh

    def _base_and_auth(self) -> tuple[str, dict[str, str], dict[str, str]]:
        if self.token.get("kind") == "api_token":
            return API, {}, {"api_token": str(self.token.get("api_token", ""))}
        if self.token.get("expires_at", 0) <= time.time():
            if not self.token.get("refresh_token"):
                raise ConnectorError("Pipedrive access expired. Please reconnect.", "reauth_required")
            fresh = _token({"grant_type": "refresh_token", "refresh_token": self.token["refresh_token"]})
            self.token = {**self.token, **fresh}
            if self.on_refresh:
                self.on_refresh(self.token)
        base = f"{str(self.token.get('api_domain') or 'https://api.pipedrive.com').rstrip('/')}/v1"
        return base, {"Authorization": f"Bearer {self.token.get('access_token', '')}"}, {}

    def request(self, method: str, path: str, params: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        base, headers, auth_params = self._base_and_auth()
        for attempt in range(3):
            resp = requests.request(method, f"{base}{path}", headers=headers, params={**(params or {}), **auth_params},
                                    timeout=TIMEOUT, **kwargs)
            if resp.status_code == 429 and attempt < 2:
                time.sleep(min(float(resp.headers.get("Retry-After", "1")), 5))
                continue
            body: dict[str, Any] = resp.json() if resp.content else {}
            if resp.status_code >= 400 or body.get("success") is False:
                code = "reauth_required" if resp.status_code == 401 else "provider_error"
                raise ConnectorError(f"Pipedrive {method} {path} failed: {body.get('error') or resp.status_code}", code)
            return body.get("data")
        raise ConnectorError("Pipedrive rate limited", "rate_limited")  # pragma: no cover

    def company(self) -> str:
        me = self.request("GET", "/users/me") or {}
        return str(me.get("company_name") or me.get("company_domain") or "Pipedrive")

    def _search(self, kind: str, term: str, field: str) -> int | None:
        if not term:
            return None
        data = self.request("GET", f"/{kind}/search", params={"term": term, "fields": field, "exact_match": "true", "limit": 1})
        items = (data or {}).get("items") or []
        return int(items[0]["item"]["id"]) if items else None

    def record_call(self, payload: dict[str, Any]) -> dict[str, Any]:
        email = str(payload.get("email") or "").lower()
        company = str(payload.get("company") or "")
        org_id = self._search("organizations", company, "name")
        if org_id is None and company:
            org_id = int(self.request("POST", "/organizations", json={"name": company})["id"])
        person_id = self._search("persons", email, "email")
        if person_id is None and email:
            person: dict[str, Any] = {"name": payload.get("name") or email.split("@")[0],
                                      "email": [{"value": email, "primary": True}]}
            if org_id is not None:
                person["org_id"] = org_id
            person_id = int(self.request("POST", "/persons", json=person)["id"])
        fields = payload.get("fields") or {}
        rows = "".join(f"<li><b>{html.escape(str(k).replace('_', ' ').title())}:</b> {html.escape(str(v))}</li>"
                       for k, v in fields.items() if v not in (None, "", []))
        note: dict[str, Any] = {"content": f"<p>{html.escape(str(payload.get('summary') or 'Call notes'))}</p>"
                                           + (f"<ul>{rows}</ul>" if rows else "") + "<p><i>Logged by Ourogen (AI coworker).</i></p>"}
        if person_id is not None:
            note["person_id"] = person_id
        if org_id is not None:
            note["org_id"] = org_id
        created = self.request("POST", "/notes", json=note) or {}
        return {"org_id": org_id, "person_id": person_id, "note_id": created.get("id")}
