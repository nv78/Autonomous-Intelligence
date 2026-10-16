"""Background sync jobs (#378) and owner notifications (#380)."""
from __future__ import annotations

import time
from datetime import timedelta
from unittest.mock import patch

import pytest

from coworker import memory, notify, responsibilities, sync_jobs
from coworker.connectors.base import ConnectorError, encrypt_token
from coworker.connectors.demo import DemoConnector
from coworker.store import Store, iso, utcnow


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for key in ("COWORKER_SYNC_MODE", "SMTP_URL", "NOTIFY_BATCH_SECONDS", "NOTIFY_MIN_INTERVAL_SECONDS"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with patch("api_endpoints.coworker.core.owner_profile", return_value=("Natan Vidra", "natan@example.com")), \
         patch("services.provider_keys.get_user_provider_key", return_value=None):
        yield


@pytest.fixture
def s(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/ops.db")
    store.create_coworker(1, "Natan Vidra", "natan@example.com", mode="demo")
    DemoConnector.seed(store, 1, "Natan Vidra", "natan@example.com")
    memory.rebuild(store, 1)
    return store


def _live(store: Store, scope: str = "") -> None:
    store.update_coworker(1, mode="live")
    store.upsert_connection(1, "google", status="connected", account_label="natan@example.com",
                            token_enc=encrypt_token({"access_token": "at", "expires_at": 9e9, "scope": scope}))


def _propose(store: Store, title: str, minutes_ago: float = 10) -> int:
    return store.insert("cw_actions", {
        "user_id": 1, "type": "send_email", "status": "proposed", "title": title, "payload": {},
        "created_at": iso(utcnow() - timedelta(minutes=minutes_ago)),
    })


# -- sync jobs ---------------------------------------------------------------

def test_request_dedupes_and_claim_is_atomic(s):
    job = sync_jobs.request(s, 1)
    again = sync_jobs.request(s, 1, rebuild=True)
    assert again["id"] == job["id"] and again["rebuild"] == 1
    assert sync_jobs.claim(s, job["id"]) is True
    assert sync_jobs.claim(s, job["id"]) is False  # second claimer loses
    assert sync_jobs.request(s, 1)["id"] == job["id"]  # still running
    # A running job that went stale is re-queued and can be reclaimed.
    s.execute("UPDATE cw_sync_jobs SET started_at = %s WHERE id = %s", (iso(utcnow() - timedelta(hours=1)), job["id"]))
    assert sync_jobs.request(s, 1)["id"] != job["id"]
    assert sync_jobs.claim(s, job["id"]) is True


def test_run_success_error_and_status(s, app):
    _live(s)
    with app.app_context(), patch("coworker.connectors.google.GoogleConnector.sync", return_value=4), \
            patch("api_endpoints.coworker.core.refresh_knowledge") as refresh:
        job = sync_jobs.request(s, 1)
        assert sync_jobs.run_job(s, job["id"]) == {"status": "done", "counts": {"google": 4}}
        refresh.assert_called_once_with(1)
        assert sync_jobs.run_job(s, job["id"]) is None  # already done
    st = sync_jobs.status(s, 1)
    assert st["job"]["phase"] == "done" and not st["running"] and st["total"] > 0 and "gmail" in st["items"]
    with patch("coworker.connectors.base.Workspace.sync", side_effect=RuntimeError("boom")):
        job = sync_jobs.request(s, 1)
        assert sync_jobs.run_job(s, job["id"])["status"] == "error"
    assert sync_jobs.status(s, 1)["job"]["error"] == "boom"


def test_run_pending_and_worker_mode(s, app, monkeypatch):
    _live(s)
    monkeypatch.setenv("COWORKER_SYNC_MODE", "worker")
    with app.app_context(), patch("coworker.connectors.google.GoogleConnector.sync", return_value=0):
        job = sync_jobs.request(s, 1)
        sync_jobs.start(s, job)  # the worker owns sync: nothing runs here
        assert sync_jobs.current(s, 1)["status"] == "queued"
        assert sync_jobs.run_pending(s) == 1
        assert sync_jobs.current(s, 1)["status"] == "done"


def test_start_runs_on_a_thread(s, app):
    _live(s)
    app.config["COWORKER_SYNC_THREADS"] = True
    with app.app_context(), patch("coworker.connectors.google.GoogleConnector.sync", return_value=0):
        sync_jobs.start(s, sync_jobs.request(s, 1))
        for _ in range(100):
            if sync_jobs.current(s, 1)["status"] == "done":
                break
            time.sleep(0.02)
    assert sync_jobs.current(s, 1)["status"] == "done"


def test_sync_endpoints(client, auth_headers):
    assert client.get("/api/coworker/sync/status", headers=auth_headers).get_json()["job"] is None
    assert client.post("/api/coworker", json={"mode": "demo"}, headers=auth_headers).status_code == 201
    demo = client.post("/api/coworker/sync?rebuild=1", headers=auth_headers)
    assert demo.status_code == 200 and demo.get_json()["queued"] is False and demo.get_json()["memory"]


def test_tick_queues_sync_and_worker_syncs_inline(client, auth_headers, app):
    from api_endpoints.coworker.delegation import run_tick
    from coworker import worker
    from coworker.store import get_store

    assert client.post("/api/coworker", json={"mode": "demo"}, headers=auth_headers).status_code == 201
    with app.app_context():
        _live(get_store())
        with patch("coworker.connectors.google.GoogleConnector.sync", return_value=2) as gsync:
            tick = client.post("/api/coworker/tick", json={"force": True}, headers=auth_headers).get_json()
            assert "queued" in tick["synced"]
            assert gsync.call_count == 1  # ran via the job (inline under tests)
            result = run_tick(1, force=True, inline_sync=True)
            assert result["synced"] == {"google": 2}
            assert worker.run_once() == 1


# -- notifications -----------------------------------------------------------

def test_demo_notification_lands_in_inbox_and_is_ignored(s):
    assert notify.deliver(s, 1, "Hello", "Body") == "demo"
    item = s.items(1, kind="email", limit=1)[0]
    assert item["subject"] == "[Ourogen] Hello" and notify.is_notification(item)
    assert memory.is_noise(item)
    assert "[Ourogen]" not in str(memory.needs_reply(s, 1))


def test_approvals_are_batched_and_rate_limited(s, monkeypatch):
    _propose(s, "Reply to Dana", minutes_ago=1)
    assert notify.maybe_notify_approvals(s, 1) == 0  # still inside the batch window
    _propose(s, "Nudge Priya", minutes_ago=6)
    assert notify.maybe_notify_approvals(s, 1) == 2
    email = s.items(1, kind="email", limit=1)[0]
    assert "2 actions waiting" in email["subject"] and "/app/coworker/approvals" in email["body"]
    _propose(s, "Book a call", minutes_ago=40)
    _propose(s, "Later one", minutes_ago=0)
    assert notify.maybe_notify_approvals(s, 1) == 0  # one email per 30 minutes
    # Even if the time check is bypassed, the slot key blocks a duplicate.
    monkeypatch.setenv("NOTIFY_MIN_INTERVAL_SECONDS", "0")
    monkeypatch.setenv("NOTIFY_BATCH_SECONDS", "0")
    with patch("coworker.notify._interval_seconds", return_value=10**9):
        s.execute("UPDATE cw_notifications SET sent_at = %s", ("2000-01-01T00:00:00Z",))
        assert notify.maybe_notify_approvals(s, 1) == 0
    assert len(notify.history(s, 1, since_hours=10**6)) == 1


def test_approval_emails_can_be_turned_off(s):
    s.update_coworker(1, settings={"notify_approvals": False})
    _propose(s, "Reply to Dana")
    assert notify.maybe_notify_approvals(s, 1) == 0


def test_live_delivery_prefers_gmail_then_smtp(s, monkeypatch):
    _live(s, scope="gmail.send")
    with patch("coworker.connectors.google.GoogleConnector.send_email") as send:
        assert notify.deliver(s, 1, "Hi", "Body") == "gmail"
        assert send.call_args.kwargs["to"] == ["natan@example.com"]
    with patch("coworker.connectors.google.GoogleConnector.send_email", side_effect=ConnectorError("no", "x")):
        assert notify.deliver(s, 1, "Hi", "Body") == ""  # no relay configured
        monkeypatch.setenv("SMTP_URL", "smtp://user%40x:pw@mail.example.com:2525")
        with patch("smtplib.SMTP") as smtp:
            assert notify.deliver(s, 1, "Hi", "Body") == "smtp"
        server = smtp.return_value
        server.login.assert_called_once_with("user@x", "pw")
        msg = server.send_message.call_args.args[0]
        assert msg["To"] == "natan@example.com" and msg["Subject"] == "[Ourogen] Hi"
    monkeypatch.setenv("SMTP_URL", "smtps://mail.example.com")
    _live(s, scope="")
    with patch("smtplib.SMTP_SSL") as ssl_smtp:
        assert notify.deliver(s, 1, "Hi", "Body") == "smtp"
        assert ssl_smtp.call_args.args[:2] == ("mail.example.com", 465)
    with patch("smtplib.SMTP_SSL", side_effect=OSError("down")):
        assert notify.deliver(s, 1, "Hi", "Body") == ""
    s.update_coworker(1, owner_email="")
    assert notify.deliver(s, 1, "Hi", "Body") == ""


def test_digest_email(s):
    d = responsibilities.digest(s, 1)
    assert notify.send_digest(s, 1, d) == ""  # off by default
    s.update_coworker(1, settings={"digest_email": True})
    assert notify.send_digest(s, 1, {**d, "executed": ["Replied to Dana"], "pending": ["Nudge Priya"]}) == "demo"
    assert notify.send_digest(s, 1, d) == ""  # once per day
    body = s.items(1, kind="email", limit=1)[0]["body"]
    assert "Replied to Dana" in body and "Waiting for you" in body


def test_daily_digest_responsibility_emails(s):
    s.update_coworker(1, settings={"digest_email": True, "timezone": "UTC"})
    s.insert("cw_responsibilities", {"user_id": 1, "name": "Daily digest", "template": "daily_digest", "enabled": 1,
                                     "autonomy": "approve", "runs": 0, "created_at": iso()})
    resp = s.query("SELECT * FROM cw_responsibilities WHERE user_id = 1")[0]
    late = utcnow().replace(hour=18)
    with patch("coworker.responsibilities.utcnow", return_value=late):
        assert responsibilities.run_one(s, 1, resp) == ["Posted the daily digest"]
    assert notify.history(s, 1)[0]["kind"] == "digest"


def test_tick_sends_notification(client, auth_headers, app):
    from coworker.store import get_store

    assert client.post("/api/coworker", json={"mode": "demo"}, headers=auth_headers).status_code == 201
    with app.app_context():
        _propose(get_store(), "Reply to Dana")
    tick = client.post("/api/coworker/tick", json={"force": True}, headers=auth_headers).get_json()
    assert tick["notified"] >= 1

