"""Calling the model that powers the coworker.

Model-agnostic: each user picks a model in Settings (``settings.model``).
Claude models use the official ``anthropic`` SDK. OpenAI, Gemini (through
Google's OpenAI-compatible endpoint), and local Ollama models use the
``openai`` SDK; requests and responses are translated to and from the
Anthropic Messages shape, so the agent loop and tools work the same for
every provider. A model is offered only when there's a key for it: the
user's own provider key from Settings, or the server's.

For Claude, the official ``anthropic`` SDK is used. Responses are read through the SDK's
raw-response path and kept as plain JSON so every content block (including
``thinking`` and ``fallback`` blocks that newer models return) can be sent
back unchanged on the next turn of a tool-use loop.

Defaults follow current guidance: ``claude-opus-5-5`` with an explicit
effort level and server-side refusal fallbacks. Override the model with
``COWORKER_MODEL``.
"""
from __future__ import annotations

import contextvars
import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

DEFAULT_MODEL = "claude-opus-5-5"
# USD per million tokens: (input, output, cache read). Anthropic list prices; other providers are
# unpriced (tokens are still counted) unless COWORKER_MODEL_PRICES='{"gpt-4o": [2.5, 10]}' sets them.
PRICES_PER_MTOK: dict[str, tuple[float, float, float]] = {
    "claude-fable-5-1": (10.0, 50.0, 0.25),
    "claude-opus-5-5": (4.0, 20.0, 0.20),
    "claude-opus-5": (5.0, 25.0, 0.50),
    "claude-sonnet-5-5": (2.0, 10.0, 0.20),
    "claude-haiku-5-5": (0.10, 0.50, 0.01),  # prompts up to 100K tokens
}
_usage_scope: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar("coworker_usage", default=None)
FALLBACK_BETA = "server-side-fallback-2026-07-01"


MODELS: list[dict[str, str]] = [
    {"id": "claude-opus-5-5", "label": "Claude Opus 5.5", "provider": "anthropic", "note": "Most capable (default)"},
    {"id": "claude-sonnet-5-5", "label": "Claude Sonnet 5.5", "provider": "anthropic", "note": "Fast and capable"},
    {"id": "claude-haiku-5-5", "label": "Claude Haiku 5.5", "provider": "anthropic", "note": "Fastest, lowest cost"},
    {"id": "gpt-4o", "label": "GPT-4o", "provider": "openai", "note": "OpenAI"},
    {"id": "gpt-4o-mini", "label": "GPT-4o mini", "provider": "openai", "note": "OpenAI, lower cost"},
    {"id": "gemini-2.5-pro", "label": "Gemini 2.5 Pro", "provider": "google", "note": "Google"},
    {"id": "gemini-2.5-flash", "label": "Gemini 2.5 Flash", "provider": "google", "note": "Google, lower cost"},
    {"id": "llama3.1", "label": "Llama 3.1 (local)", "provider": "ollama", "note": "Runs on your own server via Ollama"},
]
PROVIDER_ENV = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "google": "GEMINI_API_KEY"}
OPENAI_COMPATIBLE_BASE = {
    "google": "https://generativelanguage.googleapis.com/v1beta/openai/",
}


def catalog() -> list[dict[str, str]]:
    """Built-in models plus any extra ids from ``COWORKER_EXTRA_MODELS``
    (comma-separated ``provider:model`` pairs, e.g. ``openai:gpt-5``)."""
    extra = []
    for pair in os.environ.get("COWORKER_EXTRA_MODELS", "").split(","):
        if ":" in pair:
            provider, mid = (x.strip() for x in pair.split(":", 1))
            if provider in ("anthropic", "openai", "google", "ollama") and mid:
                extra.append({"id": mid, "label": mid, "provider": provider, "note": "Added by your admin"})
    return MODELS + [m for m in extra if m["id"] not in {x["id"] for x in MODELS}]


