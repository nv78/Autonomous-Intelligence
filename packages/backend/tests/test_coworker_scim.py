"""SCIM 2.0: token management, create/list/get/patch/put/delete as Okta and Entra send them, SSO joins invites."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from coworker import orgs, scim
from coworker.store import Store


@pytest.fixture
def s(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/scim.db")
    store.create_coworker(1, "Avery Admin", "avery@acme.com", mode="demo")
    orgs.create(store, 1, "Acme", "acme.com", "avery@acme.com")
    return store


@pytest.fixture(autouse=True)
def _no_mail():
    with patch("coworker.orgs._send_invite", return_value=""):
        yield


def test_token_lifecycle(s):
    token = scim.new_token(s, 1)
    org = scim.org_for_token(s, f"Bearer {token}")
    assert org["name"] == "Acme" and org["scim_token_hash"] != token  # only the hash is stored
    assert orgs.overview(s, 1)["scim"] is True
    rotated = scim.new_token(s, 1)
    with pytest.raises(scim.ScimError):
        scim.org_for_token(s, f"Bearer {token}")
    assert scim.org_for_token(s, f"Bearer {rotated}")
    scim.revoke_token(s, 1)
    for header in (f"Bearer {rotated}", "", "Basic x"):
        with pytest.raises(scim.ScimError) as exc:
            scim.org_for_token(s, header)
        assert exc.value.status == 401
    s.create_coworker(2, "Blake", "blake@acme.com", mode="demo")
    with pytest.raises(orgs.OrgError):
        scim.new_token(s, 2)  # not an admin


def test_provision_then_sso_joins_then_deprovision(s):
    org = scim.org_for_token(s, f"Bearer {scim.new_token(s, 1)}")
    with patch("coworker.billing.sync_seats") as seats:
        user = scim.create_user(s, org, {"userName": "Blake@Acme.com", "active": True, "schemas": [scim.USER_SCHEMA]})
    assert user["userName"] == "blake@acme.com" and user["active"] and seats.called
    with pytest.raises(scim.ScimError) as dup:
        scim.create_user(s, org, {"userName": "blake@acme.com"})
    assert dup.value.status == 409
    assert scim.list_users(s, org, 'userName eq "BLAKE@acme.com"')["totalResults"] == 1
    assert scim.list_users(s, org, 'userName eq "nobody@acme.com"')["totalResults"] == 0
    with pytest.raises(scim.ScimError):
        scim.list_users(s, org, 'name.familyName co "x"')

    s.create_coworker(2, "Blake", "blake@acme.com", mode="demo")
    joined = orgs.on_sso_login(s, 2, "blake@acme.com", "")  # a provisioned (invited) address joins on SSO
    assert joined and joined["name"] == "Acme" and orgs.membership(s, 2)["status"] == "active"

    member = scim._member(s, org, user["id"])
    okta = {"schemas": [scim.PATCH_SCHEMA], "Operations": [{"op": "replace", "value": {"active": False}}]}
    with patch("coworker.admin.revoke_all", return_value={"revoked": ["google"]}) as revoke, patch("coworker.billing.sync_seats"):
        assert scim.patch_user(s, org, member, okta)["active"] is False
    assert revoke.call_args.args[1] == 2 and orgs.membership(s, 2) is None

    entra = {"Operations": [{"op": "Replace", "path": "active", "value": "True"}]}
    with patch("coworker.billing.sync_seats"):
        back = scim.patch_user(s, org, scim._member(s, org, user["id"]), entra)
    assert back["active"] is True and scim._member(s, org, user["id"])["status"] == "invited"
    assert scim.patch_user(s, org, scim._member(s, org, user["id"]), {"Operations": [{"op": "replace", "path": "name"}]})["active"]
    with pytest.raises(scim.ScimError) as moved:
        scim.replace_user(s, org, scim._member(s, org, user["id"]), {"userName": "new@acme.com"})
    assert moved.value.scim_type == "mutability"


def test_cannot_remove_last_admin(s):
    org = scim.org_for_token(s, f"Bearer {scim.new_token(s, 1)}")
    admin_row = s.one("SELECT * FROM cw_org_members WHERE user_id = 1")
    with pytest.raises(scim.ScimError) as exc:
        scim.set_active(s, org, admin_row, False)
    assert exc.value.status == 409


def test_endpoints(client, auth_headers, app):
    from coworker.store import get_store

    with app.app_context():
        st = get_store()
        st.create_coworker(1, "Avery Admin", "avery@acme.com", mode="demo")
        orgs.create(st, 1, "Acme", "acme.com", "avery@acme.com")
    token = client.post("/api/coworker/org/scim-token", headers=auth_headers).get_json()["token"]
    h = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/coworker/scim/v2/Users").status_code == 401
    assert client.get("/api/coworker/scim/v2/ServiceProviderConfig", headers=h).get_json()["patch"]["supported"]
    with patch("coworker.billing.sync_seats"):
        created = client.post("/api/coworker/scim/v2/Users", headers=h, json={"userName": "dana@acme.com"})
        assert created.status_code == 201 and created.mimetype == "application/scim+json"
        uid_ = created.get_json()["id"]
        assert client.get(f"/api/coworker/scim/v2/Users/{uid_}", headers=h).get_json()["userName"] == "dana@acme.com"
        assert client.get("/api/coworker/scim/v2/Users/999", headers=h).status_code == 404
        assert client.get('/api/coworker/scim/v2/Users?filter=userName eq "dana@acme.com"', headers=h).get_json()["totalResults"] == 1
        assert client.put(f"/api/coworker/scim/v2/Users/{uid_}", headers=h, json={"userName": "dana@acme.com", "active": False}).get_json()["active"] is False
        assert client.patch(f"/api/coworker/scim/v2/Users/{uid_}", headers=h,
                            json={"Operations": [{"op": "replace", "path": "active", "value": True}]}).get_json()["active"]
        assert client.delete(f"/api/coworker/scim/v2/Users/{uid_}", headers=h).status_code == 204
    assert client.delete("/api/coworker/org/scim-token", headers=auth_headers).get_json() == {"ok": True}
    assert client.get("/api/coworker/scim/v2/Users", headers=h).status_code == 401
