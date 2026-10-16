"""MySQL database connection and query helpers."""
from __future__ import annotations

import os
from typing import Any

from mysql.connector.errors import Error as MySQLError

_DUPLICATE_ENTRY_ERRNO = 1062

try:
    import mysql.connector
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False


def get_connection() -> Any:
    if not MYSQL_AVAILABLE:
        raise RuntimeError("mysql-connector-python not installed")
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        database=os.environ.get("DB_NAME", "anote"),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", ""),
        autocommit=True,
    )


def get_user_by_email(cnx: Any, email: str) -> dict | None:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email = %s LIMIT 1", (email,))
    row = cursor.fetchone()
    cursor.close()
    return row


def get_user_by_id(cnx: Any, user_id: int) -> dict | None:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s LIMIT 1", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    return row


def update_user_name(cnx: Any, user_id: int, name: str) -> bool:
    cursor = cnx.cursor()
    cursor.execute("UPDATE users SET name = %s WHERE id = %s", (name, user_id))
    updated = cursor.rowcount > 0
    cursor.close()
    return updated


def create_user(cnx: Any, email: str, password_hash: str, name: str = "") -> int:
    cursor = cnx.cursor()
    cursor.execute(
        "INSERT INTO users (email, password_hash, name, created_at) VALUES (%s, %s, %s, NOW())",
        (email, password_hash, name),
    )
    user_id: int = cursor.lastrowid
    cursor.close()
    return user_id


def set_password_hash(cnx: Any, user_id: int, password_hash: str) -> None:
    cursor = cnx.cursor()
    cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (password_hash, user_id))
    cursor.close()


# ---------------------------------------------------------------------------
# Folders
# ---------------------------------------------------------------------------

def create_folder(cnx: Any, user_id: int, name: str) -> int:
    cursor = cnx.cursor()
    cursor.execute(
        "INSERT INTO folders (user_id, name) VALUES (%s, %s)",
        (user_id, name),
    )
    folder_id: int = cursor.lastrowid
    cursor.close()
    return folder_id


def get_folders(cnx: Any, user_id: int) -> list[dict]:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, name, created_at FROM folders WHERE user_id = %s ORDER BY name",
        (user_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    return rows  # type: ignore[return-value]


def rename_folder(cnx: Any, folder_id: int, user_id: int, name: str) -> bool:
    cursor = cnx.cursor()
    cursor.execute(
        "UPDATE folders SET name = %s WHERE id = %s AND user_id = %s",
        (name, folder_id, user_id),
    )
    updated = cursor.rowcount > 0
    cursor.close()
    return updated


def delete_folder(cnx: Any, folder_id: int, user_id: int) -> bool:
    cursor = cnx.cursor()
    cursor.execute(
        "DELETE FROM folders WHERE id = %s AND user_id = %s",
        (folder_id, user_id),
    )
    deleted = cursor.rowcount > 0
    cursor.close()
    return deleted


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

def create_document(cnx: Any, user_id: int, doc_uuid: str, filename: str,
                    chunk_count: int, folder_id: int | None = None,
                    chat_id: int | None = None) -> int:
    cursor = cnx.cursor()
    cursor.execute(
        "INSERT INTO documents (user_id, folder_id, chat_id, doc_uuid, filename, chunk_count) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (user_id, folder_id, chat_id, doc_uuid, filename, chunk_count),
    )
    doc_id: int = cursor.lastrowid
    cursor.close()
    return doc_id


_DOCUMENT_SELECT = (
    "SELECT d.doc_uuid as id, d.filename, d.chunk_count, d.folder_id, d.chat_id, "
    "c.name as chat_name, d.created_at "
    "FROM documents d LEFT JOIN chats c ON d.chat_id = c.id"
)


def get_documents(cnx: Any, user_id: int, folder_id: int | None = None,
                  chat_id: int | None = None) -> list[dict]:
    cursor = cnx.cursor(dictionary=True)
    query = f"{_DOCUMENT_SELECT} WHERE d.user_id = %s"
    params: list[Any] = [user_id]
    if folder_id is not None:
        query += " AND d.folder_id = %s"
        params.append(folder_id)
    if chat_id is not None:
        query += " AND d.chat_id = %s"
        params.append(chat_id)
    query += " ORDER BY d.created_at DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close()
    return rows  # type: ignore[return-value]


def get_document_by_uuid(cnx: Any, user_id: int, doc_uuid: str) -> dict | None:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        f"{_DOCUMENT_SELECT} WHERE d.user_id = %s AND d.doc_uuid = %s",
        (user_id, doc_uuid),
    )
    row = cursor.fetchone()
    cursor.close()
    return row  # type: ignore[return-value]


