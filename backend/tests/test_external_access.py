"""Tests R3 : invitations d'accès extérieurs par président/DSS."""

import re
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

# ── Helpers ─────────────────────────────────────────────────────────

def _login(client, email, password, captcha_id, captcha_answer):
    r = client.post("/api/auth/login", json={
        "email": email, "password": password,
        "captcha_id": captcha_id, "captcha_answer": captcha_answer,
    })
    assert r.status_code == 200, f"Login failed ({r.status_code}): {r.json()}"
    return r.json()["access_token"]


def _fetch_captcha(client):
    resp = client.get("/api/auth/captcha")
    assert resp.status_code == 200
    data = resp.json()
    m = re.search(r"font (\d+) \+ (\d+)", data["question"])
    assert m
    a, b = int(m.group(1)), int(m.group(2))
    return data["challenge_id"], str(a + b)


def _invite(client, token, email, account_type="salarie_designe", **extra):
    """Helper: POST /api/invitations."""
    return client.post("/api/invitations", json={
        "email": email,
        "first_name": extra.get("first_name", email.split("@")[0]),
        "last_name": extra.get("last_name", "Test"),
        "account_type": account_type,
        **{k: v for k, v in extra.items() if k not in ("first_name", "last_name")},
    }, headers={"Authorization": f"Bearer {token}"})


def _join(client, email, password, invitation_code, first_name, last_name):
    """Helper: POST /api/join."""
    cid, ans = _fetch_captcha(client)
    return client.post("/api/join", json={
        "email": email, "password": password,
        "first_name": first_name, "last_name": last_name,
        "invitation_code": invitation_code,
        "captcha_id": cid, "captcha_answer": ans,
    })


def _get_user_id(client, token, email):
    """GET /api/auth/me → id."""
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    return r.json()["id"]


# ── Fixture : org + sophie (admin+president) + marc (DSS) + tom (membre) ──

@pytest.fixture
def ext_org(client):
    """Create an org, join sophie, marc (as DSS via designate), and tom."""
    from tests.helpers import fetch_captcha, create_invitation
    from app.core.database import SessionLocal
    from app.models.user import User

    # 1. Create org
    cid, ans = fetch_captcha(client)
    r = client.post("/api/organizations", json={
        "organization_name": "TestPV",
        "company_name": "TestPV SA",
        "employee_count": 120,
        "admin_email": "sophie@ext-test.lu",
        "admin_password": "test123456",
        "admin_first_name": "Sophie",
        "admin_last_name": "Muller",
        "admin_delegue_status": "titulaire",
        "admin_delegue_role": "president",
        "captcha_id": cid, "captcha_answer": ans,
    })
    assert r.status_code == 201

    # 2. Login as sophie
    cid2, ans2 = fetch_captcha(client)
    s_token = _login(client, "sophie@ext-test.lu", "test123456", cid2, ans2)
    s_headers = {"Authorization": f"Bearer {s_token}"}

    # 3. Get org_id + sophie user_id
    r = client.get("/api/dashboard", headers=s_headers)
    org_id = r.json()["organization"]["id"]
    db = SessionLocal()
    sophie = db.query(User).filter(User.email == "sophie@ext-test.lu").first()
    sophie_id = sophie.id
    db.close()

    # 4. Create invitation rows for marc and tom (direct DB, like org_with_users)
    db2 = SessionLocal()
    create_invitation(db2, "marc@ext-test.lu", org_id, sophie_id, "MARC123",
                      delegue_status="titulaire", delegue_role="secretaire")
    create_invitation(db2, "tom@ext-test.lu", org_id, sophie_id, "TOM456",
                      delegue_status="titulaire", delegue_role="membre")
    db2.close()

    # 5. Marc joins
    cid3, ans3 = fetch_captcha(client)
    client.post("/api/join", json={
        "email": "marc@ext-test.lu", "password": "test123456",
        "first_name": "Marc", "last_name": "Weber",
        "invitation_code": "MARC123",
        "captcha_id": cid3, "captcha_answer": ans3,
    })

    # 6. Tom joins
    cid4, ans4 = fetch_captcha(client)
    client.post("/api/join", json={
        "email": "tom@ext-test.lu", "password": "test123456",
        "first_name": "Tom", "last_name": "Wagner",
        "invitation_code": "TOM456",
        "captcha_id": cid4, "captcha_answer": ans4,
    })

    # 7. Marc logs in, then Sophie designates him as DSS
    cid5, ans5 = fetch_captcha(client)
    m_token = _login(client, "marc@ext-test.lu", "test123456", cid5, ans5)
    m_headers = {"Authorization": f"Bearer {m_token}"}
    marc_id = _get_user_id(client, m_token, "marc@ext-test.lu")

    # Sophie designates marc as DSS
    cid6, ans6 = fetch_captcha(client)
    client.put(
        f"/api/organization/members/{marc_id}/designate",
        json={"field": "securite_sante", "value": True},
        headers={"Authorization": f"Bearer {s_token}"},
    )

    # Re-login marc to get updated token
    cid7, ans7 = fetch_captcha(client)
    m_token2 = _login(client, "marc@ext-test.lu", "test123456", cid7, ans7)
    m_headers2 = {"Authorization": f"Bearer {m_token2}"}

    # 8. Get tom's token
    cid8, ans8 = fetch_captcha(client)
    t_token = _login(client, "tom@ext-test.lu", "test123456", cid8, ans8)
    t_headers = {"Authorization": f"Bearer {t_token}"}

    return {
        "client": client,
        "org_id": org_id,
        "sophie_token": s_token,
        "marc_token": m_token2,
        "tom_token": t_token,
        "sophie_headers": s_headers,
        "marc_headers": m_headers2,
        "tom_headers": t_headers,
    }


