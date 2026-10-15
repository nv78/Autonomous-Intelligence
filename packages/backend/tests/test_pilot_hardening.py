"""Pilot hardening: shared rate limits, retention, error tracking and alerts."""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import fakeredis
import pytest

import observability
from coworker import retention
from coworker.store import Store, iso, utcnow
from middleware import rate_limit
from middleware.rate_limit import RateLimiter


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    for key in ("REDIS_URL", "RATE_LIMIT_REDIS_URL", "RATE_LIMIT_BACKEND", "SENTRY_DSN", "ALERT_SLACK_WEBHOOK_URL",
                "COWORKER_RETENTION_DAYS", "COWORKER_BACKFILL_DAYS", "COWORKER_TRANSCRIPT_RETENTION_DAYS"):
        monkeypatch.delenv(key, raising=False)
    rate_limit.reset_backend()
    observability._last_alert.clear()
    yield
    rate_limit.reset_backend()


# -- rate limiting -----------------------------------------------------------

def test_redis_limits_are_shared_between_limiters(monkeypatch):
    server = fakeredis.FakeServer()
    monkeypatch.setenv("REDIS_URL", "redis://fake:6379/0")
    with patch("redis.Redis.from_url", side_effect=lambda *a, **k: fakeredis.FakeRedis(server=server)):
        a = RateLimiter(max_calls=2, period=60, name="pilot")
        b = RateLimiter(max_calls=2, period=60, name="pilot")  # another process, same Redis
        assert a.is_allowed("1.2.3.4") and b.is_allowed("1.2.3.4")
        assert not a.is_allowed("1.2.3.4")
        assert b.is_allowed("5.6.7.8")
        other = RateLimiter(max_calls=1, period=60, name="other")
        assert other.is_allowed("1.2.3.4")  # names don't share counters