def delete_document(cnx: Any, user_id: int, doc_uuid: str) -> bool:
    cursor = cnx.cursor()
    cursor.execute(
        "DELETE FROM documents WHERE user_id = %s AND doc_uuid = %s",
        (user_id, doc_uuid),
    )
    deleted = cursor.rowcount > 0
    cursor.close()
    return deleted


def move_document(cnx: Any, user_id: int, doc_uuid: str, folder_id: int | None) -> bool:
    cursor = cnx.cursor()
    cursor.execute(
        "UPDATE documents SET folder_id = %s WHERE user_id = %s AND doc_uuid = %s",
        (folder_id, user_id, doc_uuid),
    )
    updated = cursor.rowcount > 0
    cursor.close()
    return updated


# ---------------------------------------------------------------------------
# Chats
# ---------------------------------------------------------------------------

def create_chat(cnx: Any, user_id: int, name: str = "New Chat") -> int:
    cursor = cnx.cursor()
    cursor.execute(
        "INSERT INTO chats (user_id, name) VALUES (%s, %s)",
        (user_id, name),
    )
    chat_id: int = cursor.lastrowid
    cursor.close()
    return chat_id


def get_chats(cnx: Any, user_id: int) -> list[dict]:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, name, created_at FROM chats WHERE user_id = %s ORDER BY created_at DESC",
        (user_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    return rows  # type: ignore[return-value]


def get_chat(cnx: Any, user_id: int, chat_id: int) -> dict | None:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, name, created_at FROM chats WHERE id = %s AND user_id = %s",
        (chat_id, user_id),
    )
    row = cursor.fetchone()
    cursor.close()
    return row  # type: ignore[return-value]


def rename_chat(cnx: Any, user_id: int, chat_id: int, name: str) -> bool:
    cursor = cnx.cursor()
    cursor.execute(
        "UPDATE chats SET name = %s WHERE id = %s AND user_id = %s",
        (name, chat_id, user_id),
    )
    updated = cursor.rowcount > 0
    cursor.close()
    return updated


def delete_chat(cnx: Any, user_id: int, chat_id: int) -> bool:
    cursor = cnx.cursor()
    cursor.execute(
        "DELETE FROM chats WHERE id = %s AND user_id = %s",
        (chat_id, user_id),
    )
    deleted = cursor.rowcount > 0
    cursor.close()
    return deleted


def search_chats(cnx: Any, user_id: int, query: str, limit: int = 20) -> list[dict]:
    """Search a user's chats by title or message content.

    Returns one row per matching chat, with the earliest matching message
    (if any) as `content` — title-only matches have `content` as NULL.
    """
    cursor = cnx.cursor(dictionary=True)
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    like = f"%{escaped.lower()}%"
    cursor.execute(
        "SELECT c.id, c.name, c.created_at, m.content "
        "FROM chats c "
        "LEFT JOIN messages m ON m.chat_id = c.id AND LOWER(m.content) LIKE %s "
        "WHERE c.user_id = %s AND (LOWER(c.name) LIKE %s OR LOWER(m.content) LIKE %s) "
        "ORDER BY c.created_at DESC, m.id ASC",
        (like, user_id, like, like),
    )
    rows = cursor.fetchall()
    cursor.close()

    seen: dict[int, dict] = {}
    for row in rows:
        chat_id = row["id"]
        if chat_id not in seen:
            seen[chat_id] = row
    return list(seen.values())[:limit]  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

def create_message(cnx: Any, chat_id: int, role: str, content: str, model: str | None = None) -> int:
    cursor = cnx.cursor()
    cursor.execute(
        "INSERT INTO messages (chat_id, role, content, model) VALUES (%s, %s, %s, %s)",
        (chat_id, role, content, model),
    )
    message_id: int = cursor.lastrowid
    cursor.close()
    return message_id


