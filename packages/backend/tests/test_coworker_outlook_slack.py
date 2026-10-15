"""Outlook (Microsoft Graph) connector and real-time Slack events."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest

from coworker.connectors import microsoft, slack
from coworker.connectors.base import ConnectorError, Workspace, encrypt_token
from coworker.store import Store
from tests.conftest import oauth_return


@pytest.fixture(autouse=True)
def _no_mysql_profile():
    with patch("api_endpoints.coworker.common.owner_profile", return_value=("Natan Vidra", "natan@example.com")), \
         patch("api_endpoints.coworker.core.owner_profile", return_value=("Natan Vidra", "natan@example.com")):
        yield


@pytest.fixture
def store(tmp_path):
    s = Store(f"sqlite:///{tmp_path}/ms.db")
    s.create_coworker(1, "Natan Vidra", "natan@contoso.com", mode="live")
    return s


def _resp(status: int = 200, body: Any = None, headers: dict | None = None) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.content = b"" if body is None else b"x"
    r.json.return_value = body if body is not None else {}
    r.text = json.dumps(body) if body is not None else ""
    r.headers = headers or {}
    return r


MESSAGES = [
    {"id": "m2", "conversationId": "c1", "internetMessageId": "<m2@x>", "subject": "Re: Pilot",
     "body": {"contentType": "text", "content": "Can we start Monday?\n\nOn Tue, Natan wrote:\n> earlier"},
     "from": {"emailAddress": {"name": "Dana Lee", "address": "Dana@Northwind.com"}},
     "toRecipients": [{"emailAddress": {"name": "Natan", "address": "natan@contoso.com"}}], "ccRecipients": [],
     "receivedDateTime": "2026-10-14T15:00:00Z", "isDraft": False, "parentFolderId": "inbox",
     "internetMessageHeaders": [{"name": "List-Unsubscribe", "value": "<mailto:x>"}]},
    {"id": "m1", "conversationId": "c1", "subject": "Pilot",
     "body": {"contentType": "html", "content": "<p>Here is the <b>plan</b></p>"},
     "from": {"emailAddress": {"name": "Natan", "address": "natan@contoso.com"}},
     "toRecipients": [{"emailAddress": {"address": "dana@northwind.com"}}], "ccRecipients": [],
     "receivedDateTime": "2026-10-13T09:00:00Z", "isDraft": False, "parentFolderId": "sent-id"},
]
EVENTS = [
    {"id": "e1", "subject": "Northwind intro", "isCancelled": False,
     "start": {"dateTime": "2026-10-16T14:00:00.0000000"}, "end": {"dateTime": "2026-10-16T14:30:00.0000000"},
     "organizer": {"emailAddress": {"name": "Natan", "address": "natan@contoso.com"}},
     "attendees": [{"emailAddress": {"name": "Dana Lee", "address": "dana@northwind.com"}},
                   {"emailAddress": {"address": "natan@contoso.com"}}],
     "onlineMeeting": {"joinUrl": "https://teams.microsoft.com/l/meetup-join/abc"}, "webLink": "https://outlook/e1"},
    {"id": "e2", "subject": "Cancelled", "isCancelled": True, "start": {"dateTime": "2026-10-16T16:00:00"},
     "end": {"dateTime": "2026-10-16T17:00:00"}},
]


class FakeGraph:
    """Answers the Graph calls the connector makes, and records writes."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Any]] = []
        self.fail_next: dict[str, MagicMock] = {}

    def __call__(self, method: str, url: str, **kw: Any) -> MagicMock:
        path = url.replace(microsoft.GRAPH, "")
        self.calls.append((method, path, kw.get("json")))
        if path in self.fail_next:
            return self.fail_next.pop(path)
        if path == "/me/mailFolders/sentitems":
            return _resp(200, {"id": "sent-id"})
        if path == "/me/messages" and method == "GET":
            return _resp(200, {"value": MESSAGES[:1], "@odata.nextLink": f"{microsoft.GRAPH}/me/messages?page=2"})
        if path.startswith("/me/messages?page=2"):
            return _resp(200, {"value": MESSAGES[1:]})
        if path == "/me/calendarView":
            return _resp(200, {"value": EVENTS})
        if path.endswith("/createReplyAll") or (path == "/me/messages" and method == "POST"):
            return _resp(201, {"id": "draft1", "conversationId": "c1"})
        if path == "/me/events":
            return _resp(201, {"id": "ev9"})
        return _resp(202)


