"""Coworker delegation: chat, tools, approvals, responsibilities, kill switch."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from coworker import brain, drafting, executor, memory, policy, responsibilities, scheduling, tools
from coworker.connectors.demo import DemoConnector
from coworker.store import Store, iso


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with patch("api_endpoints.coworker.core.owner_profile", return_value=("Natan Vidra", "natan@example.com")), \
         patch("services.provider_keys.get_user_provider_key", return_value=None):
        yield


@pytest.fixture
def s(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/deleg.db")
    store.create_coworker(1, "Natan Vidra", "natan@example.com", mode="demo")
    DemoConnector.seed(store, 1, "Natan Vidra", "natan@example.com")
    memory.rebuild(store, 1)
    return store


@pytest.fixture
def demo(client, auth_headers):
    assert client.post("/api/coworker", json={"mode": "demo"}, headers=auth_headers).status_code == 201


def _mock_cnx():
    cursor = MagicMock()
    cursor.lastrowid = 42
    cursor.rowcount = 1
    cursor.fetchone.return_value = {"id": 42, "name": "New Chat", "created_at": datetime.now(UTC)}
    cursor.fetchall.return_value = []
    cnx = MagicMock()
    cnx.cursor.return_value = cursor
    return cnx


def _sse(resp) -> list[dict]:
    out = []
    for line in resp.get_data(as_text=True).splitlines():
        if line.startswith("data: "):
            out.append(json.loads(line[6:]))
    return out


def _chat(client, headers, message, session_id=None):
    with patch("api_endpoints.coworker.delegation.get_connection", side_effect=lambda: _mock_cnx()):
        resp = client.post("/api/coworker/chat/stream", json={"message": message, "session_id": session_id}, headers=headers)
        assert resp.status_code == 200
        events = _sse(resp)
    text = "".join(e.get("text", "") for e in events if e["type"] == "text")
    return events, text


# ---------------------------------------------------------------------------
# Offline chat intents (no API key)
# ---------------------------------------------------------------------------

def test_chat_requires_coworker_and_message(client, auth_headers):
    assert client.post("/api/coworker/chat/stream", json={"message": "hi"}, headers=auth_headers).status_code == 404


def test_chat_inbox_triage(client, auth_headers, demo):
    events, text = _chat(client, auth_headers, "What needs a reply?")
    assert events[0]["type"] == "session_id"
    assert any(e["type"] == "tool" for e in events)
    assert "Sales lead" in text and "Dana Whitfield" in text
    assert any(e["type"] == "title" for e in events)


def test_chat_status_and_who_is(client, auth_headers, demo):
    _, text = _chat(client, auth_headers, "What's going on with Acme?")
    assert "Acme" in text and "waiting on them" in text
    assert "security review" in text
    _, text = _chat(client, auth_headers, "Who is Dana?", session_id=42)
    assert "Northwind Capital" in text and "prospect" in text


def test_chat_reply_creates_action_card(client, auth_headers, demo):
    events, text = _chat(client, auth_headers, "Reply to Dana")
    cards = [e for e in events if e["type"] == "card"]
    assert cards and cards[0]["action"]["type"] == "email.send"
    action = cards[0]["action"]
    assert action["status"] == "proposed"
    assert action["payload"]["to"] == ["dana@northwindcap.com"]
    assert "demo" in action["payload"]["body"].lower()
    assert "Approve" in text or "approve" in text


def test_chat_reply_with_instruction_and_followup(client, auth_headers, demo):
    events, _ = _chat(client, auth_headers, "Reply to Priya saying Tuesday at 2pm works for me")
    assert "Tuesday at 2pm works for me" in [e for e in events if e["type"] == "card"][0]["action"]["payload"]["body"]
    events, text = _chat(client, auth_headers, "Follow up with Sarah")
    action = [e for e in events if e["type"] == "card"][0]["action"]
    assert action["payload"]["to"] == ["sarah.chen@acmehealth.com"]
    assert "nudge" in text


def test_chat_schedule_with_person(client, auth_headers, demo):
    events, text = _chat(client, auth_headers, "Schedule a call with Priya next week")
    action = [e for e in events if e["type"] == "card"][0]["action"]
    assert "Would any of these work" in action["payload"]["body"]
    assert "open times" in text
    _, text = _chat(client, auth_headers, "Book time with Zelda Unknown next week")
    assert "couldn't find" in text


def test_chat_responsibility_proposal_then_confirm(client, auth_headers, demo):
    events, text = _chat(client, auth_headers, "From now on, handle all inbound sales leads")
    action = [e for e in events if e["type"] == "card"][0]["action"]
    assert action["type"] == "responsibility.create"
    assert action["payload"]["template"] == "inbound_leads"
    assert "Confirm" in text
    approved = client.post(f"/api/coworker/actions/{action['id']}/approve", headers=auth_headers).get_json()["action"]
    assert approved["status"] == "executed"
    resps = client.get("/api/coworker/responsibilities", headers=auth_headers).get_json()["responsibilities"]
    assert resps[0]["template"] == "inbound_leads"


def test_chat_misc_intents(client, auth_headers, demo):
    _, text = _chat(client, auth_headers, "What did we decide about Beta Corp?")
    assert "pass" in text
    _, text = _chat(client, auth_headers, "Prep me for my next meeting")
    assert "Prep brief" in text and "Suggested agenda" in text
    _, text = _chat(client, auth_headers, "What's on my calendar this week?")
    assert "Coming up" in text
    _, text = _chat(client, auth_headers, "Never use exclamation points")
    assert "follow that" in text
    events, text = _chat(client, auth_headers, "Tell Maya on Slack that we passed on Beta Corp until Q2")
    assert [e for e in events if e["type"] == "card"][0]["action"]["type"] == "slack.post"
    _, text = _chat(client, auth_headers, "Any pending approvals?")
    assert "Waiting for your approval" in text
    _, text = _chat(client, auth_headers, "SOC 2 bridge letter")
    assert "found" in text
    _, text = _chat(client, auth_headers, "zzqx")
    assert "not sure" in text


# ---------------------------------------------------------------------------
# Claude tool-use loop (mocked API)
# ---------------------------------------------------------------------------

def test_llm_loop_round_trips_blocks(s, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    first = {"stop_reason": "tool_use", "content": [
        {"type": "thinking", "thinking": "", "signature": "sig"},
        {"type": "text", "text": "Checking Acme."},
        {"type": "tool_use", "id": "tu1", "name": "account_status", "input": {"name": "Acme"}},
        {"type": "tool_use", "id": "tu2", "name": "send_email",
         "input": {"to": ["sarah.chen@acmehealth.com"], "subject": "Re: pilot", "body": "Hi Sarah, checking in.", "thread_id": "t-acme"}},
        {"type": "tool_use", "id": "tu3", "name": "nope", "input": "bad"},
    ]}
    second = {"stop_reason": "end_turn", "content": [{"type": "text", "text": "Drafted a nudge for your approval."}]}
    calls = []

    def fake_create(**kwargs):
        calls.append(json.loads(json.dumps(kwargs["messages"])))
        return first if len(calls) == 1 else second

    with patch("coworker.llm.create_message", side_effect=fake_create):
        events = list(brain.run_turn(s, 1, None, "Nudge Sarah", [{"role": "assistant", "content": "earlier"},
                                                                    {"role": "user", "content": "hi"}]))
    kinds = [k for k, _ in events]
    assert kinds.count("tool") == 2 and "card" in kinds
    assert calls[1][-2]["content"] == first["content"]  # assistant blocks passed back unchanged
    results = calls[1][-1]["content"]
    assert len(results) == 3 and all(r["type"] == "tool_result" for r in results)
    assert results[2]["is_error"] is True
    assert events[-1] == ("text", "Drafted a nudge for your approval.")


def test_llm_refusal_and_max_tokens(s, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    with patch("coworker.llm.create_message", return_value={"stop_reason": "refusal", "content": []}):
        assert list(brain.run_turn(s, 1, None, "x")) == [("text", "I can't help with that request.")]
    with patch("coworker.llm.create_message", return_value={"stop_reason": "max_tokens", "content": [{"type": "text", "text": "partial"}]}):
        events = list(brain.run_turn(s, 1, None, "x"))
    assert "ran out of room" in events[-1][1]


def test_system_prompt_mentions_rules(s):
    prompt = brain.system_prompt(s, 1)
    assert "untrusted_content" in prompt and "Never claim to be Natan" in prompt
    assert brain.strip_markers('hi\n:::cw {"t":"tool"}\nthere') == "hi\nthere"


def test_llm_create_message_kwargs(monkeypatch):
    from coworker import llm

    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    raw = MagicMock()
    raw.http_response.json.return_value = {"content": [{"type": "text", "text": "hello"}], "usage": {}, "stop_reason": "end_turn"}
    client = MagicMock()
    client.messages.with_raw_response.create.return_value = raw
    with patch("anthropic.Anthropic", return_value=client), patch("services.usage.record_usage"):
        assert llm.complete_text("hi") == "hello"
    kwargs = client.messages.with_raw_response.create.call_args.kwargs
    assert kwargs["model"] == "claude-opus-5-5"
    assert kwargs["extra_body"]["fallbacks"] == "default"
    assert kwargs["extra_body"]["output_config"]["effort"] == "low"
    assert kwargs["extra_headers"]["anthropic-beta"] == llm.FALLBACK_BETA
    assert llm.available() is True


def test_drafting_uses_llm_when_available(s, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    with patch("coworker.llm.complete_text", return_value="Hi Dana,\n\nHappy to demo.\n\nBest,\nNatan"):
        draft = drafting.compose_reply(s, 1, s.thread(1, "t-northwind"), "sales_lead")
    assert draft["body"].startswith("Hi Dana") and "Claude" in draft["reasoning"]
    with patch("coworker.llm.complete_text", return_value="We decided to pass on Beta Corp."):
        assert drafting.slack_answer(s, 1, "What about Beta Corp?")["confident"]
    with patch("coworker.llm.complete_text", return_value="NEEDS_NATAN"):
        assert not drafting.slack_answer(s, 1, "What's the wifi password?")["confident"]


# ---------------------------------------------------------------------------
# Drafting without a key
# ---------------------------------------------------------------------------

def test_template_drafts_by_category(s):
    lead = drafting.compose_reply(s, 1, s.thread(1, "t-northwind"), "sales_lead")
    assert lead["body"].startswith("Hi Dana,") and lead["body"].rstrip().endswith("Natan")
    assert "$49" in lead["body"] and len(lead["slots"]) == 3
    support = drafting.compose_reply(s, 1, s.thread(1, "t-globex"), "support")
    assert "50 MB" in support["body"]
    investor = drafting.compose_reply(s, 1, s.thread(1, "t-jordan"), "investor")
    assert "Pipeline" in investor["body"]
    fyi = drafting.compose_reply(s, 1, s.thread(1, "t-alex-ship"), "fyi")
    assert "Thanks" in fyi["body"]
    assert drafting.slack_answer(s, 1, "What did we decide about Beta Corp?")["confident"]
    assert not drafting.slack_answer(s, 1, "zzqx qqq?")["confident"]


def test_free_slots_avoid_busy_and_working_hours(s):
    slots = scheduling.free_slots(s, 1, count=3)
    assert len(slots) == 3
    days = {sl["start"][:10] for sl in slots}
    assert len(days) == 3
    tz = scheduling.tz_for(s.get_coworker(1))
    for sl in slots:
        local = datetime.fromisoformat(sl["start"].replace("Z", "+00:00")).astimezone(tz)
        assert 9 <= local.hour < 17 and local.weekday() < 5
    s.update_coworker(1, settings={"timezone": "Not/AZone"})
    assert scheduling.tz_for(s.get_coworker(1)).key == "America/New_York"


# ---------------------------------------------------------------------------
# Executor & policy
# ---------------------------------------------------------------------------

def _reply(s, thread="t-lumen"):
    draft = drafting.compose_reply(s, 1, s.thread(1, thread), "scheduling")
    item = [i for i in s.thread(1, thread) if i["direction"] == "inbound"][-1]
    return executor.propose(s, 1, "email.send", {"to": draft["to"], "subject": draft["subject"], "body": draft["body"],
                                                 "thread_id": thread}, title="Reply", source_item_id=item["id"])


def test_default_requires_approval_and_executes_with_disclosure(s):
    action = _reply(s)
    assert action["status"] == "proposed" and action["autonomy"] == "approve"
    done = executor.approve(s, 1, action["id"])
    assert done["status"] == "executed"
    sent = s.thread(1, "t-lumen")[-1]
    assert sent["direction"] == "outbound" and "AI coworker (Ourogen)" in sent["body"]
    with pytest.raises(executor.ActionError):
        executor.approve(s, 1, action["id"])


def test_notify_level_auto_executes_low_risk(s):
    s.update_coworker(1, autonomy={"email.send": "notify"})
    action = _reply(s)
    assert action["status"] == "executed"


def test_hard_floors_override_autonomy(s):
    s.update_coworker(1, autonomy={"email.send": "silent"})
    action = executor.propose(s, 1, "email.send", {"to": ["stranger@unknown.io"], "subject": "Hi", "body": "Our price is $99"},
                              title="Cold email", requested_in_chat=True)
    assert action["status"] == "proposed"
    assert {r["code"] for r in action["risk"]} >= {"new_recipient", "commercial_terms"}


def test_suggest_level_saves_draft(s):
    s.update_coworker(1, autonomy={"email.send": "suggest"})
    action = executor.approve(s, 1, _reply(s)["id"])
    assert action["result"]["draft"] is True


def test_edit_reject_undo_and_expiry(s):
    action = _reply(s)
    edited = executor.edit(s, 1, action["id"], {"body": "Edited body", "evil": "x"})
    assert edited["payload"]["body"] == "Edited body" and edited["edited"] == 1 and "evil" not in edited["payload"]
    rejected = executor.reject(s, 1, action["id"], "Too formal")
    assert rejected["status"] == "rejected"
    assert s.memories(1, kind="feedback")[0]["title"] == "Too formal"
    with pytest.raises(executor.ActionError):
        executor.edit(s, 1, action["id"], {"body": "x"})
    # undo while queued behind the send delay
    s.update_coworker(1, settings={"send_delay_seconds": 600})
    queued = executor.approve(s, 1, _reply(s)["id"])
    assert queued["status"] == "approved"
    assert executor.undo(s, 1, queued["id"])["status"] == "cancelled"
    # undo after execution (demo removes the sent item)
    s.update_coworker(1, settings={"send_delay_seconds": 0})
    done = executor.approve(s, 1, _reply(s)["id"])
    assert executor.undo(s, 1, done["id"])["status"] == "undone"
    with pytest.raises(executor.ActionError):
        executor.undo(s, 1, done["id"])
    with pytest.raises(executor.ActionError):
        executor.undo(s, 1, 9999)
    # expiry
    stale = _reply(s)
    s.update("cw_actions", stale["id"], 1, {"expires_at": "2000-01-01T00:00:00.000000Z"})
    assert executor.run_due(s, 1)["expired"] == 1


def test_approve_with_edits_rechecks_risk(s):
    action = _reply(s)
    done = executor.approve(s, 1, action["id"], {"to": ["someone.new@elsewhere.com"]})
    assert any(r["code"] == "new_recipient" for r in done["risk"])


def test_kill_switch(s):
    s.update_coworker(1, settings={"send_delay_seconds": 600})
    queued = executor.approve(s, 1, _reply(s)["id"])
    pending = _reply(s)
    assert executor.pause(s, 1, "testing") == 1
    assert s.get("cw_actions", queued["id"], 1)["status"] == "cancelled"
    with pytest.raises(executor.ActionError) as exc:
        executor.approve(s, 1, pending["id"])
    assert exc.value.code == "paused"
    assert executor.run_due(s, 1)["executed"] == 0
    resp = responsibilities.create(s, 1, {"template": "inbound_leads"})
    assert responsibilities.run_one(s, 1, resp) == []
    executor.resume(s, 1)
    assert s.get_coworker(1)["status"] == "active"


def test_failed_execution_is_recorded(s):
    action = executor.propose(s, 1, "calendar.create", {"title": "x", "attendees": ["dana@northwindcap.com"]},
                              title="Bad invite", requested_in_chat=True)
    done = executor.approve(s, 1, action["id"])
    assert done["status"] == "failed" and "start" in done["error"]


def test_crm_update_and_unknown_type(s):
    s.update_coworker(1, autonomy={"crm.update": "silent"})
    action = executor.propose(s, 1, "crm.update", {"company": "Northwind", "summary": "Qualified", "fields": {"budget": "yes"}},
                              title="CRM")
    assert action["status"] == "executed"
    assert s.memories(1, kind="crm")
    with pytest.raises(executor.ActionError):
        executor.propose(s, 1, "rocket.launch", {}, title="no")


def test_policy_levels_and_earned_autonomy(s):
    cw = s.get_coworker(1)
    assert policy.level_for(cw, "email.send") == "approve"
    assert policy.level_for(cw, "email.send", {"autonomy": "notify"}) == "notify"
    assert policy.decide("responsibility.create", "silent", [])["auto"] is False
    assert policy.earned_autonomy(s, 1, "email.send") is None
    for _ in range(policy.EARNED_AUTONOMY_STREAK):
        s.insert("cw_actions", {"user_id": 1, "type": "email.send", "status": "executed", "title": "x", "created_at": iso()})
    suggestion = policy.earned_autonomy(s, 1, "email.send")
    assert suggestion["to"] == "notify"


# ---------------------------------------------------------------------------
# Responsibilities
# ---------------------------------------------------------------------------

def test_inbound_leads_responsibility_is_idempotent(s):
    resp = responsibilities.create(s, 1, {"template": "inbound_leads"})
    first = responsibilities.run_one(s, 1, resp)
    assert first == ["Drafted a reply to Dana Whitfield"]
    assert responsibilities.run_one(s, 1, s.get("cw_responsibilities", resp["id"], 1)) == []
    DemoConnector.inject(s, 1, "new_lead")
    assert responsibilities.run_one(s, 1, resp) == ["Drafted a reply to Elena Rossi"]


def test_injection_email_is_not_answered(s):
    DemoConnector.inject(s, 1, "injection")
    memory.rebuild(s, 1)
    resp = responsibilities.create(s, 1, {"template": "inbound_leads"})
    responsibilities.run_one(s, 1, resp)
    actions = s.query("SELECT * FROM cw_actions WHERE user_id = 1")
    assert all("protonmail" not in json.dumps(a["payload"]) for a in actions)
    assert any(a["kind"] == "security" for a in s.activity(1))


def test_other_templates(s):
    out = []
    for template in ("scheduling", "support", "meeting_prep", "stale_deals", "slack_answers", "meeting_followup"):
        out += responsibilities.run_one(s, 1, responsibilities.create(s, 1, {"template": template}))
    joined = " | ".join(out)
    assert "Priya" in joined and "Kevin" in joined
    assert "Prepared a brief" in joined and "follow-up" in joined
    assert "Slack" in joined
    briefs = [a for a in s.activity(1) if a["kind"] == "brief"]
    assert briefs[0]["detail"]["brief"]["agenda"]


def test_custom_and_digest(s):
    custom = responsibilities.create(s, 1, responsibilities.proposal_payload("Flag anything about the founding engineer role"))
    assert custom["template"] == "custom"
    assert responsibilities.run_one(s, 1, custom)
    late = datetime(2026, 10, 15, 23, 0, tzinfo=UTC)
    with patch("coworker.responsibilities.utcnow", return_value=late):
        digest_resp = responsibilities.create(s, 1, {"template": "daily_digest"})
        assert responsibilities.run_one(s, 1, digest_resp) == ["Posted the daily digest"]
        assert responsibilities.run_one(s, 1, digest_resp) == []
    assert "Handled" in responsibilities.digest(s, 1)["headline"]


def test_template_matching_and_suggestions(s):
    assert responsibilities.match_template("handle my inbound leads") == "inbound_leads"
    assert responsibilities.match_template("brief me before every call") == "meeting_prep"
    assert responsibilities.match_template("nudge deals that go quiet") == "stale_deals"
    assert responsibilities.match_template("answer my teammates on slack") == "slack_answers"
    assert responsibilities.match_template("send me a daily digest") == "daily_digest"
    assert responsibilities.match_template("water the plants") == "custom"
    names = [sg["template"] for sg in responsibilities.suggestions(s, 1)]
    assert "inbound_leads" in names and "meeting_prep" in names


def test_tools_direct(s):
    ctx = tools.ToolContext(store=s, user_id=1)
    assert tools.run("read_thread", {"thread_id": "t-northwind"}, ctx)[0][0]["body"].startswith("<untrusted_content")
    assert tools.run("draft_reply", {"thread_id": "missing"}, ctx)[0]["error"]
    assert tools.run("schedule_meeting", {"title": "x", "attendees": [], "start": "nope"}, ctx)[0]["error"]
    result, _ = tools.run("schedule_meeting", {"title": "Demo", "attendees": ["dana@northwindcap.com"],
                                               "start": "2026-11-02T15:00:00Z"}, ctx)
    assert result["status"] == "proposed"
    assert tools.run("list_responsibilities", {}, ctx)[0] == []
    assert tools.run("nope", {}, ctx)[0]["error"]
    assert tools.run("meeting_brief", {"query": "Marcus"}, ctx)[0]["event"]["title"] == "Marcus Lee — intro chat"
    assert tools.labels()["email.send"] == "Send email"


# ---------------------------------------------------------------------------
# HTTP routes
# ---------------------------------------------------------------------------

def test_action_routes(client, auth_headers, demo):
    h = auth_headers
    body = client.post("/api/coworker/responsibilities", json={"template": "inbound_leads"}, headers=h).get_json()
    assert body["results"] == ["Drafted a reply to Dana Whitfield"]
    pending = client.get("/api/coworker/actions?status=proposed", headers=h).get_json()["actions"]
    aid = pending[0]["id"]
    assert client.get(f"/api/coworker/actions?ids={aid},x", headers=h).get_json()["actions"][0]["id"] == aid
    assert client.get("/api/coworker/actions?ids=x", headers=h).get_json()["actions"] == []
    assert client.patch(f"/api/coworker/actions/{aid}", json={"payload": {"body": "Short"}}, headers=h).status_code == 200
    assert client.post(f"/api/coworker/actions/{aid}/approve", headers=h).get_json()["action"]["status"] == "executed"
    assert client.post(f"/api/coworker/actions/{aid}/approve", headers=h).status_code == 409
    assert client.post(f"/api/coworker/actions/{aid}/undo", headers=h).status_code == 200
    assert client.post("/api/coworker/actions/9999/reject", headers=h).status_code == 404
    status = client.get("/api/coworker/status", headers=h).get_json()
    assert status["exists"] and status["status"] == "active"


def test_kill_switch_routes(client, auth_headers, demo):
    h = auth_headers
    assert client.post("/api/coworker/pause", json={"reason": "test"}, headers=h).get_json()["status"] == "paused"
    client.post("/api/coworker/responsibilities", json={"template": "inbound_leads", "runNow": False}, headers=h)
    assert client.post("/api/coworker/tick", json={"force": True}, headers=h).get_json()["results"] == []
    assert client.post("/api/coworker/resume", headers=h).get_json()["status"] == "active"
    tick = client.post("/api/coworker/tick", json={"force": True}, headers=h).get_json()
    assert tick["results"] == ["Drafted a reply to Dana Whitfield"]
    assert client.post("/api/coworker/tick", headers=h).get_json() == {"skipped": True}


def test_responsibility_routes(client, auth_headers, demo):
    h = auth_headers
    assert client.post("/api/coworker/responsibilities", json={}, headers=h).status_code == 400
    assert client.post("/api/coworker/responsibilities", json={"template": "nope"}, headers=h).status_code == 400
    created = client.post("/api/coworker/responsibilities", json={"instruction": "Prep me before every meeting",
                                                                  "autonomy": "silent", "name": "Prep"}, headers=h).get_json()
    rid = created["responsibility"]["id"]
    assert created["responsibility"]["template"] == "meeting_prep"
    assert client.patch(f"/api/coworker/responsibilities/{rid}", json={"enabled": False, "autonomy": "notify"},
                        headers=h).get_json()["responsibility"]["enabled"] is False
    assert client.patch("/api/coworker/responsibilities/999", json={"enabled": True}, headers=h).status_code == 404
    assert client.post(f"/api/coworker/responsibilities/{rid}/run", headers=h).status_code == 200
    assert client.post("/api/coworker/responsibilities/999/run", headers=h).status_code == 404
    listing = client.get("/api/coworker/responsibilities", headers=h).get_json()
    assert listing["templates"] and listing["suggestions"]
    assert client.get("/api/coworker/onboarding/suggestions", headers=h).get_json()["suggestions"]
    assert client.delete(f"/api/coworker/responsibilities/{rid}", headers=h).status_code == 200
    assert client.delete(f"/api/coworker/responsibilities/{rid}", headers=h).status_code == 404


def test_autonomy_activity_digest_routes(client, auth_headers, demo):
    h = auth_headers
    body = client.get("/api/coworker/autonomy", headers=h).get_json()
    assert body["levels"]["email.send"] == "approve" and body["hardFloors"]
    assert client.put("/api/coworker/autonomy", json={"bogus": "silent"}, headers=h).status_code == 400
    assert client.put("/api/coworker/autonomy", json={"email.send": "notify"}, headers=h).get_json()["levels"]["email.send"] == "notify"
    csv_resp = client.get("/api/coworker/activity?format=csv", headers=h)
    assert csv_resp.mimetype == "text/csv" and "summary" in csv_resp.get_data(as_text=True)
    assert client.get("/api/coworker/activity", headers=h).get_json()["activity"]
    assert "headline" in client.get("/api/coworker/digest?hours=48", headers=h).get_json()


def test_routes_without_coworker(client, auth_headers):
    h = auth_headers
    assert client.get("/api/coworker/status", headers=h).get_json() == {"exists": False}
    for path in ("/api/coworker/pause", "/api/coworker/resume", "/api/coworker/tick", "/api/coworker/responsibilities"):
        assert client.post(path, json={"template": "inbound_leads"}, headers=h).status_code == 404
    assert client.put("/api/coworker/autonomy", json={}, headers=h).status_code == 404


def test_worker_run_once(app, client, auth_headers, demo):
    from coworker import worker

    with app.app_context():
        assert worker.run_once() == 1