# ── Tests : création d'invitations ──────────────────────────────────

class TestCreateInvitationExternal:
    """POST /api/invitations — rules for external account types."""

    def test_marc_dss_invites_itm_future_expiry(self, ext_org):
        """marc (DSS non-admin) invite un ITM avec expiration future → 201."""
        tomorrow = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        r = _invite(ext_org["client"], ext_org["marc_token"], "itm@external.lu", "itm",
                     first_name="Inspector", last_name="ITM",
                     access_expires_at=tomorrow)
        assert r.status_code == 201, f"{r.status_code}: {r.json()}"
        data = r.json()
        assert data["code"]
        assert data["account_type"] == "itm"
        return data["code"]

    def test_marc_dss_invites_delegation(self, ext_org):
        """marc (DSS) invite un compte delegation → 403."""
        r = _invite(ext_org["client"], ext_org["marc_token"], "user@delegation.lu", "delegation")
        assert r.status_code == 403

    def test_tom_membre_invites_rh(self, ext_org):
        """tom (membre simple) invite un RH → 403."""
        r = _invite(ext_org["client"], ext_org["tom_token"], "rh@external.lu", "rh")
        assert r.status_code == 403

    def test_police_with_delegue_securite(self, ext_org):
        """Invitation police avec is_delegue_securite_sante=true → 400."""
        r = _invite(ext_org["client"], ext_org["marc_token"], "police@ext.lu", "police",
                     is_delegue_securite_sante=True)
        assert r.status_code == 400

    def test_police_with_past_expiry(self, ext_org):
        """Invitation police avec expiration passée → 400."""
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        r = _invite(ext_org["client"], ext_org["marc_token"], "police@ext.lu", "police",
                     access_expires_at=past)
        assert r.status_code == 400

    def test_marc_invites_rh(self, ext_org):
        """marc (DSS) invite un RH → 201 (RH est autorisé)."""
        tomorrow = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        r = _invite(ext_org["client"], ext_org["marc_token"], "rh@external.lu", "rh",
                     first_name="RH", last_name="User",
                     access_expires_at=tomorrow)
        assert r.status_code == 201


# ── Tests : cycle de vie d'un compte extérieur ──────────────────────

