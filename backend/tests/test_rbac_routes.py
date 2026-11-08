"""Tests RBAC R2 : `require_access` appliqué sur les routes.

Vérifie que la matrice role×module est respectée au niveau des dépendances
des routers (require_access) et que les contrôles fins dans les fonctions
restent en place.

Fixtures :
- `_make_user` / `_make_org` (inline, pas de dépendance à conftest)
- `_login` helper identique à conftest pour obtenir des tokens API

Testés :
- itm : safety_register read=200, POST safety_register=403, meetings=403, elections=403, compliance read=200
- police : delegate_activities=403
- rh : workforce_stats read=200, POST workforce_stats=403
- Permission matrix update → itm compliance devient none → GET compliance overview=403
- Membre interne (tom) : meetings=200
- Comptes extérieurs bloqués sur email outbox
"""

import os
import re
import tempfile
import atexit

import bcrypt
import pytest
from fastapi.testclient import TestClient

_db_fd, _db_path = tempfile.mkstemp(suffix="_rbac_r2.db", prefix="test_")
os.environ["SD_DATABASE_URL"] = f"sqlite:///{_db_path}"
os.environ["SD_EMAIL_DIR"] = tempfile.mkdtemp(prefix="sd_emails_r2_")
os.environ.setdefault("SD_SECRET_KEY", "test-secret-key-rbac-r2-0123456789abcdef01")
os.environ.setdefault("SD_INSTANCE_ADMIN_EMAILS", "")
os.environ.setdefault("SD_DATA_DIR", tempfile.mkdtemp(prefix="sd_data_r2_"))
os.environ["SD_UPDATE_LOOP"] = "0"
os.makedirs(os.environ["SD_EMAIL_DIR"], exist_ok=True)

from app.main import app
from app.core.database import SessionLocal, Base, engine
from app.core.ratelimit import reset_rate_limits
from app.core.permissions import init_default_permissions
from app.core.security import hash_password
from app.models import AccountType, User, UserRole, Organization


def _cleanup():
    os.close(_db_fd)
    try:
        os.unlink(_db_path)
    except OSError:
        pass


atexit.register(_cleanup)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    reset_rate_limits()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


# ── Helpers ───────────────────────────────────────────────────────────


