"""Mobile push notifications."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from coworker import executor, push
from coworker.store import Store

TOKEN = "ExponentPushToken[abc123]"


@pytest.fixture
def s(tmp_path, monkeypatch):
    monkeypatch.delenv("COWORKER_PUSH", raising=False)
    monkeypatch.delenv("EXPO_ACCESS_TOKEN", raising=False)
    store = Store(f"sqlite:///{tmp_path}/push.db")
    store.create_coworker(1, "Natan Vidra", "natan@anote.ai", mode="demo")
    return store


def _ok(n: int = 1, errors: list | None = None) -> MagicMock:
    r = MagicMock()
    r.json.return_value = {"data": errors or [{"status": "ok"}] * n}
    return r


def test_register_and_unregister(s):
    with pytest.raises(ValueError):
        push.register(s, 1, "not-a-token")
    for i in range(7):
        push.register(s, 1, f"ExponentPushToken[t{i}]")
    push.register(s, 1, "ExponentPushToken[t3]")  # re-registering moves it to the end, no duplicate
    assert len(push.tokens(s, 1)) == push.MAX_TOKENS and push.tokens(s, 1)[-1] == "ExponentPushToken[t3]"
    push.unregister(s, 1, "ExponentPushToken[t3]")
    assert "ExponentPushToken[t3]" not in push.tokens(s, 1)


def test_send_and_drop_dead_tokens(s, monkeypatch):
    assert push.send(s, 1, "t", "b") == 0  # no devices
    push.register(s, 1, TOKEN)
    push.register(s, 1, "ExpoPushToken[dead]")
    monkeypatch.setenv("EXPO_ACCESS_TOKEN", "x")
    with patch("requests.post", return_value=_ok(errors=[{"status": "ok"}, {"status": "error",
                                                         "details": {"error": "DeviceNotRegistered"}}])) as post:
        assert push.send(s, 1, "Title", "Body", {"type": "today"}, category="approval") == 1
    msg = post.call_args.kwargs["json"][0]
    assert msg["categoryId"] == "approval" and msg["data"] == {"type": "today"}
    assert post.call_args.kwargs["headers"]["Authorization"] == "Bearer x"
    assert push.tokens(s, 1) == [TOKEN]
    with patch("requests.post", side_effect=requests.ConnectionError()):
        assert push.send(s, 1, "t", "b") == 0
    monkeypatch.setenv("COWORKER_PUSH", "0")
    assert push.send(s, 1, "t", "b") == 0


def test_new_proposal_pushes_with_approve_buttons_coalesced(s):
    push.register(s, 1, TOKEN)
    with patch("requests.post", return_value=_ok()) as post:
        a = executor.propose(s, 1, "email.send", {"to": ["d@x.com"], "subject": "Re", "body": "Hi Dana"}, title="Reply to Dana")
        executor.propose(s, 1, "email.send", {"to": ["e@x.com"], "subject": "Re", "body": "Hi"}, title="Reply to Eve")
        executor.propose(s, 1, "email.send", {"to": ["f@x.com"], "subject": "Re", "body": "Hi"}, title="From chat",
                         requested_in_chat=True)
    assert post.call_count == 1  # one push per minute, and none for actions asked for in chat
    msg = post.call_args.kwargs["json"][0]
    assert msg["data"] == {"type": "approval", "actionId": a["id"]} and msg["categoryId"] == "approval"


def test_push_routes(client, auth_headers):
    with patch("api_endpoints.coworker.core.owner_profile", return_value=("Natan Vidra", "natan@anote.ai")):
        client.post("/api/coworker", json={"mode": "demo"}, headers=auth_headers)
    assert client.post("/api/coworker/push/register", json={"token": "x"}, headers=auth_headers).status_code == 400
    assert client.post("/api/coworker/push/register", json={"token": TOKEN}, headers=auth_headers).get_json() == {"devices": 1}
    assert client.post("/api/coworker/push/unregister", json={"token": TOKEN}, headers=auth_headers).status_code == 200