class TestExternalAccessLifecycle:
    """Full lifecycle: invite → join → access → revoke → delete."""

    def test_itm_joins_and_accesses_safety_register(self, ext_org):
        """L'ITM rejoint, se connecte, GET /api/safety-register → 200, GET /api/meetings → 403."""
        tomorrow = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        inv = _invite(ext_org["client"], ext_org["marc_token"], "itm@lifecycle.lu", "itm",
                      first_name="ITM", last_name="Lifecycle",
                      access_expires_at=tomorrow)
        invite_code = inv.json()["code"]

        # Join
        join_r = _join(ext_org["client"], "itm@lifecycle.lu", "test123456",
                       invite_code, "ITM", "Lifecycle")
        assert join_r.status_code == 201, f"{join_r.status_code}: {join_r.json()}"

        # Login
        cid, ans = _fetch_captcha(ext_org["client"])
        login_r = ext_org["client"].post("/api/auth/login", json={
            "email": "itm@lifecycle.lu", "password": "test123456",
            "captcha_id": cid, "captcha_answer": ans,
        })
        assert login_r.status_code == 200
        itm_token = login_r.json()["access_token"]
        itm_headers = {"Authorization": f"Bearer {itm_token}"}

        # GET /api/safety-register → 200 (lecture autorisée pour ITM)
        sr = ext_org["client"].get("/api/safety-register", headers=itm_headers)
        assert sr.status_code == 200, f"{sr.status_code}: {sr.json()}"

        # GET /api/meetings → 403 (interdit pour les extérieurs)
        mr = ext_org["client"].get("/api/meetings", headers=itm_headers)
        assert mr.status_code == 403

    def test_marc_sets_past_expiry_revokes_login(self, ext_org):
        """marc met une date de fin passée sur le compte ITM → login refusé (401)."""
        tomorrow = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        inv = _invite(ext_org["client"], ext_org["marc_token"], "itm2@lifecycle.lu", "itm",
                      first_name="ITM2", last_name="Lifecycle",
                      access_expires_at=tomorrow)
        invite_code = inv.json()["code"]

        # Join
        join_r = _join(ext_org["client"], "itm2@lifecycle.lu", "test123456",
                       invite_code, "ITM2", "Lifecycle")
        assert join_r.status_code == 201

        # Login — succeeds before revocation
        cid, ans = _fetch_captcha(ext_org["client"])
        login_r = ext_org["client"].post("/api/auth/login", json={
            "email": "itm2@lifecycle.lu", "password": "test123456",
            "captcha_id": cid, "captcha_answer": ans,
        })
        assert login_r.status_code == 200
        itm_token = login_r.json()["access_token"]

        # Marc sets past expiry
        past = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
        access_r = ext_org["client"].put(
            f"/api/organization/members/{_get_user_id(ext_org['client'], itm_token, 'itm2@lifecycle.lu')}/access",
            json={"access_expires_at": past},
            headers=ext_org["marc_headers"],
        )
        assert access_r.status_code == 200

        # Re-login — now fails (401) because account is revoked
        cid2, ans2 = _fetch_captcha(ext_org["client"])
        login_r2 = ext_org["client"].post("/api/auth/login", json={
            "email": "itm2@lifecycle.lu", "password": "test123456",
            "captcha_id": cid2, "captcha_answer": ans2,
        })
        assert login_r2.status_code == 401

    def test_marc_deletes_itm_account(self, ext_org):
        """marc supprime le compte ITM → 200."""
        tomorrow = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        inv = _invite(ext_org["client"], ext_org["marc_token"], "itm3@delete.lu", "itm",
                      first_name="ITM3", last_name="Delete",
                      access_expires_at=tomorrow)
        invite_code = inv.json()["code"]

        _join(ext_org["client"], "itm3@delete.lu", "test123456",
              invite_code, "ITM3", "Delete")

        cid, ans = _fetch_captcha(ext_org["client"])
        login_r = ext_org["client"].post("/api/auth/login", json={
            "email": "itm3@delete.lu", "password": "test123456",
            "captcha_id": cid, "captcha_answer": ans,
        })
        assert login_r.status_code == 200
        itm_token = login_r.json()["access_token"]
        itm_id = _get_user_id(ext_org["client"], itm_token, "itm3@delete.lu")

        # Marc deletes
        del_r = ext_org["client"].delete(
            f"/api/organization/members/{itm_id}",
            headers=ext_org["marc_headers"],
        )
        assert del_r.status_code == 200
        assert del_r.json()["removed"] is True

    def test_marc_cannot_delete_tom(self, ext_org):
        """marc tente de supprimer tom → 403."""
        tom_id = _get_user_id(ext_org["client"], ext_org["tom_token"], "tom@ext-test.lu")
        del_r = ext_org["client"].delete(
            f"/api/organization/members/{tom_id}",
            headers=ext_org["marc_headers"],
        )
        assert del_r.status_code == 403


