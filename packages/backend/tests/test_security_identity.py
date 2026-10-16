"""Regression tests for the identity findings of the pre-release security review."""
from __future__ import annotations

import time
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import bcrypt

from coworker import identity
from coworker.store import Store, get_store, iso, utcnow
from tests.test_auth import _FakeDB, _make_valid_state, _patch_db


def _token(app, user_id: str) -> dict[str, str]:
    from flask_jwt_extended import create_access_token

    with app.app_context():
        return {"Authorization": f"Bearer {create_access_token(identity=user_id)}"}


def test_someone_elses_connect_link_cannot_attach_your_mailbox(client, app):
    """Attacker (user 2) starts a Google connect and sends the link; victim (user 1) consents and finishes."""
    attacker = _token(app, "2")
    url = client.post("/api/coworker/connections/google/start", json={"level": "act"}, headers=attacker)
    if url.status_code == 501:  # Google not configured in this test env: build the state directly
        from api_endpoints.coworker.connections import _state

        with app.app_context():
            state = _state(2, "google", "act")
    else:
        state = parse_qs(urlparse(url.get_json()["url"]).query)["state"][0]
    hop = client.get(f"/api/coworker/connections/google/callback?state={state}&code=victims-code")
    assert hop.status_code == 302 and "/app/connect/finish?" in hop.location  # nothing exchanged in the callback
    with patch("coworker.connectors.google.exchange_code") as exchange:
        refused = client.post("/api/coworker/connections/google/finish", json={"state": state, "code": "victims-code"},
                              headers=_token(app, "1"))
    assert refused.status_code == 403 and refused.get_json()["code"] == "wrong_account"
    exchange.assert_not_called()
    with app.app_context():
        assert not get_store().get_connection_row(2, "google") and not get_store().get_connection_row(1, "google")
    assert client.post("/api/coworker/connections/nope/finish", json={}, headers=attacker).status_code == 404