def get_messages(cnx: Any, chat_id: int) -> list[dict]:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        "SELECT role, content, created_at FROM messages WHERE chat_id = %s ORDER BY id",
        (chat_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    return rows  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Provider keys (user-supplied Anthropic/OpenAI/Gemini keys)
# ---------------------------------------------------------------------------

def upsert_provider_key(cnx: Any, user_id: int, provider: str, key_encrypted: str) -> None:
    cursor = cnx.cursor()
    cursor.execute(
        "INSERT INTO user_provider_keys (user_id, provider, key_encrypted) VALUES (%s, %s, %s) "
        "ON DUPLICATE KEY UPDATE key_encrypted = VALUES(key_encrypted)",
        (user_id, provider, key_encrypted),
    )
    cursor.close()


def get_provider_keys(cnx: Any, user_id: int) -> list[dict]:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        "SELECT provider, key_encrypted FROM user_provider_keys WHERE user_id = %s",
        (user_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    return rows  # type: ignore[return-value]


def get_provider_key(cnx: Any, user_id: int, provider: str) -> str | None:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        "SELECT key_encrypted FROM user_provider_keys WHERE user_id = %s AND provider = %s",
        (user_id, provider),
    )
    row = cursor.fetchone()
    cursor.close()
    return row["key_encrypted"] if row else None


def delete_provider_key(cnx: Any, user_id: int, provider: str) -> bool:
    cursor = cnx.cursor()
    cursor.execute(
        "DELETE FROM user_provider_keys WHERE user_id = %s AND provider = %s",
        (user_id, provider),
    )
    deleted = cursor.rowcount > 0
    cursor.close()
    return deleted


# ---------------------------------------------------------------------------
# API usage metering (ported from the standalone backend/database/usage.py —
# flat credits-per-request, token counts stored for display only)
# ---------------------------------------------------------------------------

def deduct_credits(cnx: Any, user_id: int, credits_to_deduct: int = 1) -> bool:
    """Atomically deduct credits, refusing to go negative. Returns whether
    the deduction happened (False if the user had insufficient credits)."""
    cursor = cnx.cursor()
    cursor.execute(
        "UPDATE users SET credits = credits - %s WHERE id = %s AND credits >= %s",
        (credits_to_deduct, user_id, credits_to_deduct),
    )
    deducted = cursor.rowcount > 0
    cursor.close()
    return deducted


def log_api_usage(
    cnx: Any,
    user_id: int,
    endpoint: str,
    model: str | None,
    prompt_tokens: int,
    completion_tokens: int,
    credits_used: int = 1,
) -> None:
    cursor = cnx.cursor()
    total_tokens = prompt_tokens + completion_tokens
    cursor.execute(
        "INSERT INTO api_usage "
        "(user_id, endpoint, model, prompt_tokens, completion_tokens, total_tokens, credits_used) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (user_id, endpoint, model, prompt_tokens, completion_tokens, total_tokens, credits_used),
    )
    cursor.close()


def get_usage_rows(cnx: Any, user_id: int, limit: int = 50) -> list[dict]:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, endpoint, model, prompt_tokens, completion_tokens, total_tokens, "
        "credits_used, created_at FROM api_usage WHERE user_id = %s "
        "ORDER BY created_at DESC LIMIT %s",
        (user_id, min(limit, 200)),
    )
    rows = cursor.fetchall()
    cursor.close()
    return rows  # type: ignore[return-value]


