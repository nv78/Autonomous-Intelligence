"""Free mode: a local model when no API key is set, Telegram instead of SMS, and email via your own plus-address."""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest

from coworker import inbound_email as ie
from coworker import llm, memory, telegram
from coworker.connectors.demo import DemoConnector
from coworker.store import Store, iso, utcnow


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "COWORKER_MODEL", "OLLAMA_MODEL",
              "TELEGRAM_WEBHOOK_SECRET", "TELEGRAM_BOT_USERNAME"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("COWORKER_OFFLINE", "1")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("TELEGRAM_BOT_USERNAME", "OurogenBot")
    llm._ollama_seen.clear()
    with patch("services.provider_keys.get_user_provider_key", return_value=None), \
            patch("coworker.channels._history", return_value=[]), patch("coworker.channels._store_turn", return_value=70), \
            patch("coworker.notify.deliver", return_value="gmail") as mail:
        yield mail


@pytest.fixture
def s(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/free.db")
    store.create_coworker(1, "Natan Vidra", "natan@anote.ai", mode="demo")
    DemoConnector.seed(store, 1, "Natan Vidra", "natan@anote.ai")
    memory.rebuild(store, 1)
    return store


# -- local model ----------------------------------------------------------------------------------

def test_local_model_when_no_key(monkeypatch):
    assert llm.model_name() == "claude-opus-5-5"  # no Ollama: unchanged (offline planner)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434")
    with patch("coworker.llm.ollama_up", return_value=True):
        assert llm.model_name() == "llama3.1" and llm.api_key_for() == "ollama"
        monkeypatch.setenv("OLLAMA_MODEL", "gpt-oss:20b")
        assert llm.model_name() == "gpt-oss:20b" and llm.provider_of("gpt-oss:20b") == "ollama"
        assert llm.usable("claude-opus-5-5", None, ["claude-opus-5-5"]) == "claude-opus-5-5"  # org allows only Claude
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
        assert llm.model_name() == "claude-opus-5-5"  # a key switches back on its own
    with patch("coworker.llm.ollama_up", return_value=False):
        monkeypatch.delenv("ANTHROPIC_API_KEY")
        assert llm.model_name() == "claude-opus-5-5"


def test_explicit_model_falls_back_too(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434")
    with patch("coworker.llm.ollama_up", return_value=True), \
            patch("coworker.llm._openai_compatible", return_value={"content": [{"type": "text", "text": "hi"}]}) as call:
        assert llm.complete_text("x", model="claude-haiku-5-5") == "hi"
    assert call.call_args.args[:2] == ("ollama", "llama3.1")


def test_ollama_reachability_is_cached(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434/")

    class R:
        status_code = 200

    with patch("requests.get", return_value=R()) as get:
        assert llm.ollama_up() and llm.ollama_up()
    assert get.call_count == 1 and get.call_args.args[0] == "http://ollama:11434/api/tags"
    llm._ollama_seen.clear()
    with patch("requests.get", side_effect=OSError("refused")):
        assert not llm.ollama_up()
    monkeypatch.delenv("OLLAMA_BASE_URL")
    assert not llm.ollama_up()


# -- Telegram ---------------------------------------------------------------------------------------

class FakeTelegram:
    def __init__(self, updates=None):
        self.calls: list[tuple[str, dict]] = []
        self.updates = updates or []

    def __call__(self, method, **params):
        self.calls.append((method, params))
        if method == "getUpdates":
            out, self.updates = self.updates, []
            return out
        return {"message_id": 1}

    def sent(self):
        return [p for m, p in self.calls if m == "sendMessage"]


def _msg(text, chat=555, kind="private", update_id=None, sender=None):
    return {"update_id": update_id or abs(hash((text, chat))) % 10**9,
            "message": {"chat": {"id": chat, "type": kind}, "from": {"id": sender or chat, "username": "natan"}, "text": text}}


def _link(s, fake, chat=555):
    link = telegram.start_link(s, 1)["link"]
    assert link.startswith("https://t.me/OurogenBot?start=")
    assert telegram.handle_update(s, _msg(f"/start {link.rsplit('=', 1)[1]}", chat)) == "start"
    assert fake.sent()[-1]["text"].startswith("Linked!")


def test_telegram_link_talk_and_approve(s):
    fake = FakeTelegram()
    with patch("coworker.telegram._api", side_effect=fake):
        assert telegram.handle_update(s, _msg("hi", chat=999)) == "unlinked"
        _link(s, fake)
        assert telegram.state(s, 1)["linked"] and telegram.state(s, 1)["username"] == "natan"
        assert telegram.handle_update(s, _msg("hi", kind="group")) == "ignored"

        update = _msg("reply to my sales leads", update_id=42)
        assert telegram.handle_update(s, update) == "command"
        assert telegram.handle_update(s, update) == "duplicate"
        last = fake.sent()[-1]
        assert last["chat_id"] == "555" and last["reply_markup"]["inline_keyboard"]
        data = last["reply_markup"]["inline_keyboard"][0][0]["callback_data"]
        action_id = int(data.rsplit(":", 1)[1])

        stranger = {"callback_query": {"id": "q0", "data": data, "from": {"id": 999}, "message": {"chat": {"id": 555}}}}
        assert telegram.handle_update(s, stranger) == "refused button"
        press = {"callback_query": {"id": "q1", "data": data, "from": {"id": 555}, "message": {"chat": {"id": 555}}}}
        assert telegram.handle_update(s, press) == "button"
        assert s.get("cw_actions", action_id, 1)["status"] == "executed"
        assert telegram.handle_update(s, {"callback_query": {**press["callback_query"], "data": "cw:approve:999999"}}) == "refused button"

        assert telegram.handle_update(s, _msg("/help", update_id=43)) == "command" and "PAUSE" in fake.sent()[-1]["text"]
        assert telegram.handle_update(s, _msg("/start", update_id=48)) == "start" and "PAUSE" in fake.sent()[-1]["text"]
        telegram.handle_update(s, _msg("PAUSE", update_id=44))
        assert s.get_coworker(1)["status"] == "paused"
        telegram.handle_update(s, _msg("RESUME", update_id=45))
        assert s.get_coworker(1)["status"] == "active"
        telegram.handle_update(s, _msg("NO", update_id=46))
        assert fake.sent()[-1]["text"]
        assert telegram.handle_update(s, {"update_id": 47, "message": {"chat": {"id": 555, "type": "private"}}}) == "empty"


def test_telegram_link_rules(s):
    fake = FakeTelegram()
    with patch("coworker.telegram._api", side_effect=fake):
        telegram.handle_update(s, _msg("/start bogus"))
        assert "expired" in fake.sent()[-1]["text"]
        link = telegram.start_link(s, 1)["link"]
        s.execute("UPDATE cw_telegram SET link_expires = %s", (iso(utcnow() - timedelta(minutes=1)),))
        telegram.handle_update(s, _msg(f"/start {link.rsplit('=', 1)[1]}"))
        assert "expired" in fake.sent()[-1]["text"] and not telegram.state(s, 1)["linked"]

        s.create_coworker(2, "Eve", "eve@x.com", mode="demo")
        _link(s, fake, chat=555)
        other = telegram.start_link(s, 2)["link"]
        telegram.handle_update(s, _msg(f"/start {other.rsplit('=', 1)[1]}", chat=555))
        assert "another Ourogen coworker" in fake.sent()[-1]["text"]  # one chat, one coworker


def test_telegram_notifications_and_polling(s, monkeypatch):
    fake = FakeTelegram()
    with patch("coworker.telegram._api", side_effect=fake):
        assert not telegram.notify(s, 1, "hi")  # not linked
        _link(s, fake)
        pending = [{"id": 5, "title": "Email Dana", "status": "proposed"}]
        assert telegram.notify_approvals(s, 1, pending)
        assert fake.sent()[-1]["reply_markup"]["inline_keyboard"][0][0]["callback_data"] == "cw:approve:5"
        telegram.set_prefs(s, 1, [])
        assert not telegram.notify_approvals(s, 1, pending) and telegram.notify(s, 1, "Daily brief: ...", "tasks")
        assert len(telegram._clean("x" * 9000)) == 9000 and len(fake.sent()[-1]["text"]) < telegram.MAX_CHARS + 1

    fake = FakeTelegram([_msg("hi", update_id=900), _msg("hi", chat=1, update_id=901)])
    with patch("coworker.telegram._api", side_effect=fake):
        assert telegram.poll_once(s) == 2 and telegram._offset == 902
        monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "shh")
        assert telegram.poll_once(s) == 0  # webhook mode: Telegram pushes instead
    with pytest.raises(telegram.TelegramError):
        telegram.set_prefs(s, 3, [])


def test_telegram_routes(client, auth_headers, monkeypatch):
    fake = FakeTelegram()
    with patch("coworker.telegram._api", side_effect=fake):
        assert client.get("/api/coworker/telegram", headers=auth_headers).get_json()["configured"]
        got = client.post("/api/coworker/telegram", headers=auth_headers).get_json()
        assert got["link"].startswith("https://t.me/OurogenBot?start=") and not got["linked"]
        assert client.patch("/api/coworker/telegram", json={"notify": "x"}, headers=auth_headers).status_code == 400
        assert client.patch("/api/coworker/telegram", json={"notify": []}, headers=auth_headers).get_json()["notify"] == []
        assert client.delete("/api/coworker/telegram", headers=auth_headers).status_code == 200
        assert client.post("/api/coworker/telegram/webhook", json={}).status_code == 501  # polling mode
        monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "shh")
        assert client.post("/api/coworker/telegram/webhook", json={}).status_code == 401
        ok = client.post("/api/coworker/telegram/webhook", json=_msg("hi", chat=4242),
                         headers={"X-Telegram-Bot-Api-Secret-Token": "shh"})
        assert ok.status_code == 200 and fake.sent()[-1]["chat_id"] == "4242"
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN")
    assert client.post("/api/coworker/telegram", headers=auth_headers).status_code == 501


# -- email via your own plus-address ----------------------------------------------------------------

def _sent(s, to, sender="natan@gmail.com", direction="outbound", when=None, ext="m1", sent=True):
    s.add_item(1, {"provider": "gmail", "external_id": ext, "thread_id": ext, "kind": "email", "direction": direction,
                   "author_name": "Natan", "author_email": sender, "recipients": [{"name": "", "email": e} for e in to],
                   "subject": "Can you reply to my leads?", "body": "Please reply to my sales leads.",
                   "occurred_at": iso(when or utcnow()), "meta": {"message_id": f"<{ext}@x>", "sent": sent}})


def test_plus_address_mailbox(s, _env, monkeypatch):
    s.update_coworker(1, mode="live")
    assert ie.scan_mailbox(s, 1) == 0  # no mailbox connected
    s.upsert_connection(1, "google", status="connected", account_label="Natan@gmail.com")
    monkeypatch.setenv("COWORKER_PLUS_TAG", "AI!")
    assert ie.plus_addresses(s, 1) == ["natan+ai@gmail.com"]
    monkeypatch.delenv("COWORKER_PLUS_TAG")
    assert ie.plus_addresses(s, 1) == ["natan+coworker@gmail.com"]

    _sent(s, ["natan+coworker@gmail.com"])
    _sent(s, ["natan+coworker@gmail.com"], sender="eve@evil.com", direction="inbound", ext="m2")  # not the owner's Sent mail
    _sent(s, ["natan+coworker@gmail.com"], when=utcnow() - timedelta(days=3), ext="m3")  # too old
    _sent(s, ["dana@northwind.com"], ext="m4")  # not to the coworker
    _sent(s, ["natan+coworker@gmail.com"], ext="m6", sent=False)  # forged From: natan@gmail.com, never in Sent
    assert ie.scan_mailbox(s, 1) == 1
    assert _env.call_args.args[2] == "Re: Can you reply to my leads?"
    assert ie.scan_mailbox(s, 1) == 0  # each message once

    _sent(s, ["dana@northwind.com", "natan+coworker@gmail.com"], ext="m5")  # CC'd: drafts for Dana
    with patch("coworker.channels.ask", return_value={"text": "Drafted.", "summary": "", "actions": [], "chat_id": 70}) as ask:
        assert ie.scan_mailbox(s, 1) == 1
    assert "dana@northwind.com" in ask.call_args.args[2]


def test_sent_flag_comes_from_the_provider_not_the_from_header():
    from coworker.connectors import google, microsoft

    forged = {"id": "x", "labelIds": ["INBOX"], "payload": {"headers": [{"name": "From", "value": "natan@gmail.com"}]}}
    item = google.parse_message(forged, "natan@gmail.com")
    assert item["direction"] == "outbound" and item["meta"]["sent"] is False
    assert google.parse_message({**forged, "labelIds": ["SENT"]}, "natan@gmail.com")["meta"]["sent"] is True
    ms = {"id": "m", "from": {"emailAddress": {"address": "natan@contoso.com"}}, "parentFolderId": "inbox",
          "receivedDateTime": "2026-10-16T10:00:00Z"}
    assert microsoft.parse_message(ms, "natan@contoso.com", "sentitems")["meta"]["sent"] is False
    assert microsoft.parse_message({**ms, "parentFolderId": "sentitems"}, "natan@contoso.com", "sentitems")["meta"]["sent"] is True
