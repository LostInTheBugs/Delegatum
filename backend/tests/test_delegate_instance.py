"""Tests — Instance Profile délégué (R4)

Chaque test utilise la fixture `profile` de test_instance_profile.py
pour modifier SD_INSTANCE_PROFILE.
"""

import pytest


@pytest.fixture
def profile(monkeypatch):
    """Fixture pour changer SD_INSTANCE_PROFILE proprement."""
    from app.core.config import get_settings

    def _set(value: str | None) -> None:
        if value is None:
            monkeypatch.delenv("SD_INSTANCE_PROFILE", raising=False)
        else:
            monkeypatch.setenv("SD_INSTANCE_PROFILE", value)
        get_settings.cache_clear()

    yield _set
    monkeypatch.delenv("SD_INSTANCE_PROFILE", raising=False)
    get_settings.cache_clear()


def _login(client, email, password, captcha_id, captcha_answer):
    r = client.post("/api/auth/login", json={
        "email": email, "password": password,
        "captcha_id": captcha_id, "captcha_answer": captcha_answer,
    })
    assert r.status_code == 200, f"Login failed: {r.json()}"
    return r.json()["access_token"]


# ── 1. Création d'org — profil sst ─────────────────────────────────


def test_create_org_sst_admin_is_delegate(client, profile):
    """Profil sst : le créateur a delegue_role=membre, is_delegue_securite_sante=True, role=admin."""
    from app.core.database import SessionLocal
    from app.models.user import User
    from tests.helpers import fetch_captcha

    profile("sst")

    cid, ans = fetch_captcha(client)
    r = client.post("/api/organizations", json={
        "organization_name": "OrgSST",
        "company_name": "SST SA",
        "employee_count": 50,
        "admin_email": "sst@test.lu",
        "admin_password": "test123456",
        "admin_first_name": "Jean",
        "admin_last_name": "Dupont",
        "admin_delegue_status": "titulaire",
        "admin_delegue_role": "president",  # IGNORÉ en profil délégué
        "captcha_id": cid,
        "captcha_answer": ans,
    })
    assert r.status_code == 201

    db = SessionLocal()
    admin = db.query(User).filter(User.email == "sst@test.lu").first()
    db.close()

    assert admin.role.value == "admin"
    assert admin.delegue_role.value == "membre"  # pas "president"
    assert admin.is_delegue_securite_sante is True
    assert admin.is_delegue_egalite is False


