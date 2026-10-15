"""Real-time email: Gmail Pub/Sub push and Outlook change notifications."""
from __future__ import annotations

import base64
import json
import time
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from coworker import mail_push
from coworker.connectors.base import ConnectorError, encrypt_token
from coworker.store import Store, iso


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for key in ("GMAIL_PUBSUB_TOPIC", "GMAIL_PUSH_TOKEN", "GMAIL_PUSH_AUDIENCE", "GMAIL_PUSH_SERVICE_ACCOUNT", "BACKEND_URL"):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def s(tmp_path):
    return Store(f"sqlite:///{tmp_path}/push.db")


class Conn:
    def __init__(self, cursor: dict | None = None, fail: Exception | None = None, responses: list | None = None):
        self.user_id = 1
        self.cursor = cursor or {}
        self.calls: list[tuple[str, str, dict | None]] = []
        self.fail = fail
        self.responses = list(responses or [])

    def _request(self, method: str, url: str, **kw):
        self.calls.append((method, url, kw.get("json")))
        if self.fail:
            raise self.fail
        return self.responses.pop(0) if self.responses else {}


def _pubsub(email: str) -> dict:
    return {"message": {"data": base64.b64encode(json.dumps({"emailAddress": email, "historyId": "9"}).encode()).decode()},
            "subscription": "projects/p/subscriptions/s"}


def test_gmail_watch_starts_renews_and_backs_off(monkeypatch):
    conn = Conn(responses=[{"historyId": "1", "expiration": str(int((time.time() + 7 * 86400) * 1000))}])
    mail_push.ensure_gmail_watch(conn)
    assert conn.calls == []  # not configured
    monkeypatch.setenv("GMAIL_PUBSUB_TOPIC", "projects/p/topics/gmail")
    monkeypatch.setenv("GMAIL_PUSH_TOKEN", "tok")
    mail_push.ensure_gmail_watch(conn)
    assert conn.calls[0][1].endswith("/watch") and conn.calls[0][2]["topicName"] == "projects/p/topics/gmail"
    mail_push.ensure_gmail_watch(conn)
    assert len(conn.calls) == 1  # still valid for days

    failing = Conn(fail=ConnectorError("403"))
    mail_push.ensure_gmail_watch(failing)
    mail_push.ensure_gmail_watch(failing)
    assert len(failing.calls) == 1 and "gmail_watch_retry" in failing.cursor  # one try per hour


def test_gmail_push_endpoint(client, app, monkeypatch):
    assert client.post("/api/coworker/google/push", json=_pubsub("x@y.com")).status_code == 404
    monkeypatch.setenv("GMAIL_PUBSUB_TOPIC", "projects/p/topics/gmail")
    monkeypatch.setenv("GMAIL_PUSH_TOKEN", "tok")
    assert client.post("/api/coworker/google/push?token=nope", json=_pubsub("x@y.com")).status_code == 401
    from coworker.store import get_store

    with app.app_context():
        st = get_store()
        st.create_coworker(1, "Natan", "natan@anote.ai", mode="live")
        st.upsert_connection(1, "google", status="connected", account_label="Natan@Anote.ai",
                             token_enc=encrypt_token({"access_token": "at", "expires_at": 9e9}))
    with patch("coworker.connectors.google.GoogleConnector.sync", return_value=1) as sync, \
            patch("api_endpoints.coworker.slack_events.react") as react, \
            patch("coworker.connectors.microsoft.MicrosoftConnector.sync") as ms_sync:
        resp = client.post("/api/coworker/google/push?token=tok", json=_pubsub("natan@anote.ai"))
        assert resp.get_json() == {"ok": True, "users": 1}
        assert client.post("/api/coworker/google/push?token=tok", json={"message": {"data": "!!"}}).get_json()["users"] == 0
    sync.assert_called_once()
    react.assert_called_once()
    ms_sync.assert_not_called()  # only the mailbox that changed


def test_gmail_oidc_verification(monkeypatch):
    monkeypatch.setenv("GMAIL_PUSH_AUDIENCE", "https://chat.ourogen.ai/api/coworker/google/push")
    assert not mail_push.verify_gmail({}, {})
    assert not mail_push.verify_gmail({"Authorization": "Bearer bad"}, {})
    with patch("google.oauth2.id_token.verify_oauth2_token", return_value={"email": "push@p.iam.gserviceaccount.com"}):
        assert mail_push.verify_gmail({"Authorization": "Bearer good"}, {})
        monkeypatch.setenv("GMAIL_PUSH_SERVICE_ACCOUNT", "other@p.iam.gserviceaccount.com")
        assert not mail_push.verify_gmail({"Authorization": "Bearer good"}, {})
    assert mail_push.parse_gmail({"message": {"data": base64.b64encode(b"[1]").decode()}}) == ""


