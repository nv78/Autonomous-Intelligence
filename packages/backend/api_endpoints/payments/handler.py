"""Stripe payment endpoints — subscription checkout/portal, credit top-ups,
and the webhook that keeps plan/credits in sync with Stripe."""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

from constants import CREDIT_PACKS, PLAN_CREDITS, PLAN_SEARCHES
from database.db import (
    add_purchased_credits,
    claim_stripe_event,
    downgrade_to_free,
    get_connection,
    get_stripe_customer,
    get_user_id_for_stripe_customer,
    release_stripe_event,
    set_plan_and_credits,
    update_stripe_customer_status,
    upsert_stripe_customer,
)
from middleware.auth import require_auth

payments_bp = Blueprint("payments", __name__, url_prefix="/api/payments")


def _frontend_url() -> str:
    return os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")


def _stripe_client() -> tuple:
    """Returns (stripe module, error response) — exactly one is non-None."""
    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not stripe_key:
        return None, (jsonify({"error": "Stripe not configured"}), 503)
    import stripe
    stripe.api_key = stripe_key
    return stripe, None


_PLAN_PRICE_ENV = {
    "basic": "STRIPE_PRICE_BASIC",
    "pro": "STRIPE_PRICE_PRO",
    "enterprise": "STRIPE_PRICE_ENTERPRISE",
}


@payments_bp.get("/plans")
def list_plans() -> tuple:
    """Paid plan tiers available for upgrade, with pricing/quota info.

    A plan is only purchasable once its Stripe Price ID is configured via
    env — unconfigured tiers are still listed (for display) but flagged.
    """
    plans = []
    for plan, env_key in _PLAN_PRICE_ENV.items():
        price_id = os.environ.get(env_key, "")
        plans.append({
            "plan": plan,
            "credits": PLAN_CREDITS.get(plan, 0),
            "monthlyLimit": PLAN_SEARCHES.get(plan, 0),
            "available": bool(price_id),
        })
    return jsonify({"plans": plans, "creditPacks": CREDIT_PACKS}), 200


@payments_bp.post("/checkout")
@require_auth
def create_checkout() -> tuple:
    """Start a subscription checkout for one of the plan tiers."""
    stripe, err = _stripe_client()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    plan = data.get("plan", "")
    if plan not in PLAN_CREDITS or plan == "free":
        return jsonify({"error": "Invalid plan"}), 400
    # Price IDs are server-owned billing configuration. Trusting a client-
    # supplied Price while separately trusting its requested plan would let a
    # caller pay for one tier and grant itself another tier's allowance.
    price_id = os.environ.get(_PLAN_PRICE_ENV[plan], "")
    if not price_id:
        return jsonify({"error": "Plan is not configured"}), 503
    user_id = int(get_jwt_identity())
    return_url = _frontend_url()
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{return_url}/app/checkout?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{return_url}/app/checkout?checkout=cancelled",
            metadata={"user_id": user_id, "plan": plan},
        )
        return jsonify({"url": session.url}), 200
    except Exception as exc:
        print(f"Stripe error: {exc}")
        return jsonify({"error": "Internal server error"}), 500


@payments_bp.post("/credits/checkout")
@require_auth
def create_credit_checkout() -> tuple:
    """Start a one-off checkout to purchase a credit pack."""
    stripe, err = _stripe_client()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    credits = int(data.get("credits", 0) or 0)
    amount_cents = CREDIT_PACKS.get(credits)
    if not amount_cents:
        return jsonify({"error": "Invalid credit pack"}), 400
    user_id = int(get_jwt_identity())
    return_url = _frontend_url()
    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "unit_amount": amount_cents,
                    "product_data": {"name": f"{credits:,} Anote credits"},
                },
                "quantity": 1,
            }],
            success_url=f"{return_url}/app/checkout?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{return_url}/app/checkout?checkout=cancelled",
            metadata={"user_id": user_id, "credits": credits, "kind": "credit_pack"},
        )
        return jsonify({"url": session.url}), 200
    except Exception as exc:
        print(f"Stripe error: {exc}")
        return jsonify({"error": "Internal server error"}), 500


@payments_bp.get("/checkout/session/<session_id>")
@require_auth
def get_checkout_session(session_id: str) -> tuple:
    """Look up a completed Checkout Session for display on the success page.

    Reads directly from Stripe rather than local state so the amount shown
    is accurate immediately on redirect, without waiting on the webhook.
    Restricted to the session's own owner via its metadata.user_id.
    """
    stripe, err = _stripe_client()
    if err:
        return err
    user_id = int(get_jwt_identity())
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception as exc:
        print(f"Stripe error: {exc}")
        return jsonify({"error": "Checkout session not found"}), 404
    metadata = session.get("metadata") or {}
    if metadata.get("user_id") != str(user_id):
        return jsonify({"error": "Checkout session not found"}), 404
    if session.get("status") == "complete":
        try:
            _fulfill_checkout_session(session_id, session, already_claimed=False)
        except Exception as exc:
            print(f"Checkout fulfillment error: {exc}")
    return jsonify({
        "status": session.get("payment_status"),
        "amountTotal": session.get("amount_total"),
        "currency": session.get("currency"),
        "kind": metadata.get("kind") or ("subscription" if session.get("mode") == "subscription" else "credit_pack"),
        "plan": metadata.get("plan"),
        "credits": int(metadata["credits"]) if metadata.get("credits") else None,
    }), 200