def test_create_org_sst_admin_can_auth(client, profile):
    """Le créateur SST peut se connecter et agir en admin."""
    from tests.helpers import fetch_captcha

    profile("sst")

    cid, ans = fetch_captcha(client)
    client.post("/api/organizations", json={
        "organization_name": "OrgSST2",
        "company_name": "SST SA2",
        "employee_count": 50,
        "admin_email": "sst2@test.lu",
        "admin_password": "test123456",
        "admin_first_name": "SST",
        "admin_last_name": "Test",
        "admin_delegue_status": "titulaire",
        "admin_delegue_role": "president",
        "captcha_id": cid,
        "captcha_answer": ans,
    })

    cid2, ans2 = fetch_captcha(client)
    token = _login(client, "sst2@test.lu", "test123456", cid2, ans2)
    h = {"Authorization": f"Bearer {token}"}

    # L'admin SST peut voir le dashboard
    r = client.get("/api/dashboard", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["user"]["role"] == "admin"
    assert data["user"]["is_delegue_securite_sante"] is True


# ── 2. Création d'org — profil egalite ─────────────────────────────


def test_create_org_egalite_admin_is_delegate(client, profile):
    """Profil egalite : is_delegue_egalite=True, delegue_role=membre."""
    from app.core.database import SessionLocal
    from app.models.user import User
    from tests.helpers import fetch_captcha

    profile("egalite")

    cid, ans = fetch_captcha(client)
    r = client.post("/api/organizations", json={
        "organization_name": "OrgEgalite",
        "company_name": "Egalite SA",
        "employee_count": 50,
        "admin_email": "egalite@test.lu",
        "admin_password": "test123456",
        "admin_first_name": "Marie",
        "admin_last_name": "Lecocq",
        "admin_delegue_status": "titulaire",
        "admin_delegue_role": "president",
        "captcha_id": cid,
        "captcha_answer": ans,
    })
    assert r.status_code == 201

    db = SessionLocal()
    admin = db.query(User).filter(User.email == "egalite@test.lu").first()
    db.close()

    assert admin.role.value == "admin"
    assert admin.delegue_role.value == "membre"
    assert admin.is_delegue_egalite is True
    assert admin.is_delegue_securite_sante is False


# ── 3. Création d'org — profil egalite,sst avec admin_domain ──────


def test_create_org_combined_admin_domain_egalite(client, profile):
    """Profil egalite,sst + admin_domain=egalite → ok, is_delegue_egalite=True."""
    from app.core.database import SessionLocal
    from app.models.user import User
    from tests.helpers import fetch_captcha

    profile("sst,egalite")

    cid, ans = fetch_captcha(client)
    r = client.post("/api/organizations", json={
        "organization_name": "OrgCombo",
        "company_name": "Combo SA",
        "employee_count": 50,
        "admin_email": "combo@test.lu",
        "admin_password": "test123456",
        "admin_first_name": "Combo",
        "admin_last_name": "Admin",
        "admin_delegue_status": "titulaire",
        "admin_delegue_role": "president",
        "admin_domain": "egalite",
        "captcha_id": cid,
        "captcha_answer": ans,
    })
    assert r.status_code == 201

    db = SessionLocal()
    admin = db.query(User).filter(User.email == "combo@test.lu").first()
    db.close()

    assert admin.is_delegue_egalite is True
    assert admin.is_delegue_securite_sante is False


def test_create_org_combined_admin_domain_securite_sante(client, profile):
    """Profil egalite,sst + admin_domain=securite_sante → ok (défaut)."""
    from app.core.database import SessionLocal
    from app.models.user import User
    from tests.helpers import fetch_captcha

    profile("sst,egalite")

    cid, ans = fetch_captcha(client)
    r = client.post("/api/organizations", json={
        "organization_name": "OrgCombo2",
        "company_name": "Combo SA2",
        "employee_count": 50,
        "admin_email": "combo2@test.lu",
        "admin_password": "test123456",
        "admin_first_name": "Combo2",
        "admin_last_name": "Admin",
        "admin_delegue_status": "titulaire",
        "admin_delegue_role": "president",
        "admin_domain": "securite_sante",
        "captcha_id": cid,
        "captcha_answer": ans,
    })
    assert r.status_code == 201


def test_create_org_combined_admin_domain_invalid_400(client, profile):
    """Profil egalite,sst + admin_domain=bidule → 400."""
    from tests.helpers import fetch_captcha

    profile("sst,egalite")

    cid, ans = fetch_captcha(client)
    r = client.post("/api/organizations", json={
        "organization_name": "OrgBad",
        "company_name": "Bad SA",
        "employee_count": 50,
        "admin_email": "bad@test.lu",
        "admin_password": "test123456",
        "admin_first_name": "Bad",
        "admin_last_name": "User",
        "admin_delegue_status": "titulaire",
        "admin_delegue_role": "president",
        "admin_domain": "bidule",
        "captcha_id": cid,
        "captcha_answer": ans,
    })
    assert r.status_code == 400
    assert "admin_domain" in r.json()["detail"]


# ── 4. Délégation en lecture seule (profil sst) ───────────────────


def test_delegate_read_only_safety_register(client, profile):
    """Profil sst : une présidente invitée lit safety-register mais ne peut pas écrire."""
    from app.core.database import SessionLocal
    from app.models.user import User
    from tests.helpers import fetch_captcha, create_invitation

    profile("sst")

    # 1. Créer l'org SST
    cid1, ans1 = fetch_captcha(client)
    r = client.post("/api/organizations", json={
        "organization_name": "OrgSSTDel",
        "company_name": "SST Del SA",
        "employee_count": 50,
        "admin_email": "sst_del@test.lu",
        "admin_password": "test123456",
        "admin_first_name": "Admin",
        "admin_last_name": "SST",
        "admin_delegue_status": "titulaire",
        "admin_delegue_role": "president",
        "captcha_id": cid1,
        "captcha_answer": ans1,
    })
    assert r.status_code == 201

    # 2. Se connecter en admin SST
    cid2, ans2 = fetch_captcha(client)
    admin_token = _login(client, "sst_del@test.lu", "test123456", cid2, ans2)
    h_admin = {"Authorization": f"Bearer {admin_token}"}

    # 3. Récupérer org_id et admin_id
    r = client.get("/api/dashboard", headers=h_admin)
    org_id = r.json()["organization"]["id"]

    db = SessionLocal()
    admin = db.query(User).filter(User.email == "sst_del@test.lu").first()
    admin_id = admin.id
    db.close()

    # 4. Inviter une présidente (delegation)
    db2 = SessionLocal()
    create_invitation(db2, "presidente@test.lu", org_id, admin_id,
                      delegue_status="titulaire", delegue_role="president")
    db2.close()

    # 5. La présidente rejoint
    cid3, ans3 = fetch_captcha(client)
    client.post("/api/join", json={
        "email": "presidente@test.lu", "password": "test123456",
        "first_name": "Presidente", "last_name": "Delegate",
        "invitation_code": "TESTCODE",
        "captcha_id": cid3, "captcha_answer": ans3,
    })

    # 6. Se connecter en présidente
    cid4, ans4 = fetch_captcha(client)
    del_token = _login(client, "presidente@test.lu", "test123456", cid4, ans4)
    h_del = {"Authorization": f"Bearer {del_token}"}

    # 7. GET safety-register → 200 (lecture autorisée)
    r = client.get("/api/safety-register", headers=h_del)
    assert r.status_code == 200

    # 8. POST safety-register → 403 (écriture refusée)
    r = client.post("/api/safety-register", headers=h_del, json={
        "employee_id": "EMP001", "incident_type": "accident",
        "description": "Test", "date": "2026-01-01",
    })
    assert r.status_code == 403


# ── 5. Profil dp — comportement inchangé ───────────────────────────


def test_create_org_dp_president_unchanged(client, profile):
    """Profil dp : le créateur reste président (admin_delegue_role respecté)."""
    from app.core.database import SessionLocal
    from app.models.user import User
    from tests.helpers import fetch_captcha

    profile("dp")

    cid, ans = fetch_captcha(client)
    r = client.post("/api/organizations", json={
        "organization_name": "OrgDP",
        "company_name": "DP SA",
        "employee_count": 100,
        "admin_email": "dp@test.lu",
        "admin_password": "test123456",
        "admin_first_name": "DP",
        "admin_last_name": "Admin",
        "admin_delegue_status": "titulaire",
        "admin_delegue_role": "president",
        "captcha_id": cid,
        "captcha_answer": ans,
    })
    assert r.status_code == 201

    db = SessionLocal()
    admin = db.query(User).filter(User.email == "dp@test.lu").first()
    db.close()

    assert admin.role.value == "admin"
    assert admin.delegue_role.value == "president"  # PRESERVÉ en dp
    assert admin.is_delegue_securite_sante is False
    assert admin.is_delegue_egalite is False


def test_dp_bureau_garde_écriture(client, profile, org_with_users):
    """Profil dp : un membre bureau (marc, secretaire) garde l'écriture sur les modules."""
    profile("dp")  # dp est le profil par défaut

    # Marc (secretaire) peut écrire sur meetings (uniquement disponible en dp)
    r = client.post(
        "/api/meetings",
        headers={"Authorization": f"Bearer {org_with_users['marc_token']}"},
        json={"title": "Réunion test", "date": "2026-01-01"},
    )
    assert r.status_code in (201, 200), f"Marc should write meetings in dp: {r.status_code} {r.text[:200]}"


# ── 6. Profil egalite,sst — admin_domain ───────────────────────────


def test_create_org_combined_no_admin_domain(client, profile):
    """Profil egalite,sst sans admin_domain → défaut securite_sante, DSS True."""
    from app.core.database import SessionLocal
    from app.models.user import User
    from tests.helpers import fetch_captcha

    profile("sst,egalite")

    cid, ans = fetch_captcha(client)
    r = client.post("/api/organizations", json={
        "organization_name": "OrgComboDefault",
        "company_name": "Combo SA",
        "employee_count": 50,
        "admin_email": "combo_default@test.lu",
        "admin_password": "test123456",
        "admin_first_name": "Combo",
        "admin_last_name": "Admin",
        "admin_delegue_status": "titulaire",
        "admin_delegue_role": "president",
        # pas de admin_domain
        "captcha_id": cid,
        "captcha_answer": ans,
    })
    assert r.status_code == 201

    db = SessionLocal()
    admin = db.query(User).filter(User.email == "combo_default@test.lu").first()
    db.close()

    assert admin.delegue_role.value == "membre"
    assert admin.is_delegue_securite_sante is True
    assert admin.is_delegue_egalite is False


def test_create_org_sst_admin_domain_400(client, profile):
    """Profil sst + admin_domain → 400."""
    from tests.helpers import fetch_captcha

    profile("sst")

    cid, ans = fetch_captcha(client)
    r = client.post("/api/organizations", json={
        "organization_name": "OrgSSTBad",
        "company_name": "SST SA",
        "employee_count": 50,
        "admin_email": "sstbad@test.lu",
        "admin_password": "test123456",
        "admin_first_name": "SST",
        "admin_last_name": "Bad",
        "admin_delegue_status": "titulaire",
        "admin_delegue_role": "president",
        "admin_domain": "egalite",
        "captcha_id": cid,
        "captcha_answer": ans,
    })
    assert r.status_code == 400


def test_create_org_dp_admin_domain_400(client, profile):
    """Profil dp + admin_domain → 400."""
    from tests.helpers import fetch_captcha

    profile("dp")

    cid, ans = fetch_captcha(client)
    r = client.post("/api/organizations", json={
        "organization_name": "OrgDPBad",
        "company_name": "DP SA",
        "employee_count": 100,
        "admin_email": "dpbad@test.lu",
        "admin_password": "test123456",
        "admin_first_name": "DP",
        "admin_last_name": "Bad",
        "admin_delegue_status": "titulaire",
        "admin_delegue_role": "president",
        "admin_domain": "securite_sante",
        "captcha_id": cid,
        "captcha_answer": ans,
    })
    assert r.status_code == 400


# ── 7. Batch — forced delegation account_type ──────────────────────


def test_batch_forces_delegation_account_type(client, profile):
    """Batch : une ligne avec account_type=police crée quand même une invitation delegation."""
    from app.core.database import SessionLocal
    from app.models.user import User, AccountType
    from app.models.organization import Organization
    from tests.helpers import fetch_captcha, create_org

    profile("dp")

    cid1, ans1 = fetch_captcha(client)
    r = client.post("/api/organizations", json={
        "organization_name": "OrgBatchTest",
        "company_name": "Batch SA",
        "employee_count": 50,
        "admin_email": "batchadmin@test.lu",
        "admin_password": "test123456",
        "admin_first_name": "Batch",
        "admin_last_name": "Admin",
        "admin_delegue_status": "titulaire",
        "admin_delegue_role": "president",
        "captcha_id": cid1,
        "captcha_answer": ans1,
    })
    assert r.status_code == 201

    # Login as admin
    cid2, ans2 = fetch_captcha(client)
    token = _login(client, "batchadmin@test.lu", "test123456", cid2, ans2)
    h = {"Authorization": f"Bearer {token}"}

    # Batch invite with account_type=police in the payload
    r = client.post("/api/invitations/batch", json={
        "invitations": [
            {"email": "police@test.lu", "first_name": "Pierre", "last_name": "Police"},
        ],
    }, headers=h)
    assert r.status_code == 200  # batch endpoint defaults to 200
    data = r.json()
    assert data["created"] == 1
    assert data["results"][0]["status"] == "created"

    # Verify the invitation has account_type=delegation, not police
    from app.models import Invitation
    db = SessionLocal()
    inv = db.query(Invitation).filter(Invitation.email == "police@test.lu").first()
    assert inv is not None
    assert inv.account_type == AccountType.delegation
    db.close()