def _connector(store: Store, scope: str = "Mail.Read Mail.Send Calendars.ReadWrite") -> microsoft.MicrosoftConnector:
    token = {"access_token": "at", "refresh_token": "rt", "expires_at": time.time() + 3600, "scope": scope}
    store.upsert_connection(1, "microsoft", token_enc=encrypt_token(token), status="connected",
                            account_label="natan@contoso.com")
    row = store.get_connection_row(1, "microsoft")
    assert row
    return microsoft.MicrosoftConnector.from_row(store, row)


def test_outlook_sync_mail_and_calendar(store):
    graph = FakeGraph()
    conn = _connector(store)
    with patch("coworker.connectors.microsoft.requests.request", side_effect=graph):
        assert conn.sync(store, 1) == 3
        assert conn.sync(store, 1) == 0  # nothing new the second time
    mail = {i["external_id"]: i for i in store.items(1, provider="outlook")}
    assert mail["m2"]["direction"] == "inbound" and mail["m2"]["author_email"] == "dana@northwind.com"
    assert mail["m2"]["body"] == "Can we start Monday?" and mail["m2"]["meta"]["list_unsubscribe"]
    assert mail["m1"]["direction"] == "outbound" and mail["m1"]["body"] == "Here is the plan"
    event = store.items(1, provider="outlook_cal")[0]
    assert event["occurred_at"].startswith("2026-10-16T14:00:00")
    assert event["meta"]["location"].startswith("https://teams.microsoft.com/")
    assert [r["email"] for r in event["recipients"]] == ["dana@northwind.com"]  # the owner isn't an attendee of note
    cursor = json.loads(store.get_connection_row(1, "microsoft")["sync_cursor"])
    assert cursor["mail_since"] == "2026-10-14T15:00:00Z" and cursor["sent_folder"] == "sent-id"
    first_get = next(c for c in graph.calls if c[1] == "/me/messages")
    assert first_get[0] == "GET"


def test_outlook_reply_in_thread_draft_event_and_undo(store):
    graph = FakeGraph()
    conn = _connector(store)
    with patch("coworker.connectors.microsoft.requests.request", side_effect=graph):
        conn.sync(store, 1)
        sent = conn.send_email(store, 1, to=["dana@northwind.com"], subject="Re: Pilot", body="Monday works.",
                               thread_id="c1", cc=["ops@contoso.com"])
        assert sent.thread_id == "c1"
        writes = [(m, p) for m, p, _ in graph.calls if m != "GET"]
        assert ("POST", "/me/messages/m2/createReplyAll") in writes and ("POST", "/me/messages/draft1/send") in writes
        patch_body = next(j for m, p, j in graph.calls if m == "PATCH")
        assert patch_body["body"] == {"contentType": "Text", "content": "Monday works."}
        assert patch_body["ccRecipients"] == [{"emailAddress": {"address": "ops@contoso.com"}}]

        graph.calls.clear()  # a brand-new email when there's no thread
        conn.send_email(store, 1, to=["new@x.com"], subject="Hello", body="Hi")
        assert [(m, p) for m, p, _ in graph.calls][:2] == [("POST", "/me/messages"), ("POST", "/me/messages/draft1/send")]

        graph.fail_next["/me/messages/m2/createReplyAll"] = _resp(404, {"error": "gone"})
        draft = conn.create_draft(store, 1, to=["dana@northwind.com"], subject="Re: Pilot", body="draft", thread_id="c1")
        assert draft.undo == {"draft_id": "draft1"}
        assert conn.undo(store, 1, "email.draft", draft.undo)

        graph.fail_next["/me/events"] = _resp(400, {"error": "no teams for personal accounts"})
        ev = conn.create_event(store, 1, title="Kickoff", start="2026-10-20T15:00:00Z", end="2026-10-20T15:30:00Z",
                               attendees=["dana@northwind.com"])
        retried = [j for m, p, j in graph.calls if p == "/me/events"][-1]
        assert "isOnlineMeeting" not in retried and retried["start"] == {"dateTime": "2026-10-20T15:00:00", "timeZone": "UTC"}
        assert conn.undo(store, 1, "calendar.create", ev.undo)
        assert not conn.undo(store, 1, "email.send", {})


