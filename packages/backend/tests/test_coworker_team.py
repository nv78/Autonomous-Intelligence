"""Team plan: organizations, invites, admin policies enforced on members, removal, seats."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from coworker import billing, executor, llm, meetings, orgs
from coworker.executor import ActionError
from coworker.store import Store


@pytest.fixture
def s(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/team.db")
    store.create_coworker(1, "Avery Admin", "avery@acme.com", mode="demo")
    store.create_coworker(2, "Blake Member", "blake@acme.com", mode="demo")
    store.create_coworker(3, "Casey Member", "casey@acme.com", mode="demo")
    return store


@pytest.fixture
def org(s):
    created = orgs.create(s, 1, "Acme", "acme.com", "avery@acme.com")
    with patch("coworker.orgs._send_invite", return_value=""):
        for user_id, email in ((2, "blake@acme.com"), (3, "casey@acme.com")):
            sent = orgs.invite(s, 1, email)
            orgs.accept(s, user_id, email, sent["url"].rsplit("/", 1)[-1])
    return created


def test_acceptance_admin_rule_holds_for_every_member(s, org):
    """The issue's acceptance test: "always approve external email" applies to each teammate."""
    orgs.update(s, 1, new_policies={"autonomy_ceiling": {"email.send": "approve"}})
    for user_id in (2, 3):
        s.update_coworker(user_id, autonomy={"email.send": "silent"})  # what they picked for themselves
        with patch("coworker.executor.run_due"):
            action = executor.propose(s, user_id, "email.send", {"to": ["dana@northwind.com"], "subject": "Hi", "body": "Hello"},
                                      title="Email Dana", requested_in_chat=True)
        assert action["autonomy"] == "approve" and action["status"] == "proposed"
    assert orgs.cap_level(s, 2, "slack.post", "silent") == "silent"  # no ceiling for Slack
    assert orgs.cap_level(s, 99, "email.send", "silent") == "silent"  # not in an org


def test_blocked_domains_and_consent_and_models(s, org):
    orgs.update(s, 1, new_policies={"blocked_domains": "@Competitor.com, rival.io", "recording_consent": "all_party",
                                    "allowed_models": ["claude-sonnet-5-5"]})
    pol = orgs.policies(s, 2)
    assert pol["blocked_domains"] == ["competitor.com", "rival.io"]
    action = executor.propose(s, 2, "email.send", {"to": ["sam@competitor.com"], "subject": "x", "body": "y"},
                              title="Email Sam", requested_in_chat=True)
    assert any(r["code"] == "org_blocked" for r in action["risk"])
    with pytest.raises(ActionError) as exc:
        executor.approve(s, 2, action["id"])
    assert exc.value.code == "org_blocked"
    with patch("coworker.executor.run_due"):
        ok = executor.approve(s, 2, action["id"], {"to": ["sam@northwind.com"]})  # fixed recipient goes through
    assert ok["status"] == "approved"

    s.update_coworker(2, settings={"recording_consent": "one_party"})
    assert meetings._all_party(s, 2) is True  # the organization's rule wins
    s.update_coworker(1, settings={"recording_consent": "one_party"})
    assert meetings._all_party(s, 1) is True

    with patch("coworker.store.get_store", return_value=s):
        s.update_coworker(2, settings={"model": "claude-opus-5-5"})
        assert llm.model_name(2) == "claude-sonnet-5-5"
        listed = {m["id"]: m for m in llm.models_for(2)}
        assert listed["claude-opus-5-5"]["allowedByOrg"] is False and listed["claude-sonnet-5-5"]["allowedByOrg"]


