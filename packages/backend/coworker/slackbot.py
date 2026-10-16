"""The coworker as a Slack bot: @mention it in any channel, or DM it.

The user-token connector (``connectors/slack.py``) reads Slack *as the
user*. The bot is a separate identity in the same Slack app, so people can
talk *to* the coworker:

* **The owner** (the person whose Slack account installed it) mentions or
  DMs the bot: that's a command, the same as typing in the web chat. Same
  tools, same approvals. Each Slack thread (or DM) maps to one web chat,
  so follow-ups keep their context, and proposed actions come back with
  Approve / Skip buttons.
* **A teammate** mentions or DMs it: that's a question for the owner's
  coworker. It answers in the thread from the owner's memory and docs when
  it's confident *and* the owner lets it post on Slack without asking
  (``slack.post`` autonomy ``notify`` or ``silent``). Otherwise it replies
  that it'll check, proposes the answer for the owner to approve, or, when
  it doesn't know, asks the owner by DM. People from other companies (Slack
  Connect channels) always go through the owner's approval.

Turn it on with ``SLACK_BOT_ENABLED=1`` once the Slack app has a bot user,
the bot scopes below, the ``app_mention`` and ``message.im`` bot events,
the Messages tab in App Home, and Interactivity pointed at
``<BACKEND_URL>/api/coworker/slack/interactive``. Users reconnect Slack once
to add the bot. In a workspace where several people installed it, a
teammate's question goes to the coworker of the owner it mentions, or else
to the first person who installed it.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any

from coworker.connectors import slack
from coworker.connectors.base import ConnectorError, decrypt_token
from coworker.store import IntegrityError, Store, iso

log = logging.getLogger("coworker.slackbot")

BOT_SCOPES = ["app_mentions:read", "chat:write", "im:history", "im:read", "im:write", "users:read"]
_dm_cache: dict[tuple[str, str], bool] = {}


def enabled() -> bool:
    return os.environ.get("SLACK_BOT_ENABLED", "") == "1"


def installs(store: Store, team_id: str) -> list[tuple[int, dict[str, Any]]]:
    """(user_id, token) for each owner whose Slack connection includes the bot, oldest first."""
    out = []
    for row in store.query("SELECT user_id, token_enc FROM cw_connections WHERE provider = 'slack' "
                           "AND status IN ('connected', 'syncing') ORDER BY id"):
        token = decrypt_token(row.get("token_enc"))
        if token.get("bot_token") and token.get("team_id") == team_id:
            out.append((int(row["user_id"]), token))
    return out


def _is_bot_dm(token: dict[str, Any], channel: str) -> bool:
    """A DM with the bot (not between two people). The bot can only see its own DMs."""
    key = (token["bot_token"][-12:], channel)
    if key not in _dm_cache:
        try:
            info = slack._call("conversations.info", token["bot_token"], channel=channel).get("channel", {})
            _dm_cache[key] = bool(info.get("is_im"))
        except ConnectorError:
            _dm_cache[key] = False
    return _dm_cache[key]


def _clean(text: str, bot_user_id: str) -> str:
    return re.sub(rf"<@{re.escape(bot_user_id)}>", "", text or "").strip()


def to_mrkdwn(text: str) -> str:
    """Markdown from the chat → Slack's mrkdwn (bold, links, headings)."""
    text = re.sub(r":::cw .*", "", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"<\2|\1>", text)
    return re.sub(r"^#{1,6}\s*(.+)$", r"*\1*", text, flags=re.M).strip()


def _app_url(path: str) -> str:
    return f"{os.environ.get('FRONTEND_URL', 'http://localhost:3000').rstrip('/')}{path}"


