"""Chat-first delegation: join a meeting, reply to emails, report back, the day view."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from coworker import brain, delegate, executor, memory, reports, tools
from coworker.connectors.demo import DemoConnector
from coworker.store import Store


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("RECALL_API_KEY", raising=False)
    monkeypatch.setenv("COWORKER_OFFLINE", "1")
    with patch("services.provider_keys.get_user_provider_key", return_value=None):
        yield


@pytest.fixture
def s(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/delegate.db")
    store.create_coworker(1, "Natan Vidra", "natan@anote.ai", mode="demo")
    DemoConnector.seed(store, 1, "Natan Vidra", "natan@anote.ai")
    memory.rebuild(store, 1)
    return store


@pytest.fixture
def posted():
    with patch("coworker.reports.post", return_value=True) as post:
        yield post


def _turn(store: Store, message: str, chat_id: int = 77) -> tuple[str, tools.ToolContext, list]:
    ctx = tools.ToolContext(store=store, user_id=1, chat_id=chat_id)
    events = list(brain._offline_turn(ctx, message))
    return "".join(p for k, p in events if k == "text"), ctx, events


def test_join_meeting_from_chat_in_demo_runs_call_and_reports_back(s, posted):
    text, ctx, events = _turn(s, "Join my call with Dana and pitch the pilot, then send me the summary")
    assert "summary" in text.lower() and "follow-up" in text.lower()
    meeting_cards = [c for c in ctx.cards if c["type"] == "meeting"]
    assert len(meeting_cards) == 1
    m = s.get("cw_meetings", meeting_cards[0]["id"], 1)
    assert m["status"] == "ended" and m["answers"]["chat_id"] == 77
    assert m["answers"]["context"].startswith("pitch the pilot")
    # The summary was posted into the chat that asked, with the meeting and follow-up cards.
    chat_id, content = posted.call_args_list[-1].args[1], posted.call_args_list[-1].args[2]
    assert chat_id == 77 and "Call finished" in content and '"t": "meeting"' in content and '"t": "action"' in content
    followup = s.query("SELECT * FROM cw_actions WHERE user_id = 1 AND title LIKE 'Follow up%'")[0]
    assert followup["chat_id"] == 77


def test_join_meeting_without_bot_uses_studio_and_matches_calendar(s, posted):
    s.update_coworker(1, mode="live")
    out = delegate.join_meeting(s, 1, chat_id=5, title="the Globex QBR", context="ask about renewal")
    assert out["how"] == "studio" and out["event"]["subject"] == "Globex QBR"
    m = out["meeting"]
    assert m["mode"] == "live_call" and m["prospect_name"] == "Kevin O'Brien" and m["meeting_url"].startswith("https://zoom.us")
    s.update_coworker(1, status="paused")
    with pytest.raises(delegate.DelegateError):
        delegate.join_meeting(s, 1, chat_id=5, title="x")


def test_join_meeting_sends_bot_when_configured(s, posted, monkeypatch):
    s.update_coworker(1, mode="live")
    monkeypatch.setenv("RECALL_API_KEY", "rk")
    with patch("coworker.connectors.recall.create_bot", return_value="bot-1") as create:
        out = delegate.join_meeting(s, 1, chat_id=9, meeting_url="https://meet.google.com/abc-defg-hij",
                                    context="qualify budget", prospect_name="Dana")
    assert out["how"] == "bot" and out["meeting"]["bot_id"] == "bot-1"
    assert "AI coworker (Ourogen)" in create.call_args.args[1] and "token=" in create.call_args.args[3]


def test_join_meeting_tool_errors_are_readable(s):
    ctx = tools.ToolContext(store=s, user_id=1, chat_id=1)
    s.update_coworker(1, mode="live", status="paused")
    result, summary = tools.run("join_meeting", {"title": "standup"}, ctx)
    assert "paused" in result["error"]
    s.update_coworker(1, status="active")
    with patch("coworker.delegate.join_meeting", side_effect=RuntimeError("vendor down")):
        result, summary = tools.run("join_meeting", {"meeting_url": "https://zoom.us/j/1"}, ctx)
    assert "vendor down" in result["error"]
    text, _, _ = _turn(s, "please join the standup")  # paused path via offline planner
    assert text


def test_reply_to_emails_drafts_each_once_and_reports_after_send(s, posted):
    text, ctx, _ = _turn(s, "Reply to my unanswered emails")
    actions = [s.get("cw_actions", c["id"], 1) for c in ctx.cards if c["type"] == "action"]
    assert len(actions) >= 3 and all(a["chat_id"] == 77 and a["status"] == "proposed" for a in actions)
    assert "drafted" in text.lower()
    # Asking again doesn't draft duplicates of replies already waiting.
    assert delegate.reply_to_emails(s, 1, chat_id=77) == []
    leads = delegate.reply_to_emails(s, 1, chat_id=78, category="sales_lead")
    assert leads == []  # the lead reply is already pending from the first request
    executor.approve(s, 1, actions[0]["id"])
    content = posted.call_args.args[2]
    assert content.startswith("✅ Sent to") and "> " in content and f'"id": {actions[0]["id"]}' in content


def test_reply_to_emails_filters(s):
    only = delegate.reply_to_emails(s, 1, chat_id=1, who="globex")
    assert len(only) == 1 and "Kevin" in only[0]["title"]
    _, _, _ = _turn(s, "reply to my leads")
    text, _, _ = _turn(s, "answer my support emails")
    assert "Nothing is waiting" in text or "drafted" in text.lower()


def test_my_day_and_route(s, posted, client, auth_headers):
    _turn(s, "Join my call with Dana and pitch the pilot")
    d = delegate.day(s, 1)
    kinds = {e["kind"] for e in d["entries"]}
    assert "meeting" in kinds and d["counts"]["calls"] == 1 and d["counts"]["pending"] >= 1
    assert d["upcoming"] is not None and "waiting" in d["headline"]
    text, _, _ = _turn(s, "What did you do today?")
    assert "📞" in text
    assert delegate.day(s, 1, "2020-01-01")["entries"] == []
    with patch("api_endpoints.coworker.core.owner_profile", return_value=("Natan Vidra", "natan@anote.ai")):
        assert client.post("/api/coworker", json={"mode": "demo"}, headers=auth_headers).status_code == 201
    assert client.get("/api/coworker/day?date=bad", headers=auth_headers).status_code == 400
    body = client.get("/api/coworker/day", headers=auth_headers).get_json()
    assert set(body) >= {"date", "headline", "entries", "counts", "upcoming"}
    empty = brain._offline_turn(tools.ToolContext(store=Store(f"sqlite:///{s._sqlite_path}x"), user_id=1), "what did you do today?")
    assert "Nothing yet" in "".join(p for k, p in empty if k == "text")


def test_report_formatting():
    a = {"id": 3, "type": "email.send", "title": "Reply", "payload": {"to": ["d@x.com"], "subject": "Hi", "body": "line1\n\nline2"}}
    msg = reports.action_done(a, {})
    assert "Sent to d@x.com" in msg and "> line1\n>\n> line2" in msg
    assert "Saved a draft" in reports.action_done(a, {"draft": True})
    assert "#sales" in reports.action_done({"id": 1, "type": "slack.post", "payload": {"channel": "sales", "text": "x"}}, {})
    assert "invite" in reports.action_done({"id": 1, "type": "calendar.create", "payload": {"title": "T", "attendees": []}}, {})
    assert "HubSpot" in reports.action_done({"id": 1, "type": "crm.update", "payload": {"company": "A"}}, {"hubspot": {}})
    assert "Done" in reports.action_done({"id": 1, "type": "other", "title": "t", "payload": {}}, {})
    long = reports._quote("x" * 2000)
    assert long.endswith("…")
    summary = reports.meeting_summary({"id": 4, "title": "Call"}, {"text": "ok", "score": 70, "hot": True,
                                                                  "action_items": ["Send recap"]})
    assert "🔥" in summary and "- Send recap" in summary


def test_post_writes_to_owned_chat_only():
    cnx = MagicMock()
    with patch("database.db.get_connection", return_value=cnx), \
         patch("database.db.get_chat", side_effect=[{"id": 5}, None]), \
         patch("database.db.create_message") as create:
        assert reports.post(1, 5, "hello") is True
        assert reports.post(1, 6, "hello") is False  # not this user's chat
    create.assert_called_once_with(cnx, 5, "assistant", "hello", "coworker")
    assert reports.post(1, None, "x") is False and reports.post(1, 5, "  ") is False
    with patch("database.db.get_connection", side_effect=RuntimeError("db down")):
        assert reports.post(1, 5, "hello") is False
