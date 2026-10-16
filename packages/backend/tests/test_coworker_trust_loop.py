"""Approval loop and trust controls: email approvals, STOP, double replies,
Slack Connect, employer authorization, org disable, and the track record."""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest

from coworker import executor, governance, memory, metrics, notify
from coworker.connectors.demo import DemoConnector
from coworker.store import Store, iso, utcnow


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("COWORKER_DISABLED_DOMAINS", raising=False)
    with patch("api_endpoints.coworker.core.owner_profile", return_value=("Natan Vidra", "natan@anote.ai")), \
         patch("services.provider_keys.get_user_provider_key", return_value=None):
        yield


@pytest.fixture
def s(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/trust.db")
    store.create_coworker(1, "Natan Vidra", "natan@anote.ai", mode="demo")
    DemoConnector.seed(store, 1, "Natan Vidra", "natan@anote.ai")
    memory.rebuild(store, 1)
    return store


def _email(store: Store, thread: str, direction: str, minutes_ago: float, author: str = "dana@northwind.com",
           subject: str = "Pilot", body: str = "hi", meta: dict | None = None) -> int | None:
    return store.add_item(1, {
        "provider": "gmail", "external_id": f"x-{thread}-{direction}-{minutes_ago}-{subject[:8]}", "thread_id": thread,
        "kind": "email", "direction": direction, "author_name": "", "author_email": author, "recipients": [],
        "subject": subject, "body": body, "occurred_at": iso(utcnow() - timedelta(minutes=minutes_ago)),
        "meta": meta or {},
    })


# -- double replies ----------------------------------------------------------

def test_draft_superseded_when_owner_already_replied(s):
    _email(s, "t-dr", "inbound", 30)
    a = executor.propose(s, 1, "email.send", {"to": ["dana@northwind.com"], "subject": "Re: Pilot", "body": "Thanks!",
                                               "thread_id": "t-dr"}, title="Reply to Dana")
    _email(s, "t-dr", "outbound", 1, author="natan@anote.ai")  # the user answered it themselves
    executor.approve(s, 1, a["id"])
    assert s.get("cw_actions", a["id"], 1)["status"] == "superseded"
    # A reply before the prospect's latest message doesn't block answering it.
    _email(s, "t-ok", "outbound", 20, author="natan@anote.ai")
    _email(s, "t-ok", "inbound", 10)
    b = executor.propose(s, 1, "email.send", {"to": ["dana@northwind.com"], "subject": "Re: Pilot", "body": "Sure.",
                                               "thread_id": "t-ok"}, title="Reply again")
    assert executor.approve(s, 1, b["id"])["status"] == "executed"


# -- Slack Connect -------------------------------------------------------------

def test_slack_connect_channel_always_needs_approval(s):
    s.add_item(1, {"provider": "slack", "external_id": "ext-1", "thread_id": "slack-partners", "kind": "slack",
                   "direction": "inbound", "author_name": "Bo", "author_email": "bo@acme.com", "recipients": [],
                   "body": "hello", "channel": "partners", "occurred_at": iso(), "meta": {"shared": True}})
    s.update_coworker(1, autonomy={"slack.post": "silent"})
    a = executor.propose(s, 1, "slack.post", {"channel": "partners", "text": "On it"}, title="Post in #partners")
    assert a["status"] == "proposed"
    assert any(r["code"] == "external_channel" for r in a["risk"])


# -- email approvals -------------------------------------------------------------

def test_email_approve_and_reject_links(client, auth_headers, app):
    from api_endpoints.coworker.email_actions import action_token
    from coworker.store import get_store

    assert client.post("/api/coworker", json={"mode": "demo"}, headers=auth_headers).status_code == 201
    with app.app_context():
        st = get_store()
        a = executor.propose(st, 1, "email.send", {"to": ["dana@northwindcap.com"], "subject": "Re: hi",
                                                    "body": "<b>Thanks</b>"}, title="Reply to Dana")
        b = executor.propose(st, 1, "email.send", {"to": ["dana@northwindcap.com"], "subject": "Re: hi",
                                                    "body": "No"}, title="Second")
        ta, tb = action_token(1, a["id"]), action_token(1, b["id"])
    page = client.get(f"/api/coworker/email-actions/{ta}")
    assert page.status_code == 200 and b"Approve and send" in page.data
    assert b"<b>Thanks</b>" not in page.data and b"&lt;b&gt;" in page.data  # escaped
    assert page.headers["Cache-Control"] == "no-store"
    # GET never changes anything (link scanners prefetch).
    with app.app_context():
        assert get_store().get("cw_actions", a["id"], 1)["status"] == "proposed"
    assert client.post(f"/api/coworker/email-actions/{ta}", data={"op": "nope"}).status_code == 400
    done = client.post(f"/api/coworker/email-actions/{ta}", data={"op": "approve"})
    assert done.status_code == 200 and b"on its way" in done.data
    again = client.get(f"/api/coworker/email-actions/{ta}")
    assert b"Already executed" in again.data or b"Already approved" in again.data
    assert client.post(f"/api/coworker/email-actions/{ta}", data={"op": "approve"}).status_code == 409
    rej = client.post(f"/api/coworker/email-actions/{tb}", data={"op": "reject", "feedback": "too short"})
    assert b"Rejected" in rej.data
    with app.app_context():
        assert get_store().get("cw_actions", b["id"], 1)["feedback"] == "too short"
    assert client.get("/api/coworker/email-actions/garbage").status_code == 410
    assert client.post("/api/coworker/email-actions/garbage", data={"op": "approve"}).status_code == 410


def test_approval_email_contains_links_and_stop_hint(s):
    s.insert("cw_actions", {"user_id": 1, "type": "email.send", "status": "proposed", "title": "Reply to Dana",
                            "payload": {}, "created_at": iso(utcnow() - timedelta(minutes=10))})
    assert notify.maybe_notify_approvals(s, 1) == 1
    body = s.items(1, kind="email", limit=1)[0]["body"]
    assert "/api/coworker/email-actions/" in body and "Reply STOP" in body


# -- STOP --------------------------------------------------------------------------

def test_reply_stop_pauses_once(s):
    _email(s, "n1", "outbound", 1, author="natan@anote.ai", subject="Re: [Ourogen] 2 actions waiting",
           body="STOP\n\n> On Monday Ourogen wrote:\n> ...")
    _email(s, "n2", "outbound", 1, author="natan@anote.ai", subject="Re: [Ourogen] digest", body="thanks, looks good")
    _email(s, "n3", "inbound", 1, author="evil@x.com", subject="Re: [Ourogen] hi", body="STOP")
    assert notify.handle_stop_replies(s, 1) is True
    assert s.get_coworker(1)["status"] == "paused"
    executor.resume(s, 1)
    assert notify.handle_stop_replies(s, 1) is False  # same reply isn't applied twice
    assert s.get_coworker(1)["status"] == "active"
    s.update_coworker(1, owner_email="")
    assert notify.handle_stop_replies(s, 1) is False


# -- governance ----------------------------------------------------------------------

def test_employer_authorization_gates_live_sends(s):
    assert not governance.needs_employer_ok(s, 1)  # demo mode
    s.update_coworker(1, mode="live")
    assert governance.work_domain(s, 1) == "anote.ai" and governance.needs_employer_ok(s, 1)
    a = executor.propose(s, 1, "email.send", {"to": ["dana@northwind.com"], "subject": "x", "body": "y"}, title="Reply")
    with pytest.raises(executor.ActionError) as exc:
        executor.approve(s, 1, a["id"])
    assert exc.value.code == "employer_authorization"
    with pytest.raises(ValueError):
        governance.authorize(s, 1, "vibes")
    governance.authorize(s, 1, "owner")
    assert governance.status(s, 1)["employerAuthorized"]["basis"] == "owner"
    assert not governance.needs_employer_ok(s, 1)
    s.update_coworker(1, owner_email="natan@gmail.com")
    assert governance.work_domain(s, 1) == ""  # personal accounts never need it


def test_org_disable(client, auth_headers, monkeypatch, app):
    monkeypatch.setenv("COWORKER_DISABLED_DOMAINS", "anote.ai, other.com")
    assert client.post("/api/coworker", json={"mode": "demo"}, headers=auth_headers).status_code == 403
    monkeypatch.setenv("COWORKER_DISABLED_DOMAINS", "")
    assert client.post("/api/coworker", json={"mode": "demo"}, headers=auth_headers).status_code == 201
    monkeypatch.setenv("COWORKER_DISABLED_DOMAINS", "anote.ai")
    client.post("/api/coworker/tick", json={"force": True}, headers=auth_headers)
    assert client.get("/api/coworker", headers=auth_headers).get_json()["coworker"]["status"] == "paused"
    gov = client.get("/api/coworker/governance", headers=auth_headers).get_json()
    assert gov["orgDisabled"] is True
    monkeypatch.setenv("COWORKER_DISABLED_DOMAINS", "")
    assert client.post("/api/coworker/governance/employer", json={}, headers=auth_headers).status_code == 400
    assert client.post("/api/coworker/governance/employer", json={"confirm": True, "basis": "x"},
                       headers=auth_headers).status_code == 400
    ok = client.post("/api/coworker/governance/employer", json={"confirm": True, "basis": "permitted"}, headers=auth_headers)
    assert ok.get_json()["employerAuthorized"]["basis"] == "permitted"


def test_org_disable_blocks_approval(s, monkeypatch):
    a = executor.propose(s, 1, "email.send", {"to": ["dana@northwind.com"], "subject": "x", "body": "y"}, title="Reply")
    monkeypatch.setenv("COWORKER_DISABLED_DOMAINS", "anote.ai")
    with pytest.raises(executor.ActionError) as exc:
        executor.approve(s, 1, a["id"])
    assert exc.value.code == "org_disabled"


# -- track record ----------------------------------------------------------------------

def test_track_record(s, client, auth_headers):
    def prop(title: str, body: str = "Thanks, talk soon.") -> int:
        return executor.propose(s, 1, "email.send", {"to": ["dana@northwind.com"], "subject": "Re", "body": body},
                                title=title)["id"]

    executor.approve(s, 1, prop("A"))
    executor.approve(s, 1, prop("B"), {"body": "Thanks so much, talk next week."})
    executor.reject(s, 1, prop("C"), "Too formal")
    prop("D")
    m = metrics.track_record(s, 1)
    t = m["byType"]["email.send"]
    assert t["decided"] == 3 and t["unedited"] == 1 and t["edited"] == 1 and t["rejected"] == 1
    assert m["acceptance"] == pytest.approx(1 / 3, abs=0.01)
    assert m["edits"]["count"] == 1 and 0 < m["edits"]["avgChanged"] < 1
    assert m["rejections"]["recentReasons"] == ["Too formal"] and m["pending"] >= 1
    assert m["hoursSaved"] >= 0
    s.insert("cw_meetings", {"user_id": 1, "title": "Call", "started_at": iso(utcnow() - timedelta(minutes=30)),
                             "ended_at": iso(), "transcript": [{"speaker": "owner", "text": "ask budget"}],
                             "metrics": {"escalations": ["discount"]}})
    calls = metrics.track_record(s, 1)["calls"]
    assert calls == {"count": 1, "minutes": pytest.approx(30, abs=0.5), "escalations": 1, "interventions": 1}
    assert client.post("/api/coworker", json={"mode": "demo"}, headers=auth_headers).status_code == 201
    body = client.get("/api/coworker/metrics?days=7", headers=auth_headers).get_json()
    assert body["days"] == 7 and "hoursSaved" in body
