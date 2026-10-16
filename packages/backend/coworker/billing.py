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
    "free": {"name": "Free", "price_usd": 0, "features": ["email", "calendar", "memory"], "call_minutes": 0, "price_env": ""},
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


def effective_plan(store: Store, user_id: int) -> str:
    """The user's own plan, or Team when their organization's owner pays for Team."""
    own = plan_of(store.get_coworker(user_id) or {})
    if own == "team":
        return own
    from coworker import orgs

    org = orgs.org_for(store, user_id)
    if org and plan_of(store.get_coworker(int(org["owner_user_id"])) or {}) == "team":
        return "team"
    return own


def sync_seats(store: Store, org: dict[str, Any]) -> int | None:
    """Keep the Team subscription's quantity equal to the organization's seats (prorated).

    Only when ``COWORKER_TEAM_PER_SEAT=1`` (the Team price in Stripe is per seat);
    otherwise Team is a flat price and seats don't change the bill.
    """
    from coworker import orgs

    if os.environ.get("COWORKER_TEAM_PER_SEAT") != "1" or not os.environ.get("STRIPE_SECRET_KEY"):
        return None
    payer = store.get_coworker(int(org["owner_user_id"])) or {}
    sub_id = billing_state(payer).get("subscription_id")
    if plan_of(payer) != "team" or not sub_id:
        return None
    count = max(1, orgs.seats(store, int(org["id"])))
    stripe = _stripe()
    sub = stripe.Subscription.retrieve(sub_id)
    item = sub["items"]["data"][0]
    if int(item.get("quantity") or 1) != count:
        stripe.Subscription.modify(sub_id, proration_behavior="create_prorations", items=[{"id": item["id"], "quantity": count}])
        store.log(int(org["owner_user_id"]), "billing", f"Team seats updated to {count} (prorated on your next invoice)")
    return count


def require(store: Store, user_id: int, feature: str) -> None:
    """Raise PlanError if the user's plan doesn't include ``feature``."""
    if not enforce():
        return
    plan = PLANS[effective_plan(store, user_id)]
    if feature not in plan["features"]:
        raise PlanError(f"{plan['name']} doesn't include {feature.replace('_', ' ')}. Upgrade to Coworker + Calls.")
    if feature == "calls":
        used = store.usage_since(user_id, month_start()).get("call_seconds", 0) // 60
        if used >= plan["call_minutes"]:
            raise PlanError(f"You've used all {plan['call_minutes']} call minutes this month.")


def summary(store: Store, user_id: int) -> dict[str, Any]:
    coworker = store.get_coworker(user_id) or {}
    plan_id = effective_plan(store, user_id)
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
             "available": k == "free" or bool(v["price_env"] and os.environ.get(v["price_env"])),
             "direction": direction(plan_id, k) if k in ORDER else "same"}
            for k, v in PLANS.items()
        ],
        "subscription": {k: v for k, v in billing_state(coworker).items() if k in ("cancel_at_period_end", "current_period_end")},
        "hasBillingAccount": bool(billing_state(coworker).get("customer_id")),
        "enforced": enforce(),
    }


def apply_checkout(store: Store, metadata: dict[str, Any], session: dict[str, Any] | None = None) -> bool:
    """Called from the Stripe webhook when a coworker plan checkout completes."""
    if metadata.get("kind") != "coworker_plan" or metadata.get("plan") not in PLANS:
        return False
    user_id = int(metadata["user_id"])
    store.update_coworker(user_id, plan=metadata["plan"])
    if session:
        _save_billing(store, user_id, subscription_id=session.get("subscription"), customer_id=session.get("customer"),
                      cancel_at_period_end=False)
    store.log(user_id, "billing", f"Plan changed to {PLANS[metadata['plan']]['name']}")
    return True


# -- changing plans --------------------------------------------------------------

ORDER = ["free", "coworker", "coworker_calls", "team"]


def _stripe() -> Any:
    import stripe

    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
    return stripe


def billing_state(coworker: dict[str, Any]) -> dict[str, Any]:
    return dict((coworker.get("settings") or {}).get("billing") or {})


def _save_billing(store: Store, user_id: int, **values: Any) -> None:
    coworker = store.get_coworker(user_id) or {}
    settings = dict(coworker.get("settings") or {})
    settings["billing"] = {**billing_state(coworker), **values}
    store.update_coworker(user_id, settings=settings)


def plan_for_price(price_id: str) -> str | None:
    for plan_id, spec in PLANS.items():
        if spec["price_env"] and os.environ.get(spec["price_env"]) == price_id:
            return plan_id
    return None


def direction(current: str, target: str) -> str:
    cur = ORDER.index(current) if current in ORDER else 0
    return "upgrade" if ORDER.index(target) > cur else "downgrade" if ORDER.index(target) < cur else "same"