def test_graph_subscription_create_renew_recreate(monkeypatch):
    conn = Conn(responses=[{"id": "sub-1"}])
    mail_push.ensure_graph_subscription(conn)
    assert conn.calls == []  # needs a public https backend
    monkeypatch.setenv("BACKEND_URL", "https://chat.ourogen.ai")
    mail_push.ensure_graph_subscription(conn)
    method, url, body = conn.calls[0]
    assert (method, url) == ("POST", "/subscriptions")
    assert body["notificationUrl"] == "https://chat.ourogen.ai/api/coworker/microsoft/notify"
    assert body["resource"] == "me/mailFolders('Inbox')/messages" and body["clientState"]
    assert conn.cursor["graph_sub"]["id"] == "sub-1"
    mail_push.ensure_graph_subscription(conn)
    assert len(conn.calls) == 1  # still fresh

    conn.cursor["graph_sub"]["expires"] = iso(datetime.now(UTC) + timedelta(hours=5))
    mail_push.ensure_graph_subscription(conn)
    assert conn.calls[-1][:2] == ("PATCH", "/subscriptions/sub-1")

    gone = Conn(cursor={"graph_sub": {"id": "old", "expires": iso(datetime.now(UTC)), "client_state": "x"}})
    calls = iter([ConnectorError("gone", "not_found"), {"id": "sub-2"}])

    def answer(method, url, **kw):
        gone.calls.append((method, url, kw.get("json")))
        result = next(calls)
        if isinstance(result, Exception):
            raise result
        return result

    gone._request = answer  # type: ignore[method-assign]
    mail_push.ensure_graph_subscription(gone)
    assert gone.cursor["graph_sub"]["id"] == "sub-2"

    broken = Conn(fail=ConnectorError("validation failed"))
    mail_push.ensure_graph_subscription(broken)
    mail_push.ensure_graph_subscription(broken)
    assert len(broken.calls) == 1 and "graph_sub_retry" in broken.cursor


def test_graph_notify_endpoint(client, app):
    resp = client.post("/api/coworker/microsoft/notify?validationToken=abc%20123")
    assert resp.status_code == 200 and resp.data == b"abc 123" and resp.mimetype == "text/plain"
    from coworker.store import get_store

    with app.app_context():
        st = get_store()
        st.create_coworker(1, "Natan", "natan@contoso.com", mode="live")
        st.upsert_connection(1, "microsoft", status="connected", account_label="natan@contoso.com",
                             token_enc=encrypt_token({"access_token": "at", "expires_at": 9e9}),
                             sync_cursor=json.dumps({"graph_sub": {"id": "sub-1", "client_state": "secret"}}))
    note = {"value": [{"subscriptionId": "sub-1", "clientState": "secret", "changeType": "created"}]}
    with patch("coworker.connectors.microsoft.MicrosoftConnector.sync", return_value=1) as sync, \
            patch("api_endpoints.coworker.slack_events.react"):
        assert client.post("/api/coworker/microsoft/notify", json=note).get_json() == {"ok": True, "users": 1}
        forged = {"value": [{"subscriptionId": "sub-1", "clientState": "guess"}, {"subscriptionId": "", "clientState": "x"}]}
        assert client.post("/api/coworker/microsoft/notify", json=forged).get_json()["users"] == 0
    sync.assert_called_once()


def test_users_for_graph_skips_bad_cursor(s):
    s.upsert_connection(1, "microsoft", status="connected", sync_cursor="not json sub-1")
    assert mail_push.users_for_graph(s, [{"subscriptionId": "sub-1", "clientState": "x"}]) == []
    assert mail_push.users_for_gmail(s, "") == []


def test_refresh_runs_once_per_mailbox(app):
    from api_endpoints.coworker import mail_events

    app.config["COWORKER_SYNC_THREADS"] = True
    started = MagicMock()
    with app.test_request_context(), patch("threading.Thread", return_value=started) as thread:
        mail_events._running.add((1, "google"))
        mail_events.refresh(1, "google")  # already running: nothing new
        thread.assert_not_called()
        mail_events._running.clear()
        mail_events.refresh(1, "google")
    started.start.assert_called_once()
    mail_events._running.clear()


def test_sync_renews_the_watch(s, monkeypatch):
    monkeypatch.setenv("GMAIL_PUBSUB_TOPIC", "projects/p/topics/gmail")
    monkeypatch.setenv("GMAIL_PUSH_TOKEN", "tok")
    from coworker.connectors.google import GoogleConnector

    conn = GoogleConnector(s, 1, {"access_token": "at", "expires_at": 9e9, "scope": ""}, {})
    with patch.object(GoogleConnector, "_sync_gmail", return_value=0), \
            patch.object(GoogleConnector, "_sync_calendar", return_value=0), \
            patch.object(GoogleConnector, "_sync_drive", return_value=0), \
            patch.object(GoogleConnector, "_request", return_value={"expiration": "99999999999999"}) as req:
        conn.sync(s, 1)
    assert req.call_args.args[1].endswith("/watch")
    assert json.loads(s.get_connection_row(1, "google")["sync_cursor"])["gmail_watch_expires"] == 99999999999999
