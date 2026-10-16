"""Salesforce and Pipedrive alongside HubSpot: OAuth, token paste, logging a call, routing."""
from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest

from coworker import executor, reports, vendor_check
from coworker.connectors import crm, pipedrive, salesforce
from coworker.connectors.base import ConnectorError, decrypt_token, encrypt_token
from coworker.store import Store
from tests.conftest import oauth_return

PAYLOAD = {"company": "Northwind", "name": "Dana Lee", "email": "Dana@Northwind.com", "summary": "Wants a pilot in Q1",
           "fields": {"budget": "$30k", "timeline": "Q1", "empty": ""}}


@pytest.fixture(autouse=True)
def _no_mysql_profile():
    with patch("api_endpoints.coworker.common.owner_profile", return_value=("Natan Vidra", "natan@example.com")), \
         patch("api_endpoints.coworker.core.owner_profile", return_value=("Natan Vidra", "natan@example.com")):
        yield


def _resp(status: int = 200, body: Any = None) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.content = b"" if body is None else b"x"
    r.json.return_value = body if body is not None else {}
    r.headers = {}
    r.ok = status < 400
    return r


# -- Salesforce ----------------------------------------------------------------

def test_salesforce_records_a_call_task():
    calls: list[tuple[str, str, Any]] = []

    def fake(method: str, url: str, **kw: Any) -> MagicMock:
        calls.append((method, url, kw.get("json") or kw.get("params")))
        if url.endswith("/query"):
            q = kw["params"]["q"]
            return _resp(200, {"records": [{"Id": "001A"}]} if "Website" in q else {"records": []})
        if url.endswith("/sobjects/Contact"):
            return _resp(201, {"id": "003C"})
        if url.endswith("/sobjects/Task"):
            return _resp(201, {"id": "00TT"})
        raise AssertionError(url)

    client = salesforce.SalesforceClient({"access_token": "at", "instance_url": "https://acme.my.salesforce.com"})
    with patch("coworker.connectors.salesforce.requests.request", side_effect=fake):
        out = client.record_call(PAYLOAD)
    assert out == {"account_id": "001A", "contact_id": "003C", "task_id": "00TT"}
    contact = next(j for m, u, j in calls if u.endswith("/sobjects/Contact"))
    assert contact == {"FirstName": "Dana", "LastName": "Lee", "Email": "dana@northwind.com", "AccountId": "001A"}
    task = next(j for m, u, j in calls if u.endswith("/sobjects/Task"))
    assert task["WhoId"] == "003C" and task["WhatId"] == "001A" and task["Status"] == "Completed"
    assert "Budget: $30k" in task["Description"] and "Empty" not in task["Description"]
    assert calls[0][1].startswith("https://acme.my.salesforce.com/services/data/v60.0/")


def test_salesforce_creates_account_refreshes_and_escapes(monkeypatch):
    monkeypatch.setenv("SALESFORCE_CLIENT_ID", "cid")
    monkeypatch.setenv("SALESFORCE_CLIENT_SECRET", "sec")
    saved: list[dict] = []
    client = salesforce.SalesforceClient({"access_token": "old", "refresh_token": "rt", "instance_url": "https://x"},
                                         on_refresh=saved.append)
    seen: list[str] = []
    responses = iter([_resp(401, [{"message": "expired"}]), _resp(200, {"records": []}),
                      _resp(201, {"id": "001N"}), _resp(201, {"id": "00TT"})])

    def fake(method: str, url: str, **kw: Any) -> MagicMock:
        seen.append(str((kw.get("params") or {}).get("q", "")))
        return next(responses)

    with patch("coworker.connectors.salesforce.requests.request", side_effect=fake), \
            patch("coworker.connectors.salesforce.requests.post", return_value=_resp(200, {"access_token": "new"})):
        out = client.record_call({"company": "O'Neil & Co", "summary": "hi"})
    assert out["account_id"] == "001N" and out["contact_id"] == ""
    assert saved[0]["access_token"] == "new"
    assert "Name = 'O\\'Neil & Co'" in seen[1]
    client = salesforce.SalesforceClient({"access_token": "a", "instance_url": "https://x"})
    with patch("coworker.connectors.salesforce.requests.request", return_value=_resp(401, [{"message": "no"}])), \
            pytest.raises(ConnectorError) as exc:
        client.record_call(PAYLOAD)
    assert exc.value.code == "reauth_required"
    with patch("coworker.connectors.salesforce.requests.request", return_value=_resp(400, [{"message": "bad field"}])), \
            pytest.raises(ConnectorError, match="bad field"):
        salesforce.SalesforceClient({"access_token": "a", "refresh_token": "r", "instance_url": "https://x"}).record_call(PAYLOAD)


