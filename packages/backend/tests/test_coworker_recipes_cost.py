"""Recipes gallery and per-task cost: metering model calls, usage per task, suggestions, endpoint."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from coworker import llm, memory, orgs, responsibilities, schedules
from coworker.connectors.demo import DemoConnector
from coworker.store import Store

UTC = ZoneInfo("UTC")


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("COWORKER_OFFLINE", "1")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("COWORKER_MODEL_PRICES", raising=False)
    with patch("services.provider_keys.get_user_provider_key", return_value=None), \
            patch("coworker.channels._history", return_value=[]), patch("coworker.channels._store_turn", return_value=7):
        yield


@pytest.fixture
def s(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/rc.db")
    store.create_coworker(1, "Natan Vidra", "natan@anote.ai", mode="demo")
    DemoConnector.seed(store, 1, "Natan Vidra", "natan@anote.ai")
    memory.rebuild(store, 1)
    return store


def test_metering_prices_and_scopes(monkeypatch):
    with llm.metering() as totals:
        llm._add_to_scope("claude-opus-5-5", {"input_tokens": 1_000_000, "output_tokens": 100_000,
                                              "cache_read_input_tokens": 1_000_000})
        llm._add_to_scope("claude-haiku-5-5", {"input_tokens": 1_000_000, "output_tokens": 1_000_000})
    assert totals["calls"] == 2 and totals["input_tokens"] == 3_000_000 and totals["output_tokens"] == 1_100_000
    assert totals["cost_usd"] == pytest.approx(4.0 + 2.0 + 0.20 + 0.10 + 0.50)
    with llm.metering() as unpriced:
        llm._add_to_scope("gpt-4o", {"input_tokens": 10, "output_tokens": 10})
        llm._add_to_scope("claude-opus-5-5", {"input_tokens": 10, "output_tokens": 10})
    assert unpriced["cost_usd"] is None and unpriced["input_tokens"] == 20
    llm._add_to_scope("claude-opus-5-5", {"input_tokens": 5})  # outside a scope: nothing to add to, no error
    monkeypatch.setenv("COWORKER_MODEL_PRICES", '{"gpt-4o": [2.5, 10]}')
    assert llm.price_for("gpt-4o") == (2.5, 10.0, 0.25)
    monkeypatch.setenv("COWORKER_MODEL_PRICES", "not json")
    assert llm.price_for("gpt-4o") is None


def test_runs_record_tokens_and_cost_and_roll_up(s):
    spec = responsibilities.scheduled_spec("Reply to my sales leads", {"freq": "daily", "time": "09:00"})
    resp = responsibilities.create(s, 1, spec)
    s.update("cw_responsibilities", resp["id"], 1, {"created_at": "2026-01-01T00:00:00Z"})
    resp = s.get("cw_responsibilities", resp["id"], 1)

    real_ask = __import__("coworker.channels", fromlist=["ask"]).ask

    def ask(*a, **k):
        llm._add_to_scope("claude-opus-5-5", {"input_tokens": 50_000, "output_tokens": 5_000})
        return real_ask(*a, **k)

    with patch("coworker.channels.ask", side_effect=ask), \
            patch("coworker.schedules.utcnow", return_value=datetime(2026, 1, 5, 14, 5, tzinfo=UTC)):
        schedules.run(s, 1, resp)
    run = s.query("SELECT * FROM cw_runs WHERE responsibility_id = %s", (resp["id"],))[0]
    assert run["tokens"] == 55_000 and run["cost_micros"] == 300_000  # 0.05M×$4 + 0.005M×$20 = $0.30
    s.execute("UPDATE cw_runs SET created_at = %s", ("2099-01-01T00:00:00Z",))  # inside the 30-day window
    s.execute("UPDATE cw_actions SET created_at = %s, status = 'executed' WHERE responsibility_id = %s",
              ("2099-01-01T00:00:00Z", resp["id"]))
    with patch("coworker.schedules.utcnow", return_value=datetime(2099, 1, 10, tzinfo=UTC)):
        u = schedules.usage(s, 1, resp["id"])
        assert schedules.spend(s, 1) == 0.3
    assert u["runs"] == 1 and u["costUsd"] == 0.3 and u["tokens"] == 55_000 and u["executed"] == u["actions"] >= 1
    assert u["hoursSaved"] > 0
    with patch("coworker.schedules.utcnow", return_value=datetime(2099, 1, 10, tzinfo=UTC)):
        orgs.create(s, 1, "Anote", "anote.ai", "natan@anote.ai")
        assert orgs.overview(s, 1)["members"][0]["usage"]["taskSpendUsd"] == 0.3


def test_recipes_are_valid_and_suggested_from_data(s):
    gallery = schedules.recipes(s, 1)
    assert len(gallery) == len(schedules.RECIPES) >= 10
    assert all(r["when"] and r["sample"] and r["instruction"] for r in gallery)
    sweep = next(r for r in gallery if r["id"] == "inbox_sweep")
    assert "emails are waiting on you" in sweep["why"]
    assert gallery[0]["why"]  # suggestions first

    responsibilities.create(s, 1, responsibilities.scheduled_spec(sweep["instruction"], sweep["schedule"], sweep["name"]))
    again = schedules.recipes(s, 1)
    assert again[-1]["id"] == "inbox_sweep" and again[-1]["enabled"]  # already on: sorted last


def test_recipes_endpoint(client, auth_headers):
    with patch("api_endpoints.coworker.common.owner_profile", return_value=("Natan Vidra", "natan@example.com")), \
            patch("api_endpoints.coworker.core.owner_profile", return_value=("Natan Vidra", "natan@example.com")):
        client.post("/api/coworker", json={"mode": "demo"}, headers=auth_headers)
    recipes = client.get("/api/coworker/recipes", headers=auth_headers).get_json()["recipes"]
    assert {r["id"] for r in recipes} >= {"morning_briefing", "investor_update"}
    created = client.post("/api/coworker/responsibilities", headers=auth_headers, json={
        "name": recipes[0]["name"], "instruction": recipes[0]["instruction"], "schedule": recipes[0]["schedule"], "runNow": False})
    assert created.get_json()["responsibility"]["schedule"]["usage"]["runs"] == 0
