"""Teams and Google Chat bots: request verification, owner commands, buttons, teammates, routing, endpoints."""
from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from coworker import chatbots, identity, memory
from coworker.connectors import gchat, teams
from coworker.connectors.demo import DemoConnector
from coworker.store import Store

SERVICE = "https://smba.trafficmanager.net/amer/"


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("MICROSOFT_BOT_APP_ID", "bot-app")
    monkeypatch.setenv("MICROSOFT_BOT_APP_PASSWORD", "pw")
    monkeypatch.setenv("GOOGLE_CHAT_AUDIENCE", "1234")
    monkeypatch.setenv("COWORKER_OFFLINE", "1")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with patch("services.provider_keys.get_user_provider_key", return_value=None), \
            patch("coworker.channels._history", return_value=[]), patch("coworker.channels._store_turn", return_value=60), \
            patch("coworker.notify.deliver", return_value="smtp") as mail:
        yield mail


@pytest.fixture
def s(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/bots.db")
    store.create_coworker(1, "Natan Vidra", "natan@anote.ai", mode="demo")
    DemoConnector.seed(store, 1, "Natan Vidra", "natan@anote.ai")
    memory.rebuild(store, 1)
    identity.record(store, 1, "microsoft", "aad-natan", "natan@anote.ai", "anote.ai", "t1")
    identity.record(store, 1, "google", "sub-natan", "natan@anote.ai", "anote.ai")
    return store


# -- Teams --------------------------------------------------------------------------------------

def test_teams_token_verification():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = int(time.time())

    def token(**over):
        claims = {"iss": teams.ISSUER, "aud": "bot-app", "exp": now + 600, "nbf": now - 10, "serviceurl": SERVICE, **over}
        return "Bearer " + jwt.encode(claims, key, algorithm="RS256")

    fake = SimpleNamespace(get_signing_key_from_jwt=lambda t: SimpleNamespace(key=key.public_key()))
    with patch("coworker.connectors.teams._jwks_client", return_value=fake):
        assert teams.verify(token(), SERVICE)["aud"] == "bot-app"
        for bad in (token(aud="someone-else"), token(iss="https://evil"), token(exp=now - 1000), "nope"):
            with pytest.raises(teams.TeamsError):
                teams.verify(bad, SERVICE)
        with pytest.raises(teams.TeamsError, match="serviceUrl"):
            teams.verify(token(), "https://evil.example.com/")


class FakeBF:
    def __init__(self, emails: dict[str, str]):
        self.emails = emails
        self.posts: list[tuple[str, dict]] = []

    def __call__(self, method, service_url, path, body=None):
        if method == "GET":
            return {"email": self.emails.get(path.rsplit("/", 1)[-1], "")}
        self.posts.append((path, body))
        return {}


def _act(text="", user="29:natan", conv="a:dm1", kind="personal", **extra):
    return {"type": "message", "id": f"m{time.time_ns()}", "serviceUrl": SERVICE, "text": text,
            "from": {"id": user, "name": "Natan" if user == "29:natan" else "Dana", "aadObjectId": f"aad-{user[3:]}"},
            "conversation": {"id": conv, "conversationType": kind, "tenantId": "t1"}, **extra}


def test_teams_owner_command_buttons_and_teammates(s, _env):
    bf = FakeBF({"29:natan": "natan@anote.ai", "29:dana": "dana@anote.ai"})
    with patch("coworker.connectors.teams._api", side_effect=bf):
        assert teams.handle(s, _act("<at>Ourogen</at> reply to my sales leads")) == "command"
        path, body = bf.posts[-1]
        assert path.startswith("/conversations/a:dm1/activities/") and body["attachments"]
        card = body["attachments"][0]["content"]
        action_id = card["actions"][0]["data"]["id"]
        assert card["actions"][0]["data"]["cw"] == "approve"

        dup = _act("hi")
        assert teams.handle(s, dup) == "command" and teams.handle(s, dup) == "duplicate"

        press = _act(value={"cw": "approve", "id": action_id})
        assert teams.handle(s, press) == "button" and bf.posts[-1][1]["text"].startswith("✅")
        assert s.get("cw_actions", action_id, 1)["status"] == "executed"
        stranger = _act(user="29:dana", value={"cw": "reject", "id": action_id})
        assert teams.handle(s, stranger) == "refused button"

        with patch("coworker.drafting.slack_answer", return_value={"text": "Pilot is $5k.", "confident": True}):
            assert teams.handle(s, _act("<at>Ourogen</at> pilot price?", user="29:dana", conv="19:team", kind="channel")) == "teammate"
        assert "I'll check with Natan" in bf.posts[-2][1]["text"]
        assert bf.posts[-1][0] == "/conversations/a:dm1/activities" and "Suggested answer: Pilot is $5k." in bf.posts[-1][1]["text"]

        s.update_coworker(1, autonomy={"slack.post": "notify"})
        with patch("coworker.drafting.slack_answer", return_value={"text": "Pilot is $5k.", "confident": True}):
            teams.handle(s, _act("price?", user="29:dana", conv="19:team", kind="channel"))
        assert bf.posts[-1][1]["text"].startswith("Pilot is $5k.")

        other = FakeBF({"29:x": "x@other.com"})
    with patch("coworker.connectors.teams._api", side_effect=other):
        unlinked = _act("hi", user="29:x")
        unlinked["conversation"]["tenantId"] = "t9"
        assert teams.handle(s, unlinked) == "unlinked"
        assert teams.handle(s, {"type": "conversationUpdate"}) == "ignored"


def test_teams_escalation_falls_back_to_email(s, _env):
    bf = FakeBF({"29:natan": "natan@anote.ai", "29:dana": "dana@anote.ai"})
    with patch("coworker.connectors.teams._api", side_effect=bf):
        teams.handle(s, _act("hi", conv="19:team", kind="channel"))  # owner seen only in a channel: no DM stored
        with patch("coworker.drafting.slack_answer", return_value={"text": "?", "confident": False}):
            teams.handle(s, _act("churn?", user="29:dana", conv="19:team", kind="channel"))
    assert _env.call_args.args[2] == "A teammate asked your coworker on Teams"
    assert "I don't know this one" in _env.call_args.args[3]


def test_teams_bot_token_and_manifest():
    class R:
        status_code = 200
        content = b"1"

        def json(self):
            return {"access_token": "tok", "expires_in": 3600}

    teams._token.clear()
    with patch("coworker.connectors.teams.requests.post", return_value=R()) as post:
        assert teams._bot_token() == "tok" and teams._bot_token() == "tok"
    assert post.call_count == 1 and "botframework.com/oauth2" in post.call_args.args[0]
    m = teams.manifest("https://chat.ourogen.ai", "bot-app")
    assert m["bots"][0]["botId"] == "bot-app" and m["validDomains"] == ["chat.ourogen.ai"]


# -- Google Chat ----------------------------------------------------------------------------------

def _ev(text="", email="natan@anote.ai", kind="MESSAGE", space="DM", **extra):
    return {"type": kind, "user": {"name": f"users/{email}", "email": email, "displayName": email.split("@")[0]},
            "space": {"name": "spaces/AAA", "type": space}, "message": {
                "name": f"spaces/AAA/messages/{time.time_ns()}", "text": text, "argumentText": text,
                "thread": {"name": "spaces/AAA/threads/T1"}}, **extra}


def test_gchat_verification():
    with patch("google.oauth2.id_token.verify_token", return_value={"iss": gchat.CHAT_ISSUER, "aud": "1234"}) as v:
        assert gchat.verify("Bearer abc")["aud"] == "1234"
    assert v.call_args.kwargs["audience"] == "1234" and v.call_args.kwargs["certs_url"] == gchat.CHAT_CERTS
    with patch("google.oauth2.id_token.verify_token", return_value={"iss": "someone@else"}):
        with pytest.raises(gchat.GChatError, match="issuer"):
            gchat.verify("Bearer abc")
    with patch("google.oauth2.id_token.verify_token", side_effect=ValueError("bad")):
        with pytest.raises(gchat.GChatError):
            gchat.verify("Bearer abc")
    with pytest.raises(gchat.GChatError):
        gchat.verify("")


def test_gchat_owner_buttons_and_teammates(s, _env):
    out = gchat.handle(s, _ev("reply to my sales leads"))
    assert out["thread"]["name"] == "spaces/AAA/threads/T1" and out["cardsV2"]
    button = out["cardsV2"][0]["card"]["sections"][0]["widgets"][1]["buttonList"]["buttons"][1]
    action_id = int(button["onClick"]["action"]["parameters"][0]["value"])
    skipped = gchat.handle(s, _ev(kind="CARD_CLICKED", common={"invokedFunction": "cw_reject", "parameters": {"id": str(action_id)}}))
    assert skipped["actionResponse"]["type"] == "UPDATE_MESSAGE" and skipped["text"].startswith("Skipped")
    stranger = gchat.handle(s, _ev(kind="CARD_CLICKED", email="eve@anote.ai",
                                   action={"actionMethodName": "cw_approve", "parameters": [{"key": "id", "value": str(action_id)}]}))
    assert stranger["text"].startswith("Only the person")

    with patch("coworker.drafting.slack_answer", return_value={"text": "Renewal is March 1.", "confident": True}):
        asked = gchat.handle(s, _ev("when is Acme's renewal?", email="dana@anote.ai", space="ROOM"))
    assert "I'll check with Natan" in asked["text"] and _env.call_args.args[2].endswith("on Google Chat")
    assert gchat.handle(s, _ev("hi", email="x@other.com", space="ROOM"))["text"].startswith("I'm an Ourogen AI coworker")
    assert "@mention me" in gchat.handle(s, _ev(kind="ADDED_TO_SPACE"))["text"]
    assert gchat.handle(s, _ev("", kind="MESSAGE"))["text"].startswith("Ask me")
    assert gchat.handle(s, _ev(kind="REMOVED_FROM_SPACE")) == {}

    with patch("coworker.chatbots.command", side_effect=lambda *a: time.sleep(0.3) or {"text": "late", "actions": []}), \
            patch("coworker.connectors.gchat.SYNC_SECONDS", 0.05):
        assert "taking a moment" in gchat.handle(s, _ev("slow one"))["text"]


def test_owner_lookup_and_endpoints(s, client, monkeypatch):
    assert chatbots.owner_for_teams(s, "aad-natan", "t1") == 1
    assert chatbots.owner_for_teams(s, "aad-natan", "other-tenant") is None  # same object id, wrong tenant
    assert chatbots.owner_for_teams(s, "", "t1") is None
    assert chatbots.owner_for_google(s, "NATAN@anote.ai") == 1
    s.create_coworker(9, "Mallory", "natan@anote.ai", mode="demo")  # claiming the address proves nothing
    assert chatbots.owner_for_google(s, "natan@anote.ai") == 1 and chatbots.owner_for_google(s, "") is None

    assert client.post("/api/coworker/teams/messages", json={}).status_code == 401
    assert client.post("/api/coworker/gchat/events", json={}).status_code == 401
    with patch("coworker.connectors.teams.verify"), patch("coworker.connectors.teams.handle", return_value="ignored") as h:
        assert client.post("/api/coworker/teams/messages", json={"type": "typing"}).status_code == 202
    assert h.called
    with patch("coworker.connectors.gchat.verify"), patch("coworker.connectors.gchat.handle", return_value={"text": "hi"}):
        assert client.post("/api/coworker/gchat/events", json={"type": "MESSAGE"}).get_json() == {"text": "hi"}
    monkeypatch.delenv("MICROSOFT_BOT_APP_ID")
    monkeypatch.delenv("GOOGLE_CHAT_AUDIENCE")
    assert client.post("/api/coworker/teams/messages", json={}).status_code == 501
    assert client.post("/api/coworker/gchat/events", json={}).status_code == 501
