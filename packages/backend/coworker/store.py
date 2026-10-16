"""Persistence for the coworker.

Everything the coworker knows (synced items, people, memory) and does
(actions, runs, activity) lives in ``cw_*`` tables. The store speaks two
dialects:

* **MySQL** (default) — the same database as the rest of the backend,
  reached through ``database.db.get_connection``.
* **SQLite** — when ``COWORKER_DB_URL`` is ``sqlite:///<path>``. Used by the
  test-suite and handy for running the coworker without Docker.

Tables are created on first use (``CREATE TABLE IF NOT EXISTS``) so a
long-lived dev database picks them up without a manual migration; the same
DDL is also shipped as ``database/migrations/0005_coworker.sql``.

All timestamps are stored as ISO-8601 UTC strings and all structured
fields as JSON text, which keeps the two dialects byte-for-byte identical.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

JSON_COLUMNS = {
    "autonomy", "settings", "onboarding", "style_profile", "recipients", "meta",
    "trigger_spec", "tools", "payload", "result", "detail", "transcript",
    "metrics", "playbook", "answers", "risk", "counts", "policies", "prefs", "conversation",
}


def utcnow() -> datetime:
    return datetime.now(UTC)


def iso(dt: datetime | None = None) -> str:
    return (dt or utcnow()).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC)
    except ValueError:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def iso_in(**delta: float) -> str:
    return iso(utcnow() + timedelta(**delta))


# ---------------------------------------------------------------------------
# Schema. ``{pk}`` / ``{text}`` are expanded per dialect; everything else is
# portable SQL.
# ---------------------------------------------------------------------------

TABLES: dict[str, str] = {
    "cw_coworkers": """
        id {pk},
        user_id INT NOT NULL UNIQUE,
        owner_name VARCHAR(255) NOT NULL DEFAULT '',
        owner_email VARCHAR(255) NOT NULL DEFAULT '',
        display_name VARCHAR(255) NOT NULL DEFAULT '',
        persona {text},
        status VARCHAR(20) NOT NULL DEFAULT 'active',
        mode VARCHAR(20) NOT NULL DEFAULT 'demo',
        plan VARCHAR(40) NOT NULL DEFAULT 'pilot',
        autonomy {text},
        settings {text},
        onboarding {text},
        style_profile {text},
        playbook {text},
        created_at VARCHAR(40) NOT NULL,
        updated_at VARCHAR(40) NOT NULL
    """,
    "cw_connections": """
        id {pk},
        user_id INT NOT NULL,
        provider VARCHAR(40) NOT NULL,
        account_label VARCHAR(255) NOT NULL DEFAULT '',
        token_enc {text},
        scopes {text},
        sync_cursor {text},
        status VARCHAR(30) NOT NULL DEFAULT 'connected',
        error {text},
        last_synced_at VARCHAR(40),
        created_at VARCHAR(40) NOT NULL,
        UNIQUE (user_id, provider)
    """,
    "cw_items": """
        id {pk},
        user_id INT NOT NULL,
        provider VARCHAR(40) NOT NULL,
        external_id VARCHAR(255) NOT NULL,
        thread_id VARCHAR(255) NOT NULL DEFAULT '',
        kind VARCHAR(30) NOT NULL,
        direction VARCHAR(20) NOT NULL DEFAULT 'inbound',
        author_name VARCHAR(255) NOT NULL DEFAULT '',
        author_email VARCHAR(255) NOT NULL DEFAULT '',
        recipients {text},
        subject VARCHAR(500) NOT NULL DEFAULT '',
        body {text},
        channel VARCHAR(255) NOT NULL DEFAULT '',
        occurred_at VARCHAR(40) NOT NULL,
        meta {text},
        created_at VARCHAR(40) NOT NULL,
        UNIQUE (user_id, provider, external_id)
    """,
    "cw_people": """
        id {pk},
        user_id INT NOT NULL,
        email VARCHAR(255) NOT NULL,
        name VARCHAR(255) NOT NULL DEFAULT '',
        company VARCHAR(255) NOT NULL DEFAULT '',
        role VARCHAR(255) NOT NULL DEFAULT '',
        relationship VARCHAR(40) NOT NULL DEFAULT 'contact',
        interactions INT NOT NULL DEFAULT 0,
        last_contact_at VARCHAR(40),
        notes {text},
        user_edited INT NOT NULL DEFAULT 0,
        hidden INT NOT NULL DEFAULT 0,
        UNIQUE (user_id, email)
    """,
    "cw_memory": """
        id {pk},
        user_id INT NOT NULL,
        kind VARCHAR(30) NOT NULL,
        subject VARCHAR(255) NOT NULL DEFAULT '',
        title VARCHAR(500) NOT NULL DEFAULT '',
        detail {text},
        source_item_id INT,
        occurred_at VARCHAR(40),
        hidden INT NOT NULL DEFAULT 0,
        created_at VARCHAR(40) NOT NULL
    """,
    "cw_responsibilities": """
        id {pk},
        user_id INT NOT NULL,
        name VARCHAR(255) NOT NULL,
        template VARCHAR(60) NOT NULL DEFAULT 'custom',
        instruction {text},
        trigger_spec {text},
        tools {text},
        autonomy VARCHAR(20) NOT NULL DEFAULT 'approve',
        escalation {text},
        enabled INT NOT NULL DEFAULT 1,
        runs INT NOT NULL DEFAULT 0,
        last_run_at VARCHAR(40),
        created_at VARCHAR(40) NOT NULL
    """,
    "cw_runs": """
        id {pk},
        user_id INT NOT NULL,
        responsibility_id INT NOT NULL,
        trigger_key VARCHAR(255) NOT NULL,
        status VARCHAR(30) NOT NULL DEFAULT 'done',
        summary {text},
        created_at VARCHAR(40) NOT NULL,
        started_at VARCHAR(40),
        finished_at VARCHAR(40),
        attempts INT NOT NULL DEFAULT 1,
        error {text},
        tokens INT NOT NULL DEFAULT 0,
        cost_micros INT,
        UNIQUE (user_id, responsibility_id, trigger_key)
    """,
    "cw_worker_heartbeats": """
        id {pk},
        worker VARCHAR(120) NOT NULL UNIQUE,
        started_at VARCHAR(40) NOT NULL,
        last_tick_at VARCHAR(40) NOT NULL,
        tick_ms INT NOT NULL DEFAULT 0,
        users INT NOT NULL DEFAULT 0,
        errors INT NOT NULL DEFAULT 0
    """,
    "cw_actions": """
        id {pk},
        user_id INT NOT NULL,
        type VARCHAR(60) NOT NULL,
        status VARCHAR(30) NOT NULL DEFAULT 'proposed',
        title VARCHAR(500) NOT NULL DEFAULT '',
        payload {text},
        reasoning {text},
        autonomy VARCHAR(20) NOT NULL DEFAULT 'approve',
        approval_reason {text},
        risk {text},
        source_item_id INT,
        responsibility_id INT,
        chat_id INT,
        edited INT NOT NULL DEFAULT 0,
        feedback {text},
        result {text},
        error {text},
        execute_after VARCHAR(40),
        expires_at VARCHAR(40),
        decided_at VARCHAR(40),
        executed_at VARCHAR(40),
        created_at VARCHAR(40) NOT NULL
    """,
    "cw_activity": """
        id {pk},
        user_id INT NOT NULL,
        kind VARCHAR(40) NOT NULL,
        summary {text},
        detail {text},
        action_id INT,
        chat_id INT,
        created_at VARCHAR(40) NOT NULL
    """,
    "cw_consents": """
        id {pk},
        user_id INT NOT NULL,
        consent_type VARCHAR(40) NOT NULL,
        subject_name VARCHAR(255) NOT NULL DEFAULT '',
        code VARCHAR(20) NOT NULL DEFAULT '',
        phrase {text},
        transcript {text},
        evidence_path {text},
        status VARCHAR(20) NOT NULL DEFAULT 'pending',
        granted_at VARCHAR(40),
        revoked_at VARCHAR(40),
        created_at VARCHAR(40) NOT NULL
    """,
    "cw_twin_assets": """
        id {pk},
        user_id INT NOT NULL,
        kind VARCHAR(40) NOT NULL,
        filename VARCHAR(500) NOT NULL DEFAULT '',
        path {text},
        mime VARCHAR(120) NOT NULL DEFAULT '',
        size_bytes INT NOT NULL DEFAULT 0,
        created_at VARCHAR(40) NOT NULL
    """,
    "cw_meetings": """
        id {pk},
        user_id INT NOT NULL,
        title VARCHAR(500) NOT NULL DEFAULT '',
        mode VARCHAR(30) NOT NULL DEFAULT 'live_call',
        platform VARCHAR(40) NOT NULL DEFAULT '',
        meeting_url {text},
        bot_id VARCHAR(255) NOT NULL DEFAULT '',
        prospect_name VARCHAR(255) NOT NULL DEFAULT '',
        prospect_company VARCHAR(255) NOT NULL DEFAULT '',
        status VARCHAR(30) NOT NULL DEFAULT 'active',
        transcript {text},
        summary {text},
        answers {text},
        metrics {text},
        started_at VARCHAR(40) NOT NULL,
        ended_at VARCHAR(40)
    """,
    "cw_usage": """
        id {pk},
        user_id INT NOT NULL,
        kind VARCHAR(40) NOT NULL,
        quantity INT NOT NULL DEFAULT 0,
        created_at VARCHAR(40) NOT NULL
    """,
    "cw_sync_jobs": """
        id {pk},
        user_id INT NOT NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'queued',
        phase VARCHAR(20) NOT NULL DEFAULT 'queued',
        rebuild INT NOT NULL DEFAULT 0,
        counts {text},
        error {text},
        requested_at VARCHAR(40) NOT NULL,
        started_at VARCHAR(40),
        finished_at VARCHAR(40)
    """,
    "cw_orgs": """
        id {pk},
        name VARCHAR(255) NOT NULL,
        domain VARCHAR(255) NOT NULL DEFAULT '',
        owner_user_id INT NOT NULL,
        policies {text},
        created_at VARCHAR(40) NOT NULL,
        scim_token_hash VARCHAR(64) NOT NULL DEFAULT ''
    """,
    "cw_org_members": """
        id {pk},
        org_id INT NOT NULL,
        user_id INT,
        email VARCHAR(255) NOT NULL,
        role VARCHAR(20) NOT NULL DEFAULT 'member',
        status VARCHAR(20) NOT NULL DEFAULT 'invited',
        invited_by INT,
        invited_at VARCHAR(40),
        joined_at VARCHAR(40),
        UNIQUE (org_id, email)
    """,
    "cw_phones": """
        id {pk},
        user_id INT NOT NULL UNIQUE,
        number VARCHAR(20) NOT NULL,
        verified INT NOT NULL DEFAULT 0,
        code_hash VARCHAR(64) NOT NULL DEFAULT '',
        code_sent_at VARCHAR(40),
        attempts INT NOT NULL DEFAULT 0,
        prefs {text},
        created_at VARCHAR(40) NOT NULL
    """,
    "cw_telegram": """
        id {pk},
        user_id INT NOT NULL UNIQUE,
        chat_id VARCHAR(40) NOT NULL DEFAULT '',
        username VARCHAR(255) NOT NULL DEFAULT '',
        link_hash VARCHAR(64) NOT NULL DEFAULT '',
        link_expires VARCHAR(40),
        linked_at VARCHAR(40),
        prefs {text},
        created_at VARCHAR(40) NOT NULL
    """,
    "cw_inbound_addresses": """
        id {pk},
        user_id INT NOT NULL UNIQUE,
        handle VARCHAR(64) NOT NULL UNIQUE,
        created_at VARCHAR(40) NOT NULL
    """,
    "cw_bot_identities": """
        id {pk},
        platform VARCHAR(20) NOT NULL,
        external_id VARCHAR(255) NOT NULL,
        user_id INT NOT NULL,
        tenant VARCHAR(255) NOT NULL DEFAULT '',
        email VARCHAR(255) NOT NULL DEFAULT '',
        conversation {text},
        created_at VARCHAR(40) NOT NULL,
        UNIQUE (platform, external_id)
    """,
    "cw_verified_identities": """
        id {pk},
        user_id INT NOT NULL,
        provider VARCHAR(20) NOT NULL,
        subject VARCHAR(255) NOT NULL,
        email VARCHAR(255) NOT NULL DEFAULT '',
        managed_domain VARCHAR(255) NOT NULL DEFAULT '',
        tenant VARCHAR(255) NOT NULL DEFAULT '',
        created_at VARCHAR(40) NOT NULL,
        last_seen_at VARCHAR(40),
        UNIQUE (provider, subject)
    """,
    "cw_auth_epochs": """
        id {pk},
        user_id INT NOT NULL UNIQUE,
        tokens_valid_after VARCHAR(40) NOT NULL
    """,
    "cw_channel_threads": """
        id {pk},
        user_id INT NOT NULL,
        channel VARCHAR(20) NOT NULL,
        thread_key VARCHAR(255) NOT NULL,
        chat_id INT,
        created_at VARCHAR(40) NOT NULL,
        UNIQUE (user_id, channel, thread_key)
    """,
    "cw_turns": """
        id {pk},
        user_id INT NOT NULL,
        meeting_id INT NOT NULL,
        text {text},
        status VARCHAR(20) NOT NULL DEFAULT 'new',
        claimed_by INT,
        created_at VARCHAR(40) NOT NULL
    """,
    "cw_notifications": """
        id {pk},
        user_id INT NOT NULL,
        kind VARCHAR(30) NOT NULL,
        slot VARCHAR(40) NOT NULL,
        channel VARCHAR(20) NOT NULL DEFAULT '',
        subject VARCHAR(500) NOT NULL DEFAULT '',
        item_count INT NOT NULL DEFAULT 0,
        sent_at VARCHAR(40) NOT NULL,
        UNIQUE (user_id, kind, slot)
    """,
    "cw_pilot_applications": """
        id {pk},
        name VARCHAR(255) NOT NULL DEFAULT '',
        email VARCHAR(255) NOT NULL,
        company VARCHAR(255) NOT NULL DEFAULT '',
        role VARCHAR(255) NOT NULL DEFAULT '',
        answers {text},
        source VARCHAR(255) NOT NULL DEFAULT '',
        created_at VARCHAR(40) NOT NULL
    """,
}

INDEXES: list[tuple[str, str, str]] = [
    ("idx_cw_items_user_time", "cw_items", "user_id, occurred_at"),
    ("idx_cw_items_thread", "cw_items", "user_id, thread_id"),
    ("idx_cw_actions_user_status", "cw_actions", "user_id, status"),
    ("idx_cw_activity_user", "cw_activity", "user_id, created_at"),
    ("idx_cw_memory_user", "cw_memory", "user_id, kind"),
    ("idx_cw_sync_jobs_user", "cw_sync_jobs", "user_id, status"),
    ("idx_cw_turns_meeting", "cw_turns", "meeting_id, status"),
    ("idx_cw_org_members_user", "cw_org_members", "user_id, status"),
    ("idx_cw_phones_number", "cw_phones", "number, verified"),
    ("idx_cw_telegram_chat", "cw_telegram", "chat_id"),
    ("idx_cw_telegram_link", "cw_telegram", "link_hash"),
    ("idx_cw_verified_user", "cw_verified_identities", "user_id"),
]


# Columns added to tables that already exist in production. CREATE TABLE IF NOT EXISTS
# won't add them, so ensure_schema runs these and ignores "already there".
ADDED_COLUMNS: list[tuple[str, str, str]] = [
    ("cw_runs", "started_at", "VARCHAR(40)"),
    ("cw_runs", "finished_at", "VARCHAR(40)"),
    ("cw_runs", "attempts", "INT NOT NULL DEFAULT 1"),
    ("cw_runs", "error", "{text}"),
    ("cw_runs", "tokens", "INT NOT NULL DEFAULT 0"),
    ("cw_orgs", "scim_token_hash", "VARCHAR(64) NOT NULL DEFAULT ''"),
    ("cw_runs", "cost_micros", "INT"),
]


def ddl(dialect: str) -> list[str]:
    pk = "INTEGER PRIMARY KEY AUTOINCREMENT" if dialect == "sqlite" else "INT AUTO_INCREMENT PRIMARY KEY"
    text = "TEXT" if dialect == "sqlite" else "MEDIUMTEXT"
    statements = [
        f"CREATE TABLE IF NOT EXISTS {name} ({body.format(pk=pk, text=text).strip()})"
        for name, body in TABLES.items()
    ]
    for idx, table, cols in INDEXES:
        if dialect == "sqlite":
            statements.append(f"CREATE INDEX IF NOT EXISTS {idx} ON {table} ({cols})")
        else:
            statements.append(f"CREATE INDEX {idx} ON {table} ({cols})")
    statements += [f"ALTER TABLE {table} ADD COLUMN {col} {kind.format(text=text)}" for table, col, kind in ADDED_COLUMNS]
    return statements


_DUPLICATE_COLUMN_ERRNO = 1060
_DUPLICATE_INDEX_ERRNO = 1061
_DUPLICATE_ENTRY_ERRNO = 1062


class IntegrityError(Exception):
    """Raised when a UNIQUE constraint rejects a row (either dialect)."""


class Store:
    """Thin, dialect-neutral query layer over the ``cw_*`` tables."""

    _initialised: set[str] = set()
    _init_lock = threading.Lock()

    def __init__(self, url: str | None = None) -> None:
        self.url = url if url is not None else os.environ.get("COWORKER_DB_URL", "")
        self.dialect = "sqlite" if self.url.startswith("sqlite:///") else "mysql"
        self._sqlite_path = self.url[len("sqlite:///"):] if self.dialect == "sqlite" else ""
        self.ensure_schema()

    # -- connections -------------------------------------------------------

    def _connect(self) -> Any:
        if self.dialect == "sqlite":
            cnx = sqlite3.connect(self._sqlite_path, timeout=30, check_same_thread=False)
            cnx.row_factory = sqlite3.Row
            return cnx
        from database.db import get_connection

        return get_connection()

    @contextmanager
    def _cursor(self) -> Iterator[Any]:
        cnx = self._connect()
        try:
            cur = cnx.cursor() if self.dialect == "sqlite" else cnx.cursor(dictionary=True)
            try:
                yield cur
                if self.dialect == "sqlite":
                    cnx.commit()
            finally:
                cur.close()
        finally:
            cnx.close()

    def _sql(self, sql: str) -> str:
        return sql.replace("%s", "?") if self.dialect == "sqlite" else sql

    def ensure_schema(self) -> None:
        key = f"{self.dialect}:{self._sqlite_path or os.environ.get('DB_HOST', '')}"
        if key in Store._initialised:
            return
        with Store._init_lock:
            if key in Store._initialised:
                return
            with self._cursor() as cur:
                for stmt in ddl(self.dialect):
                    try:
                        cur.execute(stmt)
                    except Exception as exc:
                        if "duplicate column" in str(exc).lower():
                            continue  # sqlite: the column is already there
                        if getattr(exc, "errno", None) not in (_DUPLICATE_INDEX_ERRNO, _DUPLICATE_COLUMN_ERRNO):  # pragma: no cover
                            raise
            Store._initialised.add(key)

    # -- generic helpers ---------------------------------------------------

    def execute(self, sql: str, params: Iterable[Any] = ()) -> int:
        """Run a write statement; return lastrowid for inserts else rowcount."""
        with self._cursor() as cur:
            try:
                cur.execute(self._sql(sql), tuple(params))
            except sqlite3.IntegrityError as exc:
                raise IntegrityError(str(exc)) from exc
            except Exception as exc:
                if getattr(exc, "errno", None) == _DUPLICATE_ENTRY_ERRNO:
                    raise IntegrityError(str(exc)) from exc
                raise
            if sql.lstrip().upper().startswith("INSERT"):
                return int(cur.lastrowid or 0)
            return int(cur.rowcount or 0)

    def query(self, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
        with self._cursor() as cur:
            cur.execute(self._sql(sql), tuple(params))
            rows = cur.fetchall()
        return [_decode(dict(r)) for r in rows]

    def one(self, sql: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def insert(self, table: str, values: dict[str, Any]) -> int:
        cols = list(values)
        placeholders = ", ".join(["%s"] * len(cols))
        return self.execute(
            f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})",
            [_encode(c, values[c]) for c in cols],
        )

    def update(self, table: str, row_id: int, user_id: int | None, values: dict[str, Any]) -> int:
        if not values:
            return 0
        sets = ", ".join(f"{c} = %s" for c in values)
        params = [_encode(c, v) for c, v in values.items()] + [row_id]
        where = "id = %s"
        if user_id is not None:
            where += " AND user_id = %s"
            params.append(user_id)
        return self.execute(f"UPDATE {table} SET {sets} WHERE {where}", params)

    def get(self, table: str, row_id: int, user_id: int | None = None) -> dict[str, Any] | None:
        if user_id is None:
            return self.one(f"SELECT * FROM {table} WHERE id = %s", (row_id,))
        return self.one(f"SELECT * FROM {table} WHERE id = %s AND user_id = %s", (row_id, user_id))

    # -- coworker profile --------------------------------------------------

    def get_coworker(self, user_id: int) -> dict[str, Any] | None:
        return self.one("SELECT * FROM cw_coworkers WHERE user_id = %s", (user_id,))

    def create_coworker(self, user_id: int, owner_name: str, owner_email: str, mode: str = "demo") -> dict[str, Any]:
        existing = self.get_coworker(user_id)
        if existing:
            return existing
        first = (owner_name or "Your").split()[0]
        now = iso()
        try:
            self.insert("cw_coworkers", {
                "user_id": user_id,
                "owner_name": owner_name,
                "owner_email": owner_email,
                "display_name": f"{first}'s AI coworker",
                "persona": "",
                "status": "active",
                "mode": mode,
                "autonomy": {},
                "settings": {},
                "onboarding": {"step": "connect", "completed": False},
                "style_profile": {},
                "playbook": {},
                "created_at": now,
                "updated_at": now,
            })
        except IntegrityError:
            pass
        coworker = self.get_coworker(user_id)
        assert coworker is not None
        return coworker

    def update_coworker(self, user_id: int, **values: Any) -> None:
        coworker = self.get_coworker(user_id)
        if not coworker:
            return
        values["updated_at"] = iso()
        self.update("cw_coworkers", coworker["id"], user_id, values)

    # -- connections -------------------------------------------------------

    def upsert_connection(self, user_id: int, provider: str, **values: Any) -> int:
        row = self.one(
            "SELECT id FROM cw_connections WHERE user_id = %s AND provider = %s", (user_id, provider)
        )
        if row:
            self.update("cw_connections", row["id"], user_id, values)
            return int(row["id"])
        return self.insert("cw_connections", {
            "user_id": user_id, "provider": provider, "created_at": iso(), **values,
        })

    def get_connection_row(self, user_id: int, provider: str) -> dict[str, Any] | None:
        return self.one(
            "SELECT * FROM cw_connections WHERE user_id = %s AND provider = %s", (user_id, provider)
        )

    def list_connections(self, user_id: int) -> list[dict[str, Any]]:
        return self.query("SELECT * FROM cw_connections WHERE user_id = %s ORDER BY provider", (user_id,))

    def delete_connection(self, user_id: int, provider: str) -> int:
        return self.execute(
            "DELETE FROM cw_connections WHERE user_id = %s AND provider = %s", (user_id, provider)
        )

    # -- items -------------------------------------------------------------

    def add_item(self, user_id: int, item: dict[str, Any]) -> int | None:
        """Insert a synced item; return its id, or None if already present."""
        values = {
            "user_id": user_id,
            "thread_id": "",
            "direction": "inbound",
            "author_name": "",
            "author_email": "",
            "recipients": [],
            "subject": "",
            "body": "",
            "channel": "",
            "meta": {},
            "created_at": iso(),
            **item,
        }
        try:
            return self.insert("cw_items", values)
        except IntegrityError:
            return None

    def items(
        self,
        user_id: int,
        *,
        provider: str | None = None,
        kind: str | None = None,
        thread_id: str | None = None,
        direction: str | None = None,
        since: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM cw_items WHERE user_id = %s"
        params: list[Any] = [user_id]
        for col, val in (("provider", provider), ("kind", kind), ("thread_id", thread_id), ("direction", direction)):
            if val is not None:
                sql += f" AND {col} = %s"
                params.append(val)
        if since:
            sql += " AND occurred_at >= %s"
            params.append(since)
        sql += " ORDER BY occurred_at DESC, id DESC LIMIT %s"
        params.append(limit)
        return self.query(sql, params)

    def thread(self, user_id: int, thread_id: str) -> list[dict[str, Any]]:
        return list(reversed(self.items(user_id, thread_id=thread_id, limit=200)))

    def delete_items(self, user_id: int, provider: str | None = None) -> int:
        if provider:
            return self.execute("DELETE FROM cw_items WHERE user_id = %s AND provider = %s", (user_id, provider))
        return self.execute("DELETE FROM cw_items WHERE user_id = %s", (user_id,))

    # -- people & memory ---------------------------------------------------

    def people(self, user_id: int, include_hidden: bool = False) -> list[dict[str, Any]]:
        sql = "SELECT * FROM cw_people WHERE user_id = %s"
        if not include_hidden:
            sql += " AND hidden = 0"
        return self.query(sql + " ORDER BY interactions DESC, name", (user_id,))

    def person_by_email(self, user_id: int, email: str) -> dict[str, Any] | None:
        return self.one("SELECT * FROM cw_people WHERE user_id = %s AND email = %s", (user_id, email.lower()))

    def memories(self, user_id: int, kind: str | None = None, include_hidden: bool = False) -> list[dict[str, Any]]:
        sql = "SELECT * FROM cw_memory WHERE user_id = %s"
        params: list[Any] = [user_id]
        if kind:
            sql += " AND kind = %s"
            params.append(kind)
        if not include_hidden:
            sql += " AND hidden = 0"
        return self.query(sql + " ORDER BY occurred_at DESC, id DESC", params)

    # -- activity ----------------------------------------------------------

    def log(self, user_id: int, kind: str, summary: str, detail: dict | None = None,
            action_id: int | None = None, chat_id: int | None = None) -> int:
        return self.insert("cw_activity", {
            "user_id": user_id, "kind": kind, "summary": summary, "detail": detail or {},
            "action_id": action_id, "chat_id": chat_id, "created_at": iso(),
        })

    def activity(self, user_id: int, limit: int = 200, since: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM cw_activity WHERE user_id = %s"
        params: list[Any] = [user_id]
        if since:
            sql += " AND created_at >= %s"
            params.append(since)
        sql += " ORDER BY id DESC LIMIT %s"
        params.append(limit)
        return self.query(sql, params)

    # -- usage -------------------------------------------------------------

    def add_usage(self, user_id: int, kind: str, quantity: int) -> None:
        self.insert("cw_usage", {"user_id": user_id, "kind": kind, "quantity": int(quantity), "created_at": iso()})

    def usage_since(self, user_id: int, since: str) -> dict[str, int]:
        rows = self.query(
            "SELECT kind, SUM(quantity) AS total FROM cw_usage WHERE user_id = %s AND created_at >= %s GROUP BY kind",
            (user_id, since),
        )
        return {r["kind"]: int(r["total"] or 0) for r in rows}


def _encode(column: str, value: Any) -> Any:
    if column in JSON_COLUMNS and value is not None and not isinstance(value, str):
        return json.dumps(value, default=str)
    if isinstance(value, bool):
        return int(value)
    return value


def _decode(row: dict[str, Any]) -> dict[str, Any]:
    for col in JSON_COLUMNS & row.keys():
        value = row[col]
        if isinstance(value, bytes | bytearray):
            value = value.decode()
        if isinstance(value, str) and value:
            try:
                row[col] = json.loads(value)
            except ValueError:
                pass
        elif value is None or value == "":
            row[col] = None
    return row


_store_cache: dict[str, Store] = {}


def get_store() -> Store:
    """Return the process-wide store for the configured backend.

    Reads ``COWORKER_DB_URL`` from the Flask app config when inside an app
    context (so tests can point each app at its own SQLite file), else from
    the environment.
    """
    url = os.environ.get("COWORKER_DB_URL", "")
    try:
        from flask import current_app, has_app_context

        if has_app_context():
            url = str(current_app.config.get("COWORKER_DB_URL") or url)
    except ImportError:  # pragma: no cover
        pass
    store = _store_cache.get(url)
    if store is None:
        store = Store(url)
        _store_cache[url] = store
    return store
