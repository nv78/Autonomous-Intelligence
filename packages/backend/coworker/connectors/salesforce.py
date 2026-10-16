"""Salesforce CRM: log calls as completed Tasks on the Contact and Account.

OAuth 2.0 web server flow with a Connected App (``SALESFORCE_CLIENT_ID`` /
``SALESFORCE_CLIENT_SECRET``; scopes ``api refresh_token``). Set
``SALESFORCE_LOGIN_URL=https://test.salesforce.com`` for a sandbox.

An approved ``crm.update`` finds or creates the Account (by website domain,
else name) and the Contact (by email), then logs a completed call Task with
the summary and qualification answers.
"""
from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

import requests

from coworker.connectors.base import ConnectorError

TIMEOUT = 20


def _login() -> str:
    return os.environ.get("SALESFORCE_LOGIN_URL", "https://login.salesforce.com").rstrip("/")


def _version() -> str:
    return os.environ.get("SALESFORCE_API_VERSION", "v60.0")


def is_configured() -> bool:
    return bool(os.environ.get("SALESFORCE_CLIENT_ID") and os.environ.get("SALESFORCE_CLIENT_SECRET"))


def redirect_uri() -> str:
    default = f"{os.environ.get('BACKEND_URL', 'http://localhost:5000').rstrip('/')}/api/coworker/connections/salesforce/callback"
    return os.environ.get("SALESFORCE_REDIRECT_URI", default)


def auth_url(state: str) -> str:
    return f"{_login()}/services/oauth2/authorize?" + urlencode({
        "response_type": "code", "client_id": os.environ.get("SALESFORCE_CLIENT_ID", ""),
        "redirect_uri": redirect_uri(), "scope": "api refresh_token", "state": state,
    })


def _token(data: dict[str, str]) -> dict[str, Any]:
    resp = requests.post(f"{_login()}/services/oauth2/token", data={
        "client_id": os.environ.get("SALESFORCE_CLIENT_ID", ""),
        "client_secret": os.environ.get("SALESFORCE_CLIENT_SECRET", ""), **data,
    }, timeout=TIMEOUT)
    body: dict[str, Any] = resp.json() if resp.content else {}
    if resp.status_code >= 400 or not body.get("access_token"):
        code = "reauth_required" if data.get("grant_type") == "refresh_token" else "oauth_failed"
        raise ConnectorError(f"Salesforce sign-in failed: {body.get('error_description') or resp.status_code}", code)
    return body


def exchange_code(code: str) -> dict[str, Any]:
    body = _token({"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri()})
    org = re.sub(r"^https?://", "", str(body.get("instance_url") or "")).split(".")[0] or "Salesforce"
    return {"access_token": body["access_token"], "refresh_token": body.get("refresh_token", ""),
            "instance_url": body.get("instance_url", ""), "org": org}


def revoke(token: dict[str, Any]) -> None:
    value = token.get("refresh_token") or token.get("access_token")
    if value:
        try:
            requests.post(f"{_login()}/services/oauth2/revoke", data={"token": value}, timeout=TIMEOUT)
        except requests.RequestException:
            pass


def _soql(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


class SalesforceClient:
    label = "Salesforce"

    def __init__(self, token: dict[str, Any], on_refresh: Any = None) -> None:
        self.token = token
        self.on_refresh = on_refresh

    def _refresh(self) -> None:
        if not self.token.get("refresh_token"):
            raise ConnectorError("Salesforce access expired. Please reconnect.", "reauth_required")
        body = _token({"grant_type": "refresh_token", "refresh_token": self.token["refresh_token"]})
        self.token = {**self.token, "access_token": body["access_token"],
                      "instance_url": body.get("instance_url") or self.token.get("instance_url", "")}
        if self.on_refresh:
            self.on_refresh(self.token)

    def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        for attempt in range(2):
            resp = requests.request(method, f"{self.token.get('instance_url', '').rstrip('/')}/services/data/{_version()}{path}",
                                    headers={"Authorization": f"Bearer {self.token.get('access_token', '')}"},
                                    timeout=TIMEOUT, **kwargs)
            if resp.status_code == 401 and attempt == 0:
                self._refresh()  # access tokens are short-lived and carry no expiry
                continue
            body: Any = resp.json() if resp.content else {}
            if resp.status_code >= 400:
                detail = body[0].get("message") if isinstance(body, list) and body else resp.status_code
                code = "reauth_required" if resp.status_code == 401 else "provider_error"
                raise ConnectorError(f"Salesforce {method} {path} failed: {detail}", code)
            return body if isinstance(body, dict) else {}
        raise ConnectorError("Salesforce rejected the token", "reauth_required")  # pragma: no cover

    def _query_id(self, soql: str) -> str:
        records = self.request("GET", "/query", params={"q": soql}).get("records") or []
        return str(records[0]["Id"]) if records else ""

    def record_call(self, payload: dict[str, Any]) -> dict[str, Any]:
        email = str(payload.get("email") or "").lower()
        domain = str(payload.get("domain") or (email.split("@")[-1] if "@" in email else "")).lower()
        company = str(payload.get("company") or "")
        account_id = ""
        if domain:
            account_id = self._query_id(f"SELECT Id FROM Account WHERE Website LIKE '%{_soql(domain)}%' LIMIT 1")
        if not account_id and company:
            account_id = self._query_id(f"SELECT Id FROM Account WHERE Name = '{_soql(company)}' LIMIT 1")
        if not account_id and (company or domain):
            account_id = str(self.request("POST", "/sobjects/Account", json={"Name": company or domain,
                                                                           "Website": domain}).get("id", ""))
        contact_id = ""
        if email:
            contact_id = self._query_id(f"SELECT Id FROM Contact WHERE Email = '{_soql(email)}' LIMIT 1")
            if not contact_id:
                first, _, last = str(payload.get("name") or "").partition(" ")
                contact = {"FirstName": first, "LastName": last or first or email.split("@")[0], "Email": email}
                if account_id:
                    contact["AccountId"] = account_id
                contact_id = str(self.request("POST", "/sobjects/Contact", json=contact).get("id", ""))
        fields = payload.get("fields") or {}
        notes = "\n".join(f"{str(k).replace('_', ' ').title()}: {v}" for k, v in fields.items() if v not in (None, "", []))
        task: dict[str, Any] = {
            "Subject": f"Call: {company or payload.get('name') or 'prospect'}"[:255],
            "Description": f"{payload.get('summary') or 'Call notes'}\n\n{notes}\n\nLogged by Ourogen (AI coworker).".strip(),
            "Status": "Completed", "TaskSubtype": "Call", "ActivityDate": datetime.now(UTC).strftime("%Y-%m-%d"),
        }
        if contact_id:
            task["WhoId"] = contact_id
        if account_id:
            task["WhatId"] = account_id
        task_id = str(self.request("POST", "/sobjects/Task", json=task).get("id", ""))
        return {"account_id": account_id, "contact_id": contact_id, "task_id": task_id}