def get_usage_summary(cnx: Any, user_id: int) -> dict:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        "SELECT COUNT(*) AS total_requests, "
        "COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens, "
        "COALESCE(SUM(completion_tokens), 0) AS completion_tokens, "
        "COALESCE(SUM(total_tokens), 0) AS total_tokens, "
        "COALESCE(SUM(credits_used), 0) AS credits_used "
        "FROM api_usage WHERE user_id = %s",
        (user_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    return row  # type: ignore[return-value]


def count_monthly_requests(cnx: Any, user_id: int) -> int:
    """Chat requests logged for *user_id* so far in the current calendar
    month — used to enforce the plan's monthly quota (constants.PLAN_SEARCHES)."""
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        "SELECT COUNT(*) AS cnt FROM api_usage "
        "WHERE user_id = %s AND endpoint IN ('/api/chat/stream', '/api/chat') "
        "AND created_at >= DATE_FORMAT(CURRENT_TIMESTAMP, '%%Y-%%m-01')",
        (user_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    return int(row["cnt"]) if row else 0


# ---------------------------------------------------------------------------
# Billing — credits, plan changes, Stripe customer linkage
# ---------------------------------------------------------------------------

def user_has_credits(cnx: Any, user_id: int, min_credits: int = 1) -> bool:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute("SELECT credits FROM users WHERE id = %s", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    return bool(row and row["credits"] >= min_credits)


def add_purchased_credits(cnx: Any, user_id: int, credits_to_add: int) -> bool:
    if credits_to_add <= 0:
        return False
    cursor = cnx.cursor()
    cursor.execute(
        "UPDATE users SET credits = credits + %s WHERE id = %s",
        (credits_to_add, user_id),
    )
    updated = cursor.rowcount > 0
    cursor.close()
    return updated


def set_plan_and_credits(cnx: Any, user_id: int, plan: str, credits: int) -> None:
    """Set a user's plan and (re)grant their plan's credit allowance —
    called on subscription checkout and on each renewal."""
    cursor = cnx.cursor()
    cursor.execute(
        "UPDATE users SET plan = %s, credits = %s WHERE id = %s",
        (plan, credits, user_id),
    )
    cursor.close()


def downgrade_to_free(cnx: Any, user_id: int) -> None:
    cursor = cnx.cursor()
    cursor.execute(
        "UPDATE users SET plan = 'free', credits = 0 WHERE id = %s",
        (user_id,),
    )
    cursor.close()


def upsert_stripe_customer(
    cnx: Any, user_id: int, stripe_id: str, plan: str, status: str, period_end: Any = None,
) -> None:
    cursor = cnx.cursor()
    cursor.execute(
        "INSERT INTO stripe_customers (user_id, stripe_id, plan, status, period_end) "
        "VALUES (%s, %s, %s, %s, %s) "
        "ON DUPLICATE KEY UPDATE stripe_id = VALUES(stripe_id), plan = VALUES(plan), "
        "status = VALUES(status), period_end = VALUES(period_end)",
        (user_id, stripe_id, plan, status, period_end),
    )
    cursor.close()


def update_stripe_customer_status(cnx: Any, stripe_id: str, status: str) -> None:
    cursor = cnx.cursor()
    cursor.execute(
        "UPDATE stripe_customers SET status = %s WHERE stripe_id = %s",
        (status, stripe_id),
    )
    cursor.close()


def get_user_id_for_stripe_customer(cnx: Any, stripe_id: str) -> int | None:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        "SELECT user_id FROM stripe_customers WHERE stripe_id = %s",
        (stripe_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    return int(row["user_id"]) if row else None


def get_stripe_customer(cnx: Any, user_id: int) -> dict | None:
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(
        "SELECT stripe_id, plan, status, period_end FROM stripe_customers WHERE user_id = %s",
        (user_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    return row  # type: ignore[return-value]


def claim_stripe_event(cnx: Any, event_id: str, event_type: str) -> bool:
    """Atomically record that a Stripe webhook event is being processed.

    Returns False if it was already recorded — Stripe can and does
    redeliver the same event more than once, and the caller should treat
    that as a no-op rather than reprocessing it (e.g. double-crediting a
    purchase). The INSERT's primary key collision is the atomicity
    guarantee here, so this is race-safe even if two deliveries of the
    same event arrive concurrently.
    """
    cursor = cnx.cursor()
    try:
        cursor.execute(
            "INSERT INTO stripe_events (event_id, event_type) VALUES (%s, %s)",
            (event_id, event_type),
        )
    except MySQLError as exc:
        if exc.errno != _DUPLICATE_ENTRY_ERRNO:
            raise
        return False
    finally:
        cursor.close()
    return True


def release_stripe_event(cnx: Any, event_id: str) -> None:
    """Release a failed webhook claim so Stripe can safely retry it."""
    cursor = cnx.cursor()
    cursor.execute("DELETE FROM stripe_events WHERE event_id = %s", (event_id,))
    cursor.close()
