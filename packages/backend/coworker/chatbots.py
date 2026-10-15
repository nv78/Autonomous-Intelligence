"""What Teams and Google Chat bots share: who's talking, and what to say back.

Same rules as the Slack bot (``coworker/slackbot.py``):

* **The owner** (matched by their verified Microsoft object id, or a Google
  address verified at sign-in) is giving a command: it runs as a
  chat turn, one web chat per conversation, and proposed actions come back
  with Approve / Skip buttons.
* **A teammate** is asking the coworker of an owner in the same tenant /
  Workspace domain (the one they mention, else the first to link). The
  answer comes from the owner's memory and docs. It's posted only when
  confident and the owner's chat-answer autonomy (the "Post on Slack"
  level) is notify or silent. Otherwise they're told the owner will get back
  to them, and the owner gets the question, with the suggested answer, as a
  direct message and in Activity.
"""
from __future__ import annotations

from typing import Any

from coworker.store import IntegrityError, Store, iso

CHAT_NAMES = {"teams": "💬 Teams", "gchat": "💬 Google Chat"}


def owner_for_teams(store: Store, aad_object_id: str, tenant: str) -> int | None:
    """The owner behind a Teams user: their Microsoft object id and tenant, as verified at Microsoft sign-in.

    Never by email: any tenant admin can set a user's mail attribute to someone else's address.
    """
    if not aad_object_id:
        return None
    row = store.one("SELECT user_id, tenant FROM cw_verified_identities WHERE provider = 'microsoft' AND subject = %s",
                    (aad_object_id,))
    if not row or (tenant and row.get("tenant") and row["tenant"] != tenant):
        return None
    return int(row["user_id"])


def owner_for_google(store: Store, email: str) -> int | None:
    """The owner behind a Google Chat user: an address Google verified at sign-in or when connecting Gmail."""
    from coworker import identity

    return identity.user_for(store, "google", email=email) if email else None


def remember(store: Store, platform: str, external_id: str, user_id: int, tenant: str, email: str,
             conversation: dict[str, Any] | None = None) -> None:
    """Record the owner's chat identity (and their 1:1 conversation, to message them later)."""
    current = store.one("SELECT * FROM cw_bot_identities WHERE platform = %s AND external_id = %s", (platform, external_id))
    values: dict[str, Any] = {"user_id": user_id, "tenant": tenant[:255], "email": email[:255]}
    if conversation:
        values["conversation"] = conversation
    if current:
        store.update("cw_bot_identities", int(current["id"]), None, values)
        return
    try:
        store.insert("cw_bot_identities", {"platform": platform, "external_id": external_id[:255], "created_at": iso(), **values})
    except IntegrityError:  # two messages at once
        pass


def owners_in(store: Store, platform: str, tenant: str) -> list[dict[str, Any]]:
    return store.query("SELECT * FROM cw_bot_identities WHERE platform = %s AND tenant = %s ORDER BY id", (platform, tenant))


def claim(store: Store, user_id: int, key: str) -> bool:
    """Platforms retry deliveries; each message is handled once."""
    try:
        store.insert("cw_runs", {"user_id": user_id, "responsibility_id": 0, "trigger_key": key[:255], "status": "done",
                                 "created_at": iso()})
        return True
    except IntegrityError:
        return False


def command(store: Store, user_id: int, platform: str, conversation_key: str, text: str) -> dict[str, Any]:
    from coworker import channels

    answer = channels.converse(store, user_id, platform, conversation_key, text, CHAT_NAMES.get(platform, "💬 Chat"))
    reply = "\n".join(line for line in answer["text"].splitlines() if not line.startswith("• ")).strip() or "Done."
    return {"text": reply, "actions": [a for a in answer["actions"] if a["status"] == "proposed"]}


def teammate(store: Store, user_id: int, asker: str, text: str, external: bool = False) -> dict[str, Any]:
    """{"text": reply in the conversation, "owner_note": DM to the owner or ""}."""
    from coworker import drafting, orgs, policy, security

    coworker = store.get_coworker(user_id) or {}
    owner = drafting.first_name(coworker.get("owner_name", "")) or "my owner"
    if coworker.get("status") != "active":
        return {"text": f"I'm {owner}'s AI coworker, and I'm paused right now.", "owner_note": ""}
    if security.is_suspicious(text):
        store.log(user_id, "security", f"Didn't answer a suspicious chat message from {asker}.", {"text": text[:300]})
        return {"text": f"I'll pass this to {owner}.", "owner_note": ""}
    answer = drafting.slack_answer(store, user_id, text)
    level = orgs.cap_level(store, user_id, "slack.post", policy.level_for(coworker, "slack.post"))
    if answer["confident"] and level in ("notify", "silent") and not external:
        store.log(user_id, "executed", f"Answered {asker} in chat: {text[:120]}", {"answer": answer["text"]})
        return {"text": f"{answer['text']}\n\n_({owner}'s AI coworker)_", "owner_note": ""}
    store.log(user_id, "escalation", f"{asker} asked in chat: {text[:200]}",
              {"suggested": answer["text"] if answer["confident"] else ""})
    note = f"{asker} asked: “{text[:400]}”"
    note += f"\nSuggested answer: {answer['text']}" if answer["confident"] else "\nI don't know this one."
    return {"text": f"Thanks! I'm {owner}'s AI coworker. I'll check with {owner} and get back to you.", "owner_note": note}


def decide(store: Store, user_id: int, verb: str, action_id: int) -> str:
    """An Approve / Skip button press by the owner."""
    from coworker import executor
    from coworker.executor import ActionError

    try:
        if verb == "approve":
            executor.approve(store, user_id, action_id)
            executor.run_due(store, user_id)
            action = store.get("cw_actions", action_id, user_id) or {}
            return f"✅ {action.get('title', '')} ({'sent' if action.get('status') == 'executed' else action.get('status')})"
        action = executor.reject(store, user_id, action_id)
        return f"Skipped: {action['title']}"
    except ActionError as exc:
        return f"Couldn't do that: {exc}"
