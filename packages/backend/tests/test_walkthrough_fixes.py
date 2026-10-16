"""Small fixes found while recording the walkthrough: wording, dates, duplicate escalations, time zones."""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest

from coworker import meetings, memory, responsibilities, schedules
from coworker.connectors.demo import DemoConnector
from coworker.store import Store, iso, utcnow


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("COWORKER_OFFLINE", "1")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with patch("services.provider_keys.get_user_provider_key", return_value=None):
        yield


@pytest.fixture
def s(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/w.db")
    store.create_coworker(1, "Natan Vidra", "natan@anote.ai", mode="demo")
    DemoConnector.seed(store, 1, "Natan Vidra", "natan@anote.ai")
    memory.rebuild(store, 1)
    return store


def test_suggestions_use_singular_for_one(s):
    text = " ".join(x["why"] for x in responsibilities.suggestions(s, 1))
    for wrong in ("1 people", "1 customers", "1 deal threads", "1 unanswered sales inquiries", "1 teammates", "1 external meetings"):
        assert wrong not in text


def test_upcoming_meeting_is_not_last_contact(s):
    soon = iso(utcnow() + timedelta(days=2))
    s.add_item(1, {"provider": "gcal", "external_id": "ev-x", "thread_id": "ev-x", "kind": "event", "direction": "inbound",
                   "author_name": "Natan", "author_email": "natan@anote.ai", "subject": "Intro",
                   "recipients": [{"name": "New Person", "email": "new@future.io"}], "body": "", "occurred_at": soon, "meta": {}})
    memory.rebuild(s, 1)
    people = {p["email"]: p for p in s.people(1)}
    assert people["new@future.io"]["last_contact_at"] is None
    now = iso()
    assert all((p.get("last_contact_at") or "") <= now for p in people.values())


def test_escalation_recorded_once(s):
    m = meetings.start(s, 1, mode="simulated", title="t", prospect_name="Dana", company="Northwind")
    for _ in range(2):
        meetings.respond(s, 1, m["id"], "Could you do 30% off if we sign this month?")
    assert len((s.get("cw_meetings", m["id"], 1)["metrics"] or {})["escalations"]) == 1


def test_next_run_label_is_in_the_coworker_time_zone(s):
    s.update_coworker(1, settings={"timezone": "America/New_York"})
    resp = {"id": 5, "enabled": True, "trigger_spec": {"freq": "weekdays", "time": "09:00"}}
    with patch("coworker.schedules.usage", return_value={}):
        st = schedules.state(s, 1, resp)
    assert st["nextRun"] and "9:00 AM E" in st["nextRunLabel"]