def test_salesforce_oauth_helpers(monkeypatch):
    monkeypatch.setenv("SALESFORCE_CLIENT_ID", "cid")
    monkeypatch.setenv("SALESFORCE_CLIENT_SECRET", "sec")
    monkeypatch.setenv("SALESFORCE_LOGIN_URL", "https://test.salesforce.com")
    assert salesforce.auth_url("st").startswith("https://test.salesforce.com/services/oauth2/authorize?")
    with patch("coworker.connectors.salesforce.requests.post",
               return_value=_resp(200, {"access_token": "a", "refresh_token": "r", "instance_url": "https://acme.my.salesforce.com"})):
        token = salesforce.exchange_code("c")
    assert token["org"] == "acme" and token["refresh_token"] == "r"
    with patch("coworker.connectors.salesforce.requests.post", return_value=_resp(400, {"error_description": "bad"})), \
            pytest.raises(ConnectorError) as exc:
        salesforce.exchange_code("c")
    assert exc.value.code == "oauth_failed"
    with patch("coworker.connectors.salesforce.requests.post", side_effect=__import__("requests").RequestException()):
        salesforce.revoke({"refresh_token": "r"})  # never raises
    salesforce.revoke({})


# -- Pipedrive -----------------------------------------------------------------

def test_pipedrive_api_token_records_a_note():
    calls: list[tuple[str, str, Any, Any]] = []

    def fake(method: str, url: str, params: Any = None, **kw: Any) -> MagicMock:
        calls.append((method, url, params, kw.get("json")))
        if url.endswith("/organizations/search"):
            return _resp(200, {"success": True, "data": {"items": [{"item": {"id": 7}}]}})
        if url.endswith("/persons/search"):
            return _resp(200, {"success": True, "data": {"items": []}})
        if url.endswith("/persons"):
            return _resp(201, {"success": True, "data": {"id": 42}})
        if url.endswith("/notes"):
            return _resp(201, {"success": True, "data": {"id": 99}})
        raise AssertionError(url)

    client = pipedrive.PipedriveClient({"kind": "api_token", "api_token": "tok"})
    with patch("coworker.connectors.pipedrive.requests.request", side_effect=fake):
        out = client.record_call(PAYLOAD)
    assert out == {"org_id": 7, "person_id": 42, "note_id": 99}
    assert all(c[2]["api_token"] == "tok" for c in calls)
    person = next(c[3] for c in calls if c[1].endswith("/persons"))
    assert person == {"name": "Dana Lee", "email": [{"value": "dana@northwind.com", "primary": True}], "org_id": 7}
    note = next(c[3] for c in calls if c[1].endswith("/notes"))
    assert note["person_id"] == 42 and note["org_id"] == 7 and "Budget:</b> $30k" in note["content"]


