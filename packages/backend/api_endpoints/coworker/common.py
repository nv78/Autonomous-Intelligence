"""Shared helpers for coworker routes."""
from __future__ import annotations

import os
from typing import Any

from flask import Blueprint, current_app, jsonify
from flask_jwt_extended import get_jwt_identity

from coworker.store import Store, get_store

coworker_bp = Blueprint("coworker", __name__, url_prefix="/api/coworker")


def uid() -> int:
    return int(get_jwt_identity())


def store() -> Store:
    return get_store()


def error(message: str, status: int = 400, code: str = "bad_request") -> tuple[Any, int]:
    return jsonify({"error": message, "code": code}), status


def owner_profile(user_id: int) -> tuple[str, str]:
    """Name and email from the main users table; empty if unavailable."""
    try:
        from database.db import get_connection, get_user_by_id

        cnx = get_connection()
        try:
            row = get_user_by_id(cnx, user_id) or {}
        finally:
            cnx.close()
        return str(row.get("name") or ""), str(row.get("email") or "")
    except Exception:
        return "", ""


def llm_available(user_id: int | None = None) -> bool:
    if os.environ.get("COWORKER_OFFLINE") == "1":
        return False
    if os.environ.get("ANTHROPIC_API_KEY") or current_app.config.get("ANTHROPIC_API_KEY"):
        return True
    if user_id is not None:
        from services.provider_keys import get_user_provider_key

        return bool(get_user_provider_key(user_id, "anthropic"))
    return False


def frontend_url() -> str:
    return os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")


def serialize_coworker(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "displayName": row["display_name"],
        "ownerName": row["owner_name"],
        "ownerEmail": row["owner_email"],
        "persona": row.get("persona") or "",
        "status": row["status"],
        "mode": row["mode"],
        "plan": row.get("plan") or "pilot",
        "autonomy": row.get("autonomy") or {},
        "settings": row.get("settings") or {},
        "onboarding": row.get("onboarding") or {},
        "styleProfile": row.get("style_profile") or {},
        "playbook": row.get("playbook") or {},
        "createdAt": row["created_at"],
    }
