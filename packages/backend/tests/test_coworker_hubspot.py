"""HubSpot CRM connector: OAuth, private tokens, and recording calls."""
from __future__ import annotations

import time
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

from coworker import executor
from coworker.connectors import hubspot
from coworker.connectors.base import ConnectorError, decrypt_token, encrypt_token
from coworker.store import Store, iso, utcnow
from tests.conftest import oauth_return


def _resp(status: int = 200, data: dict | None = None) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.ok = status < 400
    r.content = b"{}" if data is not None else b""
    r.json.return_value = data or {}
    r.headers = {}
    return r


class FakeHubSpot:
    """Routes requests.request calls to canned HubSpot responses."""

    def __init__(self, existing_company: str = "", existing_contact: str = "") -> None:
        self.calls: list[tuple[str, str, dict]] = []
        self.existing_company = existing_company
        self.existing_contact = existing_contact

    def __call__(self, method: str, url: str, **kw):
        path = url.replace(hubspot.API, "")
        self.calls.append((method, path, kw.get("json") or {}))
        if path.endswith("/search"):
            obj = path.split("/")[4]
            hit = self.existing_company if obj == "companies" else self.existing_contact
            return _resp(200, {"results": [{"id": hit}] if hit else []})
        if method == "POST" and path == "/crm/v3/objects/companies":
            return _resp(201, {"id": "co1"})
        if method == "POST" and path == "/crm/v3/objects/contacts":
            return _resp(201, {"id": "ct1"})
        if method == "POST" and path == "/crm/v3/objects/notes":
            return _resp(201, {"id": "n1"})
        return _resp(200, {})


PAYLOAD = {"company": "Northwind Capital", "name": "Dana Park", "email": "dana@northwind.com",
           "summary": "Call 2026-10-15: score 82/100.", "fields": {"team_size": "40", "timeline": "Q1", "budget": ""}}


def test_record_call_creates_company_contact_note():
    fake = FakeHubSpot()
    with patch("requests.request", side_effect=fake):
        out = hubspot.HubSpotClient({"access_token": "pat-x", "kind": "private"}).record_call(PAYLOAD)
    assert out == {"company_id": "co1", "contact_id": "ct1", "note_id": "n1"}
    paths = [(m, p) for m, p, _ in fake.calls]
    assert ("PUT", "/crm/v4/objects/contact/ct1/associations/default/company/co1") in paths
    company = next(j for m, p, j in fake.calls if p == "/crm/v3/objects/companies")
    assert company["properties"] == {"name": "Northwind Capital", "domain": "northwind.com"}
    contact = next(j for m, p, j in fake.calls if p == "/crm/v3/objects/contacts")
    assert contact["properties"]["firstname"] == "Dana" and contact["properties"]["lastname"] == "Park"
    note = next(j for m, p, j in fake.calls if p == "/crm/v3/objects/notes")
    body = note["properties"]["hs_note_body"]
    assert "Team Size:</b> 40" in body and "Budget" not in body and "Ourogen" in body
    assert {a["types"][0]["associationTypeId"] for a in note["associations"]} == {202, 190}


def test_record_call_updates_existing_and_escapes_html():
    fake = FakeHubSpot(existing_company="c9", existing_contact="p9")
    with patch("requests.request", side_effect=fake):
        out = hubspot.HubSpotClient({"access_token": "x", "kind": "private"}).record_call(
            {**PAYLOAD, "summary": "<script>x</script>"})
    assert out["company_id"] == "c9" and out["contact_id"] == "p9"
    assert ("PATCH", "/crm/v3/objects/contacts/p9") in [(m, p) for m, p, _ in fake.calls]
    note = next(j for m, p, j in fake.calls if p == "/crm/v3/objects/notes")
    assert "<script>" not in note["properties"]["hs_note_body"]


def test_company_only_payload_skips_contact():
    fake = FakeHubSpot()
    with patch("requests.request", side_effect=fake):
        out = hubspot.HubSpotClient({"access_token": "x", "kind": "private"}).record_call(
            {"company": "Acme", "summary": "Notes"})
    assert out["contact_id"] == "" and out["company_id"] == "co1"