def _make_org(db, name="TestOrg", employee_count=120):
    from app.models.organization import Organization
    org = Organization(name=name, slug="test-org", employee_count=employee_count)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def _make_user(db, email, password, org, role="member", delegue_role="membre",
               delegue_status="titulaire", account_type="delegation",
               is_dss=False, is_deg=False):
    user = User(
        email=email,
        password_hash=hash_password(password),
        first_name="Test",
        last_name="User",
        role=UserRole(role),
        organization_id=org.id,
        delegue_role=delegue_role,
        delegue_status=delegue_status,
        account_type=AccountType(account_type),
        is_delegue_securite_sante=is_dss,
        is_delegue_egalite=is_deg,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _login(client, email, password):
    resp = client.get("/api/auth/captcha")
    assert resp.status_code == 200
    data = resp.json()
    m = re.search(r"font (\d+) \+ (\d+)", data["question"])
    assert m, f"Unexpected question format: {data['question']}"
    a, b = int(m.group(1)), int(m.group(2))
    r = client.post("/api/auth/login", json={
        "email": email, "password": password,
        "captcha_id": data["challenge_id"], "captcha_answer": str(a + b),
    })
    assert r.status_code == 200, f"Login failed: {r.json()}"
    return r.json()["access_token"]


def _setup_external_accounts(db, org):
    """Crée les comptes extérieurs : itm, rh, police.
    Initialise les permissions par défaut pour que effective_level soit cohérent.
    """
    init_default_permissions(org.id, db)
    itm = _make_user(db, "itm@test.lu", "pass1234", org,
                     account_type="itm")
    rh = _make_user(db, "rh@test.lu", "pass1234", org,
                    account_type="rh")
    police = _make_user(db, "police@test.lu", "pass1234", org,
                        account_type="police")
    return itm, rh, police


# ── Tests itm ─────────────────────────────────────────────────────────


class TestITM:
    """itm : safety_register=read, compliance=read, delegate_activities=read, meetings=none"""

    def test_itm_safety_register_get(self, client):
        """GET /api/safety-register → 200 pour itm."""
        db = SessionLocal()
        org = _make_org(db, "ITMTest", 50)
        _make_user(db, "admin@itm.lu", "pass1234", org, role="admin")
        init_default_permissions(org.id, db)
        itm, _, _ = _setup_external_accounts(db, org)
        db.close()
        token = _login(client, "itm@test.lu", "pass1234")
        r = client.get("/api/safety-register", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.json()}"

    def test_itm_safety_register_export_csv(self, client):
        """GET /api/safety-register/export.csv → 200 pour itm."""
        db = SessionLocal()
        org = _make_org(db, "ITMTest2", 50)
        _make_user(db, "admin@itm2.lu", "pass1234", org, role="admin")
        init_default_permissions(org.id, db)
        itm, _, _ = _setup_external_accounts(db, org)
        db.close()
        token = _login(client, "itm@test.lu", "pass1234")
        r = client.get("/api/safety-register/export.csv", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.json()}"

    def test_itm_safety_register_post_403(self, client):
        """POST /api/safety-register → 403 pour itm (none write)."""
        db = SessionLocal()
        org = _make_org(db, "ITMTest3", 50)
        _make_user(db, "admin@itm3.lu", "pass1234", org, role="admin")
        init_default_permissions(org.id, db)
        itm, _, _ = _setup_external_accounts(db, org)
        db.close()
        token = _login(client, "itm@test.lu", "pass1234")
        r = client.post("/api/safety-register", json={
            "date": "2026-01-01", "type": "inspection", "observations": "test"
        }, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.json()}"

    def test_itm_meetings_403(self, client):
        """GET /api/meetings → 403 pour itm (meetings=none)."""
        db = SessionLocal()
        org = _make_org(db, "ITMTest4", 50)
        _make_user(db, "admin@itm4.lu", "pass1234", org, role="admin")
        init_default_permissions(org.id, db)
        itm, _, _ = _setup_external_accounts(db, org)
        db.close()
        token = _login(client, "itm@test.lu", "pass1234")
        r = client.get("/api/meetings", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.json()}"

    def test_itm_elections_403(self, client):
        """GET /api/elections → 403 pour itm (meetings=none, elections=none)."""
        db = SessionLocal()
        org = _make_org(db, "ITMTest5", 50)
        _make_user(db, "admin@itm5.lu", "pass1234", org, role="admin")
        init_default_permissions(org.id, db)
        itm, _, _ = _setup_external_accounts(db, org)
        db.close()
        token = _login(client, "itm@test.lu", "pass1234")
        r = client.get("/api/elections", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.json()}"

    def test_itm_compliance_read(self, client):
        """GET /api/compliance/overview → 200 pour itm (compliance=read)."""
        db = SessionLocal()
        org = _make_org(db, "ITMTest6", 50)
        _make_user(db, "admin@itm6.lu", "pass1234", org, role="admin")
        init_default_permissions(org.id, db)
        itm, _, _ = _setup_external_accounts(db, org)
        db.close()
        token = _login(client, "itm@test.lu", "pass1234")
        r = client.get("/api/compliance/overview", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.json()}"


# ── Tests police ──────────────────────────────────────────────────────


class TestPolice:
    """police : safety_register=read uniquement"""

    def test_police_delegate_activities_403(self, client):
        """GET /api/delegate-activities → 403 pour police."""
        db = SessionLocal()
        org = _make_org(db, "PoliceTest", 50)
        _make_user(db, "admin@pol.lu", "pass1234", org, role="admin")
        init_default_permissions(org.id, db)
        _, _, police = _setup_external_accounts(db, org)
        db.close()
        token = _login(client, "police@test.lu", "pass1234")
        r = client.get("/api/delegate-activities", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.json()}"


# ── Tests rh ──────────────────────────────────────────────────────────


class TestRH:
    """rh : safety_register=read, delegate_activities=read, workforce_stats=read"""

    def test_rh_workforce_stats_get(self, client):
        """GET /api/workforce-stats → 200 pour rh."""
        db = SessionLocal()
        org = _make_org(db, "RHTest", 50)
        _make_user(db, "admin@rh.lu", "pass1234", org, role="admin")
        init_default_permissions(org.id, db)
        _, rh, _ = _setup_external_accounts(db, org)
        db.close()
        token = _login(client, "rh@test.lu", "pass1234")
        r = client.get("/api/workforce-stats", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.json()}"

    def test_rh_workforce_stats_post_403(self, client):
        """POST /api/workforce-stats → 403 pour rh (exterior max=write→read)."""
        db = SessionLocal()
        org = _make_org(db, "RHTest2", 50)
        _make_user(db, "admin@rh2.lu", "pass1234", org, role="admin")
        init_default_permissions(org.id, db)
        _, rh, _ = _setup_external_accounts(db, org)
        db.close()
        token = _login(client, "rh@test.lu", "pass1234")
        r = client.post("/api/workforce-stats", json={
            "date": "2026-01-01", "count": 10
        }, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.json()}"


# ── Test permission matrix update ─────────────────────────────────────


class TestPermissionMatrixUpdate:
    """Modifie la matrice → itm compliance=none → GET compliance overview=403."""

    def test_update_permissions_removes_itm_compliance(self, client):
        """PUT /api/organization/permissions : itm compliance → none → compliance overview=403."""
        db = SessionLocal()
        org = _make_org(db, "PermTest", 50)
        _make_user(db, "admin@perm.lu", "pass1234", org, role="admin")
        init_default_permissions(org.id, db)
        itm, _, _ = _setup_external_accounts(db, org)
        db.close()

        admin_token = _login(client, "admin@perm.lu", "pass1234")

        # Lire la matrice actuelle
        r = client.get("/api/organization/permissions",
                       headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200
        data = r.json()
        matrix = data["matrix"]

        # Modifier itm compliance → none (les autres niveaux restent tels quels)
        matrix["itm"]["compliance"] = "none"

        # PUT la matrice modifiée
        r = client.put("/api/organization/permissions", json={"matrix": matrix},
                       headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.json()}"

        # itm ne devrait plus avoir accès à compliance
        itm_token = _login(client, "itm@test.lu", "pass1234")
        r = client.get("/api/compliance/overview",
                       headers={"Authorization": f"Bearer {itm_token}"})
        assert r.status_code == 403, \
            f"Expected 403 after permission change, got {r.status_code}: {r.json()}"


# ── Test membre interne ──────────────────────────────────────────────


class TestInternalMember:
    """Un membre delegation (tom) garde ses accès actuels (meetings=200)."""

    def test_tom_meetings_200(self, client):
        """GET /api/meetings → 200 pour tom (membre delegation = write partout)."""
        db = SessionLocal()
        org = _make_org(db, "TomTest", 120)
        _make_user(db, "admin@tom.lu", "pass1234", org, role="admin")
        tom = _make_user(db, "tom@tom.lu", "pass1234", org, role="member",
                        delegue_role="membre")
        init_default_permissions(org.id, db)
        db.close()
        token = _login(client, "tom@tom.lu", "pass1234")
        r = client.get("/api/meetings", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.json()}"

    def test_tom_elections_200(self, client):
        """GET /api/elections → 200 pour tom (membre delegation = write everywhere)."""
        db = SessionLocal()
        org = _make_org(db, "TomTest2", 120)
        _make_user(db, "admin@tom2.lu", "pass1234", org, role="admin")
        tom = _make_user(db, "tom2@tom.lu", "pass1234", org, role="member",
                        delegue_role="membre")
        init_default_permissions(org.id, db)
        db.close()
        token = _login(client, "tom2@tom.lu", "pass1234")
        r = client.get("/api/elections", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.json()}"


# ── Test comptes extérieurs sur email outbox ──────────────────────────


class TestEmailOutboxExternal:
    """Comptes extérieurs (account_type != delegation) doivent être refusés sur les routes outbox."""

    def test_itm_email_outbox_403(self, client):
        """GET /api/emails → 403 pour itm (outbox réservé délégation)."""
        db = SessionLocal()
        org = _make_org(db, "EmailTest", 50)
        _make_user(db, "admin@email.lu", "pass1234", org, role="admin")
        itm, _, _ = _setup_external_accounts(db, org)
        db.close()
        token = _login(client, "itm@test.lu", "pass1234")
        r = client.get("/api/emails", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.json()}"

    def test_police_email_outbox_403(self, client):
        """GET /api/emails → 403 pour police."""
        db = SessionLocal()
        org = _make_org(db, "EmailTest2", 50)
        _make_user(db, "admin@email2.lu", "pass1234", org, role="admin")
        _, _, police = _setup_external_accounts(db, org)
        db.close()
        token = _login(client, "police@test.lu", "pass1234")
        r = client.get("/api/emails", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.json()}"

    def test_rh_email_outbox_403(self, client):
        """GET /api/emails → 403 pour rh."""
        db = SessionLocal()
        org = _make_org(db, "EmailTest3", 50)
        _make_user(db, "admin@email3.lu", "pass1234", org, role="admin")
        _, rh, _ = _setup_external_accounts(db, org)
        db.close()
        token = _login(client, "rh@test.lu", "pass1234")
        r = client.get("/api/emails", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.json()}"


# ── Test organization.py members ──────────────────────────────────────


class TestOrganizationMembers:
    """Vérifie require_access('members') sur les routes organization/members."""

    def test_itm_organization_members_403(self, client):
        """GET /organization/members → 403 pour itm (members=none par défaut)."""
        db = SessionLocal()
        org = _make_org(db, "OrgTest", 50)
        _make_user(db, "admin@org.lu", "pass1234", org, role="admin")
        itm, _, _ = _setup_external_accounts(db, org)
        db.close()
        token = _login(client, "itm@test.lu", "pass1234")
        r = client.get("/api/organization/members", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.json()}"

    def test_tom_organization_members_200(self, client):
        """GET /organization/members → 200 pour tom (membre delegation = members write)."""
        db = SessionLocal()
        org = _make_org(db, "OrgTest2", 120)
        _make_user(db, "admin@org2.lu", "pass1234", org, role="admin")
        tom = _make_user(db, "tom@org2.lu", "pass1234", org, role="member",
                        delegue_role="membre")
        init_default_permissions(org.id, db)
        db.close()
        token = _login(client, "tom@org2.lu", "pass1234")
        r = client.get("/api/organization/members", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.json()}"


# ── Test dashboard itm (pas de fuite de données réunions) ────────────


class TestDashboardITM:
    """GET /api/dashboard avec itm doit répondre 200 sans fuite de réunions."""

    def test_itm_dashboard_200_no_meetings(self, client):
        """GET /api/dashboard → 200 pour itm, sans données de réunions."""
        db = SessionLocal()
        org = _make_org(db, "DashTest", 50)
        _make_user(db, "admin@dash.lu", "pass1234", org, role="admin")
        itm, _, _ = _setup_external_accounts(db, org)
        db.close()
        token = _login(client, "itm@test.lu", "pass1234")
        r = client.get("/api/dashboard", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.json()}"
        data = r.json()
        # Vérifier qu'il n'y a pas de données de réunions
        meetings = data.get("meetings")
        assert meetings is None or meetings == [] or meetings == {}, \
            f"ITM should not see meetings data: {data}"


# ── Bug 1 : require_access("members") passe pour tous les rôles internes ─


class TestMembersModuleAlwaysActive:
    """members n'est pas dans ALL_MODULES → require_access doit le laisser passer."""

    def test_admin_members_200(self, client):
        """GET /api/organization/members → 200 pour l'admin."""
        db = SessionLocal()
        org = _make_org(db, "MembersTest", 120)
        _make_user(db, "admin@mem.lu", "pass1234", org, role="admin")
        _make_user(db, "tom@mem.lu", "pass1234", org, role="member", delegue_role="membre")
        db.close()
        token = _login(client, "admin@mem.lu", "pass1234")
        r = client.get("/api/organization/members", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.json()}"

    def test_tom_members_200(self, client):
        """GET /api/organization/members → 200 pour tom (membre delegation)."""
        db = SessionLocal()
        org = _make_org(db, "MembersTest2", 120)
        _make_user(db, "admin@mem2.lu", "pass1234", org, role="admin")
        tom = _make_user(db, "tom@mem2.lu", "pass1234", org, role="member",
                        delegue_role="membre")
        db.close()
        token = _login(client, "tom@mem2.lu", "pass1234")
        r = client.get("/api/organization/members", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.json()}"


# ── Bug 2 : aucune valeur write pour les rôles extérieurs dans le GET ─


class TestExteriorNoWriteInGET:
    """Pour chaque rôle extérieur, le GET /permissions ne doit jamais retourner write."""

    def test_exterior_roles_no_write(self, client):
        """Chaque rôle extérieur : aucune valeur 'write' dans le GET."""
        db = SessionLocal()
        org = _make_org(db, "WriteTest", 120)
        _make_user(db, "admin@write.lu", "pass1234", org, role="admin")
        init_default_permissions(org.id, db)
        db.close()

        admin_token = _login(client, "admin@write.lu", "pass1234")
        r = client.get("/api/organization/permissions",
                       headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200
        data = r.json()
        matrix = data["matrix"]

        exterior_roles = {"salarie_designe", "rh", "itm", "police"}
        for role in exterior_roles:
            role_perms = matrix.get(role, {})
            writable = [m for m, l in role_perms.items() if l == "write"]
            assert not writable, \
                f"Rôle extérieur {role} ne doit pas avoir de write: {writable}"
            # meetings doit être "none" pour les rôles extérieurs
            assert role_perms.get("meetings") == "none", \
                f"meetings doit être none pour {role}, got {role_perms.get('meetings')}"