def test_outlook_needs_send_scope_and_token_refresh(store):
    conn = _connector(store, scope="Mail.Read")
    assert not conn.has_scope("gmail.send") and conn.has_scope("Mail.Read")
    with pytest.raises(ConnectorError) as exc:
        conn.send_email(store, 1, to=["a@b.com"], subject="x", body="y")
    assert exc.value.code == "needs_scope"

    conn.token["expires_at"] = 0
    fresh = _resp(200, {"access_token": "at2", "refresh_token": "rt2", "expires_in": 3600, "scope": "Mail.Read"})
    with patch("coworker.connectors.microsoft.requests.post", return_value=fresh):
        assert conn._access_token() == "at2"
    from coworker.connectors.base import decrypt_token

    assert decrypt_token(store.get_connection_row(1, "microsoft")["token_enc"])["refresh_token"] == "rt2"  # rotated

    conn.token["expires_at"] = 0
    with patch("coworker.connectors.microsoft.requests.post", return_value=_resp(400, {"error": "invalid_grant"})):
        with pytest.raises(ConnectorError) as exc:
            conn._access_token()
    assert exc.value.code == "reauth_required"

    conn.token = {"access_token": "at", "expires_at": time.time() + 3600}
    with patch("coworker.connectors.microsoft.requests.request", side_effect=[_resp(401), _resp(401)]), \
            patch("coworker.connectors.microsoft.requests.post", return_value=_resp(400, {"error": "x"})):
        with pytest.raises(ConnectorError):
            conn._request("GET", "/me")
    conn.token = {"access_token": "at", "expires_at": time.time() + 3600}
    with patch("coworker.connectors.microsoft.requests.request", return_value=_resp(403, {"error": "denied"})):
        with pytest.raises(ConnectorError) as exc:
            conn._request("GET", "/me")
    assert exc.value.code == "needs_scope"


def test_workspace_routes_email_to_outlook(store):
    _connector(store)
    ws = Workspace(store, 1)
    assert ws.email_connector().provider == "microsoft"
    with patch("coworker.connectors.microsoft.MicrosoftConnector.send_email") as send:
        from coworker import notify

        assert notify.deliver(store, 1, "Approve 2 replies", "body") == "outlook"
    assert send.call_args.kwargs["to"] == ["natan@contoso.com"]
    from coworker import governance

    assert governance.work_domain(store, 1) == "contoso.com"


