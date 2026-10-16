"""AI-safety rules: what counts as the owner's request, what teammates and live calls can hear, blocked domains."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from coworker import chatbots, executor, memory, orgs, tools
from coworker.connectors.demo import DemoConnector
from coworker.store import Store


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("COWORKER_OFFLINE", "1")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with patch("services.provider_keys.get_user_provider_key", return_value=None):
        yield


@pytest.fixture
def s(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/ai.db")
    store.create_coworker(1, "Natan Vidra", "natan@anote.ai", mode="demo")
    DemoConnector.seed(store, 1, "Natan Vidra", "natan@anote.ai")
    memory.rebuild(store, 1)
    return store


def _send(ctx, to):
    tools.run("send_email", {"to": [to], "subject": "Hi", "body": "Hello"}, ctx)
    return ctx.store.query("SELECT risk FROM cw_actions WHERE user_id = 1 ORDER BY id DESC LIMIT 1")[0]["risk"]


def _codes(risk):
    import json

    return {r["code"] for r in (json.loads(risk) if isinstance(risk, str) else risk or [])}


def test_recipient_must_come_from_the_owner_once_other_text_is_read(s):
    ctx = tools.ToolContext(store=s, user_id=1, owner_message="Email Dana a quick hello")
    assert tools._requested(ctx)
    assert "recipient_not_requested" not in _codes(_send(ctx, "attacker@evil.com"))  # nothing untrusted read yet

    tools.run("search_memory", {"query": "pricing"}, ctx)
    assert ctx.read_untrusted and not tools._requested(ctx)
    assert "recipient_not_requested" in _codes(_send(ctx, "attacker@evil.com"))
    assert "recipient_not_requested" not in _codes(_send(ctx, "dana.lee@northwind.com"))  # the owner named Dana
    assert "recipient_not_requested" not in _codes(_send(ctx, "natan@anote.ai"))  # the owner themselves


def test_scheduled_runs_never_count_as_requested(s):
    ctx = tools.ToolContext(store=s, user_id=1, responsibility={"id": 7, "autonomy": "silent"})
    assert not tools._requested(ctx)
    with patch("coworker.push.approval_needed") as push:
        executor.propose(s, 1, "email.send", {"to": ["x@y.com"], "subject": "s", "body": "b"}, title="t",
                         chat_id=5, responsibility={"id": 7})
        assert push.called  # nobody is watching a scheduled run's chat
        push.reset_mock()
        executor.propose(s, 1, "email.send", {"to": ["x@y.com"], "subject": "s", "body": "b"}, title="t", chat_id=5)
        assert not push.called  # the card is in the chat the owner is using


def test_teammates_hear_only_decisions_and_docs(s):
    assert {"email", "slack"} & {h["type"] for h in memory.recall(s, 1, "pricing")}
    shared = memory.shareable_recall(s, 1, "pricing")
    assert shared and all(h["type"] in memory.SHAREABLE_TYPES for h in shared)


def test_live_call_draws_only_on_docs_and_that_contact(s):
    assert {h["type"] for h in memory.recall_with(s, 1, "pricing", "someone@unknown-co.com", k=10)} == {"doc"}
    dana = memory.recall_with(s, 1, "pricing", "dana@northwindcap.com", k=10)
    assert any(h.get("from_email") == "dana@northwindcap.com" for h in dana)
    assert not any(h.get("from_email") == "alex@anote.ai" for h in dana)  # an internal Slack thread stays private


def test_teammate_auto_answer_waits_for_employer_ok(s):
    s.update_coworker(1, autonomy={"slack.post": "silent"})
    with patch("coworker.drafting.slack_answer", return_value={"text": "Yes.", "confident": True}):
        with patch("coworker.governance.needs_employer_ok", return_value=True):
            assert chatbots.teammate(s, 1, "Dana", "is it on?")["owner_note"]
        with patch("coworker.governance.needs_employer_ok", return_value=False):
            assert chatbots.teammate(s, 1, "Dana", "is it on?")["owner_note"] == ""
    with patch("coworker.governance.org_disabled", return_value=True):
        assert "paused" in chatbots.teammate(s, 1, "Dana", "hi")["text"]


def test_blocked_domains_cover_subdomains_and_display_names(s):
    with patch("coworker.orgs.policies", return_value={"blocked_domains": ["@Competitor.com", " "]}):
        got = orgs.blocked_recipients(s, 1, ["a@competitor.com", "b@mail.competitor.com", "Eve <e@COMPETITOR.com.>",
                                            "c@notcompetitor.com", "d@ok.com"])
    assert got == ["a@competitor.com", "b@mail.competitor.com", "Eve <e@COMPETITOR.com.>"]