def test_pipedrive_oauth_refresh_and_errors(monkeypatch):
    monkeypatch.setenv("PIPEDRIVE_CLIENT_ID", "cid")
    monkeypatch.setenv("PIPEDRIVE_CLIENT_SECRET", "sec")
    saved: list[dict] = []
    client = pipedrive.PipedriveClient({"kind": "oauth", "access_token": "old", "refresh_token": "rt", "expires_at": 0,
                                        "api_domain": "https://acme.pipedrive.com"}, on_refresh=saved.append)
    fresh = _resp(200, {"access_token": "new", "refresh_token": "rt2", "expires_in": 3600, "api_domain": "https://acme.pipedrive.com"})
    with patch("coworker.connectors.pipedrive.requests.post", return_value=fresh), \
            patch("coworker.connectors.pipedrive.requests.request",
                  return_value=_resp(200, {"success": True, "data": {"company_name": "Acme"}})) as req:
        assert client.company() == "Acme"
    assert saved[0]["access_token"] == "new" and req.call_args.args[1] == "https://acme.pipedrive.com/v1/users/me"
    assert req.call_args.kwargs["headers"] == {"Authorization": "Bearer new"}
    with patch("coworker.connectors.pipedrive.requests.request", return_value=_resp(401, {"success": False, "error": "x"})), \
            pytest.raises(ConnectorError) as exc:
        pipedrive.PipedriveClient({"kind": "api_token", "api_token": "bad"}).company()
    assert exc.value.code == "reauth_required"
    with pytest.raises(ConnectorError):
        pipedrive.PipedriveClient({"kind": "oauth", "expires_at": 0}).company()
    with patch("coworker.connectors.pipedrive.requests.post", return_value=_resp(400, {"message": "bad code"})), \
            pytest.raises(ConnectorError):
        pipedrive.exchange_code("c")
    assert pipedrive.auth_url("st").startswith("https://oauth.pipedrive.com/oauth/authorize?")
    with patch("coworker.connectors.pipedrive.requests.post") as post:
        pipedrive.revoke({"kind": "oauth", "refresh_token": "rt"})
        pipedrive.revoke({"kind": "api_token"})
    assert post.call_count == 1


# -- Routing -------------------------------------------------------------------

def test_executor_uses_whichever_crm_is_connected(tmp_path):
    s = Store(f"sqlite:///{tmp_path}/crm.db")
    s.create_coworker(1, "Natan", "natan@anote.ai", mode="live")
    action = {"type": "crm.update", "autonomy": "approve", "payload": PAYLOAD}
    assert executor._execute(s, 1, action, {}) == {"recorded": True}  # notes only
    s.upsert_connection(1, "pipedrive", status="connected", token_enc=encrypt_token({"kind": "api_token", "api_token": "t"}))
    with patch("coworker.connectors.pipedrive.PipedriveClient.record_call", return_value={"note_id": 1}):
        result = executor._execute(s, 1, action, {})
    assert result["crm"] == {"provider": "pipedrive", "label": "Pipedrive", "note_id": 1}
    assert "Pipedrive" in reports.action_done({"id": 1, "type": "crm.update", "payload": PAYLOAD}, result)
    s.upsert_connection(1, "hubspot", status="connected", token_enc=encrypt_token({"access_token": "h", "kind": "private"}))
    with patch("coworker.connectors.hubspot.HubSpotClient.record_call", return_value={"note_id": "n"}):
        result = executor._execute(s, 1, action, {})
    assert result["crm"]["label"] == "HubSpot" and result["hubspot"] == {"note_id": "n"}
    found = crm.client_for(s, 1)
    assert found and found[0] == "hubspot"
    found[1].on_refresh({"access_token": "h2"})
    assert decrypt_token(s.get_connection_row(1, "hubspot")["token_enc"])["access_token"] == "h2"
    assert crm.label("nope") == "your CRM"
    crm.revoke("nope", {})


