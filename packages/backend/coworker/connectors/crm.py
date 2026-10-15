"""The user's CRM, whichever one they connected: HubSpot, Salesforce, or Pipedrive.

Every client exposes ``label`` and ``record_call(payload)``, where the
payload of an approved ``crm.update`` is ``{company, name, email, domain,
summary, fields}``. If more than one CRM is connected, the first in
``PROVIDERS`` order is used.
"""
from __future__ import annotations

from typing import Any

from coworker.store import Store

PROVIDERS = ("hubspot", "salesforce", "pipedrive")


def _module(provider: str) -> Any:
    from coworker.connectors import hubspot, pipedrive, salesforce

    return {"hubspot": hubspot, "salesforce": salesforce, "pipedrive": pipedrive}[provider]


def _client_class(provider: str) -> Any:
    from coworker.connectors.hubspot import HubSpotClient
    from coworker.connectors.pipedrive import PipedriveClient
    from coworker.connectors.salesforce import SalesforceClient

    return {"hubspot": HubSpotClient, "salesforce": SalesforceClient, "pipedrive": PipedriveClient}[provider]


def client_for(store: Store, user_id: int) -> tuple[str, Any] | None:
    """(provider, client) for the user's connected CRM, or None."""
    from coworker.connectors.base import decrypt_token, encrypt_token

    for provider in PROVIDERS:
        row = store.get_connection_row(user_id, provider)
        if not row or row.get("status") not in ("connected", "syncing"):
            continue

        def save(token: dict[str, Any], provider: str = provider) -> None:
            store.upsert_connection(user_id, provider, token_enc=encrypt_token(token))

        return provider, _client_class(provider)(decrypt_token(row.get("token_enc")), on_refresh=save)
    return None


def revoke(provider: str, token: dict[str, Any]) -> None:
    if provider in PROVIDERS:
        _module(provider).revoke(token)


def label(provider: str) -> str:
    return str(_client_class(provider).label) if provider in PROVIDERS else "your CRM"
