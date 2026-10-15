"""Scheduled tasks: parsing, next run across DST, once per occurrence, autonomy, delivery, and the API."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from coworker import brain, executor, memory, responsibilities, schedules, tools
from coworker.connectors.demo import DemoConnector
from coworker.store import Store

UTC = ZoneInfo("UTC")
NY = ZoneInfo("America/New_York")


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("COWORKER_OFFLINE", "1")
    with patch("services.provider_keys.get_user_provider_key", return_value=None), \
            patch("coworker.channels._history", return_value=[]), \
            patch("coworker.channels._store_turn", return_value=55) as stored:
        yield stored


@pytest.fixture
def s(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/sched.db")
    store.create_coworker(1, "Natan Vidra", "natan@anote.ai", mode="demo")
    store.update_coworker(1, settings={"timezone": "America/New_York"})
    DemoConnector.seed(store, 1, "Natan Vidra", "natan@anote.ai")
    memory.rebuild(store, 1)
    return store


@pytest.mark.parametrize("text, described, instruction", [
    ("Every weekday at 8:30am tell me what's on my plate", "Every weekday at 8:30 AM", "Tell me what's on my plate"),
    ("every Monday at 9 post the pipeline summary in #sales", "Every Monday at 9 AM", "Post the pipeline summary in #sales"),
    ("Every Friday at 4 draft my weekly update to the team", "Every Friday at 4 PM", "Draft my weekly update to the team"),
    ("on the 1st of every month email clients with overdue invoices", "On the 1st of every month at 9 AM",
     "Email clients with overdue invoices"),
    ("on Mondays and Thursdays at 2:15pm send the standup notes", "Every Monday and Thursday at 2:15 PM",
     "Send the standup notes"),
    ("every month on the 15th at noon remind me about payroll", "On the 15th of every month at 12 PM",
     "Remind me about payroll"),
    ("each evening summarize my inbox", "Every day at 6 PM", "Summarize my inbox"),
    ("every 3 hours check for urgent emails", "Every 3 hours", "Check for urgent emails"),
])
def test_parse_and_describe(text, described, instruction):
    spec = schedules.parse(text)
    assert spec and schedules.describe(spec) == described
    assert schedules.strip_schedule(text) == instruction


@pytest.mark.parametrize("text", ["reply to Dana on Friday", "every time a lead emails, reply", "handle my support inbox"])
def test_one_offs_and_event_jobs_are_not_schedules(text):
    assert schedules.parse(text) is None


def test_clean_rejects_bad_specs():
    with pytest.raises(ValueError):
        schedules.clean({"freq": "fortnightly"})
    with pytest.raises(ValueError):
        schedules.clean({"freq": "daily", "time": "25:00"})
    spec = schedules.clean({"freq": "weekly", "days": ["Fridays", "nope"], "deliver": ["email", "fax"]})
    assert spec["days"] == ["fri"] and spec["deliver"] == ["chat", "email"]


def test_next_run_keeps_local_time_across_dst_and_clamps_months():
    weekday = schedules.parse("every weekday at 8:30am x")
    # Friday afternoon before US DST starts (Sun Mar 8, 2026): next is Monday 8:30 EDT = 12:30 UTC, not 13:30.
    assert schedules.next_run(weekday, NY, datetime(2026, 3, 6, 19, 0, tzinfo=UTC)) == datetime(2026, 3, 9, 12, 30, tzinfo=UTC)
    month_end = schedules.clean({"freq": "monthly", "day": 31, "time": "09:00"})
    assert schedules.next_run(month_end, NY, datetime(2026, 2, 1, tzinfo=UTC)) == datetime(2026, 2, 28, 14, 0, tzinfo=UTC)
    hourly = schedules.clean({"freq": "hourly", "every_hours": 6, "time": "00:15"})
    assert schedules.next_run(hourly, NY, datetime(2026, 1, 5, 12, 0, tzinfo=UTC)) == datetime(2026, 1, 5, 17, 15, tzinfo=UTC)


def test_due_respects_grace_window_and_creation_time():
    spec = schedules.parse("every day at 9am x")
    at_nine = datetime(2026, 1, 5, 14, 0, tzinfo=UTC)
    assert schedules.due(spec, NY, datetime(2026, 1, 5, 14, 30, tzinfo=UTC)) == at_nine
    assert schedules.due(spec, NY, datetime(2026, 1, 5, 17, 0, tzinfo=UTC)) is None  # missed by 3h: skipped
    assert schedules.due(spec, NY, datetime(2026, 1, 5, 13, 59, tzinfo=UTC)) is None  # not yet
    assert schedules.due(spec, NY, datetime(2026, 1, 5, 14, 30, tzinfo=UTC), not_before=datetime(2026, 1, 5, 14, 10, tzinfo=UTC)) is None


def test_chat_request_becomes_a_scheduled_task(s):
    ctx = tools.ToolContext(store=s, user_id=1, chat_id=9)
    text = "".join(p for k, p in brain._offline_turn(ctx, "Every weekday at 8:30am reply to my sales leads") if k == "text")
    assert "Every weekday at 8:30 AM" in text
    card = s.get("cw_actions", ctx.cards[0]["id"], 1)
    assert card["type"] == "responsibility.create" and card["payload"]["template"] == "scheduled"
    with patch("coworker.executor.run_due"):
        executor.approve(s, 1, card["id"])
    executor.run_due(s, 1)
    resp = s.query("SELECT * FROM cw_responsibilities WHERE user_id = 1 AND template = 'scheduled'")[0]
    assert resp["instruction"] == "Reply to my sales leads"
    assert resp["trigger_spec"]["freq"] == "weekdays" and resp["trigger_spec"]["time"] == "08:30"


def _task(s: Store, text: str, autonomy: str = "approve", **schedule) -> dict:
    spec = responsibilities.scheduled_spec(text, {"freq": "daily", "time": "09:00", **schedule})
    spec["autonomy"] = autonomy
    resp = responsibilities.create(s, 1, spec)
    s.update("cw_responsibilities", resp["id"], 1, {"created_at": "2026-01-01T00:00:00Z"})
    fresh = s.get("cw_responsibilities", resp["id"], 1)
    assert fresh is not None
    return fresh


def test_runs_once_per_occurrence_at_the_tasks_autonomy(s, _env):
    resp = _task(s, "Reply to my sales leads", deliver=["chat", "email", "push"])
    nine = datetime(2026, 1, 5, 14, 5, tzinfo=UTC)
    with patch("coworker.schedules.utcnow", return_value=nine), \
            patch("coworker.notify.deliver", return_value="smtp") as mail, patch("coworker.push.send", return_value=1) as push:
        assert responsibilities.run_one(s, 1, resp) == ["Ran 'Reply to my sales leads'"]
        assert responsibilities.run_one(s, 1, s.get("cw_responsibilities", resp["id"], 1)) == []  # same occurrence
    actions = s.query("SELECT * FROM cw_actions WHERE user_id = 1 AND responsibility_id = %s", (resp["id"],))
    assert actions and all(a["autonomy"] == "approve" and a["status"] == "proposed" for a in actions)
    assert all(a["chat_id"] == 55 for a in actions)
    assert mail.call_args.args[2].startswith("Reply to my sales leads:") and push.called
    fresh = s.get("cw_responsibilities", resp["id"], 1)
    assert fresh["trigger_spec"]["chat_id"] == 55  # later runs post in the same chat
    assert _env.call_args.args[3].startswith("⏰ Scheduled run:")
    state = schedules.state(s, 1, fresh)
    assert state["runs"][0]["status"] == "done" and state["description"] == "Every day at 9 AM"

    with patch("coworker.schedules.utcnow", return_value=datetime(2026, 1, 6, 14, 1, tzinfo=UTC)):
        assert responsibilities.run_one(s, 1, fresh)  # next day's occurrence runs


def test_notify_level_and_org_ceiling(s):
    from coworker import orgs

    resp = _task(s, "Reply to my sales leads", autonomy="notify")
    with patch("coworker.schedules.utcnow", return_value=datetime(2026, 1, 5, 14, 5, tzinfo=UTC)):
        responsibilities.run_one(s, 1, resp)
    assert {a["autonomy"] for a in s.query("SELECT autonomy FROM cw_actions WHERE responsibility_id = %s", (resp["id"],))} == {"notify"}

    orgs.create(s, 1, "Anote", "anote.ai", "natan@anote.ai")
    orgs.update(s, 1, new_policies={"autonomy_ceiling": {"email.send": "approve"}})
    s.execute("DELETE FROM cw_actions")
    with patch("coworker.schedules.utcnow", return_value=datetime(2026, 1, 6, 14, 5, tzinfo=UTC)):
        responsibilities.run_one(s, 1, s.get("cw_responsibilities", resp["id"], 1))
    assert {a["autonomy"] for a in s.query("SELECT autonomy FROM cw_actions WHERE responsibility_id = %s", (resp["id"],))} == {"approve"}


def test_paused_failed_and_no_self_scheduling(s):
    resp = _task(s, "Reply to my sales leads")
    nine = datetime(2026, 1, 5, 14, 5, tzinfo=UTC)
    s.update_coworker(1, status="paused")
    with patch("coworker.schedules.utcnow", return_value=nine):
        assert schedules.run(s, 1, resp) == [] and schedules.run(s, 1, resp, force=True) == []
    s.update_coworker(1, status="active")
    with patch("coworker.schedules.utcnow", return_value=nine), patch("coworker.channels.ask", side_effect=RuntimeError("boom")):
        assert schedules.run(s, 1, resp) == []
    assert schedules.state(s, 1, resp)["runs"][0]["status"] == "failed"
    assert any("failed: boom" in a["summary"] for a in s.activity(1, limit=10))

    ctx = tools.ToolContext(store=s, user_id=1, responsibility=resp)
    result, _ = tools.run("propose_responsibility", {"request": "every day at 9 do it again"}, ctx)
    assert "error" in result


def test_api_create_list_update_and_run_now(client, auth_headers):
    from api_endpoints.coworker.common import store

    with patch("api_endpoints.coworker.common.owner_profile", return_value=("Natan Vidra", "natan@example.com")), \
            patch("api_endpoints.coworker.core.owner_profile", return_value=("Natan Vidra", "natan@example.com")):
        assert client.post("/api/coworker", json={"mode": "demo"}, headers=auth_headers).status_code == 201
    bad = client.post("/api/coworker/responsibilities", json={"instruction": "x", "schedule": {"freq": "never"}}, headers=auth_headers)
    assert bad.status_code == 400
    created = client.post("/api/coworker/responsibilities", headers=auth_headers, json={
        "instruction": "Tell me what's on my plate", "schedule": {"freq": "weekdays", "time": "08:30"}, "runNow": False})
    assert created.status_code == 201
    task = created.get_json()["responsibility"]
    assert task["template"] == "scheduled" and task["schedule"]["description"] == "Every weekday at 8:30 AM"
    assert task["schedule"]["nextRun"]

    patched = client.patch(f"/api/coworker/responsibilities/{task['id']}", headers=auth_headers,
                           json={"schedule": {"freq": "weekly", "days": ["fri"], "time": "16:00"}})
    assert patched.get_json()["responsibility"]["schedule"]["description"] == "Every Friday at 4 PM"
    ran = client.post(f"/api/coworker/responsibilities/{task['id']}/run", headers=auth_headers)
    assert ran.get_json()["results"] == ["Ran 'Tell me what's on my plate'"]
    listed = client.get("/api/coworker/responsibilities", headers=auth_headers).get_json()["responsibilities"]
    assert listed[-1]["schedule"]["runs"][0]["status"] == "done"
    with client.application.app_context():
        assert store().query("SELECT trigger_key FROM cw_runs")[-1]["trigger_key"].startswith("manual:")
