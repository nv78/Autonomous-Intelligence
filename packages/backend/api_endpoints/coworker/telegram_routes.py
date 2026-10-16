"""Message your coworker on Telegram: link a chat, and Telegram's webhook (see ``coworker/telegram.py``)."""
from __future__ import annotations

import threading
from typing import Any

from flask import current_app, jsonify, request

from api_endpoints.coworker.common import coworker_bp, error, store, uid
from coworker import telegram
from middleware.auth import require_auth


def _fail(exc: telegram.TelegramError) -> tuple:
    return error(str(exc), exc.status, exc.code)


@coworker_bp.get("/telegram")
@require_auth
def get_telegram() -> tuple:
    return jsonify(telegram.state(store(), uid())), 200


@coworker_bp.post("/telegram")
@require_auth
def link_telegram() -> tuple:
    try:
        return jsonify(telegram.start_link(store(), uid())), 200
    except telegram.TelegramError as exc:
        return _fail(exc)


@coworker_bp.patch("/telegram")
@require_auth
def telegram_prefs() -> tuple:
    notify = (request.get_json(silent=True) or {}).get("notify")
    if not isinstance(notify, list):
        return error("notify must be a list")
    try:
        return jsonify(telegram.set_prefs(store(), uid(), [str(k) for k in notify])), 200
    except telegram.TelegramError as exc:
        return _fail(exc)


@coworker_bp.delete("/telegram")
@require_auth
def unlink_telegram() -> tuple:
    telegram.remove(store(), uid())
    return jsonify(telegram.state(store(), uid())), 200


@coworker_bp.post("/telegram/webhook")
def telegram_webhook() -> Any:
    """Telegram's webhook. Each update carries the secret set with setWebhook."""
    if not telegram.is_configured() or not telegram.uses_webhook():
        return error("Telegram webhook isn't configured", 501, "not_configured")
    if not telegram.valid_secret(request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")):
        return error("bad secret", 401, "unauthorized")
    update = request.get_json(silent=True) or {}
    app = current_app._get_current_object()  # type: ignore[attr-defined]

    def work() -> None:
        with app.app_context():
            try:
                telegram.handle_update(store(), update)
            except Exception as exc:
                app.logger.exception("Telegram update failed: %s", exc)

    if app.config.get("TESTING") and not app.config.get("COWORKER_SYNC_THREADS"):
        work()
    else:
        threading.Thread(target=work, name="coworker-telegram", daemon=True).start()
    return jsonify({"ok": True}), 200