def test_errors_refresh_and_rate_limit():
    client = hubspot.HubSpotClient({"access_token": "x", "kind": "private"})
    with patch("requests.request", return_value=_resp(401, {"message": "expired"})):
        with pytest.raises(ConnectorError) as exc:
            client.request("GET", "/crm/v3/objects/contacts")
    assert exc.value.code == "reauth_required"
    with patch("requests.request", return_value=_resp(500, {})):
        assert client.request("GET", "/x", allow_error=True) == {}
    limited = _resp(429, {})
    limited.headers = {"Retry-After": "0"}
    with patch("requests.request", side_effect=[limited, _resp(200, {"ok": 1})]):
        assert client.request("GET", "/x") == {"ok": 1}

    saved = []
    expired = hubspot.HubSpotClient({"access_token": "old", "refresh_token": "r1", "kind": "oauth", "expires_at": 0},
                                    on_refresh=saved.append)
    with patch("requests.post", return_value=_resp(200, {"access_token": "new", "expires_in": 1800})), \
            patch("requests.request", return_value=_resp(200, {})) as req:
        expired.request("GET", "/x")
    assert req.call_args.kwargs["headers"]["Authorization"] == "Bearer new"
    assert saved[0]["refresh_token"] == "r1" and saved[0]["expires_at"] > time.time()
    no_refresh = hubspot.HubSpotClient({"access_token": "old", "kind": "oauth", "expires_at": 0})
    with pytest.raises(ConnectorError):
        no_refresh.request("GET", "/x")
    with patch("requests.post", return_value=_resp(400, {"message": "bad"})), pytest.raises(ConnectorError) as exc:
        hubspot.HubSpotClient({"refresh_token": "r", "kind": "oauth", "expires_at": 0}).request("GET", "/x")
    assert exc.value.code == "reauth_required"


def test_oauth_helpers(monkeypatch):
    monkeypatch.setenv("HUBSPOT_CLIENT_ID", "cid")
    monkeypatch.setenv("HUBSPOT_CLIENT_SECRET", "sec")
    monkeypatch.setenv("BACKEND_URL", "https://chat.ourogen.ai")
    assert hubspot.is_configured()
    url = hubspot.auth_url("st")
    assert "client_id=cid" in url and "connections%2Fhubspot%2Fcallback" in url and "crm.objects.contacts.write" in url
    with patch("requests.post", return_value=_resp(200, {"access_token": "at", "refresh_token": "rt", "expires_in": 60})), \
            patch("requests.get", return_value=_resp(200, {"hub_domain": "northwind.hubspot.com", "scopes": ["oauth"]})):
        token = hubspot.exchange_code("code")
    assert token["portal"] == "northwind.hubspot.com" and token["kind"] == "oauth" and token["refresh_token"] == "rt"
    with patch("requests.delete") as delete:
        hubspot.revoke(token)
        hubspot.revoke({"kind": "private", "access_token": "pat"})
    delete.assert_called_once()
    with patch("requests.request", side_effect=[_resp(200, {"results": []}), _resp(200, {"portalId": 42})]):
        assert hubspot.verify_private_token("pat-1")["portal"] == "42"