def test_falls_back_to_memory_when_redis_is_down(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://nowhere:6379/0")
    with patch("redis.Redis.from_url", side_effect=ConnectionError("down")) as connect:
        limiter = RateLimiter(max_calls=1, period=60)
        assert limiter.is_allowed("k") and not limiter.is_allowed("k")
        limiter.is_allowed("j")
        assert connect.call_count == 1  # doesn't retry Redis on every call


def test_falls_back_when_redis_errors_mid_flight(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://fake:6379/0")
    broken = fakeredis.FakeRedis()
    with patch("redis.Redis.from_url", return_value=broken):
        limiter = RateLimiter(max_calls=1, period=60)
        with patch.object(broken, "pipeline", side_effect=ConnectionError("reset")):
            assert limiter.is_allowed("k")
        assert rate_limit._redis_client is None


def test_memory_backend_can_be_forced(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://fake:6379/0")
    monkeypatch.setenv("RATE_LIMIT_BACKEND", "memory")
    with patch("redis.Redis.from_url") as connect:
        assert RateLimiter(max_calls=1).is_allowed("k")
        connect.assert_not_called()


def test_recall_webhook_is_rate_limited(client):
    from api_endpoints.coworker import calls

    with patch.object(calls._webhook_ip_limiter, "is_allowed", return_value=False):
        assert client.post("/api/coworker/meetings/recall/webhook?token=x", json={}).status_code == 429
    assert client.post("/api/coworker/meetings/recall/webhook?token=x", json={}).status_code == 403
    from itsdangerous import URLSafeSerializer

    token = URLSafeSerializer("test-secret", salt="recall-webhook").dumps({"u": 1, "m": 1})
    with patch.object(calls._webhook_meeting_limiter, "is_allowed", return_value=False):
        resp = client.post(f"/api/coworker/meetings/recall/webhook?token={token}", json={})
    assert resp.status_code == 429


# -- retention ---------------------------------------------------------------

@pytest.fixture
def s(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/ret.db")
    store.create_coworker(1, "Natan Vidra", "natan@example.com", mode="demo")
    store.create_coworker(2, "Dana Lee", "dana@example.com", mode="demo")
    return store


def _item(store: Store, user_id: int, ext: str, days_ago: int) -> None:
    store.add_item(user_id, {"provider": "gmail", "external_id": ext, "thread_id": ext, "kind": "email",
                             "direction": "inbound", "subject": ext, "body": "", "occurred_at": iso(utcnow() - timedelta(days=days_ago))})


def test_policy_never_below_backfill(monkeypatch):
    assert retention.policy() == {"items": 180, "transcripts": 180, "activity": 730}
    monkeypatch.setenv("COWORKER_RETENTION_DAYS", "30")
    assert retention.policy()["items"] == 91  # backfill is 90 days
    monkeypatch.setenv("COWORKER_RETENTION_DAYS", "junk")
    assert retention.policy()["items"] == 180


def test_purge_old_items_transcripts_activity(s):
    for uid in (1, 2):
        _item(s, uid, f"old-{uid}", 200)
        _item(s, uid, f"new-{uid}", 5)
    old_start = iso(utcnow() - timedelta(days=200))
    s.insert("cw_meetings", {"user_id": 1, "title": "Old call", "transcript": [{"who": "x", "text": "hi"}],
                             "summary": "kept", "started_at": old_start})
    s.insert("cw_meetings", {"user_id": 1, "title": "New call", "transcript": [{"who": "x", "text": "hi"}],
                             "started_at": iso()})
    s.insert("cw_activity", {"user_id": 1, "kind": "x", "summary": "ancient", "created_at": iso(utcnow() - timedelta(days=800))})
    one = retention.purge(s, 1)
    assert one["items"] == 1 and one["transcripts"] == 1 and one["activity"] == 1
    assert [i["external_id"] for i in s.items(2, kind="email", limit=10)].count("old-2") == 1  # other user untouched
    meetings = {m["title"]: m for m in s.query("SELECT * FROM cw_meetings")}
    assert meetings["Old call"]["transcript"] is None and meetings["Old call"]["summary"] == "kept"
    assert meetings["New call"]["transcript"]
    assert retention.purge(s)["items"] == 1  # everyone


def test_worker_runs_retention(app, monkeypatch):
    from coworker import worker

    monkeypatch.setattr(worker, "_last_purge", 0.0)
    with app.app_context(), patch("coworker.retention.purge", return_value={"items": 2, "transcripts": 0}) as purge:
        worker.run_once()
        worker.run_once()  # not again within the interval
    assert purge.call_count == 1


# -- error tracking ----------------------------------------------------------

def test_sentry_init_only_with_dsn(monkeypatch):
    monkeypatch.setattr(observability, "_initialised", False)
    assert observability.init("web") is False
    monkeypatch.setenv("SENTRY_DSN", "https://key@o0.ingest.sentry.io/0")
    with patch("sentry_sdk.init") as init:
        assert observability.init("worker") is True
        assert init.call_args.kwargs["send_default_pii"] is False
        assert observability.init("worker") is True
        assert init.call_count == 1
    with patch("sentry_sdk.capture_exception") as cap, patch("sentry_sdk.capture_message") as msg:
        observability.capture(ValueError("x"), user_id=1)
        assert observability.alert("k", "Something failed", user_id=1)
    cap.assert_called_once()
    msg.assert_called_once()
    monkeypatch.setattr(observability, "_initialised", False)


def test_alerts_are_throttled_and_posted_to_slack(monkeypatch):
    monkeypatch.setenv("ALERT_SLACK_WEBHOOK_URL", "https://hooks.slack.com/x")
    with patch("requests.post") as post:
        assert observability.alert("sync:1", "gmail sync failed", user_id=1)
        assert not observability.alert("sync:1", "gmail sync failed", user_id=1)
        assert observability.alert("sync:2", "gmail sync failed", user_id=2)
    assert post.call_count == 2 and "gmail sync failed (user_id=1)" in post.call_args_list[0].kwargs["json"]["text"]
    with patch("requests.post", side_effect=OSError("down")):
        assert observability.alert("sync:3", "x")  # never raises


def test_failed_action_and_sync_error_alert(s):
    from coworker import executor
    from coworker.connectors.base import ConnectorError, Workspace

    s.insert("cw_actions", {"user_id": 1, "type": "send_email", "status": "approved", "title": "Reply",
                            "payload": {}, "execute_after": iso(utcnow() - timedelta(minutes=1)), "created_at": iso()})
    with patch("coworker.executor._execute", side_effect=ConnectorError("quota", "rate_limited")), \
            patch("observability.alert") as alert:
        assert executor.run_due(s, 1)["failed"] == 1
    assert alert.call_args.args[0] == "action-failed:1:rate_limited"
    s.update_coworker(1, mode="live")
    s.upsert_connection(1, "google", status="connected", token_enc="")
    with patch("coworker.connectors.google.GoogleConnector.from_row") as from_row, patch("observability.alert") as alert:
        from_row.return_value.sync.side_effect = ConnectorError("500 from Gmail", "upstream")
        Workspace(s, 1).sync()
    assert alert.call_args.args[0] == "sync-error:google:1"
