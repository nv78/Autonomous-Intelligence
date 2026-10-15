"""Calling Claude for the coworker.

Uses the official ``anthropic`` SDK. Responses are read through the SDK's
raw-response path and kept as plain JSON so every content block (including
``thinking`` and ``fallback`` blocks that newer models return) can be sent
back unchanged on the next turn of a tool-use loop.

Defaults follow current guidance: ``claude-opus-5-5`` with an explicit
effort level and server-side refusal fallbacks. Override the model with
``COWORKER_MODEL``.
"""
from __future__ import annotations

import os
from typing import Any

DEFAULT_MODEL = "claude-opus-5-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"


def model_name() -> str:
    return os.environ.get("COWORKER_MODEL", DEFAULT_MODEL)


def api_key_for(user_id: int | None = None) -> str:
    if user_id is not None:
        from services.provider_keys import get_user_provider_key

        user_key = get_user_provider_key(user_id, "anthropic")
        if user_key:
            return user_key
    return os.environ.get("ANTHROPIC_API_KEY", "")


def available(user_id: int | None = None) -> bool:
    return os.environ.get("COWORKER_OFFLINE") != "1" and bool(api_key_for(user_id))


def create_message(
    *,
    system: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    user_id: int | None = None,
    max_tokens: int = 16000,
    effort: str | None = None,
) -> dict[str, Any]:
    """One Messages API call. Returns the response as a JSON dict."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key_for(user_id), max_retries=2, timeout=300)
    model = model_name()
    extra_body: dict[str, Any] = {"output_config": {"effort": effort or os.environ.get("COWORKER_EFFORT", "medium")}}
    extra_headers: dict[str, str] = {}
    if os.environ.get("COWORKER_FALLBACKS", "1") == "1" and model in ("claude-opus-5-5", "claude-fable-5-1", "claude-opus-5"):
        extra_body["fallbacks"] = "default"
        extra_headers["anthropic-beta"] = FALLBACK_BETA
    kwargs: dict[str, Any] = {
        "model": model, "max_tokens": max_tokens, "system": system, "messages": messages,
        "extra_body": extra_body, "extra_headers": extra_headers,
    }
    if tools:
        kwargs["tools"] = tools
    raw = client.messages.with_raw_response.create(**kwargs)
    data: dict[str, Any] = raw.http_response.json()
    usage = data.get("usage") or {}
    try:
        from services.usage import record_usage

        record_usage(user_id, "/api/coworker", model, usage.get("input_tokens", 0), usage.get("output_tokens", 0))
    except Exception:  # pragma: no cover - metering must never break the agent
        pass
    return data


def text_of(response: dict[str, Any]) -> str:
    return "".join(b.get("text", "") for b in response.get("content", []) if b.get("type") == "text")


def complete_text(prompt: str, *, system: str = "You are a precise assistant.", user_id: int | None = None,
                  max_tokens: int = 4000, effort: str = "low") -> str:
    response = create_message(system=system, messages=[{"role": "user", "content": prompt}],
                              user_id=user_id, max_tokens=max_tokens, effort=effort)
    if response.get("stop_reason") == "refusal":
        return ""
    return text_of(response)