def provider_of(model: str) -> str:
    if os.environ.get("OLLAMA_BASE_URL") and model == free_model():
        return "ollama"  # e.g. OLLAMA_MODEL=gpt-oss:20b is still local
    for m in catalog():
        if m["id"] == model:
            return m["provider"]
    if model.startswith("claude"):
        return "anthropic"
    if model.startswith(("gpt", "o1", "o3", "o4")):
        return "openai"
    if model.startswith("gemini"):
        return "google"
    return "ollama"


def model_name(user_id: int | None = None) -> str:
    """The user's chosen model, else the server default; always within the organization's allowed models."""
    chosen = ""
    allowed: list[str] = []
    if user_id is not None:
        try:
            from coworker import orgs
            from coworker.store import get_store

            store = get_store()
            chosen = str(((store.get_coworker(user_id) or {}).get("settings") or {}).get("model") or "")
            allowed = orgs.allowed_models(store, user_id)
        except Exception:  # pragma: no cover - never block a call on settings lookup
            pass
    model = chosen or os.environ.get("COWORKER_MODEL", DEFAULT_MODEL)
    if allowed and model not in allowed:
        model = allowed[0]
    return usable(model, user_id, allowed)


def free_model() -> str:
    """The local model used when no API key is set (``OLLAMA_MODEL``, default llama3.1)."""
    return os.environ.get("OLLAMA_MODEL") or "llama3.1"


def usable(model: str, user_id: int | None = None, allowed: list[str] | None = None) -> str:
    """``model`` if its provider has a key; otherwise the free local model when Ollama is set up.

    So the coworker runs with no API keys at all, and switches back to the chosen model on its own
    once a key is added. An organization that restricts models only falls back to an allowed one.
    """
    if key_for(provider_of(model), user_id) or not ollama_up():
        return model
    free = free_model()
    return free if not allowed or free in allowed else model


FAST_MODELS = {"anthropic": "claude-haiku-5-5", "openai": "gpt-4o-mini", "google": "gemini-2.5-flash"}


def call_model(user_id: int | None = None) -> str:
    """The model for live calls, where every second of thinking is dead air.

    ``settings.call_model`` or ``COWORKER_CALL_MODEL`` if set; otherwise the
    fast sibling of the user's chosen model from the same provider (so the
    same API key works), or the chosen model itself.
    """
    if user_id is not None:
        try:
            from coworker.store import get_store

            chosen = ((get_store().get_coworker(user_id) or {}).get("settings") or {}).get("call_model")
            if chosen:
                return str(chosen)
        except Exception:  # pragma: no cover
            pass
    if os.environ.get("COWORKER_CALL_MODEL"):
        return os.environ["COWORKER_CALL_MODEL"]
    base = model_name(user_id)
    return FAST_MODELS.get(provider_of(base), base)


_ollama_seen: dict[str, Any] = {}
OLLAMA_CHECK_SECONDS = 60


def ollama_up() -> bool:
    """Whether the Ollama server at ``OLLAMA_BASE_URL`` answers (checked at most once a minute)."""
    import time

    base = os.environ.get("OLLAMA_BASE_URL", "").rstrip("/")
    if not base:
        return False
    if _ollama_seen.get("base") == base and time.monotonic() - _ollama_seen.get("at", 0) < OLLAMA_CHECK_SECONDS:
        return bool(_ollama_seen["up"])
    try:
        import requests

        up = requests.get(f"{base}/api/tags", timeout=1.5).status_code == 200
    except Exception:
        up = False
    _ollama_seen.update(base=base, at=time.monotonic(), up=up)
    return up


def key_for(provider: str, user_id: int | None = None) -> str:
    if provider == "ollama":
        return "ollama" if ollama_up() else ""
    if user_id is not None and provider in PROVIDER_ENV:
        from services.provider_keys import get_user_provider_key

        user_key = get_user_provider_key(user_id, provider)
        if user_key:
            return user_key
    key = os.environ.get(PROVIDER_ENV.get(provider, ""), "")
    if not key and provider == "google":
        key = os.environ.get("GOOGLE_API_KEY", "")
    return key


def api_key_for(user_id: int | None = None) -> str:
    return key_for(provider_of(model_name(user_id)), user_id)