def test_outlook_oauth_routes(client, auth_headers, monkeypatch):
    h = auth_headers
    client.post("/api/coworker", json={"mode": "demo"}, headers=h)
    monkeypatch.delenv("MICROSOFT_CLIENT_ID", raising=False)
    assert client.post("/api/coworker/connections/microsoft/start", headers=h).status_code == 501
    monkeypatch.setenv("MICROSOFT_CLIENT_ID", "mid")
    monkeypatch.setenv("MICROSOFT_CLIENT_SECRET", "msec")
    assert client.get("/api/coworker", headers=h).get_json()["capabilities"]["microsoft"] is True
    assert client.post("/api/coworker/connections/microsoft/start", json={"level": "x"}, headers=h).status_code == 400
    url = client.post("/api/coworker/connections/microsoft/start", json={"level": "act"}, headers=h).get_json()["url"]
    assert url.startswith("https://login.microsoftonline.com/common/oauth2/v2.0/authorize") and "Mail.Send" in url
    state = parse_qs(urlparse(url).query)["state"][0]
    token = {"access_token": "at", "refresh_token": "rt", "scope": "Mail.Read Mail.Send", "expires_at": 9e9}
    with patch("coworker.connectors.microsoft.exchange_code", return_value=token), \
         patch("coworker.connectors.microsoft.fetch_account_email", return_value="natan@contoso.com"):
        assert "connected=microsoft" in oauth_return(client, f"/api/coworker/connections/microsoft/callback?state={state}&code=c").location
    cw = client.get("/api/coworker", headers=h).get_json()
    assert cw["coworker"]["mode"] == "live" and cw["connections"][0]["account"] == "natan@contoso.com"
    assert "connect_error=microsoft" in oauth_return(client, "/api/coworker/connections/microsoft/callback?state=bad").location
    denied = oauth_return(client, f"/api/coworker/connections/microsoft/callback?state={state}&error=access_denied")
    assert "connect_error" in denied.location
    with patch("coworker.connectors.microsoft.exchange_code", side_effect=ConnectorError("nope")):
        assert "connect_error" in oauth_return(client, f"/api/coworker/connections/microsoft/callback?state={state}&code=c").location
    assert client.delete("/api/coworker/connections/microsoft", headers=h).get_json()["disconnected"]


def test_outlook_helpers():
    assert microsoft.fetch_account_email.__name__  # module imports cleanly
    with patch("coworker.connectors.microsoft.requests.get", return_value=_resp(200, {"userPrincipalName": "N@C.com"})):
        assert microsoft.fetch_account_email("at") == "n@c.com"
    with patch("coworker.connectors.microsoft.requests.get", return_value=_resp(401, {})):
        assert microsoft.fetch_account_email("at") == ""
    with patch("coworker.connectors.microsoft.requests.post",
               return_value=_resp(200, {"access_token": "a", "expires_in": 10})) as post:
        assert microsoft.exchange_code("code")["access_token"] == "a"
    assert post.call_args.kwargs["data"]["grant_type"] == "authorization_code"
    assert microsoft.revoke({}) is None
    assert microsoft._to_utc("") == ""


# -- Slack events ------------------------------------------------------------

def _signed(body: bytes, secret: str = "sssh", ts: int | None = None) -> dict[str, str]:
    ts = ts or int(time.time())
    sig = "v0=" + hmac.new(secret.encode(), f"v0:{ts}:".encode() + body, hashlib.sha256).hexdigest()
    return {"X-Slack-Request-Timestamp": str(ts), "X-Slack-Signature": sig, "Content-Type": "application/json"}


def test_slack_signature_rules(monkeypatch):
    body = b'{"a":1}'
    assert not slack.verify_signature(body, "1", "v0=x")  # no secret configured
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "sssh")
    h = _signed(body)
    assert slack.verify_signature(body, h["X-Slack-Request-Timestamp"], h["X-Slack-Signature"])
    assert not slack.verify_signature(b'{"a":2}', h["X-Slack-Request-Timestamp"], h["X-Slack-Signature"])
    old = _signed(body, ts=int(time.time()) - 600)
    assert not slack.verify_signature(body, old["X-Slack-Request-Timestamp"], old["X-Slack-Signature"])
    assert not slack.verify_signature(body, "nan", h["X-Slack-Signature"])


def _event(**over: Any) -> dict[str, Any]:
    event = {"type": "message", "channel": "D1", "channel_type": "im", "user": "U2", "text": "Can you send me the deck?",
             "ts": "1760000000.000100"}
    event.update(over)
    return {"type": "event_callback", "team_id": "T1", "authorizations": [{"user_id": "U1", "team_id": "T1"}],
            "event": event}


