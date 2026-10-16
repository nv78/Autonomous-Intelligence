"""Message your coworker on Telegram: a free alternative to SMS (no Twilio, no carrier registration).

* **Setup**: create a bot with @BotFather and set ``TELEGRAM_BOT_TOKEN``. That's all for local or
  self-hosted use: the worker long-polls Telegram, so no public URL is needed. With a public backend,
  set ``TELEGRAM_WEBHOOK_SECRET`` too and run ``python -m coworker.telegram setup`` to switch to a
  webhook at ``<BACKEND_URL>/api/coworker/telegram/webhook``.
* **Linking**: the owner presses "Connect Telegram" in Settings and opens the one-time link
  (``t.me/<bot>?start=<code>``, valid 15 minutes). Only the private chat that opened it is linked.
  Messages from any other chat get one short reply and never reach a coworker.
* **Talking**: a message runs as a chat turn (same tools and approvals as the web chat) in the
  owner's "Telegram" chat. Proposals come back with Approve / Skip buttons. ``YES 12``, ``NO 12``,
  ``EDIT 12 <text>``, ``PAUSE`` and ``RESUME`` work as they do by text message.
* **Notifications**: new approvals (a setting) and scheduled tasks set to "Text me".
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import secrets
import sys
from datetime import timedelta
from typing import Any

import requests

from coworker.store import Store, iso, parse_iso, utcnow

log = logging.getLogger("coworker.telegram")

API = "https://api.telegram.org"
LINK_TTL = timedelta(minutes=15)
MAX_CHARS = 4000
TIMEOUT = 15
HELP = ("Ask me anything you'd ask in Ourogen chat, or hand off work. Tap Approve / Skip on a proposal, or reply "
        "YES 12 / NO 12 / EDIT 12 <new text>. PAUSE stops your coworker, RESUME restarts it.")
_offset = 0
_username = ""


class TelegramError(Exception):
    def __init__(self, message: str, code: str = "invalid", status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


def is_configured() -> bool:
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN"))


def uses_webhook() -> bool:
    return bool(os.environ.get("TELEGRAM_WEBHOOK_SECRET"))


def _api(method: str, **params: Any) -> Any:
    if not is_configured():
        raise TelegramError("Telegram isn't configured on this server.", "not_configured", 501)
    resp = requests.post(f"{API}/bot{os.environ['TELEGRAM_BOT_TOKEN']}/{method}", json=params,
                         timeout=TIMEOUT + int(params.get("timeout") or 0))
    data = resp.json() if resp.content else {}
    if resp.status_code >= 300 or not data.get("ok"):
        raise TelegramError(f"Telegram {method} failed ({resp.status_code}): {str(data.get('description'))[:200]}",
                            "provider_error", 502)
    return data.get("result")


def bot_username() -> str:
    global _username
    if not _username:
        _username = os.environ.get("TELEGRAM_BOT_USERNAME", "").lstrip("@") or str((_api("getMe") or {}).get("username") or "")
    return _username


def valid_secret(header: str) -> bool:
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
    return bool(secret) and hmac.compare_digest(secret, header or "")


def _hash(code: str) -> str:
    key = os.environ.get("JWT_SECRET_KEY", "") or os.environ.get("PROVIDER_KEY_ENCRYPTION_KEY", "") or "dev"
    return hmac.new(key.encode(), f"telegram:{code}".encode(), hashlib.sha256).hexdigest()


# -- linking ------------------------------------------------------------------------------------

def link_for(store: Store, user_id: int) -> dict[str, Any] | None:
    return store.one("SELECT * FROM cw_telegram WHERE user_id = %s", (user_id,))


def owner_of(store: Store, chat_id: str) -> dict[str, Any] | None:
    return store.one("SELECT * FROM cw_telegram WHERE chat_id = %s", (chat_id,)) if chat_id else None


def start_link(store: Store, user_id: int) -> dict[str, Any]:
    """A one-time t.me link that links whichever private chat opens it first."""
    if not is_configured():
        raise TelegramError("Telegram isn't configured on this server.", "not_configured", 501)
    code = secrets.token_urlsafe(18)  # Telegram's start parameter allows A-Z a-z 0-9 _ -
    fields = {"link_hash": _hash(code), "link_expires": iso(utcnow() + LINK_TTL)}
    row = link_for(store, user_id)
    if row:
        store.update("cw_telegram", int(row["id"]), user_id, fields)
    else:
        store.insert("cw_telegram", {"user_id": user_id, "chat_id": "", "prefs": {"notify": ["approvals"]},
                                     "created_at": iso(), **fields})
    return {**state(store, user_id), "link": f"https://t.me/{bot_username()}?start={code}"}


def _redeem(store: Store, code: str, chat_id: str, username: str) -> str:
    row = store.one("SELECT * FROM cw_telegram WHERE link_hash = %s", (_hash(code),)) if code else None
    expires = parse_iso((row or {}).get("link_expires"))
    if not row or not expires or expires < utcnow():
        return "That link has expired. Open Ourogen → Settings → Telegram and press Connect again."
    other = owner_of(store, chat_id)
    if other and int(other["user_id"]) != int(row["user_id"]):
        return "This Telegram account is already linked to another Ourogen coworker. Unlink it there first."
    user_id = int(row["user_id"])
    store.update("cw_telegram", int(row["id"]), user_id, {"chat_id": chat_id, "username": username[:255],
                                                          "link_hash": "", "link_expires": None, "linked_at": iso()})
    store.log(user_id, "settings", f"Linked Telegram{f' (@{username})' if username else ''}")
    return "Linked! I'm your Ourogen coworker. " + HELP


def set_prefs(store: Store, user_id: int, notify: list[str]) -> dict[str, Any]:
    row = link_for(store, user_id)
    if not row:
        raise TelegramError("Connect Telegram first.", "not_found", 404)
    store.update("cw_telegram", int(row["id"]), user_id,
                 {"prefs": {**(row.get("prefs") or {}), "notify": [k for k in notify if k == "approvals"]}})
    return state(store, user_id)


def remove(store: Store, user_id: int) -> None:
    store.execute("DELETE FROM cw_telegram WHERE user_id = %s", (user_id,))


def state(store: Store, user_id: int) -> dict[str, Any]:
    row = link_for(store, user_id) or {}
    return {"configured": is_configured(), "linked": bool(row.get("chat_id")), "username": row.get("username") or "",
            "notify": list((row.get("prefs") or {}).get("notify") or []), "bot": os.environ.get("TELEGRAM_BOT_USERNAME", "")}


# -- sending ------------------------------------------------------------------------------------

def _clean(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"\1", re.sub(r":::cw .*", "", text or "")).strip() or "Done."


def buttons(actions: list[dict[str, Any]]) -> dict[str, Any] | None:
    rows = [[{"text": f"✅ Approve #{a['id']}", "callback_data": f"cw:approve:{a['id']}"},
             {"text": "Skip", "callback_data": f"cw:reject:{a['id']}"}]
            for a in actions[:5] if a.get("status") == "proposed"]
    return {"inline_keyboard": rows} if rows else None


def send(chat_id: str, text: str, actions: list[dict[str, Any]] | None = None) -> None:
    body = _clean(text)
    if len(body) > MAX_CHARS:
        body = body[:MAX_CHARS - 40].rstrip() + "… (more in the Ourogen app)"
    params: dict[str, Any] = {"chat_id": chat_id, "text": body, "disable_web_page_preview": True}
    markup = buttons(actions or [])
    if markup:
        params["reply_markup"] = markup
    _api("sendMessage", **params)


def notify(store: Store, user_id: int, body: str, kind: str = "tasks",
           actions: list[dict[str, Any]] | None = None) -> bool:
    """Message the owner. Approval alerts are a setting; tasks choose "Text me" themselves."""
    row = link_for(store, user_id)
    if not row or not row.get("chat_id") or not is_configured():
        return False
    if kind == "approvals" and "approvals" not in ((row.get("prefs") or {}).get("notify") or []):
        return False
    try:
        send(str(row["chat_id"]), body, actions)
        return True
    except (TelegramError, requests.RequestException) as exc:
        log.warning("couldn't message user %s on Telegram: %s", user_id, exc)
        return False


def notify_approvals(store: Store, user_id: int, pending: list[dict[str, Any]]) -> bool:
    lines = [f"#{p['id']} {p['title'][:90]}" for p in pending[:5]]
    more = f"\n…and {len(pending) - 5} more in the app" if len(pending) > 5 else ""
    return notify(store, user_id, "Ourogen needs your OK:\n" + "\n".join(lines) + more, "approvals", pending[:5])


# -- receiving ----------------------------------------------------------------------------------

def handle_update(store: Store, update: dict[str, Any]) -> str:
    """Handle one Telegram update. Returns what happened (for logs and tests)."""
    from coworker import chatbots

    if "callback_query" in update:
        return _button(store, update["callback_query"])
    msg = update.get("message") or {}
    chat = msg.get("chat") or {}
    if not msg or chat.get("type") != "private":
        return "ignored"  # groups and channels never reach a coworker
    chat_id, text = str(chat.get("id") or ""), str(msg.get("text") or "").strip()
    username = str((msg.get("from") or {}).get("username") or "")
    if text.startswith("/start"):
        code = text.removeprefix("/start").strip()
        send(chat_id, _redeem(store, code, chat_id, username) if code or not owner_of(store, chat_id) else HELP)
        return "start"
    row = owner_of(store, chat_id)
    if not row:
        send(chat_id, "I'm an Ourogen AI coworker. To talk to yours, open Ourogen → Settings → Telegram and press Connect.")
        return "unlinked"
    user_id = int(row["user_id"])
    if not chatbots.claim(store, user_id, f"telegram:{update.get('update_id', '')}"):
        return "duplicate"
    if not text:
        send(chat_id, "I can read text messages. " + HELP)
        return "empty"
    reply, actions = command(store, user_id, chat_id, text)
    send(chat_id, reply, actions)
    return "command"


def command(store: Store, user_id: int, chat_id: str, text: str) -> tuple[str, list[dict[str, Any]]]:
    from coworker import channels, executor, sms

    word = text.strip().upper().lstrip("/")
    if word in ("HELP", "?"):
        return HELP, []
    if word == "PAUSE":
        executor.pause(store, user_id, "Paused from Telegram")
        return "Paused. Nothing will go out until you send RESUME or resume in the app.", []
    if word == "RESUME":
        executor.resume(store, user_id)
        return "Back on. I'll pick up where I left off.", []
    if (m := sms._YES.match(text)) or (m := sms._NO.match(text)) or (m := sms._EDIT.match(text)):
        return sms._decide(store, user_id, m, text), []
    answer = channels.converse(store, user_id, "telegram", chat_id, text[:4000], "✈️ Telegram")
    return answer["text"], [a for a in answer["actions"] if a.get("status") == "proposed"]


def _button(store: Store, query: dict[str, Any]) -> str:
    from coworker import chatbots

    chat_id = str(((query.get("message") or {}).get("chat") or {}).get("id") or "")
    row = owner_of(store, chat_id)
    m = re.fullmatch(r"cw:(approve|reject):(\d+)", str(query.get("data") or ""))
    if not row or not m or str((query.get("from") or {}).get("id") or "") != chat_id:
        _api("answerCallbackQuery", callback_query_id=query.get("id", ""), text="Only the person this coworker works for can do that.")
        return "refused button"
    user_id, action_id = int(row["user_id"]), int(m.group(2))
    if store.get("cw_actions", action_id, user_id) is None:
        _api("answerCallbackQuery", callback_query_id=query.get("id", ""), text="That action isn't yours.")
        return "refused button"
    result = chatbots.decide(store, user_id, m.group(1), action_id)
    _api("answerCallbackQuery", callback_query_id=query.get("id", ""), text=result[:190])
    send(chat_id, result)
    return "button"


def poll_once(store: Store, wait: int = 0) -> int:
    """Fetch and handle pending updates (polling mode: no public URL needed). Returns how many were handled."""
    global _offset
    if not is_configured() or uses_webhook():
        return 0
    updates = _api("getUpdates", offset=_offset, timeout=wait, allowed_updates=["message", "callback_query"]) or []
    for u in updates:
        _offset = max(_offset, int(u.get("update_id", 0)) + 1)
        try:
            handle_update(store, u)
        except Exception as exc:  # one bad update must not block the rest
            log.exception("Telegram update failed: %s", exc)
    return len(updates)


# -- setup (python -m coworker.telegram setup) ------------------------------------------------------

def configure_webhook() -> dict[str, str]:
    url = f"{os.environ.get('BACKEND_URL', '').rstrip('/')}/api/coworker/telegram/webhook"
    if not url.startswith("https://"):
        raise TelegramError("Set BACKEND_URL to your public https:// URL first (or leave the webhook off and let the worker poll).")
    if not uses_webhook():
        raise TelegramError("Set TELEGRAM_WEBHOOK_SECRET first (any random string); Telegram sends it with every update.")
    _api("setWebhook", url=url, secret_token=os.environ["TELEGRAM_WEBHOOK_SECRET"],
         allowed_updates=["message", "callback_query"])
    return {"webhook": url, "bot": bot_username()}


def main(argv: list[str]) -> None:  # pragma: no cover - CLI wrapper
    if argv[:1] == ["setup"]:
        print(configure_webhook())
    elif argv[:1] == ["polling"]:
        _api("deleteWebhook")
        print(f"Webhook removed; the worker will poll for @{bot_username()}.")
    else:
        raise SystemExit("usage: python -m coworker.telegram setup | polling")


if __name__ == "__main__":  # pragma: no cover
    main(sys.argv[1:])