def available(user_id: int | None = None) -> bool:
    return os.environ.get("COWORKER_OFFLINE") != "1" and bool(api_key_for(user_id))


def models_for(user_id: int | None = None) -> list[dict[str, Any]]:
    """The catalog, marking which models this user can use right now (and which their organization allows)."""
    current = model_name(user_id)
    allowed: list[str] = []
    if user_id is not None:
        try:
            from coworker import orgs
            from coworker.store import get_store

            allowed = orgs.allowed_models(get_store(), user_id)
        except Exception:  # pragma: no cover
            pass
    return [{**m, "available": bool(key_for(m["provider"], user_id)) and (not allowed or m["id"] in allowed),
             "allowedByOrg": not allowed or m["id"] in allowed, "selected": m["id"] == current} for m in catalog()]


def create_message(
    *,
    system: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    user_id: int | None = None,
    max_tokens: int = 16000,
    effort: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """One Messages API call. Returns the response as a JSON dict."""
    model = usable(model, user_id) if model else model_name(user_id)
    provider = provider_of(model)
    if provider != "anthropic":
        translated = _openai_compatible(provider, model, system=system, messages=messages, tools=tools,
                                        user_id=user_id, max_tokens=max_tokens)
        _meter(user_id, model, translated)
        return translated
    import anthropic

    client = anthropic.Anthropic(api_key=key_for("anthropic", user_id), max_retries=2, timeout=300)
    extra_body: dict[str, Any] = {}
    if model.startswith(("claude-opus-5", "claude-sonnet-5", "claude-fable-5")):
        extra_body["output_config"] = {"effort": effort or os.environ.get("COWORKER_EFFORT", "medium")}
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
    _meter(user_id, model, data)
    return data


def price_for(model: str) -> tuple[float, float, float] | None:
    try:
        custom = json.loads(os.environ.get("COWORKER_MODEL_PRICES") or "{}")
    except ValueError:
        custom = {}
    if isinstance(custom.get(model), list) and len(custom[model]) >= 2:
        p = [float(x) for x in custom[model]]
        return p[0], p[1], p[2] if len(p) > 2 else p[0] / 10
    return PRICES_PER_MTOK.get(model)


@contextmanager
def metering() -> Iterator[dict[str, Any]]:
    """Add up tokens and cost for every model call inside the block (one scheduled run, say).

    ``cost_usd`` is None when any call used a model without a known price.
    """
    totals: dict[str, Any] = {"input_tokens": 0, "output_tokens": 0, "calls": 0, "cost_usd": 0.0}
    token = _usage_scope.set(totals)
    try:
        yield totals
    finally:
        _usage_scope.reset(token)


def _add_to_scope(model: str, usage: dict[str, Any]) -> None:
    totals = _usage_scope.get()
    if totals is None:
        return
    fresh, cached = int(usage.get("input_tokens") or 0), int(usage.get("cache_read_input_tokens") or 0)
    written, out = int(usage.get("cache_creation_input_tokens") or 0), int(usage.get("output_tokens") or 0)
    totals["input_tokens"] += fresh + cached + written
    totals["output_tokens"] += out
    totals["calls"] += 1
    price = price_for(model)
    if price is None or totals["cost_usd"] is None:
        totals["cost_usd"] = None
        return
    totals["cost_usd"] += ((fresh + written * 1.25) * price[0] + cached * price[2] + out * price[1]) / 1_000_000


def _meter(user_id: int | None, model: str, data: dict[str, Any]) -> None:
    usage = data.get("usage") or {}
    _add_to_scope(model, usage)
    try:
        from services.usage import record_usage

        record_usage(user_id, "/api/coworker", model, usage.get("input_tokens", 0), usage.get("output_tokens", 0),
                     credits_used=0)
    except Exception:  # pragma: no cover - metering must never break the agent
        pass


# -- OpenAI-compatible providers (OpenAI, Gemini, Ollama) ----------------------

def to_openai_messages(system: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Anthropic-shaped conversation to Chat Completions messages."""
    import json

    out: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for msg in messages:
        content = msg["content"]
        if isinstance(content, str):
            out.append({"role": msg["role"], "content": content})
            continue
        if msg["role"] == "assistant":
            text = "".join(b.get("text", "") for b in content if b.get("type") == "text")
            calls = [{"id": b["id"], "type": "function",
                      "function": {"name": b["name"], "arguments": json.dumps(b.get("input") or {})}}
                     for b in content if b.get("type") == "tool_use"]
            entry: dict[str, Any] = {"role": "assistant", "content": text or None}
            if calls:
                entry["tool_calls"] = calls
            out.append(entry)
            continue
        texts = []
        for b in content:
            if b.get("type") == "tool_result":
                body = b.get("content")
                if isinstance(body, list):
                    body = "".join(x.get("text", "") for x in body if isinstance(x, dict))
                out.append({"role": "tool", "tool_call_id": b["tool_use_id"],
                            "content": ("ERROR: " if b.get("is_error") else "") + str(body or "")})
            elif b.get("type") == "text":
                texts.append(b.get("text", ""))
        if texts:
            out.append({"role": "user", "content": "\n".join(texts)})
    return out


def to_openai_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"type": "function", "function": {"name": t["name"], "description": t.get("description", ""),
                                              "parameters": t.get("input_schema") or {"type": "object"}}} for t in tools]


STOP_REASONS = {"tool_calls": "tool_use", "function_call": "tool_use", "length": "max_tokens", "stop": "end_turn",
                "content_filter": "refusal"}


def from_openai_response(resp: dict[str, Any]) -> dict[str, Any]:
    """Chat Completions response to an Anthropic-shaped message."""
    import json

    choice = (resp.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    blocks: list[dict[str, Any]] = []
    if message.get("content"):
        blocks.append({"type": "text", "text": message["content"]})
    for call in message.get("tool_calls") or []:
        fn = call.get("function") or {}
        try:
            args: Any = json.loads(fn.get("arguments") or "{}")
        except ValueError:
            args = fn.get("arguments")  # the agent loop reports invalid input back to the model
        blocks.append({"type": "tool_use", "id": call.get("id") or f"call_{len(blocks)}", "name": fn.get("name", ""),
                       "input": args})
    stop = STOP_REASONS.get(choice.get("finish_reason") or "stop", "end_turn")
    if any(b["type"] == "tool_use" for b in blocks):
        stop = "tool_use"
    usage = resp.get("usage") or {}
    return {"content": blocks, "stop_reason": stop, "model": resp.get("model"),
            "usage": {"input_tokens": usage.get("prompt_tokens", 0), "output_tokens": usage.get("completion_tokens", 0)}}


def _openai_compatible(provider: str, model: str, *, system: str, messages: list[dict[str, Any]],
                       tools: list[dict[str, Any]] | None, user_id: int | None, max_tokens: int) -> dict[str, Any]:
    from openai import OpenAI

    base = OPENAI_COMPATIBLE_BASE.get(provider)
    if provider == "ollama":
        base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/") + "/v1"
    client = OpenAI(api_key=key_for(provider, user_id) or "none", base_url=base, max_retries=2, timeout=300)
    kwargs: dict[str, Any] = {"model": model, "messages": to_openai_messages(system, messages),
                              "max_tokens": min(max_tokens, 8000)}
    if tools:
        kwargs["tools"] = to_openai_tools(tools)
    resp = client.chat.completions.create(**kwargs)
    return from_openai_response(resp.model_dump())


def text_of(response: dict[str, Any]) -> str:
    return "".join(b.get("text", "") for b in response.get("content", []) if b.get("type") == "text")


def complete_text(prompt: str, *, system: str = "You are a precise assistant.", user_id: int | None = None,
                  max_tokens: int = 4000, effort: str = "low", model: str | None = None) -> str:
    response = create_message(system=system, messages=[{"role": "user", "content": prompt}],
                              user_id=user_id, max_tokens=max_tokens, effort=effort, model=model)
    if response.get("stop_reason") == "refusal":
        return ""
    return text_of(response)
