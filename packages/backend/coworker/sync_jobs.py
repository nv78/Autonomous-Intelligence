"""Background sync: pull Gmail/Calendar/Drive/Slack without blocking a request.

A first backfill can make hundreds of API calls, so web requests never sync
inline. They queue a job and return. The job runs on a short-lived thread in
the web process, or in ``coworker.worker`` when ``COWORKER_SYNC_MODE=worker``.
Either way a job is claimed with one conditional UPDATE, so the thread and
the worker can never run the same job twice.

Phases: ``queued`` -> ``syncing`` -> ``learning`` (memory and style rebuild)
-> ``done`` (or ``error``). The status endpoint reports the phase plus live
item counts, so onboarding can show progress while data arrives.
"""
from __future__ import annotations

import logging
import os
import threading
from datetime import timedelta
from typing import Any

from coworker.store import Store, iso, utcnow

log = logging.getLogger("coworker.sync")

STALE_SECONDS = 15 * 60  # a "running" job older than this is assumed dead
ACTIVE = ("queued", "running")


def _stale_cutoff() -> str:
    return iso(utcnow() - timedelta(seconds=STALE_SECONDS))


def current(store: Store, user_id: int) -> dict[str, Any] | None:
    return store.one("SELECT * FROM cw_sync_jobs WHERE user_id = %s ORDER BY id DESC LIMIT 1", (user_id,))


def request(store: Store, user_id: int, rebuild: bool = False) -> dict[str, Any]:
    """Queue a sync unless one is already queued or running. Returns the job."""
    job = current(store, user_id)
    if job and job["status"] in ACTIVE and not (job["status"] == "running" and (job["started_at"] or "") < _stale_cutoff()):
        if rebuild and not job["rebuild"]:
            store.execute("UPDATE cw_sync_jobs SET rebuild = 1 WHERE id = %s", (job["id"],))
            job["rebuild"] = 1
        return job
    job_id = store.insert("cw_sync_jobs", {
        "user_id": user_id, "status": "queued", "phase": "queued", "rebuild": int(rebuild), "requested_at": iso(),
    })
    row = store.one("SELECT * FROM cw_sync_jobs WHERE id = %s", (job_id,))
    assert row is not None
    return row


def claim(store: Store, job_id: int) -> bool:
    """Atomically move a job to running. Only one caller ever wins."""
    return store.execute(
        "UPDATE cw_sync_jobs SET status = 'running', phase = 'syncing', started_at = %s "
        "WHERE id = %s AND (status = 'queued' OR (status = 'running' AND started_at < %s))",
        (iso(), job_id, _stale_cutoff()),
    ) == 1


def _set(store: Store, job_id: int, **values: Any) -> None:
    store.update("cw_sync_jobs", job_id, None, values)


def run(store: Store, job: dict[str, Any]) -> dict[str, Any]:
    """Run a claimed job: sync every connected account, then rebuild memory."""
    from api_endpoints.coworker.core import refresh_knowledge
    from coworker.connectors.base import Workspace

    user_id = int(job["user_id"])
    try:
        counts = Workspace(store, user_id).sync()
        _set(store, job["id"], phase="learning", counts=counts)
        if any(counts.values()) or job.get("rebuild"):
            refresh_knowledge(user_id)
        coworker = store.get_coworker(user_id) or {}
        store.update_coworker(user_id, settings={**(coworker.get("settings") or {}), "last_sync": iso()})
        _set(store, job["id"], status="done", phase="done", finished_at=iso())
        return {"status": "done", "counts": counts}
    except Exception as exc:  # report, don't crash the worker or thread
        log.exception("sync job %s failed", job["id"])
        _set(store, job["id"], status="error", phase="error", error=str(exc)[:500], finished_at=iso())
        import observability

        observability.capture(exc, user_id=user_id, job_id=job["id"], where="sync")
        return {"status": "error", "error": str(exc)}


def run_job(store: Store, job_id: int) -> dict[str, Any] | None:
    if not claim(store, job_id):
        return None
    job = store.one("SELECT * FROM cw_sync_jobs WHERE id = %s", (job_id,))
    return run(store, job) if job else None


def run_pending(store: Store) -> int:
    """Worker entrypoint: run every queued (or abandoned) job."""
    rows = store.query(
        "SELECT id FROM cw_sync_jobs WHERE status = 'queued' OR (status = 'running' AND started_at < %s) ORDER BY id",
        (_stale_cutoff(),),
    )
    return sum(1 for r in rows if run_job(store, int(r["id"])) is not None)


def uses_worker() -> bool:
    return os.environ.get("COWORKER_SYNC_MODE", "thread") == "worker"


def start(store: Store, job: dict[str, Any]) -> None:
    """Run the job off the request: inline under tests, else on a thread
    (unless a dedicated worker owns sync)."""
    if job["status"] != "queued" or uses_worker():
        return
    from flask import current_app

    app = current_app._get_current_object()  # type: ignore[attr-defined]
    if app.config.get("TESTING") and not app.config.get("COWORKER_SYNC_THREADS"):
        run_job(store, int(job["id"]))
        return

    def target() -> None:
        with app.app_context():
            run_job(store, int(job["id"]))

    threading.Thread(target=target, name=f"coworker-sync-{job['id']}", daemon=True).start()


def status(store: Store, user_id: int) -> dict[str, Any]:
    job = current(store, user_id)
    rows = store.query(
        "SELECT provider, COUNT(*) AS n FROM cw_items WHERE user_id = %s GROUP BY provider", (user_id,)
    )
    items = {r["provider"]: int(r["n"]) for r in rows}
    return {
        "job": None if not job else {
            "id": job["id"], "status": job["status"], "phase": job["phase"], "counts": job.get("counts") or {},
            "error": job.get("error") or "", "requestedAt": job["requested_at"], "startedAt": job.get("started_at"),
            "finishedAt": job.get("finished_at"),
        },
        "running": bool(job and job["status"] in ACTIVE),
        "items": items,
        "total": sum(items.values()),
    }
