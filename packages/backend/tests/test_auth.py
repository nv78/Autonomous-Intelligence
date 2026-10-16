"""Tests for authentication endpoints."""


def test_register_missing_email(client):
    resp = client.post("/auth/register", json={"password": "password123"})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_register_missing_password(client):
    resp = client.post("/auth/register", json={"email": "test@example.com"})
    assert resp.status_code == 400


def test_register_short_password(client):
    resp = client.post("/auth/register", json={"email": "t@e.com", "password": "short"})
    assert resp.status_code == 400


def test_register_success(client):
    resp = client.post("/auth/register", json={"email": "new@example.com", "password": "password123"})
    # No DB in the test client, so this surfaces as a clean 503 rather than a fake token.
    assert resp.status_code == 503


class _FakeConnection:
    def close(self):
        pass


class _FakeDB:
    """In-memory stand-in for database.db, keyed by email, used to drive the
    register/Google-callback flows through their real success paths without
    a MySQL connection."""

    def __init__(self, existing_users=None):
        self._users = dict(existing_users or {})
        self._next_id = max([u["id"] for u in self._users.values()], default=0) + 1

    def get_connection(self):
        return _FakeConnection()

    def get_user_by_email(self, cnx, email):
        return self._users.get(email)

    def set_password_hash(self, cnx, user_id, password_hash):
        for u in self._users.values():
            if u["id"] == user_id:
                u["password_hash"] = password_hash

    def create_user(self, cnx, email, password_hash, name=""):
        user_id = self._next_id
        self._next_id += 1
        self._users[email] = {"id": user_id, "email": email, "password_hash": password_hash, "name": name}
        return user_id


def _patch_db(monkeypatch, fake_db):
    import database.db as db_module
    monkeypatch.setattr(db_module, "get_connection", fake_db.get_connection)
    monkeypatch.setattr(db_module, "get_user_by_email", fake_db.get_user_by_email)
    monkeypatch.setattr(db_module, "create_user", fake_db.create_user)
    monkeypatch.setattr(db_module, "set_password_hash", fake_db.set_password_hash)


def test_register_success_new_user_is_flagged(client, monkeypatch):
    _patch_db(monkeypatch, _FakeDB())
    resp = client.post(
        "/auth/register", json={"email": "brandnew@example.com", "password": "password123"}
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["isNewUser"] is True
    assert "token" in body and "userId" in body


def test_register_duplicate_email_rejected(client, monkeypatch):
    _patch_db(monkeypatch, _FakeDB({"dupe@example.com": {"id": 1, "email": "dupe@example.com"}}))
    resp = client.post(
        "/auth/register", json={"email": "dupe@example.com", "password": "password123"}
    )
    assert resp.status_code == 409


def test_login_missing_credentials(client):
    resp = client.post("/auth/login", json={})
    assert resp.status_code == 400


def test_login_no_db(client):
    resp = client.post("/auth/login", json={"email": "x@x.com", "password": "password123"})
    assert resp.status_code in (401, 503)


def test_me_without_token(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_with_token(client, auth_headers):
    resp = client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert "userId" in resp.get_json()


def test_google_login_start_not_configured(client, monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    resp = client.get("/auth/google/login")
    assert resp.status_code == 503


def test_google_login_start_redirects_to_google(client, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    resp = client.get("/auth/google/login")
    assert resp.status_code == 302
    assert resp.headers["Location"].startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "client_id=test-client-id" in resp.headers["Location"]


def test_callback_google_denied(client):
    resp = client.get("/callback?error=access_denied")
    assert resp.status_code == 302
    assert "error=google_denied" in resp.headers["Location"]


def test_callback_missing_code(client):
    resp = client.get("/callback")
    assert resp.status_code == 302
    assert "error=missing_code" in resp.headers["Location"]


def test_callback_invalid_state(client):
    resp = client.get("/callback?code=abc&state=not-a-real-state")
    assert resp.status_code == 302
    assert "error=invalid_state" in resp.headers["Location"]


def _make_valid_state(app):
    from api_endpoints.auth.handler import _state_serializer
    with app.app_context():
        return _state_serializer().dumps("nonce")


def test_callback_not_configured(client, app, monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    state = _make_valid_state(app)
    resp = client.get(f"/callback?code=abc&state={state}")
    assert resp.status_code == 302
    assert "error=not_configured" in resp.headers["Location"]


def test_callback_success_no_db(client, app, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    state = _make_valid_state(app)

    from api_endpoints.auth import handler

    class FakeTokenResponse:
        ok = True
        status_code = 200
        text = ""

        def json(self):
            return {"id_token": "fake-id-token"}

    def fake_post(url, data, timeout):
        assert url == handler.GOOGLE_TOKEN_URL
        assert data["code"] == "abc"
        return FakeTokenResponse()

    def fake_verify(id_token_str, request, audience, clock_skew_in_seconds=0):
        assert id_token_str == "fake-id-token"
        assert audience == "test-client-id"
        return {"email": "googleuser@example.com", "email_verified": True, "name": "Google User"}

    monkeypatch.setattr(handler.http_requests, "post", fake_post)
    monkeypatch.setattr(handler.google_id_token, "verify_oauth2_token", fake_verify)

    resp = client.get(f"/callback?code=abc&state={state}")
    # No DB in the test client, so this surfaces as a clean redirect-with-error
    # rather than a fake token.
    assert resp.status_code == 302
    assert "error=service_unavailable" in resp.headers["Location"]


def _setup_google_callback(client, app, monkeypatch, email, fake_db):
    """Wires GOOGLE env vars, a valid OAuth state, a stubbed token exchange +
    id-token verification, and a fake DB, then returns the /callback response
    for that email — exercising the real create-or-fetch-user code path."""
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    state = _make_valid_state(app)

    from api_endpoints.auth import handler

    class FakeTokenResponse:
        ok = True
        status_code = 200
        text = ""

        def json(self):
            return {"id_token": "fake-id-token"}

    monkeypatch.setattr(handler.http_requests, "post", lambda url, data, timeout: FakeTokenResponse())
    monkeypatch.setattr(
        handler.google_id_token,
        "verify_oauth2_token",
        lambda id_token_str, request, audience, clock_skew_in_seconds=0: {
            "email": email,
            "email_verified": True,
            "name": "Google User",
        },
    )
    _patch_db(monkeypatch, fake_db)

    return client.get(f"/callback?code=abc&state={state}")


def test_callback_creates_account_for_new_google_user(client, app, monkeypatch):
    resp = _setup_google_callback(client, app, monkeypatch, "newgoogleuser@example.com", _FakeDB())

    assert resp.status_code == 302
    location = resp.headers["Location"]
    assert location.startswith("http://localhost:3000/oauth/callback#token=")
    assert "isNewUser=1" in location


def test_callback_signs_in_existing_google_user_without_new_user_flag(client, app, monkeypatch):
    fake_db = _FakeDB({"returninguser@example.com": {"id": 42, "email": "returninguser@example.com"}})
    resp = _setup_google_callback(client, app, monkeypatch, "returninguser@example.com", fake_db)

    assert resp.status_code == 302
    location = resp.headers["Location"]
    assert location.startswith("http://localhost:3000/oauth/callback#token=")
    assert "isNewUser" not in location
