"""Real-time video avatar via Tavus Conversational Video.

Requires ``TAVUS_API_KEY`` and a replica trained on the user's video
(``TAVUS_REPLICA_ID``, created in the Tavus dashboard from the same
consented footage). Returns a conversation URL the web app embeds.

Request shapes follow Tavus's v2 API; verify against their current docs
before relying on this outside the pilot.
"""
from __future__ import annotations

import os
from typing import Any

import requests

from coworker.connectors.base import ConnectorError

API = "https://tavusapi.com/v2"


def is_configured() -> bool:
    return bool(os.environ.get("TAVUS_API_KEY") and os.environ.get("TAVUS_REPLICA_ID"))


def create_conversation(name: str, context: str, greeting: str) -> dict[str, Any]:
    body = {
        "replica_id": os.environ.get("TAVUS_REPLICA_ID", ""),
        "conversation_name": name[:100],
        "conversational_context": context[:8000],
        "custom_greeting": greeting[:500],
    }
    if os.environ.get("TAVUS_PERSONA_ID"):
        body["persona_id"] = os.environ["TAVUS_PERSONA_ID"]
    resp = requests.post(f"{API}/conversations", headers={"x-api-key": os.environ.get("TAVUS_API_KEY", "")},
                         json=body, timeout=30)
    if resp.status_code >= 400:
        raise ConnectorError(f"Tavus failed ({resp.status_code}): {resp.text[:200]}")
    data: dict[str, Any] = resp.json()
    return {"url": data.get("conversation_url", ""), "id": data.get("conversation_id", "")}
