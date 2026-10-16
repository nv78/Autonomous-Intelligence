"""Data retention.

Synced content (email, Slack, calendar, docs) older than
``COWORKER_RETENTION_DAYS`` (default 180) is deleted, along with call
transcripts older than ``COWORKER_TRANSCRIPT_RETENTION_DAYS`` (default: the
same). The summary, score, and answers of a call are kept: they're the
record of what happened, without the raw words. Activity logs are the audit
trail and are kept for ``COWORKER_ACTIVITY_RETENTION_DAYS`` (default 730).

Retention never goes below the sync backfill window
(``COWORKER_BACKFILL_DAYS``), or the next sync would just fetch the deleted
mail again.

Twin files and consent recordings live as long as the consent: revoking it
deletes them immediately (see ``twin.revoke``).
"""
from __future__ import annotations

import os
from datetime import timedelta
from typing import Any

from coworker.store import Store, iso, utcnow


def _days(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, str(default))))
    except ValueError:
        return default


def policy() -> dict[str, int]:
    backfill = _days("COWORKER_BACKFILL_DAYS", 90)
    items = max(_days("COWORKER_RETENTION_DAYS", 180), backfill + 1)
    return {
        "items": items,
        "transcripts": _days("COWORKER_TRANSCRIPT_RETENTION_DAYS", items),
        "activity": _days("COWORKER_ACTIVITY_RETENTION_DAYS", 730),
    }


def purge(store: Store, user_id: int | None = None) -> dict[str, Any]:
    """Apply the policy to one user, or to everyone when ``user_id`` is None."""
    p = policy()
    now = utcnow()
    scope, params = ("", ()) if user_id is None else (" AND user_id = %s", (user_id,))

    def cutoff(days: int) -> str:
        return iso(now - timedelta(days=days))

    items = store.execute(f"DELETE FROM cw_items WHERE occurred_at < %s{scope}", (cutoff(p["items"]), *params))
    transcripts = store.execute(
        f"UPDATE cw_meetings SET transcript = NULL WHERE transcript IS NOT NULL AND started_at < %s{scope}",
        (cutoff(p["transcripts"]), *params),
    )
    activity = store.execute(f"DELETE FROM cw_activity WHERE created_at < %s{scope}", (cutoff(p["activity"]), *params))
    sync_jobs = store.execute(f"DELETE FROM cw_sync_jobs WHERE requested_at < %s{scope}", (cutoff(30), *params))
    return {"items": items, "transcripts": transcripts, "activity": activity, "syncJobs": sync_jobs, "policy": p}