# ── Tests : PUT access_expires_at ───────────────────────────────────

class TestUpdateMemberAccess:
    """PUT /api/organization/members/{id}/access."""

    def test_marc_sets_future_expiry(self, ext_org):
        """marc met une date de fin future → 200."""
        tomorrow = (datetime.now(timezone.utc) + timedelta(days=60)).isoformat()
        inv = _invite(ext_org["client"], ext_org["marc_token"], "rh-update@ext.lu", "rh",
                      first_name="RH-Update", last_name="User",
                      access_expires_at=tomorrow)
        invite_code = inv.json()["code"]
        _join(ext_org["client"], "rh-update@ext.lu", "test123456",
              invite_code, "RH-Update", "User")

        cid, ans = _fetch_captcha(ext_org["client"])
        login_r = ext_org["client"].post("/api/auth/login", json={
            "email": "rh-update@ext.lu", "password": "test123456",
            "captcha_id": cid, "captcha_answer": ans,
        })
        assert login_r.status_code == 200
        rh_token = login_r.json()["access_token"]
        rh_id = _get_user_id(ext_org["client"], rh_token, "rh-update@ext.lu")

        # Marc changes expiry to 30 days
        new_expiry = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        access_r = ext_org["client"].put(
            f"/api/organization/members/{rh_id}/access",
            json={"access_expires_at": new_expiry},
            headers=ext_org["marc_headers"],
        )
        assert access_r.status_code == 200
        # Compare datetimes (server strips timezone suffix → naive, request is aware)
        resp_dt = datetime.fromisoformat(access_r.json()["access_expires_at"])
        req_dt = datetime.fromisoformat(new_expiry).replace(tzinfo=None)
        assert abs((resp_dt - req_dt).total_seconds()) < 1
        assert access_r.json()["is_active"] is True

    def test_marc_cannot_modify_internal_access(self, ext_org):
        """marc tente de modifier l'accès de tom → 403."""
        tom_id = _get_user_id(ext_org["client"], ext_org["tom_token"], "tom@ext-test.lu")
        access_r = ext_org["client"].put(
            f"/api/organization/members/{tom_id}/access",
            json={"access_expires_at": None},
            headers=ext_org["marc_headers"],
        )
        assert access_r.status_code == 403

    def test_marc_cannot_delete_delegation(self, ext_org):
        """marc tente de supprimer un compte delegation → 403."""
        # Sophie (admin) creates a delegation invitation
        del_inv = ext_org["client"].post("/api/invitations", json={
            "email": "del-user@ext.lu",
            "first_name": "Deleg",
            "last_name": "User",
            "account_type": "delegation",
        }, headers=ext_org["sophie_headers"])
        assert del_inv.status_code == 201, f"{del_inv.status_code}: {del_inv.json()}"
        invite_code = del_inv.json()["code"]

        # Join with the actual code
        cid3, ans3 = _fetch_captcha(ext_org["client"])
        join_r = ext_org["client"].post("/api/join", json={
            "email": "del-user@ext.lu", "password": "test123456",
            "first_name": "Deleg", "last_name": "User",
            "invitation_code": invite_code,
            "captcha_id": cid3, "captcha_answer": ans3,
        })
        assert join_r.status_code == 201, f"Join failed ({join_r.status_code}): {join_r.json()}"

        # Login delegation user
        cid4, ans4 = _fetch_captcha(ext_org["client"])
        d_token = _login(ext_org["client"], "del-user@ext.lu", "test123456", cid4, ans4)
        d_id = _get_user_id(ext_org["client"], d_token, "del-user@ext.lu")

        marc_del = ext_org["client"].delete(
            f"/api/organization/members/{d_id}",
            headers=ext_org["marc_headers"],
        )
        assert marc_del.status_code == 403

    def test_tom_cannot_modify_itm_access(self, ext_org):
        """tom (membre simple) PUT /access sur le compte itm → 403."""
        inv = _invite(ext_org["client"], ext_org["marc_token"], "itm-restrict@ext.lu", "itm",
                      first_name="ITM", last_name="Restrict")
        invite_code = inv.json()["code"]
        _join(ext_org["client"], "itm-restrict@ext.lu", "test123456",
              invite_code, "ITM", "Restrict")

        cid, ans = _fetch_captcha(ext_org["client"])
        login_r = ext_org["client"].post("/api/auth/login", json={
            "email": "itm-restrict@ext.lu", "password": "test123456",
            "captcha_id": cid, "captcha_answer": ans,
        })
        assert login_r.status_code == 200
        itm_token = login_r.json()["access_token"]
        itm_id = _get_user_id(ext_org["client"], itm_token, "itm-restrict@ext.lu")

        tom_access = ext_org["client"].put(
            f"/api/organization/members/{itm_id}/access",
            json={"access_expires_at": None},
            headers=ext_org["tom_headers"],
        )
        assert tom_access.status_code == 403

    def test_reactivation_with_future_date(self, ext_org):
        """marc révoque un ITM (date passée) puis remet une date future → ITM se reconnecte."""
        inv = _invite(ext_org["client"], ext_org["marc_token"], "itm-react@ext.lu", "itm",
                      first_name="ITM", last_name="React",
                      access_expires_at=(datetime.now(timezone.utc) + timedelta(days=30)).isoformat())
        invite_code = inv.json()["code"]
        _join(ext_org["client"], "itm-react@ext.lu", "test123456",
              invite_code, "ITM", "React")

        cid, ans = _fetch_captcha(ext_org["client"])
        login_r = ext_org["client"].post("/api/auth/login", json={
            "email": "itm-react@ext.lu", "password": "test123456",
            "captcha_id": cid, "captcha_answer": ans,
        })
        assert login_r.status_code == 200
        itm_token = login_r.json()["access_token"]
        itm_id = _get_user_id(ext_org["client"], itm_token, "itm-react@ext.lu")

        # Marc sets past expiry → revocation
        past = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
        access_r = ext_org["client"].put(
            f"/api/organization/members/{itm_id}/access",
            json={"access_expires_at": past},
            headers=ext_org["marc_headers"],
        )
        assert access_r.status_code == 200

        # Re-login → should fail (401) because of past expiry + token_version bump
        cid2, ans2 = _fetch_captcha(ext_org["client"])
        login_r2 = ext_org["client"].post("/api/auth/login", json={
            "email": "itm-react@ext.lu", "password": "test123456",
            "captcha_id": cid2, "captcha_answer": ans2,
        })
        assert login_r2.status_code == 401

        # Marc sets a FUTURE date → reactivates
        new_future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        access_r2 = ext_org["client"].put(
            f"/api/organization/members/{itm_id}/access",
            json={"access_expires_at": new_future},
            headers=ext_org["marc_headers"],
        )
        assert access_r2.status_code == 200

        # Re-login → should succeed now
        cid3, ans3 = _fetch_captcha(ext_org["client"])
        login_r3 = ext_org["client"].post("/api/auth/login", json={
            "email": "itm-react@ext.lu", "password": "test123456",
            "captcha_id": cid3, "captcha_answer": ans3,
        })
        assert login_r3.status_code == 200


# ── Tests : batch endpoint ──────────────────────────────────────────

class TestBatchExternalInvitations:
    """POST /api/invitations/batch — external account types."""

    def test_admin_batch_with_external_accounts(self, ext_org):
        """Admin crée un batch avec des comptes extérieurs → 201."""
        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        r = ext_org["client"].post(
            "/api/invitations/batch",
            json={
                "invitations": [
                    {
                        "email": "itm-batch@ext.lu",
                        "first_name": "ITM", "last_name": "Batch",
                        "account_type": "itm",
                        "access_expires_at": future,
                    },
                    {
                        "email": "rh-batch@ext.lu",
                        "first_name": "RH", "last_name": "Batch",
                        "account_type": "rh",
                        "access_expires_at": future,
                    },
                ]
            },
            headers=ext_org["sophie_headers"],
        )
        assert r.status_code == 200
        data = r.json()
        assert data["created"] == 2
        assert data["skipped"] == 0
        assert data["failed"] == 0