def action_blocks(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for a in actions:
        if a.get("status") != "proposed":
            continue
        payload = a.get("payload") or {}
        preview = str(payload.get("body") or payload.get("text") or "")[:600]
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*{a['title']}*\n{preview}"[:2900]}})
        blocks.append({"type": "actions", "elements": [
            {"type": "button", "action_id": "cw_approve", "value": str(a["id"]), "style": "primary",
             "text": {"type": "plain_text", "text": "Approve"}},
            {"type": "button", "action_id": "cw_reject", "value": str(a["id"]), "text": {"type": "plain_text", "text": "Skip"}},
            {"type": "button", "action_id": "cw_open", "url": _app_url("/app/coworker/approvals"),
             "text": {"type": "plain_text", "text": "Edit in Ourogen"}},
        ]})
    return blocks


def post(token: dict[str, Any], channel: str, text: str, thread_ts: str | None = None,
         blocks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    params: dict[str, Any] = {"channel": channel, "text": text[:39000]}
    if thread_ts:
        params["thread_ts"] = thread_ts
    if blocks:
        params["blocks"] = [{"type": "section", "text": {"type": "mrkdwn", "text": text[:2900] or " "}}, *blocks][:50]
    return slack._call("chat.postMessage", token["bot_token"], http="POST", **params)


def _claim(store: Store, user_id: int, key: str) -> bool:
    """Slack retries events it thinks we missed; each message is handled once."""
    try:
        store.insert("cw_runs", {"user_id": user_id, "responsibility_id": 0, "trigger_key": f"slackbot:{key}"[:255],
                                 "status": "done", "created_at": iso()})
        return True
    except IntegrityError:
        return False


def route(store: Store, team_id: str, event: dict[str, Any]) -> tuple[int, dict[str, Any]] | None:
    """Which owner's coworker this event is for, or None when it isn't for the bot."""
    kind = event.get("type")
    if event.get("bot_id") or event.get("subtype") or slack.AI_PREFIX in (event.get("text") or ""):
        return None
    if kind not in ("app_mention", "message") or not event.get("channel") or not event.get("ts"):
        return None
    found = installs(store, team_id)
    found = [(u, t) for u, t in found if event.get("user") != t.get("bot_user_id")]
    if not found:
        return None
    if kind == "message" and not (event.get("channel_type") == "im" and _is_bot_dm(found[0][1], event["channel"])):
        return None
    sender = event.get("user", "")
    for user_id, token in found:  # the owner talking to their own coworker
        if token.get("user_id") == sender:
            return user_id, token
    text = event.get("text") or ""
    for user_id, token in found:  # a teammate asking about a specific owner
        if token.get("user_id") and f"<@{token['user_id']}>" in text:
            return user_id, token
    return found[0]


def handle(store: Store, user_id: int, token: dict[str, Any], event: dict[str, Any]) -> str:
    """Answer one mention or DM. Returns what happened (for logs and tests)."""
    channel, ts = event["channel"], event["ts"]
    if not _claim(store, user_id, f"{channel}:{ts}"):
        return "duplicate"
    coworker = store.get_coworker(user_id) or {}
    text = _clean(event.get("text") or "", token.get("bot_user_id", ""))
    is_dm = event.get("channel_type") == "im"
    thread_ts = event.get("thread_ts") or (None if is_dm else ts)
    if coworker.get("status") != "active":
        post(token, channel, "I'm paused right now. Turn me back on in Ourogen to pick this up.", thread_ts)
        return "paused"
    if not text:
        post(token, channel, "Hi! Ask me something, or tell me what to do.", thread_ts)
        return "empty"
    if event.get("user") == token.get("user_id"):
        return _command(store, user_id, token, channel, thread_ts, text, is_dm)
    return _question(store, user_id, token, event, channel, thread_ts, text)


def _command(store: Store, user_id: int, token: dict[str, Any], channel: str, thread_ts: str | None,
             text: str, is_dm: bool) -> str:
    from coworker import channels

    key = f"{channel}:{thread_ts or 'dm'}"
    answer = channels.converse(store, user_id, "slack", key, text, "💬 Slack")
    lines = [line for line in answer["text"].splitlines() if not line.startswith("• ")]
    reply = to_mrkdwn("\n".join(lines)) or "Done."
    post(token, channel, reply, thread_ts, action_blocks(answer["actions"]))
    return "command"


def _question(store: Store, user_id: int, token: dict[str, Any], event: dict[str, Any], channel: str,
              thread_ts: str | None, text: str) -> str:
    from coworker import drafting, executor, governance, orgs, policy, security

    coworker = store.get_coworker(user_id) or {}
    owner = drafting.first_name(coworker.get("owner_name", "")) or "my owner"
    asker = event.get("user", "")
    if security.is_suspicious(text):
        store.log(user_id, "security", f"Didn't answer a suspicious Slack message from <@{asker}>.", {"text": text[:300]})
        post(token, channel, f"I'll pass this to {owner}.", thread_ts)
        return "suspicious"
    answer = drafting.slack_answer(store, user_id, text)
    level = orgs.cap_level(store, user_id, "slack.post", policy.level_for(coworker, "slack.post"))
    # Someone from another company in a Slack Connect channel never gets an unreviewed answer from private memory.
    external = bool(event.get("user_team")) and event.get("user_team") != token.get("team_id")
    if answer["confident"] and level in ("notify", "silent") and not external and not governance.needs_employer_ok(store, user_id):
        post(token, channel, f"{answer['text']}\n_({owner}'s AI coworker)_", thread_ts)
        store.log(user_id, "executed", f"Answered <@{asker}> on Slack: {text[:120]}", {"answer": answer["text"]})
        return "answered"
    post(token, channel, f"Thanks! I'm {owner}'s AI coworker. I'll check with {owner} and get back to you here.", thread_ts)
    if answer["confident"]:
        action = executor.propose(
            store, user_id, "slack.post",
            {"channel": channel, "text": f"{answer['text']}\n_({owner}'s AI coworker)_", "thread_ts": thread_ts, "via": "bot"},
            title=f"Answer <@{asker}> on Slack", reasoning="Answered from your memory and docs.",
        )
        _dm_owner(token, f"<@{asker}> asked: “{text[:400]}”\nHere's my answer. Send it?", [executor.serialize(action)])
        return "proposed"
    store.log(user_id, "escalation", f"<@{asker}> asked on Slack and I didn't know: {text[:200]}", {"channel": channel})
    _dm_owner(token, f"<@{asker}> asked: “{text[:400]}”\nI don't know this one. Reply in their thread, or tell me "
                     "the answer here and I'll remember it.", [])
    return "escalated"


def _dm_owner(token: dict[str, Any], text: str, actions: list[dict[str, Any]]) -> None:
    try:
        dm = slack._call("conversations.open", token["bot_token"], http="POST", users=token["user_id"]).get("channel", {})
        post(token, dm.get("id", ""), text, None, action_blocks(actions))
    except ConnectorError as exc:
        log.info("couldn't DM the owner: %s", exc)


# -- executing a bot post (approved actions) and undo ---------------------------------------

def token_for(store: Store, user_id: int) -> dict[str, Any]:
    row = store.one("SELECT token_enc FROM cw_connections WHERE user_id = %s AND provider = 'slack'", (user_id,))
    token = decrypt_token((row or {}).get("token_enc"))
    if not token.get("bot_token"):
        raise ConnectorError("Reconnect Slack to add the Ourogen bot.", "reauth_required")
    return token


def send(store: Store, user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    token = token_for(store, user_id)
    data = post(token, payload["channel"], payload.get("text", ""), payload.get("thread_ts"))
    return {"external_id": data.get("ts", ""), "undo": {"via": "bot", "channel_id": data.get("channel", payload["channel"]),
                                                        "ts": data.get("ts", "")}}


def delete(store: Store, user_id: int, undo: dict[str, Any]) -> bool:
    if not undo.get("ts"):
        return False
    slack._call("chat.delete", token_for(store, user_id)["bot_token"], http="POST", channel=undo["channel_id"], ts=undo["ts"])
    return True


# -- buttons ----------------------------------------------------------------------------------

def interact(store: Store, payload: dict[str, Any]) -> str:
    """An Approve / Skip button. Only the owner can press it. Returns the text that replaces the buttons."""
    from coworker import executor
    from coworker.executor import ActionError

    if payload.get("type") != "block_actions":
        return ""
    clicked = (payload.get("actions") or [{}])[0]
    if clicked.get("action_id") not in ("cw_approve", "cw_reject"):
        return ""
    team_id = (payload.get("team") or {}).get("id", "")
    presser = (payload.get("user") or {}).get("id", "")
    owner = next((u for u, t in installs(store, team_id) if t.get("user_id") == presser), None)
    if owner is None:
        return "Only the person this coworker works for can approve this."
    try:
        action_id = int(clicked.get("value") or 0)
        if clicked["action_id"] == "cw_approve":
            action = executor.approve(store, owner, action_id)
            executor.run_due(store, owner)
            action = store.get("cw_actions", action_id, owner) or action
            return f"✅ {action['title']} ({'sent' if action['status'] == 'executed' else action['status']})"
        action = executor.reject(store, owner, action_id)
        return f"Skipped: {action['title']}"
    except (ActionError, ValueError) as exc:
        return f"Couldn't do that: {exc}"
