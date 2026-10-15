"""Background worker: runs every user's coworker loop on an interval.

    python -m coworker.worker            # loop forever (default every 60s)
    python -m coworker.worker --once     # one pass, then exit

The web app also ticks while it's open, so the worker is only needed for
coworkers that should keep working when nobody has the app open.
"""
from __future__ import annotations

import argparse
import time

from app import create_app


def run_once() -> int:
    from api_endpoints.coworker.delegation import run_tick
    from coworker.store import get_store

    users = [r["user_id"] for r in get_store().query("SELECT user_id FROM cw_coworkers WHERE status = 'active'")]
    for user_id in users:
        try:
            result = run_tick(int(user_id), force=True)
            if result.get("results") or result.get("executed"):
                print(f"[coworker] user {user_id}: {result}")
        except Exception as exc:  # keep going for other users
            print(f"[coworker] user {user_id} failed: {exc}")
    return len(users)


def main() -> None:  # pragma: no cover - CLI entrypoint
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()
    app = create_app()
    with app.app_context():
        while True:
            run_once()
            if args.once:
                return
            time.sleep(args.interval)


if __name__ == "__main__":  # pragma: no cover
    main()
