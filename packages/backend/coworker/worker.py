"""Background worker: runs every user's coworker loop on an interval.

    python -m coworker.worker            # loop forever (default every 60s)
    python -m coworker.worker --once     # one pass, then exit

The web app also ticks while it's open, so the worker is only needed for
coworkers that should keep working when nobody has the app open.
"""
from __future__ import annotations

import argparse
import os
import time

import observability
from app import create_app
from coworker import retention

PURGE_EVERY_SECONDS = 6 * 3600
_last_purge = 0.0


def run_once() -> int:
    global _last_purge
    from api_endpoints.coworker.delegation import run_tick
    from coworker import sync_jobs
    from coworker.store import get_store

    store = get_store()
    try:
        sync_jobs.run_pending(store)  # syncs queued from the web app (onboarding, "Sync now")
    except Exception as exc:  # pragma: no cover - keep the loop alive
        print(f"[coworker] sync jobs failed: {exc}")
        observability.capture(exc, where="worker.sync_jobs")
    if time.monotonic() - _last_purge > PURGE_EVERY_SECONDS or not _last_purge:
        try:
            result = retention.purge(store)
            _last_purge = time.monotonic()
            if result["items"] or result["transcripts"]:
                print(f"[coworker] retention: {result}")
        except Exception as exc:  # pragma: no cover - keep the loop alive
            observability.capture(exc, where="worker.retention")
    started = time.monotonic()
    errors = 0
    users = [r["user_id"] for r in store.query("SELECT user_id FROM cw_coworkers WHERE status = 'active'")]
    for user_id in users:
        try:
            result = run_tick(int(user_id), force=True, inline_sync=True)
            if result.get("results") or result.get("executed"):
                print(f"[coworker] user {user_id}: {result}")
        except Exception as exc:  # keep going for other users
            errors += 1
            print(f"[coworker] user {user_id} failed: {exc}")
            observability.capture(exc, user_id=user_id, where="worker.run_tick")
    try:
        from coworker import ops

        ops.heartbeat(store, int((time.monotonic() - started) * 1000), len(users), errors)
    except Exception as exc:  # pragma: no cover - a heartbeat failure must not stop the work
        observability.capture(exc, where="worker.heartbeat")
    return len(users)


def main() -> None:  # pragma: no cover - CLI entrypoint
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()
    os.environ.setdefault("COWORKER_PROCESS", "worker")
    app = create_app()
    with app.app_context():
        while True:
            run_once()
            if args.once:
                return
            time.sleep(args.interval)


if __name__ == "__main__":  # pragma: no cover
    main()
