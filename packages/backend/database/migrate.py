"""Applies pending SQL files in database/migrations/ to the configured DB.

Tracks applied migrations in a schema_migrations table so each file runs
at most once. schema.sql seeds that table for migrations whose changes
are already part of the fresh-install schema, but that seed only takes
effect when MySQL runs schema.sql itself (a genuinely empty data
directory via docker-entrypoint-initdb.d) — a long-lived dev DB whose
volume predates that seeding, or whose schema was applied ad hoc, can
already have a migration's columns/tables without schema_migrations
knowing it. _apply_migration tolerates exactly that: a statement that
fails because its effect already exists is treated as a no-op rather
than aborting the whole run.

Run manually with `python -m database.migrate`, or automatically on
container start (see entrypoint.sh) — a MySQL named lock keeps concurrent
callers (e.g. multiple ECS tasks starting during a rolling deploy) from
applying the same migration twice at once.
"""
from __future__ import annotations

import os
from glob import glob

from mysql.connector.errors import Error as MySQLError

from database.db import get_connection

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")
LOCK_NAME = "anote_schema_migrations"
LOCK_TIMEOUT_SECONDS = 60

# MySQL errnos meaning "the thing this statement creates already exists" —
# safe to skip rather than treat as a real migration failure.
_ALREADY_APPLIED_ERRNOS = {
    1050,  # table already exists
    1060,  # duplicate column name
    1061,  # duplicate key name
    1022,  # duplicate key (index)
    1826,  # duplicate foreign key constraint name
}


def _ensure_migrations_table(cnx) -> None:
    cursor = cnx.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version     VARCHAR(255) PRIMARY KEY,
            applied_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.close()


def _applied_versions(cnx) -> set[str]:
    cursor = cnx.cursor()
    cursor.execute("SELECT version FROM schema_migrations")
    versions = {row[0] for row in cursor.fetchall()}
    cursor.close()
    return versions


def _pending_migrations(applied: set[str]) -> list[str]:
    paths = sorted(glob(os.path.join(MIGRATIONS_DIR, "*.sql")))
    return [p for p in paths if os.path.basename(p) not in applied]


def _strip_sql_comments(sql: str) -> str:
    """Drop full-line `--` comments before splitting on `;` — a semicolon
    inside a comment's prose (e.g. "already exists; skip it") would otherwise
    be mistaken for a statement terminator and split a comment mid-sentence,
    feeding the second half to MySQL as if it were SQL."""
    return "\n".join(
        line for line in sql.splitlines() if not line.strip().startswith("--")
    )


def _apply_migration(cnx, path: str) -> None:
    version = os.path.basename(path)
    with open(path, encoding="utf-8") as f:
        sql = _strip_sql_comments(f.read())
    cursor = cnx.cursor()
    try:
        for statement in filter(None, (s.strip() for s in sql.split(";"))):
            try:
                cursor.execute(statement)
            except MySQLError as exc:
                if exc.errno not in _ALREADY_APPLIED_ERRNOS:
                    raise
                print(f"[migrate] {version}: already applied ({exc}), skipping statement")
        cursor.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
    finally:
        cursor.close()
    print(f"[migrate] applied {version}")


def run_migrations() -> None:
    cnx = get_connection()
    try:
        lock_cursor = cnx.cursor()
        lock_cursor.execute("SELECT GET_LOCK(%s, %s)", (LOCK_NAME, LOCK_TIMEOUT_SECONDS))
        got_lock = lock_cursor.fetchone()[0] == 1
        lock_cursor.close()
        if not got_lock:
            raise RuntimeError(
                f"Could not acquire migration lock '{LOCK_NAME}' within "
                f"{LOCK_TIMEOUT_SECONDS}s; another migration may be stuck."
            )
        try:
            _ensure_migrations_table(cnx)
            applied = _applied_versions(cnx)
            pending = _pending_migrations(applied)
            if not pending:
                print("[migrate] no pending migrations")
            for path in pending:
                _apply_migration(cnx, path)
        finally:
            # Best-effort: if a migration above failed, the connection may be
            # in a state where issuing another query raises its own error —
            # that must never replace/hide the real migration failure.
            try:
                release_cursor = cnx.cursor()
                release_cursor.execute("SELECT RELEASE_LOCK(%s)", (LOCK_NAME,))
                release_cursor.fetchall()  # read the result, or close() raises "Unread result found"
                release_cursor.close()
            except MySQLError as exc:
                print(f"[migrate] failed to release lock '{LOCK_NAME}': {exc}")
    finally:
        cnx.close()


if __name__ == "__main__":
    run_migrations()