def test_invites_roles_and_removal(s, org):
    with patch("coworker.orgs._send_invite", return_value=""):
        invite = orgs.invite(s, 1, "Dee@Acme.com", "admin")
    assert invite["email"] == "dee@acme.com" and "/app/join/" in invite["url"]
    token = invite["url"].rsplit("/", 1)[-1]
    with pytest.raises(orgs.OrgError):
        orgs.invite(s, 2, "x@acme.com")  # members can't invite
    with pytest.raises(orgs.OrgError):
        orgs.invite(s, 1, "not-an-email")
    with pytest.raises(orgs.OrgError):
        orgs.invite(s, 1, "x@acme.com", "owner")
    with pytest.raises(orgs.OrgError) as exc:
        orgs.invite(s, 1, "blake@acme.com")
    assert exc.value.code == "conflict"
    s.create_coworker(4, "Dee", "dee@acme.com", mode="demo")
    with pytest.raises(orgs.OrgError) as exc:
        orgs.accept(s, 4, "someone@else.com", token)
    assert exc.value.code == "forbidden"
    with pytest.raises(orgs.OrgError) as exc:
        orgs.accept(s, 4, "dee@acme.com", "forged")
    assert exc.value.status == 410
    orgs.accept(s, 4, "dee@acme.com", token)
    assert orgs.membership(s, 4)["role"] == "admin"
    assert (s.get_coworker(4) or {})["settings"]["employer_authorized"]["basis"] == "organization"

    blake = s.one("SELECT id FROM cw_org_members WHERE email = 'blake@acme.com'")["id"]
    with patch("coworker.admin.revoke_all", return_value={"cancelled": 0, "revoked": ["google"]}) as revoke:
        out = orgs.remove(s, 1, blake)
    assert out == {"removed": "blake@acme.com", "revoked": ["google"]} and revoke.call_args.args[1] == 2
    assert orgs.membership(s, 2) is None and orgs.cap_level(s, 2, "email.send", "silent") == "silent"
    with pytest.raises(orgs.OrgError):
        orgs.remove(s, 1, blake)
    # Re-inviting a removed member works; withdrawing an invite blocks its link
    with patch("coworker.orgs._send_invite", return_value=""):
        again = orgs.invite(s, 1, "blake@acme.com")
    removed_invite = s.one("SELECT id FROM cw_org_members WHERE email = 'blake@acme.com'")["id"]
    orgs.remove(s, 1, removed_invite)
    with pytest.raises(orgs.OrgError) as exc:
        orgs.accept(s, 2, "blake@acme.com", again["url"].rsplit("/", 1)[-1])
    assert exc.value.code == "not_found"


def test_last_admin_and_leaving(s, org):
    admin_row = s.one("SELECT id FROM cw_org_members WHERE user_id = 1")["id"]
    with pytest.raises(orgs.OrgError):
        orgs.set_role(s, 1, admin_row, "member")
    with pytest.raises(orgs.OrgError):
        orgs.remove(s, 1, admin_row)
    with pytest.raises(orgs.OrgError):
        orgs.leave(s, 1)
    casey = s.one("SELECT id FROM cw_org_members WHERE user_id = 3")["id"]
    orgs.set_role(s, 1, casey, "admin")
    with pytest.raises(orgs.OrgError):
        orgs.set_role(s, 1, casey, "boss")
    with pytest.raises(orgs.OrgError):
        orgs.set_role(s, 1, 9999, "admin")
    orgs.leave(s, 1)
    assert orgs.membership(s, 1) is None
    with pytest.raises(orgs.OrgError):
        orgs.leave(s, 1)
    with pytest.raises(orgs.OrgError):
        orgs.update(s, 2, name="Nope")  # members can't edit
    with pytest.raises(orgs.OrgError):
        orgs.create(s, 2, "Second org")  # already in one
    with pytest.raises(orgs.OrgError):
        orgs.create(s, 1, "  ")


def test_overview_and_usage(s, org):
    over = orgs.overview(s, 1)
    assert over["name"] == "Acme" and over["role"] == "admin" and over["seats"] == 3
    assert all("usage" in m for m in over["members"])
    member_view = orgs.overview(s, 2)
    assert member_view["role"] == "member" and all("usage" not in m for m in member_view["members"])
    assert orgs.overview(s, 99) is None
    clean = orgs.clean_policies({"autonomy_ceiling": {"email.send": "notify", "responsibility.create": "silent",
                                                      "bogus": "approve", "slack.post": "nope"}, "allowed_models": ["a", 3]})
    assert clean["autonomy_ceiling"] == {"email.send": "notify"} and clean["allowed_models"] == ["a"]


def test_team_plan_covers_members_and_syncs_seats(s, org, monkeypatch):
    s.update_coworker(1, plan="team", settings={"billing": {"subscription_id": "sub_1"}})
    assert billing.effective_plan(s, 2) == "team" and billing.effective_plan(s, 1) == "team"
    assert billing.effective_plan(s, 99) == "pilot"
    monkeypatch.setenv("COWORKER_ENFORCE_PLANS", "1")
    billing.require(s, 2, "calls")  # a member gets Team features through the organization
    assert billing.summary(s, 2)["plan"] == "team"
    assert billing.sync_seats(s, org) is None  # flat price unless per-seat is on
    monkeypatch.setenv("COWORKER_TEAM_PER_SEAT", "1")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test")
    stripe = MagicMock()
    stripe.Subscription.retrieve.return_value = {"items": {"data": [{"id": "si_1", "quantity": 1}]}}
    with patch("coworker.billing._stripe", return_value=stripe):
        assert billing.sync_seats(s, org) == 3
    stripe.Subscription.modify.assert_called_once_with("sub_1", proration_behavior="create_prorations",
                                                       items=[{"id": "si_1", "quantity": 3}])
    s.update_coworker(1, plan="coworker")
    assert billing.sync_seats(s, org) is None