@payments_bp.post("/portal")
@require_auth
def create_portal() -> tuple:
    """Open the Stripe billing portal for the caller's own subscription.

    The Stripe customer id is looked up server-side from the caller's JWT
    identity — never trusted from the request — so one user can't open
    another's billing portal.
    """
    stripe, err = _stripe_client()
    if err:
        return err
    user_id = int(get_jwt_identity())
    cnx = get_connection()
    try:
        customer = get_stripe_customer(cnx, user_id)
    finally:
        cnx.close()
    if not customer:
        return jsonify({"error": "No billing account found for this user"}), 404
    return_url = _frontend_url()
    try:
        session = stripe.billing_portal.Session.create(
            customer=customer["stripe_id"],
            return_url=f"{return_url}/app",
        )
        return jsonify({"url": session.url}), 200
    except Exception as exc:
        print(f"Stripe error: {exc}")
        return jsonify({"error": "Internal server error"}), 500


@payments_bp.post("/webhook")
def stripe_webhook() -> tuple:
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature", "")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not webhook_secret or not stripe_key:
        # A 2xx response permanently acknowledges the event. Fail closed so
        # Stripe retries after a transient or accidental configuration gap.
        return jsonify({"error": "Stripe webhook not configured"}), 503

    import stripe
    stripe.api_key = stripe_key
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception as exc:
        print(f"Webhook signature error: {exc}")
        return jsonify({"error": "Invalid webhook signature"}), 400

    # Stripe can and does redeliver the same event more than once (retries,
    # at-least-once delivery) — claim it first so a redelivery is a no-op
    # instead of double-crediting a purchase or reprocessing a subscription.
    event_id = event.get("id", "")
    if event_id:
        cnx = get_connection()
        try:
            claimed = claim_stripe_event(cnx, event_id, event.get("type", ""))
        finally:
            cnx.close()
        if not claimed:
            return jsonify({"received": True}), 200

    try:
        _handle_webhook_event(event)
    except Exception as exc:
        print(f"Webhook handling error: {exc}")
        # The claim must be released before returning a retryable error;
        # otherwise the next Stripe delivery would be treated as a duplicate
        # even though the customer was never credited or upgraded.
        if event_id:
            cnx = get_connection()
            try:
                release_stripe_event(cnx, event_id)
            finally:
                cnx.close()
        return jsonify({"error": "Webhook processing failed"}), 500
    return jsonify({"received": True}), 200


def _fulfill_checkout_session(session_id: str, obj: dict, already_claimed: bool) -> None:
    """Grant the credits/plan for a completed Checkout Session.

    Called from both the webhook (`checkout.session.completed`) and, as a
    synchronous fallback, from the session-lookup endpoint the success page
    polls — so a purchase is reflected immediately even if the webhook is
    slow, misconfigured, or (in local dev) not forwarded at all.

    The webhook has already claimed this event by its Stripe event id before
    calling in here (`already_claimed=True`), so it owns dedup/retry via that
    claim and this function must not take out — or release — a second,
    session-scoped claim of its own. The session-lookup endpoint has no such
    claim, so it takes one out itself (`already_claimed=False`) to stay a
    no-op against a webhook delivery that's already fulfilling (or already
    fulfilled) the same session.
    """
    cnx = get_connection()
    try:
        if not already_claimed:
            if not claim_stripe_event(cnx, f"checkout_session:{session_id}", "checkout_session_fulfillment"):
                return
        metadata = obj.get("metadata") or {}
        try:
            if metadata.get("kind") == "coworker_plan":
                from coworker.billing import apply_checkout
                from coworker.store import get_store

                apply_checkout(get_store(), metadata, obj)
            elif metadata.get("kind") == "credit_pack":
                user_id = int(metadata["user_id"])
                credits = int(metadata["credits"])
                add_purchased_credits(cnx, user_id, credits)
            elif obj.get("mode") == "subscription":
                user_id = int(metadata["user_id"])
                plan = metadata.get("plan", "free")
                customer_id = obj.get("customer", "")
                upsert_stripe_customer(cnx, user_id, customer_id, plan, "active")
                set_plan_and_credits(cnx, user_id, plan, PLAN_CREDITS.get(plan, 0))
        except Exception:
            if not already_claimed:
                release_stripe_event(cnx, f"checkout_session:{session_id}")
            raise
    finally:
        cnx.close()


def _handle_webhook_event(event: dict) -> None:
    event_type = event.get("type", "")
    obj = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        _fulfill_checkout_session(obj.get("id", ""), obj, already_claimed=True)

    elif event_type == "invoice.payment_succeeded":
        # Fired on subscription renewal (and the first invoice) — this is
        # what grants each billing period's credit allowance.
        customer_id = obj.get("customer", "")
        cnx = get_connection()
        try:
            renewing_user_id = get_user_id_for_stripe_customer(cnx, customer_id)
            if renewing_user_id is not None:
                customer = get_stripe_customer(cnx, renewing_user_id)
                plan = (customer or {}).get("plan") or "free"
                set_plan_and_credits(cnx, renewing_user_id, plan, PLAN_CREDITS.get(plan, 0))
        finally:
            cnx.close()

    elif event_type in ("customer.subscription.deleted", "customer.subscription.updated"):
        if (obj.get("metadata") or {}).get("kind") == "coworker_plan":
            from coworker.billing import apply_subscription_event
            from coworker.store import get_store

            apply_subscription_event(get_store(), event_type, obj)
            return
        customer_id = obj.get("customer", "")
        cancellation_requested = (
            event_type == "customer.subscription.deleted"
            or (obj.get("cancellation_details") or {}).get("reason") == "cancellation_requested"
        )
        if not cancellation_requested:
            return
        cnx = get_connection()
        try:
            canceling_user_id = get_user_id_for_stripe_customer(cnx, customer_id)
            if canceling_user_id is not None:
                downgrade_to_free(cnx, canceling_user_id)
                update_stripe_customer_status(cnx, customer_id, "canceled")
        finally:
            cnx.close()
