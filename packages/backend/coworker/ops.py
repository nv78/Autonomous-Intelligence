"""Running unattended: worker heartbeats, health, and run history.

Every worker pass writes a heartbeat. The web app reports the worker as
``ok``, ``stale`` (no pass for ``COWORKER_WORKER_STALE_SECONDS``, default
180), or ``missing`` (never ran). A stale worker raises an operator alert.
``python -m coworker.ops --check`` exits non-zero when this host's worker
is stale, for container health checks.
"""
from __future__ import annotations

import argparse
import os
import socket
import sys
from datetime import timedelta
from typing import Any

from coworker.store import IntegrityError, Store, iso, parse_iso, utcnow

_started = iso()


def worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"[:120]


def stale_after() -> timedelta:
    try:
        return timedelta(seconds=max(60, int(os.environ.get("COWORKER_WORKER_STALE_SECONDS", "180"))))
    except ValueError:
        return timedelta(seconds=180)


def heartbeat(store: Store, tick_ms: int, users: int, errors: int) -> None:
    values = {"last_tick_at": iso(), "tick_ms": tick_ms, "users": users, "errors": errors}
    me = worker_id()
    try:
        store.insert("cw_worker_heartbeats", {"worker": me, "started_at": _started, **values})
    except IntegrityError:
        store.execute("UPDATE cw_worker_heartbeats SET last_tick_at = %s, tick_ms = %s, users = %s, errors = %s "
                      "WHERE worker = %s", (values["last_tick_at"], tick_ms, users, errors, me))
    # forget workers gone for a day (old containers), so status reflects what's running
    store.execute("DELETE FROM cw_worker_heartbeats WHERE last_tick_at < %s", (iso(utcnow() - timedelta(days=1)),))


def worker_status(store: Store) -> dict[str, Any]:
    rows = store.query("SELECT * FROM cw_worker_heartbeats ORDER BY last_tick_at DESC")
    if not rows:
        return {"status": "missing", "lastTickAt": None, "workers": 0}
    last = parse_iso(rows[0]["last_tick_at"])
    fresh = [r for r in rows if (parse_iso(r["last_tick_at"]) or utcnow()) > utcnow() - stale_after()]
    status = "ok" if fresh else "stale"
    if status == "stale":
        import observability

        observability.alert("worker_stale", "The coworker worker has stopped: scheduled tasks and responsibilities "
                            "aren't running.", last_tick=rows[0]["last_tick_at"])
    return {"status": status, "lastTickAt": iso(last) if last else None, "workers": len(fresh),
            "tickMs": int(rows[0].get("tick_ms") or 0)}


def recent_runs(store: Store, user_id: int, limit: int = 50) -> list[dict[str, Any]]:
    rows = store.query(
        "SELECT r.*, p.name FROM cw_runs r LEFT JOIN cw_responsibilities p ON p.id = r.responsibility_id "
        "WHERE r.user_id = %s AND r.responsibility_id != 0 ORDER BY r.id DESC LIMIT %s", (user_id, max(1, min(limit, 200))))
    out = []
    for r in rows:
        started, finished = parse_iso(r.get("started_at") or ""), parse_iso(r.get("finished_at") or "")
        out.append({
            "id": r["id"], "responsibility": r.get("name") or "(removed)", "responsibilityId": r["responsibility_id"],
            "status": r["status"], "summary": r.get("summary") or "", "error": r.get("error") or "",
            "attempts": int(r.get("attempts") or 1), "at": r.get("started_at") or r["created_at"],
            "tokens": int(r.get("tokens") or 0),
            "costUsd": None if r.get("cost_micros") is None else round(int(r["cost_micros"]) / 1_000_000, 4),
            "durationMs": int((finished - started).total_seconds() * 1000) if started and finished else None,
        })
    return out


def main() -> None:  # pragma: no cover - container health check
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="exit 1 if no worker on this host ticked recently")
    args = parser.parse_args()
    from app import create_app
    from coworker.store import get_store

    with create_app().app_context():
        rows = get_store().query("SELECT last_tick_at FROM cw_worker_heartbeats WHERE worker LIKE %s",
                                 (f"{socket.gethostname()}:%",))
    ok = any((parse_iso(r["last_tick_at"]) or utcnow()) > utcnow() - stale_after() for r in rows)
    print("ok" if ok else "stale")
    if args.check and not ok:
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