def test_sign_in_callback_needs_this_browsers_nonce(app, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    fresh = app.test_client()  # a browser that never started this sign-in
    state = _make_valid_state(app)
    assert "invalid_state" in fresh.get(f"/callback?code=abc&state={state}").location
    fresh.set_cookie("cw_login_nonce", "other")
    assert "invalid_state" in fresh.get(f"/callback?code=abc&state={state}").location
    start = fresh.get("/auth/google/login")
    assert start.status_code == 302 and "HttpOnly" in start.headers["Set-Cookie"] and "SameSite=Lax" in start.headers["Set-Cookie"]
    assert fresh.get("/auth/google/url").get_json()["url"].endswith("/auth/google/login")


def test_first_verified_sign_in_replaces_a_squatters_password_and_sessions(client, app, monkeypatch):
    squat_hash = bcrypt.hashpw(b"attacker-pass", bcrypt.gensalt()).decode()
    fake = _FakeDB({"alice@corp.com": {"id": 7, "email": "alice@corp.com", "password_hash": squat_hash}})
    _patch_db(monkeypatch, fake)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    from api_endpoints.auth import handler

    class TokenResp:
        ok, status_code, text = True, 200, ""

        def json(self):
            return {"id_token": "t"}

    monkeypatch.setattr(handler.http_requests, "post", lambda url, data, timeout: TokenResp())
    monkeypatch.setattr(handler.google_id_token, "verify_oauth2_token",
                        lambda *a, **k: {"email": "alice@corp.com", "email_verified": True, "sub": "g-alice", "hd": "corp.com"})
    old_session = _token(app, "7")
    time.sleep(1.1)  # tokens carry whole-second issue times
    resp = client.get(f"/callback?code=abc&state={_make_valid_state(app)}")
    assert "/oauth/callback#token=" in resp.location  # the token travels in the fragment, not the query
    assert fake.get_user_by_email(None, "alice@corp.com")["password_hash"] != squat_hash
    with app.app_context():
        assert identity.verified_emails(get_store(), 7) == {"alice@corp.com"}
    assert client.get("/auth/me", headers=old_session).status_code == 401  # the squatter's session is over
    new_token = resp.location.split("#token=")[1].split("&")[0]
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {new_token}"}).status_code == 200

    pw_hash = fake.get_user_by_email(None, "alice@corp.com")["password_hash"]
    client.set_cookie("cw_login_nonce", "nonce")
    client.get(f"/callback?code=abc&state={_make_valid_state(app)}")  # later sign-ins change nothing
    assert fake.get_user_by_email(None, "alice@corp.com")["password_hash"] == pw_hash


def test_token_revocation_rules(tmp_path):
    s = Store(f"sqlite:///{tmp_path}/r.db")
    now = int(utcnow().timestamp())
    assert not identity.token_revoked(s, {"sub": "3", "iat": now})
    identity.revoke_sessions(s, 3)
    assert identity.token_revoked(s, {"sub": "3", "iat": now - 60})
    assert not identity.token_revoked(s, {"sub": "3", "iat": now + 60})
    assert not identity.token_revoked(s, {"sub": "x"}) and identity.token_revoked(s, {"sub": "3"})
    s.execute("UPDATE cw_auth_epochs SET tokens_valid_after = %s", (iso(utcnow() - timedelta(days=1)),))
    assert not identity.token_revoked(s, {"sub": "3", "iat": now})


def test_sessions_expire(app):
    assert app.config["JWT_ACCESS_TOKEN_EXPIRES"] == timedelta(days=14)


def test_owner_email_and_admin_rights_come_from_verified_identities(client, app, auth_headers, monkeypatch):
    with patch("api_endpoints.coworker.core.owner_profile", return_value=("Eve", "eve@example.com")):
        made = client.post("/api/coworker", json={"mode": "demo", "email": "natan@ourogen.ai"}, headers=auth_headers)
    assert made.get_json()["coworker"]["ownerEmail"] == "eve@example.com"  # the body can't choose it
    monkeypatch.setenv("PILOT_ADMIN_EMAILS", "eve@example.com")
    assert client.get("/api/coworker/pilot/applications", headers=auth_headers).status_code == 403  # typed, not verified
    with app.app_context():
        identity.record(get_store(), 1, "google", "g-eve", "eve@example.com")
    assert client.get("/api/coworker/pilot/applications", headers=auth_headers).status_code == 200


def test_personal_microsoft_accounts_manage_no_domain(client, app, monkeypatch):
    import jwt as pyjwt

    from api_endpoints.auth import handler

    monkeypatch.setenv("MICROSOFT_CLIENT_ID", "m")
    monkeypatch.setenv("MICROSOFT_CLIENT_SECRET", "s")
    _patch_db(monkeypatch, _FakeDB())

    class R:
        ok, status_code, text = True, 200, ""

        def __init__(self, data):
            self._d = data

        def json(self):
            return self._d

    personal = pyjwt.encode({"tid": handler.MICROSOFT_PERSONAL_TENANT}, "k", algorithm="HS256")
    monkeypatch.setattr(handler.http_requests, "post", lambda url, data, timeout: R({"access_token": "a", "id_token": personal}))
    monkeypatch.setattr(handler.http_requests, "get", lambda url, timeout, headers: R({"id": "oid-1", "userPrincipalName": "ex@corp.com"}))
    with patch("coworker.orgs.on_sso_login", return_value=None) as joined:
        with app.app_context():
            state = handler._microsoft_state_serializer().dumps("nonce")
        client.get(f"/auth/microsoft/callback?code=c&state={state}")
    assert joined.call_args.args[3] == ""  # managed domain: none, so no automatic joining


def test_oversized_request_is_rejected(client, app, monkeypatch):
    monkeypatch.setenv("COWORKER_INBOUND_DOMAIN", "coworker.example.com")
    monkeypatch.setenv("COWORKER_INBOUND_TOKEN", "sekrit")
    app.config["MAX_CONTENT_LENGTH"] = 1024
    assert client.post("/api/coworker/email/inbound?token=sekrit", data="x" * 4096,
                       content_type="application/json").status_code == 413
