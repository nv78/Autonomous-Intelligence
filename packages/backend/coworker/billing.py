"""Coworker plans, usage metering, and unit economics.

Prices are starting hypotheses to validate with pilot users, not
published prices. Plan gating is enforced only when
``COWORKER_ENFORCE_PLANS=1`` so the pilot and local testing stay open.
"""
from __future__ import annotations

import os
from datetime import UTC
from typing import Any

from coworker.store import Store, iso, utcnow

PLANS: dict[str, dict[str, Any]] = {
    "pilot": {"name": "Founder pilot", "price_usd": 0, "features": ["email", "slack", "calendar", "memory", "calls", "twin"],
              "call_minutes": 300, "price_env": ""},
    "coworker": {"name": "Coworker", "price_usd": 199, "features": ["email", "slack", "calendar", "memory", "listen_only_meetings"],
                 "call_minutes": 0, "price_env": "STRIPE_PRICE_COWORKER"},
    "coworker_calls": {"name": "Coworker + Calls", "price_usd": 599, "features": ["email", "slack", "calendar", "memory", "calls", "twin"],
                       "call_minutes": 600, "price_env": "STRIPE_PRICE_COWORKER_CALLS"},
    "team": {"name": "Team", "price_usd": 1000, "features": ["email", "slack", "calendar", "memory", "calls", "twin", "admin", "sso"],
             "call_minutes": 2000, "price_env": "STRIPE_PRICE_COWORKER_TEAM"},
}

# Rough variable cost per unit, used for the internal margin view. Override per deployment.
COST_PER_CALL_MINUTE = float(os.environ.get("COWORKER_COST_PER_CALL_MINUTE", "0.15"))
COST_PER_1K_TTS_CHARS = float(os.environ.get("COWORKER_COST_PER_1K_TTS_CHARS", "0.10"))
COST_PER_ACTION = float(os.environ.get("COWORKER_COST_PER_ACTION", "0.02"))


class PlanError(Exception):
    pass


def month_start() -> str:
    now = utcnow().astimezone(UTC)
    return iso(now.replace(day=1, hour=0, minute=0, second=0, microsecond=0))


def enforce() -> bool:
    return os.environ.get("COWORKER_ENFORCE_PLANS") == "1"


def plan_of(coworker: dict[str, Any]) -> str:
    plan = coworker.get("plan") or "pilot"
    return plan if plan in PLANS else "pilot"


def require(store: Store, user_id: int, feature: str) -> None:
    """Raise PlanError if the user's plan doesn't include ``feature``."""
    if not enforce():
        return
    coworker = store.get_coworker(user_id) or {}
    plan = PLANS[plan_of(coworker)]
    if feature not in plan["features"]:
        raise PlanError(f"{plan['name']} doesn't include {feature.replace('_', ' ')}. Upgrade to Coworker + Calls.")
    if feature == "calls":
        used = store.usage_since(user_id, month_start()).get("call_seconds", 0) // 60
        if used >= plan["call_minutes"]:
            raise PlanError(f"You've used all {plan['call_minutes']} call minutes this month.")


def summary(store: Store, user_id: int) -> dict[str, Any]:
    coworker = store.get_coworker(user_id) or {}
    plan_id = plan_of(coworker)
    plan = PLANS[plan_id]
    usage = store.usage_since(user_id, month_start())
    actions = store.one(
        "SELECT COUNT(*) AS n FROM cw_actions WHERE user_id = %s AND status = 'executed' AND created_at >= %s",
        (user_id, month_start()),
    )
    executed = int((actions or {}).get("n") or 0)
    call_minutes = round(usage.get("call_seconds", 0) / 60, 1)
    cost = call_minutes * COST_PER_CALL_MINUTE + usage.get("tts_chars", 0) / 1000 * COST_PER_1K_TTS_CHARS + executed * COST_PER_ACTION
    return {
        "plan": plan_id,
        "planName": plan["name"],
        "priceUsd": plan["price_usd"],
        "callMinutes": call_minutes,
        "callMinutesIncluded": plan["call_minutes"],
        "warn": bool(plan["call_minutes"]) and call_minutes >= 0.8 * plan["call_minutes"],
        "actionsExecuted": executed,
        "ttsChars": usage.get("tts_chars", 0),
        "estimatedCostUsd": round(cost, 2),
        "estimatedMarginUsd": round(plan["price_usd"] - cost, 2),
        "plans": [
            {"id": k, "name": v["name"], "priceUsd": v["price_usd"], "features": v["features"], "callMinutes": v["call_minutes"],
             "available": bool(v["price_env"] and os.environ.get(v["price_env"]))}
            for k, v in PLANS.items()
        ],
        "enforced": enforce(),
    }


def apply_checkout(store: Store, metadata: dict[str, Any]) -> bool:
    """Called from the Stripe webhook when a coworker plan checkout completes."""
    if metadata.get("kind") != "coworker_plan" or metadata.get("plan") not in PLANS:
        return False
    user_id = int(metadata["user_id"])
    store.update_coworker(user_id, plan=metadata["plan"])
    store.log(user_id, "billing", f"Plan changed to {PLANS[metadata['plan']]['name']}")
    return True