def test_slack_events_endpoint(client, auth_headers, app, monkeypatch):
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "sssh")
    client.post("/api/coworker", json={"mode": "demo"}, headers=auth_headers)
    from coworker.store import get_store

    with app.app_context():
        s = get_store()
        s.update_coworker(1, mode="live")
        s.execute("DELETE FROM cw_items WHERE user_id = 1")  # connecting for real drops the demo workspace
        s.upsert_connection(1, "slack", status="connected", account_label="Anote",
                            token_enc=encrypt_token({"access_token": "xoxp-1", "user_id": "U1", "team_id": "T1"}))

    def post(payload: dict[str, Any], headers: dict[str, str] | None = None) -> Any:
        body = json.dumps(payload).encode()
        return client.post("/api/coworker/slack/events", data=body, headers=headers or _signed(body))

    assert post({"type": "url_verification", "challenge": "abc"}).get_json() == {"challenge": "abc"}
    assert post({"type": "event_callback"}, headers={"Content-Type": "application/json"}).status_code == 401
    assert post({"type": "app_rate_limited"}).get_json() == {"ok": True}

    users = {"U2": {"real_name": "Dana Lee", "profile": {"email": "dana@anote.ai"}}}
    with patch("coworker.connectors.slack._call",
               side_effect=lambda method, tok, http="GET", **p: {"user": users.get(p.get("user"), {})}), \
            patch("api_endpoints.coworker.slack_events.react") as react:
        assert post(_event()).get_json()["stored"] == 1
        assert post(_event()).get_json()["stored"] == 0  # Slack retries are deduplicated
        assert post(_event(subtype="message_changed", ts="1760000001.0")).get_json()["stored"] == 0
        assert post(_event(text=f"{slack.AI_PREFIX}\nsure", ts="1760000002.0")).get_json()["stored"] == 0
        other = _event(ts="1760000003.0")
        other["authorizations"] = [{"user_id": "U9"}]
        assert post(other).get_json()["stored"] == 0  # not one of our users
    assert react.call_count == 1
    with app.app_context():
        item = get_store().items(1, provider="slack")[0]
    assert item["channel"] == "dm-dana" and item["meta"]["mentions_owner"] and item["author_email"] == "dana@anote.ai"

    channel_info = {"channel": {"name": "deals", "is_shared": True}}
    with patch("coworker.connectors.slack._call",
               side_effect=lambda method, tok, http="GET", **p: channel_info if method == "conversations.info" else {"user": {}}), \
            patch("api_endpoints.coworker.slack_events.react"):
        assert post(_event(channel="C5", channel_type="channel", text="<@U1> pricing?", ts="1760000004.0")).get_json()["stored"] == 1
    with app.app_context():
        deal = next(i for i in get_store().items(1, provider="slack") if i["channel"] == "deals")
    assert deal["meta"]["shared"] and deal["meta"]["mentions_owner"]


def test_slack_react_respects_pause(app):
    from api_endpoints.coworker.slack_events import react
    from coworker.store import get_store

    with app.app_context():
        s = get_store()
        s.create_coworker(1, "Natan", "natan@anote.ai", mode="live")
        with patch("coworker.responsibilities.run_all", return_value=["ok"]) as run_all, \
                patch("coworker.notify.maybe_notify_approvals"):
            assert react(s, 1) == ["ok"]
            s.update_coworker(1, status="paused")
            assert react(s, 1) == []
        assert run_all.call_count == 1


def test_slack_dm_name_fallbacks(store):
    conn = slack.SlackConnector(store, 1, {"access_token": "xoxp", "user_id": "U1"}, {})
    with patch("coworker.connectors.slack._call", side_effect=ConnectorError("x")):
        assert conn._dm_name(store, 1, "D7", "") == "dm-d7"
    with patch("coworker.connectors.slack._call",
               side_effect=lambda m, t, http="GET", **p: {"channel": {"user": "U3"}} if m == "conversations.info"
               else {"user": {"real_name": "Sam Park"}}):
        assert conn._dm_name(store, 1, "D8", "") == "dm-sam"
    assert conn.ingest_event(store, 1, {"type": "reaction_added"}) is None
