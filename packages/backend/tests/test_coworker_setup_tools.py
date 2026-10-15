"""Setup helpers: the Slack app manifest, Twilio webhook setup, and the new vendor checks."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from coworker import slack_manifest, slackbot, sms, vendor_check
from coworker.connectors import slack


def test_manifest_has_everything_and_matches_the_checked_in_file():
    m = slack_manifest.manifest("https://chat.ourogen.ai/")
    assert m["oauth_config"]["scopes"] == {"user": slack.USER_SCOPES, "bot": slackbot.BOT_SCOPES}
    assert m["oauth_config"]["redirect_urls"] == ["https://chat.ourogen.ai/api/coworker/connections/slack/callback"]
    assert m["settings"]["event_subscriptions"]["request_url"] == "https://chat.ourogen.ai/api/coworker/slack/events"
    assert set(m["settings"]["event_subscriptions"]["bot_events"]) == {"app_mention", "message.im"}
    assert m["settings"]["interactivity"]["request_url"].endswith("/api/coworker/slack/interactive")
    assert m["features"]["app_home"]["messages_tab_enabled"]
    checked_in = json.loads((Path(__file__).parent.parent / "deploy" / "slack-app-manifest.json").read_text())
    assert checked_in == m  # regenerate with: python -m coworker.slack_manifest https://chat.ourogen.ai


def _resp(status: int, body: dict) -> MagicMock:
    r = MagicMock(status_code=status, text=json.dumps(body))
    r.json.return_value = body
    return r


@pytest.fixture
def twilio_env(monkeypatch):
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC1")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "tok")
    monkeypatch.setenv("TWILIO_FROM_NUMBER", "+15550000000")
    monkeypatch.setenv("BACKEND_URL", "https://chat.ourogen.ai")


def test_configure_webhook_sets_it_once(twilio_env):
    number = {"sid": "PN1", "sms_url": "", "sms_method": "GET"}
    calls = []

    def request(method, url, auth, data, timeout):
        calls.append((method, url, data))
        if method == "POST":
            number.update(sms_url=data["SmsUrl"], sms_method=data["SmsMethod"])
            return _resp(200, number)
        return _resp(200, {"incoming_phone_numbers": [dict(number)]})

    with patch("coworker.sms.requests.request", side_effect=request):
        first = sms.configure_webhook()
        second = sms.configure_webhook()
    assert first["changed"] == "yes" and second["changed"].startswith("no")
    assert calls[0][1].endswith("/IncomingPhoneNumbers.json?PhoneNumber=%2B15550000000")
    assert calls[1] == ("POST", "https://api.twilio.com/2010-04-01/Accounts/AC1/IncomingPhoneNumbers/PN1.json",
                        {"SmsUrl": "https://chat.ourogen.ai/api/coworker/sms/inbound", "SmsMethod": "POST"})
    assert [c[0] for c in calls].count("POST") == 1

    with patch("coworker.sms.requests.request", return_value=_resp(401, {})):
        with pytest.raises(sms.SmsError, match="rejected"):
            sms.number_settings()
    with patch("coworker.sms.requests.request", return_value=_resp(200, {"incoming_phone_numbers": []})):
        with pytest.raises(sms.SmsError, match="isn't a number"):
            sms.configure_webhook()


def test_configure_webhook_needs_https_and_config(twilio_env, monkeypatch):
    monkeypatch.setenv("BACKEND_URL", "http://localhost:5000")
    with pytest.raises(sms.SmsError, match="public https"):
        sms.configure_webhook()
    monkeypatch.delenv("TWILIO_AUTH_TOKEN")
    with pytest.raises(sms.SmsError, match="Set TWILIO"):
        sms.number_settings()


def test_vendor_checks_for_twilio_slack_bot_and_worker(twilio_env, monkeypatch, tmp_path):
    good = {"incoming_phone_numbers": [{"sid": "PN1", "sms_url": "https://chat.ourogen.ai/api/coworker/sms/inbound"}]}
    with patch("coworker.sms.requests.request", return_value=_resp(200, good)):
        assert vendor_check.check_twilio()["status"] == "ok"
    wrong = {"incoming_phone_numbers": [{"sid": "PN1", "sms_url": "https://old.example.com/sms"}]}
    with patch("coworker.sms.requests.request", return_value=_resp(200, wrong)):
        assert "coworker.sms setup" in vendor_check.check_twilio()["detail"]
    for key in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER"):
        monkeypatch.delenv(key)
    assert vendor_check.check_twilio()["status"] == "skipped"

    monkeypatch.setenv("SLACK_CLIENT_ID", "c")
    monkeypatch.setenv("SLACK_CLIENT_SECRET", "s")
    monkeypatch.setenv("SLACK_BOT_ENABLED", "1")
    monkeypatch.delenv("SLACK_SIGNING_SECRET", raising=False)
    assert vendor_check.check_slack()["status"] == "fail"
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "x")
    assert "bot on" in vendor_check.check_slack()["detail"]

    from coworker import ops
    from coworker.store import Store

    s = Store(f"sqlite:///{tmp_path}/w.db")
    with patch("coworker.store.get_store", return_value=s):
        assert vendor_check.check_worker()["status"] == "fail"
        ops.heartbeat(s, 5, 1, 0)
        assert vendor_check.check_worker()["status"] == "ok"
    with patch("coworker.store.get_store", side_effect=RuntimeError("no db")):
        assert vendor_check.check_worker()["status"] == "skipped"
