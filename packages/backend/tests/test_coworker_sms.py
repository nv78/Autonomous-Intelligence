"""Text your coworker: linking a phone, signed inbound texts, chat by text, approvals by text, notifications."""
from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import datetime
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from coworker import executor, memory, notify, sms
from coworker.connectors.demo import DemoConnector
from coworker.store import Store

UTC = ZoneInfo("UTC")
NOON_NY = datetime(2026, 1, 5, 17, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC1")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "tok")
    monkeypatch.setenv("TWILIO_FROM_NUMBER", "+15550000000")
    monkeypatch.setenv("COWORKER_OFFLINE", "1")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with patch("services.provider_keys.get_user_provider_key", return_value=None), \
            patch("coworker.channels._history", return_value=[]), \
            patch("coworker.channels._store_turn", return_value=80), \
            patch("coworker.sms.utcnow", return_value=NOON_NY):
        yield


@pytest.fixture
def texts():
    sent: list[dict] = []

    def post(url, timeout, auth, data):
        sent.append(data)
        r = MagicMock(status_code=201)
        r.json.return_value = {"sid": f"SM{len(sent)}"}
        return r

    with patch("coworker.sms.requests.post", side_effect=post):
        yield sent


@pytest.fixture
def s(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/sms.db")
    store.create_coworker(1, "Natan Vidra", "natan@anote.ai", mode="demo")
    store.update_coworker(1, settings={"timezone": "America/New_York"})
    DemoConnector.seed(store, 1, "Natan Vidra", "natan@anote.ai")
    memory.rebuild(store, 1)
    return store


def _code(texts) -> str:
    return texts[-1]["Body"].split("code is ")[1][:6]


def _linked(s: Store, texts) -> None:
    sms.start(s, 1, "(555) 123-4567")
    sms.verify(s, 1, _code(texts))


def test_normalize_and_split():
    assert sms.normalize("(555) 123-4567") == "+15551234567"
    assert sms.normalize("whatsapp:+44 20 7946 0958") == "+442079460958"
    with pytest.raises(sms.SmsError):
        sms.normalize("123")
    parts = sms.split("**Hi**\n" + "word " * 1000)
    assert len(parts) == 3 and parts[0].startswith("Hi") and all(len(p) <= sms.SEGMENT for p in parts)
    assert parts[-1].endswith("(more in the Ourogen app)")
    assert sms.mask("+15551234567") == "+1••••••4567"


def test_link_verify_and_guardrails(s, texts):
    state = sms.start(s, 1, "555-123-4567")
    assert state["number"] == "+15551234567" and not state["verified"]
    assert texts[-1]["To"] == "+15551234567" and texts[-1]["From"] == "+15550000000"
    with pytest.raises(sms.SmsError, match="isn't right"):
        sms.verify(s, 1, "000000" if _code(texts) != "000000" else "111111")
    state = sms.verify(s, 1, _code(texts))
    assert state["verified"] and state["notify"] == ["approvals"]
    assert "You're set" in texts[-1]["Body"]

    s.create_coworker(2, "Other", "o@x.com", mode="demo")
    with pytest.raises(sms.SmsError) as exc:
        sms.start(s, 2, "+15551234567")
    assert exc.value.status == 409
    assert sms.set_prefs(s, 1, ["approvals", "spam"])["notify"] == ["approvals"]


def test_code_limits(s, texts):
    for _ in range(sms.MAX_CODE_SENDS_PER_HOUR):
        sms.start(s, 1, "+15551234567")
    with pytest.raises(sms.SmsError) as exc:
        sms.start(s, 1, "+15551234567")
    assert exc.value.code == "rate_limited"
    for _ in range(sms.MAX_ATTEMPTS):
        with pytest.raises(sms.SmsError):
            sms.verify(s, 1, "abc")
    with pytest.raises(sms.SmsError, match="Too many wrong codes"):
        sms.verify(s, 1, _code(texts))
    with patch("coworker.sms.utcnow", return_value=datetime(2026, 1, 5, 18, 0, tzinfo=UTC)):
        with pytest.raises(sms.SmsError) as expired:
            sms.verify(s, 2, "123456")
    assert expired.value.status == 404


def test_texting_the_coworker(s, texts):
    assert "isn't linked" in sms.handle_inbound(s, "+15551234567", "hi")
    _linked(s, texts)
    reply = sms.handle_inbound(s, "+15551234567", "reply to my sales leads")
    pending = s.query("SELECT id FROM cw_actions WHERE status = 'proposed' ORDER BY id")
    assert pending and f"Reply YES {pending[0]['id']} to approve." in reply
    assert s.one("SELECT chat_id FROM cw_channel_threads WHERE channel = 'sms'")["chat_id"] == 80

    second = executor.propose(s, 1, "email.send", {"to": ["dana@northwind.com"], "subject": "Re: times", "body": "Draft"},
                              title="Reply to Dana", requested_in_chat=True)["id"]
    assert "Reply with the number" in sms.handle_inbound(s, "+15551234567", "yes")
    first = pending[0]["id"]
    assert sms.handle_inbound(s, "+15551234567", f"YES {first}").startswith(f"Sent #{first}")
    assert s.get("cw_actions", first, 1)["status"] == "executed"
    assert "Couldn't do" in sms.handle_inbound(s, "+15551234567", f"no {first}")
    assert sms.handle_inbound(s, "+15551234567", f"EDIT {second} Thanks! Tuesday at 2 works.").startswith(f"Sent #{second}")
    assert s.get("cw_actions", second, 1)["payload"]["body"].startswith("Thanks! Tuesday at 2 works.")
    third = executor.propose(s, 1, "slack.post", {"channel": "general", "text": "hi"}, title="Say hi", requested_in_chat=True)["id"]
    assert sms.handle_inbound(s, "+15551234567", f"skip #{third}") == f"Skipped #{third}: Say hi"
    s.execute("UPDATE cw_actions SET status = 'rejected' WHERE status = 'proposed'")
    assert sms.handle_inbound(s, "+15551234567", "yes") == "Nothing is waiting for your approval."

    assert sms.handle_inbound(s, "+15551234567", "help") == sms.HELP
    assert "Paused" in sms.handle_inbound(s, "+15551234567", "PAUSE")
    assert s.get_coworker(1)["status"] == "paused"
    assert "Back on" in sms.handle_inbound(s, "+15551234567", "resume")
    assert sms.handle_inbound(s, "+15551234567", "STOP") == ""
    assert sms.state(s, 1)["optedOut"] and not sms.notify(s, 1, "x", "approvals")
    assert "again" in sms.handle_inbound(s, "+15551234567", "start")
    assert sms.handle_inbound(s, "junk", "hi") == ""


def test_notifications_respect_prefs_and_quiet_hours(s, texts):
    _linked(s, texts)
    sms.set_prefs(s, 1, [])
    assert sms.notify(s, 1, "task done", "tasks") and texts[-1]["Body"] == "task done"  # the task asked for a text
    assert not sms.notify(s, 1, "approve?", "approvals")  # approval texts turned off
    sms.set_prefs(s, 1, ["approvals"])
    with patch("coworker.sms.utcnow", return_value=datetime(2026, 1, 6, 3, 0, tzinfo=UTC)):  # 10pm in New York
        assert not sms.notify(s, 1, "late", "tasks")

    action = executor.propose(s, 1, "email.send", {"to": ["dana@northwind.com"], "subject": "Hi", "body": "Hello"},
                              title="Email Dana", requested_in_chat=True)
    s.update("cw_actions", action["id"], 1, {"created_at": "2026-01-05T16:00:00Z"})
    with patch("coworker.notify.utcnow", return_value=NOON_NY), patch("coworker.notify.deliver", return_value="smtp"):
        assert notify.maybe_notify_approvals(s, 1) >= 1
    assert texts[-1]["Body"].startswith("Ourogen needs your OK:") and f"YES {action['id']}" in texts[-1]["Body"]


def _sign(url: str, params: dict[str, str]) -> str:
    data = url + "".join(f"{k}{params[k]}" for k in sorted(params))
    return base64.b64encode(hmac.new(b"tok", data.encode(), hashlib.sha1).digest()).decode()


def test_signature_and_endpoints(client, auth_headers, app, texts, monkeypatch):
    monkeypatch.setenv("BACKEND_URL", "https://api.example.com")
    url = "https://api.example.com/api/coworker/sms/inbound"
    params = {"From": "+15551234567", "Body": "help", "To": "+15550000000"}
    assert sms.valid_signature(params, _sign(url, params))
    assert not sms.valid_signature({**params, "Body": "x"}, _sign(url, params))
    assert client.post("/api/coworker/sms/inbound", data=params).status_code == 401

    with patch("api_endpoints.coworker.common.owner_profile", return_value=("Natan Vidra", "natan@example.com")), \
            patch("api_endpoints.coworker.core.owner_profile", return_value=("Natan Vidra", "natan@example.com")):
        client.post("/api/coworker", json={"mode": "demo"}, headers=auth_headers)
    assert client.get("/api/coworker/phone", headers=auth_headers).get_json()["configured"]
    assert client.post("/api/coworker/phone", json={"number": "1"}, headers=auth_headers).status_code == 400
    assert client.post("/api/coworker/phone", json={"number": "+1 555 123 4567"}, headers=auth_headers).status_code == 200
    bad = client.post("/api/coworker/phone/verify", json={"code": "nope"}, headers=auth_headers)
    assert bad.status_code == 400
    ok = client.post("/api/coworker/phone/verify", json={"code": _code(texts)}, headers=auth_headers)
    assert ok.get_json()["verified"]
    assert client.patch("/api/coworker/phone", json={"notify": "x"}, headers=auth_headers).status_code == 400
    assert client.patch("/api/coworker/phone", json={"notify": ["approvals"]}, headers=auth_headers).get_json()["notify"] == ["approvals"]

    resp = client.post("/api/coworker/sms/inbound", data=params, headers={"X-Twilio-Signature": _sign(url, params)})
    assert resp.status_code == 200 and resp.mimetype == "text/xml"
    assert texts[-1]["Body"] == sms.HELP and texts[-1]["To"] == "+15551234567"
    wa = {**params, "From": "whatsapp:+15551234567"}
    monkeypatch.setenv("TWILIO_WHATSAPP_FROM", "+15559999999")
    client.post("/api/coworker/sms/inbound", data=wa, headers={"X-Twilio-Signature": _sign(url, wa)})
    assert texts[-1]["From"] == "whatsapp:+15559999999" and texts[-1]["To"] == "whatsapp:+15551234567"

    assert client.delete("/api/coworker/phone", headers=auth_headers).get_json()["number"] == ""
