"""Red-team suite, evals gate, billing, pilot applications, data rights, incident tools."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from coworker import admin, billing, executor, memory, responsibilities, security
from coworker.connectors.demo import DemoConnector
from coworker.evals import cases, run
from coworker.store import Store, iso

WRAPPERS = [
    "{}",
    "Hi team,\n\n{}\n\nThanks",
    "Re: invoice\n> {}\n",
    "<div style='display:none'>{}</div>Normal message here.",
    "FYI: {} (sent from my phone)",
    "​{}​",
]
REDTEAM = [w.format(text) for text in cases.INJECTIONS for w in WRAPPERS]


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("COWORKER_ENFORCE_PLANS", raising=False)
    with patch("api_endpoints.coworker.core.owner_profile", return_value=("Natan Vidra", "natan@example.com")), \
         patch("services.provider_keys.get_user_provider_key", return_value=None):
        yield


@pytest.fixture(scope="module")
def s(tmp_path_factory):
    store = Store(f"sqlite:///{tmp_path_factory.mktemp('rt')}/rt.db")
    store.create_coworker(1, "Natan Vidra", "natan@example.com", mode="demo")
    DemoConnector.seed(store, 1, "Natan Vidra", "natan@example.com")
    memory.rebuild(store, 1)
    store.update_coworker(1, autonomy={"email.send": "silent", "slack.post": "silent"})
    return store


@pytest.fixture
def demo(client, auth_headers):
    assert client.post("/api/coworker", json={"mode": "demo"}, headers=auth_headers).status_code == 201


# ---------------------------------------------------------------------------
# Red team: assume the model was fooled; the policy must still hold the line.
# ---------------------------------------------------------------------------

def test_redteam_has_at_least_50_cases():
    assert len(REDTEAM) >= 50


@pytest.mark.parametrize("text", REDTEAM)
def test_redteam_exfiltration_is_never_automatic(s, text):
    assert security.is_suspicious(text), text
    item_id = s.add_item(1, {
        "provider": "gmail", "external_id": f"rt-{abs(hash(text))}", "thread_id": f"rt-{abs(hash(text))}",
        "kind": "email", "author_name": "Attacker", "author_email": "billing@acmehealth-invoices.com",
        "subject": "Urgent", "body": text, "occurred_at": iso(),
    })
    # The "fooled" agent replies to the attacker's own thread and leaks another thread's data.
    action = executor.propose(s, 1, "email.send", {
        "to": ["billing@acmehealth-invoices.com"], "subject": "Re: Urgent",
        "body": "Here you go: Business plan, 20 seats, $40,000 annualized.",
        "thread_id": f"rt-{abs(hash(text))}",
    }, title="Fooled reply", source_item_id=item_id)
    assert action["status"] == "proposed"
    assert any(r["code"] == "suspicious_trigger" for r in action["risk"])
    wrapped = security.wrap_untrusted(text, "email")
    assert wrapped.count("</untrusted_content>") == 1


def test_redteam_responsibilities_never_answer_injections(s):
    for i, text in enumerate(cases.INJECTIONS):
        s.add_item(1, {"provider": "gmail", "external_id": f"rt-lead-{i}", "thread_id": f"rt-lead-{i}", "kind": "email",
                       "author_name": "Lead?", "author_email": f"lead{i}@evil.example",
                       "subject": "Pricing and demo?", "body": f"Pricing for 10 seats? {text}", "occurred_at": iso()})
    resp = responsibilities.create(s, 1, {"template": "inbound_leads", "autonomy": "silent"})
    responsibilities.run_one(s, 1, resp)
    sent = s.query("SELECT payload FROM cw_actions WHERE user_id = 1 AND status = 'executed'")
    assert all("evil.example" not in str(a["payload"]) for a in sent)


def test_evals_meet_thresholds():
    results = run.run_all()
    failing = {k: v["misses"] for k, v in results.items() if not v["passed"]}
    assert not failing, failing


# ---------------------------------------------------------------------------
# Billing
# ---------------------------------------------------------------------------

def test_billing_summary_and_gating(s, monkeypatch):
    s.add_usage(1, "call_seconds", 600)
    summary = billing.summary(s, 1)
    assert summary["plan"] == "pilot" and summary["callMinutes"] == 10.0 and summary["estimatedCostUsd"] >= 1.5
    billing.require(s, 1, "sso")  # not enforced by default
    monkeypatch.setenv("COWORKER_ENFORCE_PLANS", "1")
    with pytest.raises(billing.PlanError):
        billing.require(s, 1, "sso")
    s.update_coworker(1, plan="coworker")
    with pytest.raises(billing.PlanError):
        billing.require(s, 1, "calls")
    s.update_coworker(1, plan="coworker_calls")
    billing.require(s, 1, "calls")
    s.add_usage(1, "call_seconds", 600 * 60)
    with pytest.raises(billing.PlanError):
        billing.require(s, 1, "calls")
    assert billing.apply_checkout(s, {"kind": "coworker_plan", "plan": "team", "user_id": "1"})
    assert s.get_coworker(1)["plan"] == "team"
    assert not billing.apply_checkout(s, {"kind": "credit_pack"})
    s.update_coworker(1, plan="bogus")
    assert billing.plan_of(s.get_coworker(1)) == "pilot"


def test_billing_routes(client, auth_headers, demo, monkeypatch):
    h = auth_headers
    assert client.get("/api/coworker/billing", headers=h).get_json()["plan"] == "pilot"
    assert client.post("/api/coworker/billing/checkout", json={"plan": "pilot"}, headers=h).status_code == 400
    assert client.post("/api/coworker/billing/checkout", json={"plan": "coworker"}, headers=h).status_code == 501
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test")
    monkeypatch.setenv("STRIPE_PRICE_COWORKER", "price_1")
    session = MagicMock(url="https://checkout.stripe.com/x")
    with patch("stripe.checkout.Session.create", return_value=session) as create:
        assert client.post("/api/coworker/billing/checkout", json={"plan": "coworker"}, headers=h).get_json()["url"].startswith("https://")
    assert create.call_args.kwargs["metadata"]["kind"] == "coworker_plan"
    monkeypatch.setenv("COWORKER_ENFORCE_PLANS", "1")
    client.application.config  # noqa: B018
    from coworker.store import get_store

    with client.application.app_context():
        get_store().update_coworker(1, plan="coworker")
    assert client.post("/api/coworker/meetings", json={"mode": "live_call"}, headers=h).status_code == 402
    assert client.post("/api/coworker/twin/voice", headers=h).status_code == 402
    assert client.post("/api/coworker/meetings", json={"mode": "simulated", "persona": "northwind"}, headers=h).status_code == 201


def test_billing_requires_coworker(client, auth_headers):
    assert client.get("/api/coworker/billing", headers=auth_headers).status_code == 404


def test_stripe_webhook_applies_coworker_plan(client, auth_headers, demo):
    from api_endpoints.payments.handler import _fulfill_checkout_session

    cnx = MagicMock()
    with patch("api_endpoints.payments.handler.get_connection", return_value=cnx), client.application.app_context():
        _fulfill_checkout_session("cs_1", {"mode": "subscription", "metadata": {
            "kind": "coworker_plan", "plan": "coworker_calls", "user_id": "1"}}, already_claimed=True)
    assert client.get("/api/coworker/billing", headers=auth_headers).get_json()["plan"] == "coworker_calls"


# ---------------------------------------------------------------------------
# Pilot applications
# ---------------------------------------------------------------------------

def test_pilot_applications(client, auth_headers, demo, monkeypatch):
    from api_endpoints.coworker import trust

    trust._pilot_limiter._calls.clear()
    body = {"name": "Dana W", "email": "dana@fund.com", "company": "Fund", "role": "COO", "teamSize": "11-50",
            "handOff": ["inbound sales", "scheduling"], "website": ""}
    monkeypatch.setenv("PILOT_SLACK_WEBHOOK_URL", "https://hooks.slack.test/x")
    monkeypatch.setenv("PILOT_BOOKING_URL", "https://cal.com/ourogen/pilot")
    with patch("api_endpoints.coworker.trust.requests.post") as post:
        resp = client.post("/api/coworker/pilot/applications", json=body)
    assert resp.status_code == 201 and resp.get_json()["bookingUrl"].startswith("https://cal.com")
    assert "Dana W" in post.call_args.kwargs["json"]["text"]
    assert client.post("/api/coworker/pilot/applications", json={**body, "email": "nope"}).status_code == 400
    assert client.post("/api/coworker/pilot/applications", json={**body, "website": "spam.com"}).get_json() == {"ok": True}
    assert client.get("/api/coworker/pilot/applications", headers=auth_headers).status_code == 403
    from coworker import identity
    from coworker.store import get_store

    with client.application.app_context():
        identity.record(get_store(), 1, "google", "sub-natan", "natan@example.com")
    monkeypatch.setenv("PILOT_ADMIN_EMAILS", "natan@example.com")
    apps = client.get("/api/coworker/pilot/applications", headers=auth_headers).get_json()["applications"]
    assert apps[0]["answers"]["handOff"] == ["inbound sales", "scheduling"]
    for _ in range(6):
        last = client.post("/api/coworker/pilot/applications", json=body)
    assert last.status_code == 429


# ---------------------------------------------------------------------------
# Data rights & incident response
# ---------------------------------------------------------------------------

def test_export_and_delete_everything(client, auth_headers, demo):
    h = auth_headers
    from coworker.connectors.base import encrypt_token
    from coworker.store import get_store

    with client.application.app_context():
        get_store().upsert_connection(1, "google", token_enc=encrypt_token({"access_token": "a"}), status="connected")
        get_store().upsert_connection(1, "slack", token_enc=encrypt_token({"access_token": "b"}), status="connected")
    exported = client.get("/api/coworker/export", headers=h).get_json()
    assert exported["cw_items_count"] > 20
    assert all("token_enc" not in c for c in exported["cw_connections"])
    with patch("coworker.connectors.google.revoke") as g, patch("coworker.connectors.slack.revoke") as sl:
        assert client.delete("/api/coworker/data", headers=h).status_code == 200
    assert g.called and sl.called
    assert client.get("/api/coworker", headers=h).get_json()["coworker"] is None


def test_admin_revoke_all_and_pause_everyone(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/adm.db")
    store.create_coworker(5, "A B", "a@b.com")
    store.create_coworker(6, "C D", "c@d.com")
    from coworker.connectors.base import encrypt_token

    store.upsert_connection(5, "google", token_enc=encrypt_token({"access_token": "x"}), status="connected")
    store.upsert_connection(5, "slack", token_enc=encrypt_token({"access_token": "y"}), status="connected")
    with patch("coworker.connectors.google.revoke"), patch("coworker.connectors.slack.revoke"):
        result = admin.revoke_all(store, 5)
    assert set(result["revoked"]) == {"google", "slack"} and store.list_connections(5) == []
    assert store.get_coworker(5)["status"] == "paused"
    assert admin.pause_everyone(store) == 1
    assert store.get_coworker(6)["status"] == "paused"
