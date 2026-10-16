"""Model choice (any provider through one agent loop) and plan changes."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from coworker import billing, llm
from coworker.store import Store


@pytest.fixture
def s(tmp_path, monkeypatch):
    for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "OLLAMA_BASE_URL",
              "COWORKER_OFFLINE", "COWORKER_MODEL", "COWORKER_EXTRA_MODELS", "STRIPE_SECRET_KEY",
              "STRIPE_PRICE_COWORKER", "STRIPE_PRICE_COWORKER_CALLS", "STRIPE_PRICE_COWORKER_TEAM"):
        monkeypatch.delenv(k, raising=False)
    store = Store(f"sqlite:///{tmp_path}/m.db")
    store.create_coworker(1, "Natan Vidra", "natan@anote.ai", mode="demo")
    with patch("coworker.store.get_store", return_value=store), \
         patch("services.provider_keys.get_user_provider_key", return_value=None):
        yield store


# -- models -----------------------------------------------------------------------

def test_catalog_availability_and_selection(s, monkeypatch):
    models = {m["id"]: m for m in llm.models_for(1)}
    assert not any(m["available"] for m in models.values())
    assert models["claude-opus-5-5"]["selected"]
    monkeypatch.setenv("OPENAI_API_KEY", "sk")
    monkeypatch.setenv("COWORKER_EXTRA_MODELS", "openai:gpt-5, bogus, nope:x")
    models = {m["id"]: m for m in llm.models_for(1)}
    assert models["gpt-4o"]["available"] and models["gpt-5"]["available"] and "x" not in models
    s.update_coworker(1, settings={"model": "gpt-4o"})
    assert llm.model_name(1) == "gpt-4o" and llm.available(1)
    assert llm.provider_of("gemini-9") == "google" and llm.provider_of("o4-mini") == "openai"
    assert llm.provider_of("claude-x") == "anthropic" and llm.provider_of("mistral") == "ollama"
    monkeypatch.setenv("GOOGLE_API_KEY", "g")
    assert llm.key_for("google") == "g"
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    with patch("coworker.llm.ollama_up", return_value=True):
        assert llm.key_for("ollama") == "ollama"
    with patch("coworker.llm.ollama_up", return_value=False):
        assert llm.key_for("ollama") == ""  # configured but not running: not available
    with patch("services.provider_keys.get_user_provider_key", return_value="user-key"):
        assert llm.key_for("anthropic", 1) == "user-key"


def test_openai_translation_roundtrip():
    from coworker import tools

    messages = [
        {"role": "user", "content": "Reply to Dana"},
        {"role": "assistant", "content": [
            {"type": "thinking", "thinking": "x"}, {"type": "text", "text": "Looking."},
            {"type": "tool_use", "id": "t1", "name": "search_memory", "input": {"query": "Dana"}}]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t1", "content": "[]", "is_error": False},
            {"type": "tool_result", "tool_use_id": "t2", "content": [{"type": "text", "text": "bad"}], "is_error": True},
            {"type": "text", "text": "also this"}]},
    ]
    out = llm.to_openai_messages("SYS", messages)
    assert out[0] == {"role": "system", "content": "SYS"}
    assert out[2]["tool_calls"][0]["function"] == {"name": "search_memory", "arguments": '{"query": "Dana"}'}
    assert out[3] == {"role": "tool", "tool_call_id": "t1", "content": "[]"}
    assert out[4]["content"] == "ERROR: bad" and out[5] == {"role": "user", "content": "also this"}
    fns = llm.to_openai_tools(tools.DEFINITIONS)
    assert fns[0]["type"] == "function" and fns[0]["function"]["parameters"]["type"] == "object"
    resp = llm.from_openai_response({"model": "gpt-4o", "usage": {"prompt_tokens": 5, "completion_tokens": 2},
                                     "choices": [{"finish_reason": "tool_calls", "message": {"content": "On it.", "tool_calls": [
                                         {"id": "c1", "function": {"name": "who_is", "arguments": '{"name": "Dana"}'}},
                                         {"id": "c2", "function": {"name": "who_is", "arguments": "{oops"}}]}}]})
    assert resp["stop_reason"] == "tool_use" and resp["content"][1]["input"] == {"name": "Dana"}
    assert resp["content"][2]["input"] == "{oops" and resp["usage"] == {"input_tokens": 5, "output_tokens": 2}
    assert llm.from_openai_response({"choices": [{"finish_reason": "length", "message": {"content": "x"}}]})["stop_reason"] == "max_tokens"
    assert llm.from_openai_response({"choices": [{"finish_reason": "content_filter", "message": {}}]})["stop_reason"] == "refusal"


def test_create_message_dispatches_by_provider(s, monkeypatch):
    s.update_coworker(1, settings={"model": "gemini-2.5-flash"})
    monkeypatch.setenv("GEMINI_API_KEY", "gk")
    fake = MagicMock()
    fake.chat.completions.create.return_value.model_dump.return_value = {
        "choices": [{"finish_reason": "stop", "message": {"content": "Hello from Gemini"}}]}
    with patch("openai.OpenAI", return_value=fake) as ctor:
        assert llm.complete_text("hi", user_id=1) == "Hello from Gemini"
    assert ctor.call_args.kwargs["base_url"].startswith("https://generativelanguage.googleapis.com")
    assert ctor.call_args.kwargs["api_key"] == "gk"
    s.update_coworker(1, settings={"model": "llama3.1"})
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434/")
    with patch("openai.OpenAI", return_value=fake) as ctor:
        llm.create_message(system="s", messages=[{"role": "user", "content": "x"}], tools=[{"name": "t", "input_schema": {}}],
                           user_id=1)
    assert ctor.call_args.kwargs["base_url"] == "http://ollama:11434/v1"
    assert "tools" in fake.chat.completions.create.call_args.kwargs
    s.update_coworker(1, settings={"model": "claude-haiku-5-5"})
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ak")
    raw = MagicMock()
    raw.http_response.json.return_value = {"content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn"}
    with patch("anthropic.Anthropic") as anth:
        anth.return_value.messages.with_raw_response.create.return_value = raw
        assert llm.complete_text("hi", user_id=1) == "ok"
    kwargs = anth.return_value.messages.with_raw_response.create.call_args.kwargs
    assert kwargs["model"] == "claude-haiku-5-5" and "output_config" not in kwargs["extra_body"]


def test_brain_runs_on_openai_compatible_model(s, monkeypatch):
    """The whole agent loop (tool call, tool result, final answer) on a non-Claude model."""
    from coworker import brain, memory
    from coworker.connectors.demo import DemoConnector

    DemoConnector.seed(s, 1, "Natan Vidra", "natan@anote.ai")
    memory.rebuild(s, 1)
    s.update_coworker(1, settings={"model": "gpt-4o"})
    monkeypatch.setenv("OPENAI_API_KEY", "sk")
    replies = [
        {"choices": [{"finish_reason": "tool_calls", "message": {"content": None, "tool_calls": [
            {"id": "c1", "function": {"name": "who_is", "arguments": '{"name": "Dana"}'}}]}}]},
        {"choices": [{"finish_reason": "stop", "message": {"content": "Dana runs ops at Northwind."}}]},
    ]
    fake = MagicMock()
    fake.chat.completions.create.return_value.model_dump.side_effect = replies
    with patch("openai.OpenAI", return_value=fake):
        events = list(brain.run_turn(s, 1, None, "Who is Dana?", []))
    assert ("text", "Dana runs ops at Northwind.") in events
    assert any(k == "tool" and p["name"] == "who_is" for k, p in events)
    second = fake.chat.completions.create.call_args_list[1].kwargs["messages"]
    assert second[-1]["role"] == "tool" and second[-1]["tool_call_id"] == "c1"


def test_model_routes(client, auth_headers, monkeypatch):
    for k in ("OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    with patch("api_endpoints.coworker.core.owner_profile", return_value=("Natan Vidra", "natan@anote.ai")), \
         patch("services.provider_keys.get_user_provider_key", return_value=None):
        client.post("/api/coworker", json={"mode": "demo"}, headers=auth_headers)
        body = client.get("/api/coworker/models", headers=auth_headers).get_json()
        assert body["default"] == "claude-opus-5-5" and len(body["models"]) >= 8
        assert client.patch("/api/coworker", json={"settings": {"model": "nope"}}, headers=auth_headers).status_code == 400
        r = client.patch("/api/coworker", json={"settings": {"model": "gpt-4o"}}, headers=auth_headers)
        assert r.status_code == 400 and r.get_json()["code"] == "key_required"
        monkeypatch.setenv("OPENAI_API_KEY", "sk")
        assert client.patch("/api/coworker", json={"settings": {"model": "gpt-4o"}}, headers=auth_headers).status_code == 200


# -- plans ---------------------------------------------------------------------------

@pytest.fixture
def stripe_env(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test")
    monkeypatch.setenv("STRIPE_PRICE_COWORKER", "price_cw")
    monkeypatch.setenv("STRIPE_PRICE_COWORKER_CALLS", "price_calls")
    monkeypatch.setenv("STRIPE_PRICE_COWORKER_TEAM", "price_team")
    fake = MagicMock()
    with patch("coworker.billing._stripe", return_value=fake):
        yield fake


def test_first_purchase_goes_to_checkout(s, stripe_env):
    stripe_env.checkout.Session.create.return_value = {"url": "https://checkout.stripe.test/x"}
    out = billing.change_plan(s, 1, "coworker")
    assert out == {"status": "checkout", "url": "https://checkout.stripe.test/x"}
    kwargs = stripe_env.checkout.Session.create.call_args.kwargs
    assert kwargs["subscription_data"]["metadata"]["kind"] == "coworker_plan"
    assert billing.apply_checkout(s, {"kind": "coworker_plan", "plan": "coworker", "user_id": "1"},
                                  {"subscription": "sub_1", "customer": "cus_1"})
    assert s.get_coworker(1)["plan"] == "coworker"
    assert billing.billing_state(s.get_coworker(1))["subscription_id"] == "sub_1"


def test_upgrade_downgrade_and_cancel(s, stripe_env):
    s.update_coworker(1, plan="coworker", settings={"billing": {"subscription_id": "sub_1", "customer_id": "cus_1"}})
    stripe_env.Subscription.retrieve.return_value = {"items": {"data": [{"id": "si_1"}]}}
    up = billing.change_plan(s, 1, "coworker_calls")
    assert up["status"] == "changed" and up["direction"] == "upgrade" and s.get_coworker(1)["plan"] == "coworker_calls"
    args = stripe_env.Subscription.modify.call_args
    assert args.kwargs["items"] == [{"id": "si_1", "price": "price_calls"}]
    assert args.kwargs["proration_behavior"] == "create_prorations"
    down = billing.change_plan(s, 1, "coworker")
    assert down["direction"] == "downgrade"
    assert billing.change_plan(s, 1, "coworker")["status"] == "same"
    stripe_env.Subscription.modify.return_value = {"current_period_end": 1800000000}
    cancel = billing.change_plan(s, 1, "free")
    assert cancel == {"status": "scheduled", "plan": "free", "effectiveAt": 1800000000}
    assert s.get_coworker(1)["plan"] == "coworker"  # until the period ends
    summary = billing.summary(s, 1)
    assert summary["subscription"]["cancel_at_period_end"] and summary["hasBillingAccount"]
    assert {p["id"]: p["direction"] for p in summary["plans"]}["team"] == "upgrade"
    # Stripe ends the subscription at period end.
    assert billing.apply_subscription_event(s, "customer.subscription.deleted",
                                            {"metadata": {"kind": "coworker_plan", "user_id": "1"}})
    assert s.get_coworker(1)["plan"] == "free"


def test_plan_errors_and_portal(s, stripe_env, monkeypatch):
    with pytest.raises(billing.PlanError):
        billing.change_plan(s, 1, "pilot")
    with pytest.raises(billing.PlanError):
        billing.portal_url(s, 1, "https://x")
    s.update_coworker(1, settings={"billing": {"customer_id": "cus_1"}})
    stripe_env.billing_portal.Session.create.return_value = {"url": "https://billing.stripe.test/p"}
    assert billing.portal_url(s, 1, "https://x") == "https://billing.stripe.test/p"
    assert billing.change_plan(s, 1, "free") == {"status": "changed", "plan": "free"}  # no subscription to cancel
    monkeypatch.delenv("STRIPE_PRICE_COWORKER_TEAM")
    with pytest.raises(billing.PlanError, match="isn't available"):
        billing.change_plan(s, 1, "team")
    monkeypatch.delenv("STRIPE_SECRET_KEY")
    with pytest.raises(billing.PlanError, match="isn't configured"):
        billing.change_plan(s, 1, "coworker")


def test_portal_plan_change_syncs(s, stripe_env):
    assert not billing.apply_subscription_event(s, "customer.subscription.updated", {"metadata": {}})
    obj = {"id": "sub_9", "customer": "cus_9", "cancel_at_period_end": False, "current_period_end": 1,
           "metadata": {"kind": "coworker_plan", "user_id": "1"}, "items": {"data": [{"price": {"id": "price_team"}}]}}
    assert billing.apply_subscription_event(s, "customer.subscription.updated", obj)
    assert s.get_coworker(1)["plan"] == "team"
    assert billing.plan_for_price("nope") is None


def test_billing_routes(client, auth_headers, monkeypatch):
    with patch("api_endpoints.coworker.core.owner_profile", return_value=("Natan Vidra", "natan@anote.ai")):
        client.post("/api/coworker", json={"mode": "demo"}, headers=auth_headers)
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    assert client.post("/api/coworker/billing/change", json={"plan": "pilot"}, headers=auth_headers).status_code == 400
    assert client.post("/api/coworker/billing/change", json={"plan": "coworker"}, headers=auth_headers).status_code == 501
    assert client.post("/api/coworker/billing/change", json={"plan": "nope"}, headers=auth_headers).status_code == 400
    assert client.post("/api/coworker/billing/portal", headers=auth_headers).status_code == 400
    with patch("coworker.billing.change_plan", return_value={"status": "changed", "plan": "team"}):
        r = client.post("/api/coworker/billing/change", json={"plan": "team"}, headers=auth_headers)
    assert r.status_code == 200 and r.get_json()["plan"] == "team" and "billing" in r.get_json()
    with patch("coworker.billing.portal_url", return_value="https://p"):
        assert client.post("/api/coworker/billing/portal", headers=auth_headers).get_json()["url"] == "https://p"


def test_webhook_routes_coworker_subscription_events():
    from api_endpoints.payments import handler

    obj = {"metadata": {"kind": "coworker_plan", "user_id": "1"}}
    with patch("coworker.billing.apply_subscription_event") as apply, patch("coworker.store.get_store"):
        handler._handle_webhook_event({"type": "customer.subscription.deleted", "data": {"object": obj}})
    assert apply.call_args.args[1] == "customer.subscription.deleted"