def test_team_api(client, auth_headers, app, monkeypatch):
    h = auth_headers
    from coworker.store import get_store

    with app.app_context():
        get_store().create_coworker(1, "Avery Admin", "avery@acme.com", mode="demo")
    with patch("api_endpoints.coworker.team.owner_profile", return_value=("Avery", "avery@acme.com")):
        assert client.get("/api/coworker/org", headers=h).get_json() == {"org": None}
        monkeypatch.setenv("COWORKER_ENFORCE_PLANS", "1")
        assert client.post("/api/coworker/org", json={"name": "Acme"}, headers=h).status_code == 402
        monkeypatch.delenv("COWORKER_ENFORCE_PLANS")
        created = client.post("/api/coworker/org", json={"name": "Acme", "domain": "acme.com"}, headers=h)
        assert created.status_code == 201 and created.get_json()["org"]["role"] == "admin"
        assert client.post("/api/coworker/org", json={"name": "Again"}, headers=h).status_code == 409
        upd = client.patch("/api/coworker/org", json={"policies": {"blocked_domains": ["rival.io"]}}, headers=h).get_json()
        assert upd["org"]["policies"]["blocked_domains"] == ["rival.io"]
        with patch("coworker.orgs._send_invite", return_value=""):
            inv = client.post("/api/coworker/org/invites", json={"email": "blake@acme.com"}, headers=h)
        assert inv.status_code == 201
        assert client.post("/api/coworker/org/invites", json={"email": "nope"}, headers=h).status_code == 400
        member_id = next(m["id"] for m in inv.get_json()["org"]["members"] if m["email"] == "blake@acme.com")
        assert client.patch(f"/api/coworker/org/members/{member_id}", json={"role": "admin"}, headers=h).status_code == 200
        assert client.patch("/api/coworker/org/members/9999", json={"role": "admin"}, headers=h).status_code == 404
        assert client.delete(f"/api/coworker/org/members/{member_id}", headers=h).get_json()["removed"] == "blake@acme.com"
        assert client.delete("/api/coworker/org/members/9999", headers=h).status_code == 404
        token = inv.get_json()["invite"]["url"].rsplit("/", 1)[-1]
        assert client.post(f"/api/coworker/org/join/{token}", headers=h).status_code in (403, 409)
        assert client.post("/api/coworker/org/leave", headers=h).status_code == 409  # the only admin
        assert client.patch("/api/coworker", json={"settings": {"model": "gpt-4o"}}, headers=h).status_code in (200, 400)
        client.patch("/api/coworker/org", json={"policies": {"allowed_models": ["claude-haiku-5-5"]}}, headers=h)
        blocked = client.patch("/api/coworker", json={"settings": {"model": "gpt-4o"}}, headers=h)
        assert blocked.status_code == 403 and blocked.get_json().get("code", "org_policy") == "org_policy"
        autonomy = client.get("/api/coworker/autonomy", headers=h).get_json()
        assert "orgCeiling" in autonomy


def test_join_and_leave_api(client, auth_headers, app):
    h = auth_headers
    from coworker.store import get_store

    with app.app_context():
        st = get_store()
        st.create_coworker(1, "Blake", "blake@acme.com", mode="demo")
        st.create_coworker(7, "Avery", "avery@acme.com", mode="demo")
        org = orgs.create(st, 7, "Acme", "acme.com", "avery@acme.com")
        with patch("coworker.orgs._send_invite", return_value=""):
            url = orgs.invite(st, 7, "blake@acme.com")["url"]
    with patch("api_endpoints.coworker.team.owner_profile", return_value=("Blake", "blake@acme.com")):
        joined = client.post(f"/api/coworker/org/join/{url.rsplit('/', 1)[-1]}", headers=h)
        assert joined.status_code == 200 and joined.get_json()["org"]["role"] == "member"
        assert client.post("/api/coworker/org/invites", json={"email": "x@acme.com"}, headers=h).status_code == 403
        assert client.post("/api/coworker/org/leave", headers=h).get_json() == {"org": None}
        assert client.post("/api/coworker/org/leave", headers=h).status_code == 404
    assert org["name"] == "Acme"


def test_invite_email_channels(s, org, monkeypatch):
    sent = orgs._send_invite(s, 1, org, "x@acme.com", "https://app/join/t")
    assert sent == ""  # demo coworker, no SMTP: the admin shares the link
    monkeypatch.setenv("SMTP_URL", "smtp://u:p@mail:587")
    with patch("coworker.notify._smtp_send") as smtp:
        assert orgs._send_invite(s, 1, org, "x@acme.com", "https://app/join/t") == "smtp"
    assert "invited you to join Acme" in smtp.call_args.args[2]
    s.update_coworker(1, mode="live")
    mailbox = MagicMock()
    mailbox.has_scope.return_value = True
    with patch("coworker.connectors.base.Workspace.email_connector", return_value=mailbox):
        assert orgs._send_invite(s, 1, org, "x@acme.com", "https://app/join/t") == "mailbox"
