"""Team plan SSO: Microsoft sign-in, domain auto-join, and "require Google/Microsoft sign-in"."""
from __future__ import annotations

import bcrypt
import pytest

from coworker import orgs
from coworker.store import Store, get_store
from tests.test_auth import _FakeDB, _patch_db


@pytest.fixture
def s(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/sso.db")
    store.create_coworker(1, "Avery Admin", "avery@acme.com", mode="demo")
    store.create_coworker(2, "Blake New", "blake@acme.com", mode="demo")
    return store


def test_auto_join_needs_a_real_company_domain(s):
    org = orgs.create(s, 1, "Acme", "", "avery@acme.com")
    with pytest.raises(orgs.OrgError, match="Set your company domain"):
        orgs.update(s, 1, new_policies={"domain_auto_join": True})
    with pytest.raises(orgs.OrgError, match="public email provider"):
        orgs.update(s, 1, new_policies={"domain_auto_join": True}, domain="gmail.com")
    with pytest.raises(orgs.OrgError) as exc:
        orgs.update(s, 1, new_policies={"domain_auto_join": True}, domain="initech.com")  # not the admin's domain
    assert exc.value.status == 403
    updated = orgs.update(s, 1, new_policies={"domain_auto_join": True, "sso_required": True}, domain="@Acme.com")
    assert updated["domain"] == "acme.com" and updated["policies"]["domain_auto_join"] is True

    s.create_coworker(5, "Squatter", "sam@acme.com", mode="demo")  # a second org can't claim the same domain
    orgs.create(s, 5, "Acme Rival", "acme.com", "sam@acme.com")
    with pytest.raises(orgs.OrgError) as exc:
        orgs.update(s, 5, new_policies={"domain_auto_join": True})
    assert exc.value.code == "conflict"
    assert org["id"] != orgs.org_for(s, 5)["id"]


def test_sso_login_joins_the_domain_org_and_respects_removal(s):
    orgs.create(s, 1, "Acme", "acme.com", "avery@acme.com")
    assert orgs.on_sso_login(s, 2, "blake@acme.com", "acme.com") is None  # auto-join off
    orgs.update(s, 1, new_policies={"domain_auto_join": True})

    assert orgs.on_sso_login(s, 2, "blake@acme.com", "") is None  # personal Google account on a work address
    joined = orgs.on_sso_login(s, 2, "Blake@Acme.com", "Acme.com")
    assert joined and joined["name"] == "Acme"
    assert orgs.membership(s, 2)["role"] == "member"
    assert s.get_coworker(2)["settings"]["employer_authorized"]["basis"] == "organization"
    assert orgs.on_sso_login(s, 2, "blake@acme.com", "acme.com") is None  # already in

    member = orgs.membership(s, 2)
    orgs.remove(s, 1, int(member["id"]))
    assert orgs.on_sso_login(s, 2, "blake@acme.com", "acme.com") is None  # removed people stay out
    assert orgs.on_sso_login(s, 3, "casey@other.com", "other.com") is None
    assert orgs.on_sso_login(s, 4, "someone@gmail.com", "gmail.com") is None


def test_sso_required_only_for_members_of_that_org(s):
    orgs.create(s, 1, "Acme", "acme.com", "avery@acme.com")
    assert orgs.sso_required(s, "avery@acme.com") is False
    orgs.update(s, 1, new_policies={"sso_required": True})
    assert orgs.sso_required(s, "AVERY@acme.com") is True
    assert orgs.sso_required(s, "blake@acme.com") is False  # not a member


def test_password_login_refused_when_org_requires_sso(client, app, monkeypatch):
    hashed = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode()
    _patch_db(monkeypatch, _FakeDB({"avery@acme.com": {"id": 1, "email": "avery@acme.com", "password_hash": hashed}}))
    assert client.post("/auth/login", json={"email": "avery@acme.com", "password": "password123"}).status_code == 200
    with app.app_context():
        store = get_store()
        store.create_coworker(1, "Avery", "avery@acme.com", mode="demo")
        orgs.create(store, 1, "Acme", "acme.com", "avery@acme.com")
        orgs.update(store, 1, new_policies={"sso_required": True})
    resp = client.post("/auth/login", json={"email": "avery@acme.com", "password": "password123"})
    assert resp.status_code == 403 and resp.get_json()["code"] == "sso_required"
    bad = client.post("/auth/login", json={"email": "avery@acme.com", "password": "wrong-password"})
    assert bad.status_code == 401  # membership isn't revealed without the right password


# -- Microsoft sign-in ------------------------------------------------------------

class _Resp:
    def __init__(self, data, ok=True, status=200):
        self._data, self.ok, self.status_code, self.text = data, ok, status, ""

    def json(self):
        return self._data


@pytest.fixture
def ms(monkeypatch):
    monkeypatch.setenv("MICROSOFT_CLIENT_ID", "ms-client")
    monkeypatch.setenv("MICROSOFT_CLIENT_SECRET", "ms-secret")


def _state(app):
    from api_endpoints.auth.handler import _microsoft_state_serializer

    with app.app_context():
        return _microsoft_state_serializer().dumps("nonce")


def _callback(client, app, monkeypatch, profile, token_ok=True):
    from api_endpoints.auth import handler

    monkeypatch.setattr(handler.http_requests, "post", lambda url, data, timeout: _Resp({"access_token": "at"}, ok=token_ok, status=400))
    monkeypatch.setattr(handler.http_requests, "get", lambda url, timeout, headers: _Resp(profile))
    return client.get(f"/auth/microsoft/callback?code=abc&state={_state(app)}")


def test_microsoft_login_urls(client, monkeypatch):
    monkeypatch.delenv("MICROSOFT_CLIENT_ID", raising=False)
    assert client.get("/auth/microsoft/url").status_code == 503
    assert client.get("/auth/microsoft/login").status_code == 503
    monkeypatch.setenv("MICROSOFT_CLIENT_ID", "ms-client")
    monkeypatch.setenv("MICROSOFT_CLIENT_SECRET", "ms-secret")
    url = client.get("/auth/microsoft/url").get_json()["url"]
    assert url.startswith("https://login.microsoftonline.com/common/oauth2/v2.0/authorize?") and "User.Read" in url
    assert client.get("/auth/microsoft/login").status_code == 302


def test_microsoft_callback_errors(client, app, monkeypatch, ms):
    assert "microsoft_denied" in client.get("/auth/microsoft/callback?error=access_denied").headers["Location"]
    assert "missing_code" in client.get("/auth/microsoft/callback").headers["Location"]
    assert "invalid_state" in client.get("/auth/microsoft/callback?code=a&state=nope").headers["Location"]
    failed = _callback(client, app, monkeypatch, {}, token_ok=False)
    assert "microsoft_auth_failed" in failed.headers["Location"]
    guest = _callback(client, app, monkeypatch, {"userPrincipalName": "eve_evil.com#EXT#@acme.onmicrosoft.com"})
    assert "unverified_email" in guest.headers["Location"]


def test_microsoft_callback_not_configured(client, app, monkeypatch):
    monkeypatch.delenv("MICROSOFT_CLIENT_ID", raising=False)
    resp = client.get(f"/auth/microsoft/callback?code=abc&state={_state(app)}")
    assert "not_configured" in resp.headers["Location"]


def test_microsoft_callback_signs_in_and_auto_joins(client, app, monkeypatch, ms):
    fake = _FakeDB({"avery@acme.com": {"id": 1, "email": "avery@acme.com"}})
    _patch_db(monkeypatch, fake)
    with app.app_context():
        store = get_store()
        store.create_coworker(1, "Avery", "avery@acme.com", mode="demo")
        orgs.create(store, 1, "Acme", "acme.com", "avery@acme.com")
        orgs.update(store, 1, new_policies={"domain_auto_join": True})

    resp = _callback(client, app, monkeypatch, {"userPrincipalName": "Blake@Acme.com", "mail": "ceo@acme.com",
                                                "givenName": "Blake"})
    location = resp.headers["Location"]
    assert location.startswith("http://localhost:3000/oauth/callback?token=") and "isNewUser=1" in location
    new_id = fake.get_user_by_email(None, "blake@acme.com")["id"]  # the UPN, never the unverified mail field
    assert fake.get_user_by_email(None, "ceo@acme.com") is None
    with app.app_context():
        assert orgs.membership(get_store(), new_id)["email"] == "blake@acme.com"


def test_google_sign_in_auto_joins_only_workspace_accounts(client, app, monkeypatch):
    from tests.test_auth import _setup_google_callback

    with app.app_context():
        store = get_store()
        store.create_coworker(1, "Avery", "avery@acme.com", mode="demo")
        orgs.create(store, 1, "Acme", "acme.com", "avery@acme.com")
        orgs.update(store, 1, new_policies={"domain_auto_join": True})
    fake = _FakeDB({"avery@acme.com": {"id": 1, "email": "avery@acme.com"}})
    _setup_google_callback(client, app, monkeypatch, "blake@acme.com", fake)  # no hd claim: personal account
    with app.app_context():
        assert orgs.membership(get_store(), fake.get_user_by_email(None, "blake@acme.com")["id"]) is None

    from api_endpoints.auth import handler

    monkeypatch.setattr(handler.google_id_token, "verify_oauth2_token", lambda *a, **k: {
        "email": "casey@acme.com", "email_verified": True, "hd": "acme.com"})
    client.get(f"/callback?code=abc&state={_google_state(app)}")
    with app.app_context():
        assert orgs.membership(get_store(), fake.get_user_by_email(None, "casey@acme.com")["id"])["email"] == "casey@acme.com"


def _google_state(app):
    from tests.test_auth import _make_valid_state

    return _make_valid_state(app)
