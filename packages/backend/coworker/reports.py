"""Report back into the chat where the user asked for something.

When an action that came from a chat is carried out, or a call the user
sent the coworker to ends, the coworker posts what it did into that same
chat thread: the email it sent, word for word, or the call summary. The
chat stays the one place to see what was asked and what happened.
"""
from __future__ import annotations

import json
import logging
from typing import Any

log = logging.getLogger("coworker.reports")


def marker(data: dict[str, Any]) -> str:
    return f"\n:::cw {json.dumps(data)}\n"


def post(user_id: int, chat_id: int | None, content: str) -> bool:
    """Append an assistant message to one of the user's chats."""
    if not chat_id or not content.strip():
        return False
    try:
        from database.db import create_message, get_chat, get_connection

        cnx = get_connection()
        try:
            if not get_chat(cnx, user_id, int(chat_id)):
                return False
            create_message(cnx, int(chat_id), "assistant", content, "coworker")
        finally:
            cnx.close()
        return True
    except Exception as exc:  # the action already happened; a missing report must not undo it
        log.warning("couldn't post a report to chat %s: %s", chat_id, exc)
        return False


def new_chat(user_id: int, name: str, content: str) -> int | None:
    """Open a chat in the user's sidebar that starts with a message from the coworker."""
    try:
        from database.db import create_chat, create_message, get_connection

        cnx = get_connection()
        try:
            chat_id = create_chat(cnx, user_id, name[:255] or "Coworker")
            create_message(cnx, chat_id, "assistant", content, "coworker")
        finally:
            cnx.close()
        return int(chat_id)
    except Exception as exc:  # the brief is also in Activity; a missing chat must not block the meeting
        log.warning("couldn't open a chat for user %s: %s", user_id, exc)
        return None


def _quote(text: str, limit: int = 1200) -> str:
    text = (text or "").strip()
    if len(text) > limit:
        text = text[:limit].rstrip() + "…"
    return "\n".join(f"> {line}" if line else ">" for line in text.splitlines())


def action_done(action: dict[str, Any], result: dict[str, Any]) -> str:
    """What to say in chat once an action from that chat went out."""
    p = action.get("payload") or {}
    kind = action["type"]
    if kind == "email.send":
        verb = "Saved a draft in Gmail" if result.get("draft") else "Sent"
        return (f"✅ {verb} to {', '.join(p.get('to') or [])}: **{p.get('subject', '')}**\n\n{_quote(p.get('body', ''))}"
                + marker({"t": "action", "id": action["id"]}))
    if kind == "slack.post":
        return f"✅ Posted in #{p.get('channel', '')}:\n\n{_quote(p.get('text', ''))}" + marker({"t": "action", "id": action["id"]})
    if kind == "calendar.create":
        return f"✅ Sent the invite **{p.get('title', '')}** to {', '.join(p.get('attendees') or [])}." + marker(
            {"t": "action", "id": action["id"]})
    if kind == "crm.update":
        where = "HubSpot" if "hubspot" in result else "your CRM notes"
        return f"✅ Logged the call with {p.get('company', '')} in {where}."
    return f"✅ Done: {action.get('title', '')}"


def meeting_summary(meeting: dict[str, Any], summary: dict[str, Any]) -> str:
    who = meeting.get("prospect_name") or meeting.get("title") or "the call"
    lines = [f"📞 **Call finished: {meeting.get('title') or who}**", "", summary.get("text") or ""]
    if summary.get("score") is not None:
        lines.append(f"\nLead score: **{summary['score']}/100**{' 🔥' if summary.get('hot') else ''}")
    if summary.get("action_items"):
        lines.append("\nNext steps:\n" + "\n".join(f"- {a}" for a in summary["action_items"]))
    text = "\n".join(lines)
    text += marker({"t": "meeting", "id": meeting["id"]})
    if summary.get("followup_action_id"):
        text += "\nI drafted the follow-up. Approve it and I'll send it:" + marker({"t": "action", "id": summary["followup_action_id"]})
    return text
