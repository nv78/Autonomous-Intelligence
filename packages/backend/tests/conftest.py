"""Shared pytest fixtures."""
import os
import sys

import pytest

# Ensure packages/backend is on the path when running from CI
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402


@pytest.fixture
def app(tmp_path):
    return create_app({
        "COWORKER_DB_URL": f"sqlite:///{tmp_path}/coworker.db",
        "TESTING": True,
        "JWT_SECRET_KEY": "test-secret",
        "DB_HOST": "localhost",
        "ANTHROPIC_API_KEY": "",
        "STRIPE_SECRET_KEY": "",
    })


@pytest.fixture
def client(app):
    c = app.test_client()
    # The browser that started a Google/Microsoft sign-in holds this nonce (see auth/handler.py);
    # tests sign the same value into their states.
    c.set_cookie("cw_login_nonce", "nonce")
    return c


@pytest.fixture
def auth_headers(client, app):
    with app.app_context():
        from flask_jwt_extended import create_access_token
        token = create_access_token(identity="1")
    return {"Authorization": f"Bearer {token}"}


def oauth_return(client, callback_url: str, user_id: str = "1"):
    """Follow a provider redirect the way the browser does: the callback hands the parameters to the
    web app, which finishes the connection as the signed-in user. Returns where the browser lands."""
    from types import SimpleNamespace
    from urllib.parse import parse_qs, urlparse

    from flask_jwt_extended import create_access_token

    hop = client.get(callback_url)
    assert hop.status_code == 302 and "/app/connect/finish?" in hop.location
    params = {k: v[0] for k, v in parse_qs(urlparse(hop.location).query).items()}
    provider = params.pop("provider")
    with client.application.app_context():
        token = create_access_token(identity=user_id)
    resp = client.post(f"/api/coworker/connections/{provider}/finish", json=params,
                       headers={"Authorization": f"Bearer {token}"})
    if resp.status_code != 200:
        return SimpleNamespace(status_code=resp.status_code, location="", headers={"Location": ""}, json=resp.get_json())
    location = resp.get_json()["next"]
    return SimpleNamespace(status_code=302, location=location, headers={"Location": location})
