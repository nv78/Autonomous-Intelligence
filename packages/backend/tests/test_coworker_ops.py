"""Autonomous operations: worker heartbeats and status, health, run history, and columns added in place."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from coworker import ops
from coworker.store import Store, iso

UTC = ZoneInfo("UTC")


def test_heartbeat_and_status(tmp_path):
    s = Store(f"sqlite:///{tmp_path}/ops.db")
    assert ops.worker_status(s)["status"] == "missing"
    ops.heartbeat(s, 850, 3, 0)
    ops.heartbeat(s, 900, 4, 1)  # same worker: one row, updated
    rows = s.query("SELECT * FROM cw_worker_heartbeats")
    assert len(rows) == 1 and rows[0]["users"] == 4 and rows[0]["errors"] == 1
    st = ops.worker_status(s)
    assert st["status"] == "ok" and st["workers"] == 1 and st["tickMs"] == 900

    later = datetime.now(UTC) + timedelta(minutes=10)
    with patch("coworker.ops.utcnow", return_value=later), patch("observability.alert") as alert:
        assert ops.worker_status(s)["status"] == "stale"
    assert alert.call_args.args[0] == "worker_stale"

    s.execute("UPDATE cw_worker_heartbeats SET last_tick_at = %s", (iso(datetime.now(UTC) - timedelta(days=2)),))
    ops.heartbeat(s, 1, 0, 0)  # a new pass forgets workers gone for a day
    assert len(s.query("SELECT * FROM cw_worker_heartbeats")) == 1


def test_worker_pass_writes_a_heartbeat(app):
    from coworker import worker
    from coworker.store import get_store

    with app.app_context(), patch("api_endpoints.coworker.delegation.run_tick", return_value={}):
        s = get_store()
        s.create_coworker(1, "Natan", "n@x.com", mode="demo")
        assert worker.run_once() == 1
        assert ops.worker_status(s)["status"] == "ok"


def test_health_status_and_runs_endpoints(client, auth_headers, app):
    assert client.get("/health").get_json()["worker"] == "missing"
    with patch("api_endpoints.coworker.common.owner_profile", return_value=("Natan Vidra", "natan@example.com")), \
            patch("api_endpoints.coworker.core.owner_profile", return_value=("Natan Vidra", "natan@example.com")):
        client.post("/api/coworker", json={"mode": "demo"}, headers=auth_headers)
    from coworker.store import get_store

    with app.app_context():
        ops.heartbeat(get_store(), 10, 1, 0)
    assert client.get("/health").get_json()["worker"] == "ok"
    assert client.get("/api/coworker/status", headers=auth_headers).get_json()["worker"]["status"] == "ok"

    created = client.post("/api/coworker/responsibilities", headers=auth_headers, json={
        "instruction": "Tell me what's on my plate", "schedule": {"freq": "daily", "time": "09:00"}, "runNow": False})
    task_id = created.get_json()["responsibility"]["id"]
    with patch("coworker.channels._store_turn", return_value=5), patch("coworker.channels._history", return_value=[]):
        client.post(f"/api/coworker/responsibilities/{task_id}/run", headers=auth_headers)
    runs = client.get("/api/coworker/runs?limit=5", headers=auth_headers).get_json()["runs"]
    assert runs[0]["responsibility"] == "Tell me what's on my plate" and runs[0]["status"] == "done"
    assert runs[0]["attempts"] == 1 and runs[0]["durationMs"] is not None


def test_columns_are_added_to_existing_tables(tmp_path):
    path = f"{tmp_path}/old.db"
    old = sqlite3.connect(path)
    old.execute("CREATE TABLE cw_runs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INT NOT NULL, responsibility_id INT NOT NULL, "
                "trigger_key VARCHAR(255) NOT NULL, status VARCHAR(30) NOT NULL DEFAULT 'done', summary TEXT, "
                "created_at VARCHAR(40) NOT NULL, UNIQUE (user_id, responsibility_id, trigger_key))")
    old.execute("INSERT INTO cw_runs (user_id, responsibility_id, trigger_key, created_at) VALUES (1, 1, 'k', '2026-01-01')")
    old.commit()
    old.close()
    s = Store(f"sqlite:///{path}")
    row = s.query("SELECT * FROM cw_runs")[0]
    assert row["attempts"] == 1 and row["error"] is None and "started_at" in row