@pytest.fixture
def s(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/hs.db")
    store.create_coworker(1, "Natan Vidra", "natan@example.com", mode="demo")
    return store


def test_executor_pushes_crm_update(s):
    def approve(payload):
        return s.insert("cw_actions", {"user_id": 1, "type": "crm.update", "status": "approved", "title": "Update CRM",
                                       "payload": payload, "execute_after": iso(utcnow() - timedelta(minutes=1)),
                                       "created_at": iso()})

    approve(PAYLOAD)
    assert executor.run_due(s, 1)["executed"] == 1  # not connected: local record only
    s.upsert_connection(1, "hubspot", status="connected", token_enc=encrypt_token({"access_token": "pat", "kind": "private"}))
    aid = approve(PAYLOAD)
    with patch("requests.request", side_effect=FakeHubSpot()):
        assert executor.run_due(s, 1)["executed"] == 1
    assert s.get("cw_actions", aid, 1)["result"]["hubspot"]["note_id"] == "n1"
    approve(PAYLOAD)
    with patch("requests.request", return_value=_resp(500, {"message": "down"})):
        assert executor.run_due(s, 1)["failed"] == 1
    assert len(s.query("SELECT id FROM cw_memory WHERE kind = 'crm'")) == 2  # failure recorded nothing


def test_client_for_saves_refreshed_token(s):
    assert hubspot.client_for(s, 1) is None
    s.upsert_connection(1, "hubspot", status="connected",
                        token_enc=encrypt_token({"access_token": "old", "refresh_token": "r", "kind": "oauth", "expires_at": 0}))
    client = hubspot.client_for(s, 1)
    assert client is not None
    with patch("requests.post", return_value=_resp(200, {"access_token": "new", "expires_in": 1800})), \
            patch("requests.request", return_value=_resp(200, {})):
        client.request("GET", "/x")
    assert decrypt_token(s.get_connection_row(1, "hubspot")["token_enc"])["access_token"] == "new"


def test_hubspot_routes(client, auth_headers, monkeypatch):
    monkeypatch.delenv("HUBSPOT_CLIENT_ID", raising=False)
    with patch("api_endpoints.coworker.core.owner_profile", return_value=("Natan Vidra", "natan@example.com")):
        assert client.post("/api/coworker/connections/hubspot/token", json={"token": "pat-1"}, headers=auth_headers).status_code == 404
        assert client.post("/api/coworker", json={"mode": "demo"}, headers=auth_headers).status_code == 201
        caps = client.get("/api/coworker", headers=auth_headers).get_json()["capabilities"]
        assert caps["hubspot_oauth"] is False
        assert client.post("/api/coworker/connections/hubspot/start", headers=auth_headers).status_code == 501
        assert client.post("/api/coworker/connections/hubspot/token", json={"token": "nope"}, headers=auth_headers).status_code == 400
        with patch("coworker.connectors.hubspot.verify_private_token", side_effect=ConnectorError("bad", "x")):
            assert client.post("/api/coworker/connections/hubspot/token", json={"token": "pat-1"},
                               headers=auth_headers).status_code == 400
        with patch("coworker.connectors.hubspot.verify_private_token",
                   return_value={"access_token": "pat-1", "kind": "private", "portal": "42"}):
            ok = client.post("/api/coworker/connections/hubspot/token", json={"token": "pat-1"}, headers=auth_headers)
        assert ok.get_json() == {"connected": True, "portal": "42"}
        me = client.get("/api/coworker", headers=auth_headers).get_json()["coworker"]
        assert me["mode"] == "demo"  # a CRM doesn't switch the workspace to live
        conns = client.get("/api/coworker/connections", headers=auth_headers).get_json()["connections"]
        assert any(c["provider"] == "hubspot" for c in conns)
        assert client.delete("/api/coworker/connections/hubspot", headers=auth_headers).get_json()["purged"] == 0

        monkeypatch.setenv("HUBSPOT_CLIENT_ID", "cid")
        monkeypatch.setenv("HUBSPOT_CLIENT_SECRET", "sec")
        url = client.post("/api/coworker/connections/hubspot/start", headers=auth_headers).get_json()["url"]
        state = url.split("state=")[1]
        bad = oauth_return(client, "/api/coworker/connections/hubspot/callback?state=nope&code=c")
        assert "connect_error=hubspot" in bad.headers["Location"]
        with patch("coworker.connectors.hubspot.exchange_code", side_effect=ConnectorError("denied", "oauth_failed")):
            assert "connect_error" in oauth_return(client, f"/api/coworker/connections/hubspot/callback?state={state}&code=c").headers["Location"]
        with patch("coworker.connectors.hubspot.exchange_code",
                   return_value={"access_token": "a", "kind": "oauth", "portal": "nw", "scope": "oauth"}):
            done = oauth_return(client, f"/api/coworker/connections/hubspot/callback?state={state}&code=c")
        assert "connected=hubspot" in done.headers["Location"]