def change_plan(store: Store, user_id: int, target: str) -> dict[str, Any]:
    """Move to ``target``. Returns {"status": "checkout"|"changed"|"scheduled", ...}.

    * No subscription yet, paid target: start Stripe Checkout.
    * Existing subscription, paid target: swap the price on the subscription,
      prorated, effective now (upgrades and downgrades alike).
    * ``free``: cancel at the end of the paid period; the plan drops to Free
      when Stripe says the subscription ended.
    """
    if target not in ORDER:
        raise PlanError("Pick Free, Coworker, Coworker + Calls, or Team.")
    coworker = store.get_coworker(user_id) or {}
    current = plan_of(coworker)
    state = billing_state(coworker)
    sub_id = state.get("subscription_id")
    if target == current and not state.get("cancel_at_period_end"):
        return {"status": "same", "plan": current}
    if not os.environ.get("STRIPE_SECRET_KEY"):
        raise PlanError("Billing isn't configured on this server yet. Pilot users are free.")
    stripe = _stripe()
    if target == "free":
        if not sub_id:
            store.update_coworker(user_id, plan="free")
            store.log(user_id, "billing", "Switched to the Free plan")
            return {"status": "changed", "plan": "free"}
        sub = stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
        _save_billing(store, user_id, cancel_at_period_end=True, current_period_end=sub.get("current_period_end"))
        store.log(user_id, "billing", f"Scheduled a move to Free at the end of your {PLANS[current]['name']} period")
        return {"status": "scheduled", "plan": "free", "effectiveAt": sub.get("current_period_end")}
    price_id = os.environ.get(PLANS[target]["price_env"], "")
    if not price_id:
        raise PlanError(f"{PLANS[target]['name']} isn't available yet.")
    if not sub_id:
        base = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
        session = stripe.checkout.Session.create(
            mode="subscription", line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{base}/app/coworker/settings?checkout=success",
            cancel_url=f"{base}/app/coworker/settings?checkout=cancel",
            customer=state.get("customer_id") or None,
            metadata={"kind": "coworker_plan", "plan": target, "user_id": str(user_id)},
            subscription_data={"metadata": {"kind": "coworker_plan", "user_id": str(user_id)}},
        )
        return {"status": "checkout", "url": session["url"] if isinstance(session, dict) else session.url}
    sub = stripe.Subscription.retrieve(sub_id)
    item_id = sub["items"]["data"][0]["id"]
    stripe.Subscription.modify(sub_id, cancel_at_period_end=False, proration_behavior="create_prorations",
                               items=[{"id": item_id, "price": price_id}],
                               metadata={"kind": "coworker_plan", "user_id": str(user_id)})
    store.update_coworker(user_id, plan=target)
    _save_billing(store, user_id, cancel_at_period_end=False)
    verb = direction(current, target)
    store.log(user_id, "billing", f"{'Upgraded' if verb == 'upgrade' else 'Moved'} to {PLANS[target]['name']} "
                                  "(prorated on your next invoice)")
    return {"status": "changed", "plan": target, "direction": verb}


def portal_url(store: Store, user_id: int, return_url: str) -> str:
    customer = billing_state(store.get_coworker(user_id) or {}).get("customer_id")
    if not customer or not os.environ.get("STRIPE_SECRET_KEY"):
        raise PlanError("No billing account yet. Pick a paid plan first.")
    session = _stripe().billing_portal.Session.create(customer=customer, return_url=return_url)
    return str(session["url"] if isinstance(session, dict) else session.url)


def apply_subscription_event(store: Store, event_type: str, obj: dict[str, Any]) -> bool:
    """Keep the plan in sync with Stripe (portal changes, renewals ending)."""
    meta = obj.get("metadata") or {}
    if meta.get("kind") != "coworker_plan" or not meta.get("user_id"):
        return False
    user_id = int(meta["user_id"])
    if event_type == "customer.subscription.deleted":
        store.update_coworker(user_id, plan="free")
        _save_billing(store, user_id, subscription_id=None, cancel_at_period_end=False)
        store.log(user_id, "billing", "Your subscription ended; you're on the Free plan")
        return True
    items = ((obj.get("items") or {}).get("data") or [])
    plan = plan_for_price(((items[0] if items else {}).get("price") or {}).get("id", ""))
    _save_billing(store, user_id, subscription_id=obj.get("id"), customer_id=obj.get("customer"),
                  cancel_at_period_end=bool(obj.get("cancel_at_period_end")),
                  current_period_end=obj.get("current_period_end"))
    if plan and plan != plan_of(store.get_coworker(user_id) or {}):
        store.update_coworker(user_id, plan=plan)
        store.log(user_id, "billing", f"Plan changed to {PLANS[plan]['name']}")
    return True