def test_crm_routes(client, auth_headers, monkeypatch):
    h = auth_headers
    client.post("/api/coworker", json={"mode": "demo"}, headers=h)
    for provider in ("salesforce", "pipedrive"):
        monkeypatch.delenv(f"{provider.upper()}_CLIENT_ID", raising=False)
        assert client.post(f"/api/coworker/connections/{provider}/start", headers=h).status_code == 501
        monkeypatch.setenv(f"{provider.upper()}_CLIENT_ID", "cid")
        monkeypatch.setenv(f"{provider.upper()}_CLIENT_SECRET", "sec")
    caps = client.get("/api/coworker", headers=h).get_json()["capabilities"]
    assert caps["salesforce_oauth"] and caps["pipedrive_oauth"]

    url = client.post("/api/coworker/connections/salesforce/start", headers=h).get_json()["url"]
    state = parse_qs(urlparse(url).query)["state"][0]
    with patch("coworker.connectors.salesforce.exchange_code",
               return_value={"access_token": "a", "refresh_token": "r", "instance_url": "https://acme", "org": "acme"}):
        assert "connected=salesforce" in oauth_return(client, f"/api/coworker/connections/salesforce/callback?state={state}&code=c").location
    assert "connect_error" in oauth_return(client, f"/api/coworker/connections/salesforce/callback?state={state}&error=denied").location
    assert "connect_error" in oauth_return(client, "/api/coworker/connections/salesforce/callback?state=bad").location
    with patch("coworker.connectors.salesforce.exchange_code", side_effect=ConnectorError("no")):
        assert "connect_error" in oauth_return(client, f"/api/coworker/connections/salesforce/callback?state={state}&code=c").location

    url = client.post("/api/coworker/connections/pipedrive/start", headers=h).get_json()["url"]
    state = parse_qs(urlparse(url).query)["state"][0]
    with patch("coworker.connectors.pipedrive.exchange_code", return_value={"kind": "oauth", "access_token": "a",
                                                                              "expires_at": time.time() + 99, "company": "Acme"}):
        assert "connected=pipedrive" in oauth_return(client, f"/api/coworker/connections/pipedrive/callback?state={state}&code=c").location
    assert "connect_error" in oauth_return(client, "/api/coworker/connections/pipedrive/callback?state=bad").location
    with patch("coworker.connectors.pipedrive.exchange_code", side_effect=ConnectorError("no")):
        assert "connect_error" in oauth_return(client, f"/api/coworker/connections/pipedrive/callback?state={state}&code=c").location

    accounts = {c["provider"]: c["account"] for c in client.get("/api/coworker/connections", headers=h).get_json()["connections"]
                if c["provider"] != "demo"}
    assert accounts == {"salesforce": "acme", "pipedrive": "Acme"}
    with patch("coworker.connectors.salesforce.revoke") as revoke:
        assert client.delete("/api/coworker/connections/salesforce", headers=h).get_json()["purged"] == 0
    revoke.assert_called_once()
    client.delete("/api/coworker/connections/pipedrive", headers=h)

    assert client.post("/api/coworker/connections/pipedrive/token", json={"token": "short"}, headers=h).status_code == 400
    with patch("coworker.connectors.pipedrive.verify_api_token", side_effect=ConnectorError("bad")):
        assert client.post("/api/coworker/connections/pipedrive/token", json={"token": "x" * 40}, headers=h).status_code == 400
    with patch("coworker.connectors.pipedrive.verify_api_token", return_value={"kind": "api_token", "api_token": "x" * 40,
                                                                                 "company": "Acme"}):
        assert client.post("/api/coworker/connections/pipedrive/token", json={"token": "x" * 40},
                           headers=h).get_json() == {"connected": True, "company": "Acme"}


def test_pipedrive_token_needs_a_coworker(client, auth_headers):
    assert client.post("/api/coworker/connections/pipedrive/token", json={"token": "x" * 40},
                       headers=auth_headers).status_code == 404


def test_vendor_check_crms(monkeypatch):
    for env in ("HUBSPOT", "SALESFORCE", "PIPEDRIVE"):
        monkeypatch.delenv(f"{env}_CLIENT_ID", raising=False)
        monkeypatch.delenv(f"{env}_CLIENT_SECRET", raising=False)
    assert vendor_check.check_crms()["status"] == "skipped"
    monkeypatch.setenv("SALESFORCE_CLIENT_ID", "x")
    assert vendor_check.check_crms()["status"] == "fail"
    monkeypatch.setenv("SALESFORCE_CLIENT_SECRET", "y")
    assert vendor_check.check_crms() == {"name": "CRM OAuth", "status": "ok", "detail": "Salesforce configured"}
    with patch("coworker.connectors.pipedrive.requests.request",
               return_value=_resp(200, {"success": True, "data": {"company_domain": "acme"}})):
        assert pipedrive.verify_api_token("t" * 40)["company"] == "acme"
