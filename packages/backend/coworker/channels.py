"""Talk to the coworker from anywhere: one call for every surface that isn't the web chat.

Scheduled tasks, the Slack bot, and text messages all go through ``ask``.
It runs a turn of the same reasoning loop as the web chat (same tools,
same approvals), stores the exchange in a chat thread so the web app shows
it, and returns plain text for surfaces that can't render cards.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from coworker import brain, executor
from coworker.store import Store

log = logging.getLogger("coworker.channels")


def _marker(data: dict[str, Any]) -> str:
    return f"\n:::cw {json.dumps(data)}\n"


def _history(user_id: int, chat_id: int | None) -> list[dict[str, str]]:
    if not chat_id:
        return []
    try:
        from database.db import get_chat, get_connection, get_messages

        cnx = get_connection()
        try:
            if not get_chat(cnx, user_id, int(chat_id)):
                return []
            return [{"role": m["role"], "content": m["content"]} for m in get_messages(cnx, int(chat_id))]
        finally:
            cnx.close()
    except Exception as exc:  # no history is better than no answer
        log.info("couldn't load chat %s history: %s", chat_id, exc)
        return []


def _store_turn(user_id: int, chat_id: int | None, chat_name: str, user_text: str, content: str) -> int | None:
    """Save the exchange; opens a new chat when ``chat_id`` is missing or gone. Returns the chat id."""
    try:
        from database.db import create_chat, create_message, get_chat, get_connection

        cnx = get_connection()
        try:
            if not chat_id or not get_chat(cnx, user_id, int(chat_id)):
                chat_id = create_chat(cnx, user_id, (chat_name or "Coworker")[:255])
            create_message(cnx, int(chat_id), "user", user_text)
            if content:
                create_message(cnx, int(chat_id), "assistant", content, "coworker")
        finally:
            cnx.close()
        return int(chat_id)
    except Exception as exc:  # the work is done and returned to the caller either way
        log.warning("couldn't store a %s turn for user %s: %s", chat_name, user_id, exc)
        return int(chat_id) if chat_id else None


def plain(action: dict[str, Any]) -> str:
    status = {"proposed": "waiting for your approval", "executed": "done", "approved": "approved, sending shortly",
              "failed": "failed", "rejected": "skipped"}.get(action["status"], action["status"])
    return f"• {action['title']} ({status}, #{action['id']})"


def ask(store: Store, user_id: int, message: str, *, chat_id: int | None = None, chat_name: str = "Coworker",
        responsibility: dict[str, Any] | None = None, show_prompt: str | None = None) -> dict[str, Any]:
    """Run one turn. Returns ``{"text", "summary", "actions", "chat_id"}``.

    ``show_prompt`` is what the chat shows as the user's message when it
    differs from what the model is told (scheduled runs add instructions).
    """
    history = _history(user_id, chat_id)
    parts: list[str] = []
    texts: list[str] = []
    action_ids: list[int] = []
    for kind, payload in brain.run_turn(store, user_id, chat_id, message, history, responsibility=responsibility):
        if kind == "text":
            parts.append(payload)
            texts.append(payload)
        elif kind == "tool":
            parts.append(_marker({"t": "tool", **payload}))
        elif kind == "card":
            parts.append(_marker({"t": payload["type"], **{k: v for k, v in payload.items() if k != "type"}}))
            if payload["type"] == "action":
                action_ids.append(int(payload["id"]))
    content = "".join(parts).strip()
    chat_id = _store_turn(user_id, chat_id, chat_name, show_prompt or message, content)
    if chat_id and action_ids:  # cards made before the chat existed report back here once they run
        for action_id in action_ids:
            store.update("cw_actions", action_id, user_id, {"chat_id": chat_id})
    actions = [a for a in (store.get("cw_actions", i, user_id) for i in action_ids) if a]
    text = "".join(texts).strip()
    if actions:
        text = (text + "\n\n" if text else "") + "\n".join(plain(a) for a in actions)
    first = next((line.strip(" #*-") for line in text.splitlines() if line.strip(" #*-")), "Done.")
    return {"text": text or "Done.", "summary": first[:200], "actions": [executor.serialize(a) for a in actions],
            "chat_id": chat_id}


def thread_chat(store: Store, user_id: int, channel: str, key: str) -> int | None:
    """The web chat that holds this outside conversation (a Slack thread, a phone number), if any."""
    row = store.one("SELECT chat_id FROM cw_channel_threads WHERE user_id = %s AND channel = %s AND thread_key = %s",
                    (user_id, channel, key[:255]))
    return int(row["chat_id"]) if row and row.get("chat_id") else None


def remember_thread(store: Store, user_id: int, channel: str, key: str, chat_id: int | None) -> None:
    if not chat_id:
        return
    from coworker.store import IntegrityError, iso

    try:
        store.insert("cw_channel_threads", {"user_id": user_id, "channel": channel, "thread_key": key[:255],
                                            "chat_id": chat_id, "created_at": iso()})
    except IntegrityError:
        store.execute("UPDATE cw_channel_threads SET chat_id = %s WHERE user_id = %s AND channel = %s AND thread_key = %s",
                      (chat_id, user_id, channel, key[:255]))


def converse(store: Store, user_id: int, channel: str, key: str, message: str, chat_name: str,
             show_prompt: str | None = None) -> dict[str, Any]:
    """``ask`` inside the chat that belongs to this outside conversation, so follow-ups have context."""
    answer = ask(store, user_id, message, chat_id=thread_chat(store, user_id, channel, key), chat_name=chat_name,
                 show_prompt=show_prompt)
    remember_thread(store, user_id, channel, key, answer["chat_id"])
    return answer
