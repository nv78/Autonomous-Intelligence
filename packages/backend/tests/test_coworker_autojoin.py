"""Auto-join: brief before, join at start, skip, notes from the meeting's chat, the Today view."""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest

from coworker import autojoin, brain, delegate, responsibilities, tools
from coworker.store import Store, iso, utcnow


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("COWORKER_OFFLINE", "1")
    monkeypatch.setenv("RECALL_API_KEY", "rk")
    with patch("services.provider_keys.get_user_provider_key", return_value=None):
        yield


@pytest.fixture
def s(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/aj.db")
    store.create_coworker(1, "Natan Vidra", "natan@anote.ai", mode="live")
    return store


@pytest.fixture
def chats():
    """new_chat / post / chat notes without MySQL."""
    with patch("coworker.reports.new_chat", return_value=41) as new_chat, \
            patch("coworker.reports.post", return_value=True) as post, \
            patch("coworker.push.send", return_value=1) as push, \
            patch("coworker.notify.deliver", return_value="smtp") as deliver:
        yield {"new_chat": new_chat, "post": post, "push": push, "deliver": deliver}


def _event(store: Store, ext: str, minutes: int, subject: str = "Northwind intro", url: str = "https://zoom.us/j/123",
           guests: list[dict] | None = None) -> None:
    store.add_item(1, {
        "provider": "gcal", "external_id": ext, "thread_id": f"event-{ext}", "kind": "event", "subject": subject,
        "occurred_at": iso(utcnow() + timedelta(minutes=minutes)), "body": url,
        "recipients": guests if guests is not None else [{"name": "Dana Lee", "email": "dana@northwind.com"}],
        "meta": {"location": url},
    })


def _resp(store: Store, **trigger) -> dict:
    spec = responsibilities.proposal_payload("Join all my external intro calls from now on")
    spec["trigger"].update(trigger)
    return responsibilities.create(store, 1, spec)


def test_chat_request_becomes_a_standing_auto_join(s):
    assert responsibilities.match_template("From now on, join every external call for me") == "auto_join"
    assert responsibilities.match_template("take all my intro calls") == "auto_join"
    assert responsibilities.match_template("Join my 2pm with Dana") != "auto_join"  # one meeting, not a rule
    spec = responsibilities.proposal_payload("Join all my external intro and demo calls")
    assert spec["template"] == "auto_join" and spec["trigger"]["keywords"] == ["intro", "demo"]
    assert spec["trigger"]["external_only"] is True
    ctx = tools.ToolContext(store=s, user_id=1, chat_id=9)
    text = "".join(p for k, p in brain._offline_turn(ctx, "Join all my external calls from now on") if k == "text")
    assert "Skip" in text and "Join my external meetings" in text


def test_brief_then_join_then_report(s, chats):
    resp = _resp(s, keywords=[])
    _event(s, "e1", 20)
    _event(s, "internal", 15, subject="Team sync", guests=[{"name": "Sam", "email": "sam@anote.ai"}])
    _event(s, "nolink", 15, subject="Lunch", url="")
    _event(s, "later", 120, subject="Globex QBR")

    out = responsibilities.run_one(s, 1, resp)
    assert out == ["Prepared a brief for Northwind intro and scheduled to join"]
    assert chats["new_chat"].call_args.args[1] == "📞 Northwind intro"
    assert "Skip this one" in chats["new_chat"].call_args.args[2]
    assert chats["push"].call_args.args[2].startswith("Joining Northwind intro")
    assert "/api/coworker/autojoin/skip/" in chats["deliver"].call_args.args[3]
    assert responsibilities.run_one(s, 1, resp) == []  # nothing twice
    assert autojoin.pending_for_chat(s, 1, 41) == {"event_id": "e1", "responsibility_id": resp["id"]}

    # It starts in a minute: the bot joins with the user's notes from the meeting's chat.
    s.execute("UPDATE cw_items SET occurred_at = %s WHERE external_id = 'e1'", (iso(utcnow() + timedelta(minutes=1)),))
    with patch("coworker.autojoin._chat_context", return_value="Notes from the user for this call: push for a pilot"), \
            patch("coworker.connectors.recall.create_bot", return_value="bot-9") as create_bot:
        out = responsibilities.run_one(s, 1, resp)
    assert out == ["Joined Northwind intro"]
    assert create_bot.call_args.args[0] == "https://zoom.us/j/123"
    meeting = s.query("SELECT * FROM cw_meetings WHERE user_id = 1")[0]
    assert meeting["bot_id"] == "bot-9" and meeting["answers"]["chat_id"] == 41
    assert "push for a pilot" in meeting["answers"]["context"]
    assert "Joining now" in chats["post"].call_args.args[2]
    assert autojoin.pending_for_chat(s, 1, 41) is None  # an ordinary chat again
    assert autojoin.state(s, 1, "e1") == "joined"
    with patch("coworker.connectors.recall.create_bot") as again:
        responsibilities.run_one(s, 1, resp)
    again.assert_not_called()


def test_skip_from_chat_link_and_api(s, chats, client, auth_headers, app):
    resp = _resp(s)
    _event(s, "e2", 25)
    responsibilities.run_one(s, 1, resp)
    events = list(autojoin.chat_turn(s, 1, autojoin.pending_for_chat(s, 1, 41), "Make sure to ask about budget"))
    assert "bring that into the call" in events[0][1]
    events = list(autojoin.chat_turn(s, 1, autojoin.pending_for_chat(s, 1, 41), "Actually skip it, I'll take this one"))
    assert "won't join" in events[0][1]
    assert autojoin.state(s, 1, "e2") == "skipped" and autojoin.skip(s, 1, "e2")  # skipping twice is fine
    s.execute("UPDATE cw_items SET occurred_at = %s WHERE external_id = 'e2'", (iso(utcnow()),))
    with patch("coworker.connectors.recall.create_bot") as create_bot:
        responsibilities.run_one(s, 1, resp)
    create_bot.assert_not_called()

    # The signed link from the email, against the app's store.
    from coworker.store import get_store

    with app.app_context():
        store = get_store()
        store.create_coworker(1, "Natan Vidra", "natan@anote.ai", mode="live")
        resp2 = _resp(store)
        _event(store, "e3", 20)
        responsibilities.run_one(store, 1, resp2)
        token = autojoin.skip_token(1, "e3")
    page = client.get(f"/api/coworker/autojoin/skip/{token}")
    assert page.status_code == 200 and b"Northwind intro" in page.data
    assert b"won't join" in client.post(f"/api/coworker/autojoin/skip/{token}").data
    assert client.get("/api/coworker/autojoin/skip/forged").status_code == 410
    assert client.post("/api/coworker/autojoin/skip/forged").status_code == 410
    with app.app_context():
        _event(get_store(), "e4", 20)
        responsibilities.run_one(get_store(), 1, resp2)
        get_store().insert("cw_runs", {"user_id": 1, "responsibility_id": resp2["id"], "trigger_key": "autojoin:e5",
                                       "status": "done", "created_at": iso()})
    assert client.post("/api/coworker/autojoin/e4/skip", headers=auth_headers).get_json() == {"skipped": True}
    assert client.post("/api/coworker/autojoin/e5/skip", headers=auth_headers).status_code == 409
    with app.app_context():
        late = autojoin.skip_token(1, "e5")
    assert client.post(f"/api/coworker/autojoin/skip/{late}").status_code == 409

    day = client.get("/api/coworker/day", headers=auth_headers).get_json()
    states = {e["autojoin"]["eventId"]: e["autojoin"]["state"] for e in day["entries"] if e.get("autojoin")}
    assert states == {"e3": "skipped", "e4": "skipped"}


def test_keywords_no_bot_and_failures(s, chats, monkeypatch):
    resp = _resp(s, keywords=["demo"])
    _event(s, "intro", 20, subject="Northwind intro")
    _event(s, "demo", 20, subject="Globex demo")
    assert responsibilities.run_one(s, 1, resp) == ["Prepared a brief for Globex demo and scheduled to join"]

    monkeypatch.delenv("RECALL_API_KEY")
    resp2 = _resp(s, keywords=[])
    _event(s, "nobot", 1, subject="Acme intro")
    out = responsibilities.run_one(s, 1, resp2)
    assert "Prepared a brief for Acme intro" in out and all("Joined" not in o for o in out)
    assert "can't join" in chats["new_chat"].call_args.args[2]
    assert autojoin.state(s, 1, "nobot", will_join=False) == "brief_only"

    monkeypatch.setenv("RECALL_API_KEY", "rk")
    s.execute("UPDATE cw_items SET occurred_at = %s WHERE external_id = 'demo'", (iso(utcnow() + timedelta(minutes=1)),))
    from coworker.connectors.base import ConnectorError

    with patch("coworker.connectors.recall.create_bot", side_effect=ConnectorError("Recall 500")):
        assert responsibilities.run_one(s, 1, resp) == []
    assert autojoin.state(s, 1, "demo") == "failed"
    assert "couldn't join" in chats["post"].call_args.args[2]
    assert any(a["kind"] == "escalation" for a in s.activity(1))

    s.update_coworker(1, status="paused")
    assert responsibilities.run_one(s, 1, resp) == []


def test_paused_coworker_cannot_be_sent(s, chats):
    resp = _resp(s)
    _event(s, "p1", 1)
    with patch("coworker.delegate.join_meeting", side_effect=delegate.DelegateError("Your coworker is paused.")):
        assert autojoin.run(s, 1, resp) == ["Prepared a brief for Northwind intro and scheduled to join"]
    assert autojoin.state(s, 1, "p1") == "failed"


def test_helpers():
    assert autojoin.read_skip_token("nope") is None
    assert autojoin.meeting_url({"meta": {"location": "Room 4"}, "body": "join https://meet.google.com/abc-def"}) == \
        "https://meet.google.com/abc-def"
    assert autojoin._chat_context(1, None) == ""
    with patch("database.db.get_connection", side_effect=RuntimeError("no db")):
        assert autojoin._chat_context(1, 5) == ""
    from unittest.mock import MagicMock

    with patch("database.db.get_connection", return_value=MagicMock()), \
            patch("database.db.get_messages", return_value=[{"role": "assistant", "content": "brief"},
                                                            {"role": "user", "content": "Ask about budget"}]):
        assert autojoin._chat_context(1, 5) == "Notes from the user for this call: Ask about budget"
    from coworker import reports

    with patch("database.db.get_connection", return_value=MagicMock()), \
            patch("database.db.create_chat", return_value=12), patch("database.db.create_message") as msg:
        assert reports.new_chat(1, "📞 Call", "hi") == 12
    assert msg.call_args.args[1:] == (12, "assistant", "hi", "coworker")
    with patch("database.db.get_connection", side_effect=RuntimeError("down")):
        assert reports.new_chat(1, "x", "y") is None


def test_suggested_when_a_bot_is_configured(s):
    _event(s, "s1", 24 * 60)
    assert any(x["template"] == "auto_join" for x in responsibilities.suggestions(s, 1))
