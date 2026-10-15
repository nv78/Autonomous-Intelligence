"""The weekly report: numbers, suggestions, one-tap links, sending once on Monday."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from coworker import weekly
from coworker.store import Store, iso

MONDAY_10AM = datetime(2026, 10, 19, 10, 0, tzinfo=UTC)


@pytest.fixture
def s(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/weekly.db")
    store.create_coworker(1, "Natan Vidra", "natan@anote.ai", mode="live")
    store.update_coworker(1, settings={"timezone": "UTC"})
    return store


def _actions(store: Store, n: int, action_type: str = "email.send", edited: int = 0, status: str = "executed") -> None:
    for i in range(n):
        store.insert("cw_actions", {"user_id": 1, "type": action_type, "status": status, "title": f"Reply {i}",
                                    "payload": {}, "edited": edited, "autonomy": "approve",
                                    "created_at": iso(MONDAY_10AM - timedelta(days=2)),
                                    "executed_at": iso(MONDAY_10AM - timedelta(days=2))})


def test_report_numbers_and_autonomy_suggestion(s):
    _actions(s, 9)
    with patch("coworker.metrics.utcnow", return_value=MONDAY_10AM), patch("coworker.weekly.utcnow", return_value=MONDAY_10AM):
        data = weekly.report(s, 1)
    assert data["emails"] == 9 and data["acceptance"] == 1.0
    assert data["suggestions"][0]["kind"] == "autonomy" and data["suggestions"][0]["action_type"] == "email.send"
    headline, body = weekly.render(s, 1, data)
    assert headline.startswith("I saved you about") and "9 emails sent" in headline
    assert "Hi Natan" in body and "/api/coworker/weekly/apply/" in body and "estimate" in body

    _actions(s, 1, edited=1)  # one edit breaks the streak
    with patch("coworker.metrics.utcnow", return_value=MONDAY_10AM), patch("coworker.weekly.utcnow", return_value=MONDAY_10AM):
        assert not [x for x in weekly.report(s, 1)["suggestions"] if x["kind"] == "autonomy"]


def test_sends_once_on_monday_only(s):
    _actions(s, 3)
    with patch("coworker.notify.deliver", return_value="smtp") as deliver, patch("coworker.push.send") as push, \
            patch("coworker.metrics.utcnow", return_value=MONDAY_10AM):
        with patch("coworker.weekly.utcnow", return_value=MONDAY_10AM - timedelta(hours=3)):
            assert weekly.maybe_send(s, 1) == ""  # 7am: too early
        with patch("coworker.weekly.utcnow", return_value=MONDAY_10AM + timedelta(days=1)):
            assert weekly.maybe_send(s, 1) == ""  # Tuesday
        with patch("coworker.weekly.utcnow", return_value=MONDAY_10AM):
            assert weekly.maybe_send(s, 1) == "smtp"
            assert weekly.maybe_send(s, 1) == ""  # once per week
            s.update_coworker(1, settings={"timezone": "UTC", "weekly_report": False})
    assert deliver.call_count == 1 and push.call_count == 1
    assert deliver.call_args.args[2] == "Your week with your coworker"
    with patch("coworker.weekly.utcnow", return_value=MONDAY_10AM + timedelta(days=7)):
        assert weekly.maybe_send(s, 1) == ""  # turned off


def test_quiet_week_sends_nothing(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/quiet.db")
    store.create_coworker(1, "Natan", "natan@anote.ai", mode="live")
    store.update_coworker(1, settings={"timezone": "UTC"})
    with patch("coworker.weekly.utcnow", return_value=MONDAY_10AM), patch("coworker.notify.deliver") as deliver:
        assert weekly.maybe_send(store, 1) == ""
    deliver.assert_not_called()


def test_apply_suggestions(s):
    assert "Done" in weekly.apply(s, 1, {"kind": "autonomy", "action_type": "email.send", "level": "notify"})
    assert (s.get_coworker(1) or {})["autonomy"]["email.send"] == "notify"
    assert "isn't valid" in weekly.apply(s, 1, {"kind": "autonomy", "action_type": "email.send", "level": "silent"})
    assert "isn't valid" in weekly.apply(s, 1, {"kind": "autonomy", "action_type": "responsibility.create", "level": "notify"})
    assert "Done" in weekly.apply(s, 1, {"kind": "responsibility", "template": "stale_deals"})
    assert "already" in weekly.apply(s, 1, {"kind": "responsibility", "template": "stale_deals"})
    assert "isn't valid" in weekly.apply(s, 1, {"kind": "responsibility", "template": "nope"})
    assert "isn't valid" in weekly.apply(s, 1, {"kind": "other"})


def test_one_tap_links(client, app):
    from coworker.store import get_store

    with app.app_context():
        get_store().create_coworker(1, "Natan", "natan@anote.ai", mode="live")
        tok = weekly.token(1, {"kind": "responsibility", "template": "stale_deals", "text": "Nudge stalled deals?"})
    page = client.get(f"/api/coworker/weekly/apply/{tok}")
    assert page.status_code == 200 and b"Nudge stalled deals?" in page.data
    assert b"taken on" in client.post(f"/api/coworker/weekly/apply/{tok}").data
    assert client.get("/api/coworker/weekly/apply/forged").status_code == 410
    assert client.post("/api/coworker/weekly/apply/forged").status_code == 410
    assert weekly.read_token("forged") is None
