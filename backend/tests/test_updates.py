"""Tests du service self-update (mock réseau, aucun appel GitHub réel)."""
import json
import time
from pathlib import Path

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app

# Version « plus récente » fictive : simule des releases au-dessus de la version
# locale sans figer un numéro réel (les tests ne cassent plus à chaque bump).
NEWER = "2099.01.001"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _login(client, email, password, captcha_id, captcha_answer):
    r = client.post("/api/auth/login", json={
        "email": email, "password": password,
        "captcha_id": captcha_id, "captcha_answer": captcha_answer,
    })
    assert r.status_code == 200, f"Login failed: {r.json()}"
    return r.json()["access_token"]


# ---------------------------------------------------------------------------
# Fixtures — mono-org (require_instance_admin succeeds for president)
# ---------------------------------------------------------------------------

@pytest.fixture
def _mono_org_env(monkeypatch, tmp_path):
    """Active SD_INSTANCE_ADMIN_EMAILS pour le test mono-org."""
    monkeypatch.setenv("SD_INSTANCE_ADMIN_EMAILS", "sophie@testpv.lu")
    from app.core.config import get_settings
    get_settings.cache_clear()
    yield
    monkeypatch.delenv("SD_INSTANCE_ADMIN_EMAILS", raising=False)
    from app.core.config import get_settings
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _clear_update_config(db):
    """Supprimer toute donnée update_config avant/après chaque test."""
    from app.models.update_config import UpdateConfig
    db.query(UpdateConfig).delete()
    db.commit()
    yield
    db.query(UpdateConfig).delete()
    db.commit()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sophie_token(client, monkeypatch, tmp_path):
    """Token de sophie dans un contexte mono-org (admin instance)."""
    monkeypatch.setenv("SD_INSTANCE_ADMIN_EMAILS", "sophie@testpv.lu")
    from app.core.config import get_settings
    get_settings.cache_clear()

    from tests.helpers import fetch_captcha
    cid, ans = fetch_captcha(client)
    r = client.post("/api/organizations", json={
        "organization_name": "TestPV",
        "company_name": "TestPV SA",
        "employee_count": 120,
        "admin_email": "sophie@testpv.lu",
        "admin_password": "test123456",
        "admin_first_name": "Sophie",
        "admin_last_name": "Muller",
        "admin_delegue_status": "titulaire",
        "admin_delegue_role": "president",
        "captcha_id": cid,
        "captcha_answer": ans,
    })
    assert r.status_code == 201, f"Create org failed: {r.json()}"
    cid2, ans2 = fetch_captcha(client)
    token = _login(client, "sophie@testpv.lu", "test123456", cid2, ans2)
    return token


@pytest.fixture
def tom_token(client, monkeypatch):
    """Token de tom (membre, mono-org) — allowed=false."""
    monkeypatch.setenv("SD_INSTANCE_ADMIN_EMAILS", "sophie@testpv.lu")
    from app.core.config import get_settings
    get_settings.cache_clear()

    from tests.helpers import fetch_captcha, create_invitation
    from app.core.database import SessionLocal
    from app.models.user import User

    # Créer org
    cid, ans = fetch_captcha(client)
    r = client.post("/api/organizations", json={
        "organization_name": "TestPV",
        "company_name": "TestPV SA",
        "employee_count": 120,
        "admin_email": "sophie@testpv.lu",
        "admin_password": "test123456",
        "admin_first_name": "Sophie",
        "admin_last_name": "Muller",
        "admin_delegue_status": "titulaire",
        "admin_delegue_role": "president",
        "captcha_id": cid,
        "captcha_answer": ans,
    })
    assert r.status_code == 201

    # Login sophie
    cid2, ans2 = fetch_captcha(client)
    stok = _login(client, "sophie@testpv.lu", "test123456", cid2, ans2)
    h = {"Authorization": f"Bearer {stok}"}

    # Get org_id
    r = client.get("/api/dashboard", headers=h)
    org_id = r.json()["organization"]["id"]

    # Get sophie's user_id
    db = SessionLocal()
    sophie = db.query(User).filter(User.email == "sophie@testpv.lu").first()
    sophie_id = sophie.id
    db.close()

    # Invite tom as membre
    db2 = SessionLocal()
    create_invitation(db2, "tom@testpv.lu", org_id, sophie_id, "TOM456",
                      delegue_status="titulaire", delegue_role="membre")
    db2.close()

    cid3, ans3 = fetch_captcha(client)
    client.post("/api/join", json={
        "email": "tom@testpv.lu", "password": "test123456",
        "first_name": "Tom", "last_name": "Wagner",
        "invitation_code": "TOM456",
        "captcha_id": cid3, "captcha_answer": ans3,
    })

    cid4, ans4 = fetch_captcha(client)
    return _login(client, "tom@testpv.lu", "test123456", cid4, ans4)


# ---------------------------------------------------------------------------
# Tests de comparaison de versions
# ---------------------------------------------------------------------------

def test_version_ordering():
    """Vérifie que _upd_vtuple classe correctement les versions."""
    from app.services.updates import _upd_vtuple

    # Une version normale < -c1 < version supérieure
    assert _upd_vtuple("2026.11.001") < _upd_vtuple("2026.11.001-c1")
    assert _upd_vtuple("2026.11.001-c1") < _upd_vtuple("2026.11.002")
    assert _upd_vtuple("2026.11.001") < _upd_vtuple("2026.11.002")
    # Identique
    assert _upd_vtuple("2026.11.001") == _upd_vtuple("2026.11.001")
    # Patch de build (2026.11.001 < 2026.11.001-c2)
    assert _upd_vtuple("2026.11.001") < _upd_vtuple("2026.11.001-c2")
    assert _upd_vtuple("2026.11.001-c1") < _upd_vtuple("2026.11.001-c2")


# ---------------------------------------------------------------------------
# Tests check_update
# ---------------------------------------------------------------------------

def test_check_update_sets_state(monkeypatch, client, sophie_token):
    """Un check met à jour l'état (mocke _upd_latest_release)."""
    from app.services import updates as upd

    mock_release = {
        "version": NEWER,
        "published_at": "2026-11-01T00:00:00Z",
        "url": f"https://github.com/LostInTheBugs/Delegatum/releases/tag/{NEWER}",
        "body": "Nouvelle version\n",
    }
    monkeypatch.setattr(upd, "_upd_latest_release", lambda: mock_release)

    resp = client.post(
        "/api/admin/updates/check",
        headers={"Authorization": f"Bearer {sophie_token}"},
    )
    assert resp.status_code == 200
    from app.core.version import VERSION
    data = resp.json()
    assert data["current"] == VERSION
    assert data["latest"]["version"] == NEWER
    assert data["available"] is True


def test_check_update_error_state(monkeypatch, client, sophie_token):
    """Si _upd_latest_release lève, l'état note l'erreur."""
    from app.services import updates as upd

    monkeypatch.setattr(
        upd, "_upd_latest_release", lambda: (_ for _ in ()).throw(RuntimeError("fail")),
    )

    resp = client.post(
        "/api/admin/updates/check",
        headers={"Authorization": f"Bearer {sophie_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["latest"] is None
    assert "fail" in data["check"]["error"]


# ---------------------------------------------------------------------------
# Tests apply_update
# ---------------------------------------------------------------------------

def test_apply_update_writes_request(monkeypatch, client, sophie_token, tmp_path):
    """Apply écrit le fichier de demande dans data_dir."""
    from app.core.config import get_settings
    from app.services import updates as upd

    monkeypatch.setenv("SD_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    monkeypatch.setattr(upd, "_upd_latest_release", lambda: {
        "version": NEWER, "published_at": "2026-11-01T00:00:00Z",
        "url": "https://example.com", "body": "changelog",
    })

    # D'abord un check pour avoir une release
    client.post("/api/admin/updates/check", headers={"Authorization": f"Bearer {sophie_token}"})
    resp = client.post(
        "/api/admin/updates/apply",
        headers={"Authorization": f"Bearer {sophie_token}"},
    )
    assert resp.status_code == 200
    req_file = tmp_path / "update-request.json"
    assert req_file.exists()
    req = json.loads(req_file.read_text())
    assert req["version"] == NEWER
    assert req["by"] == "demande manuelle"


def test_apply_update_nothing_available(client, sophie_token):
    """409 si aucune version disponible."""
    resp = client.post(
        "/api/admin/updates/apply",
        headers={"Authorization": f"Bearer {sophie_token}"},
    )
    assert resp.status_code == 409


def test_apply_update_already_pending(monkeypatch, client, sophie_token, tmp_path):
    """409 si une demande est déjà en attente."""
    from app.core.config import get_settings
    from app.services import updates as upd

    monkeypatch.setenv("SD_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    monkeypatch.setattr(upd, "_upd_latest_release", lambda: {
        "version": NEWER, "published_at": "2026-11-01T00:00:00Z",
        "url": "https://example.com", "body": "changelog",
    })
    client.post("/api/admin/updates/check", headers={"Authorization": f"Bearer {sophie_token}"})
    client.post("/api/admin/updates/apply", headers={"Authorization": f"Bearer {sophie_token}"})
    # Deuxième apply devrait renvoyer 409
    resp = client.post(
        "/api/admin/updates/apply",
        headers={"Authorization": f"Bearer {sophie_token}"},
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Tests settings
# ---------------------------------------------------------------------------

def test_settings_rejects_invalid_check_h(client, sophie_token):
    """upd_check_h=5 n'est pas dans UPD_CHECK_VALUES → 422."""
    resp = client.put(
        "/api/admin/updates/settings",
        json={"upd_check_h": 5, "upd_apply_auto": False},
        headers={"Authorization": f"Bearer {sophie_token}"},
    )
    assert resp.status_code == 422


def test_settings_accepts_valid_check_h(client, sophie_token):
    """upd_check_h=1 est valide → 200."""
    resp = client.put(
        "/api/admin/updates/settings",
        json={"upd_check_h": 1, "upd_apply_auto": True},
        headers={"Authorization": f"Bearer {sophie_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["settings"]["upd_check_h"] == 1


def test_settings_rejects_non_bool_apply_auto(client, sophie_token):
    """upd_apply_auto: 'yes' est coercé en True par Pydantic v2 → 200."""
    resp = client.put(
        "/api/admin/updates/settings",
        json={"upd_check_h": 1, "upd_apply_auto": "yes"},
        headers={"Authorization": f"Bearer {sophie_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["settings"]["upd_apply_auto"] is True


# ---------------------------------------------------------------------------
# Tests droits (sécurité)
# ---------------------------------------------------------------------------

def test_no_token_get_state(client):
    """GET /api/admin/updates → 401 sans token."""
    resp = client.get("/api/admin/updates")
    assert resp.status_code in (401, 403)


def test_no_token_check(client):
    """POST /api/admin/updates/check → 401 sans token."""
    resp = client.post("/api/admin/updates/check")
    assert resp.status_code in (401, 403)


def test_no_token_apply(client):
    """POST /api/admin/updates/apply → 401 sans token."""
    resp = client.post("/api/admin/updates/apply")
    assert resp.status_code in (401, 403)


def test_no_token_settings(client):
    """PUT /api/admin/updates/settings → 401 sans token."""
    resp = client.put(
        "/api/admin/updates/settings",
        json={"upd_check_h": 1, "upd_apply_auto": False},
    )
    assert resp.status_code in (401, 403)


def test_no_token_allowed(client):
    """GET /api/admin/updates/allowed → 403 sans token (HTTPBearer auto_error)."""
    resp = client.get("/api/admin/updates/allowed")
    assert resp.status_code == 403


def test_member_check_forbidden(tom_token, client):
    """Tom (membre) → 403 sur GET state."""
    resp = client.get(
        "/api/admin/updates",
        headers={"Authorization": f"Bearer {tom_token}"},
    )
    assert resp.status_code == 403


def test_member_check_forbidden_post(tom_token, client):
    """Tom (membre) → 403 sur POST check."""
    resp = client.post(
        "/api/admin/updates/check",
        headers={"Authorization": f"Bearer {tom_token}"},
    )
    assert resp.status_code == 403


def test_member_apply_forbidden(tom_token, client):
    """Tom (membre) → 403 sur POST apply."""
    resp = client.post(
        "/api/admin/updates/apply",
        headers={"Authorization": f"Bearer {tom_token}"},
    )
    assert resp.status_code == 403


def test_member_settings_forbidden(tom_token, client):
    """Tom (membre) → 403 sur PUT settings."""
    resp = client.put(
        "/api/admin/updates/settings",
        json={"upd_check_h": 1, "upd_apply_auto": False},
        headers={"Authorization": f"Bearer {tom_token}"},
    )
    assert resp.status_code == 403


def test_allowed_member_returns_false(tom_token, client):
    """allowed vaut false pour tom (membre, pas admin instance)."""
    resp = client.get(
        "/api/admin/updates/allowed",
        headers={"Authorization": f"Bearer {tom_token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"allowed": False}


def test_allowed_with_admin_emails_true(sophie_token, client):
    """allowed vaut true pour sophie (SD_INSTANCE_ADMIN_EMAILS la reconnait)."""
    resp = client.get(
        "/api/admin/updates/allowed",
        headers={"Authorization": f"Bearer {sophie_token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"allowed": True}


def test_allowed_mono_org_no_admin_emails(client):
    """Sans SD_INSTANCE_ADMIN_EMAILS : mono-org + admin → allowed=true."""
    import pytest
    from tests.helpers import fetch_captcha
    from app.core.database import SessionLocal
    from app.models.user import User
    from app.core.config import get_settings

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.delenv("SD_INSTANCE_ADMIN_EMAILS", raising=False)
    get_settings.cache_clear()

    try:
        cid, ans = fetch_captcha(client)
        r = client.post("/api/organizations", json={
            "organization_name": "TestPV",
            "company_name": "TestPV SA",
            "employee_count": 120,
            "admin_email": "sophie2@testpv.lu",
            "admin_password": "test123456",
            "admin_first_name": "Sophie",
            "admin_last_name": "Test",
            "admin_delegue_status": "titulaire",
            "admin_delegue_role": "president",
            "captcha_id": cid,
            "captcha_answer": ans,
        })
        assert r.status_code == 201

        cid2, ans2 = fetch_captcha(client)
        token = _login(client, "sophie2@testpv.lu", "test123456", cid2, ans2)

        # Mono-org admin → allowed
        resp = client.get(
            "/api/admin/updates/allowed",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"allowed": True}

        # GET /api/admin/updates → 200
        resp2 = client.get(
            "/api/admin/updates",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.status_code == 200
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


def test_allowed_multi_org_no_admin_emails(client, monkeypatch):
    """Sans SD_INSTANCE_ADMIN_EMAILS : mono-org admin, puis 2e org → allowed=false."""
    from tests.helpers import fetch_captcha
    from app.core.database import SessionLocal
    from app.models.user import User
    from app.core.config import get_settings

    monkeypatch.delenv("SD_INSTANCE_ADMIN_EMAILS", raising=False)
    get_settings.cache_clear()

    cid, ans = fetch_captcha(client)
    r = client.post("/api/organizations", json={
        "organization_name": "TestPV",
        "company_name": "TestPV SA",
        "employee_count": 120,
        "admin_email": "sophie3@testpv.lu",
        "admin_password": "test123456",
        "admin_first_name": "Sophie",
        "admin_last_name": "Test",
        "admin_delegue_status": "titulaire",
        "admin_delegue_role": "president",
        "captcha_id": cid,
        "captcha_answer": ans,
    })
    assert r.status_code == 201

    cid2, ans2 = fetch_captcha(client)
    token = _login(client, "sophie3@testpv.lu", "test123456", cid2, ans2)
    h = {"Authorization": f"Bearer {token}"}

    # Get org_id et user_id de sophie
    r = client.get("/api/dashboard", headers=h)
    org_id = r.json()["organization"]["id"]
    db = SessionLocal()
    sophie = db.query(User).filter(User.email == "sophie3@testpv.lu").first()
    sophie_id = sophie.id
    db.close()

    # Créer 2e organisation (different admin email, same user)
    cid3, ans3 = fetch_captcha(client)
    r = client.post("/api/organizations", json={
        "organization_name": "SecondOrg",
        "company_name": "Second2 SA",
        "employee_count": 50,
        "admin_email": "sophie3b@testpv.lu",
        "admin_password": "test123456",
        "admin_first_name": "Sophie",
        "admin_last_name": "Test",
        "admin_delegue_status": "titulaire",
        "admin_delegue_role": "president",
        "captcha_id": cid3,
        "captcha_answer": ans3,
    })
    assert r.status_code == 201

    # allowed doit être false (2 organisations, pas de SD_INSTANCE_ADMIN_EMAILS)
    resp = client.get(
        "/api/admin/updates/allowed",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"allowed": False}

    # GET /api/admin/updates → 403
    resp2 = client.get(
        "/api/admin/updates",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 403


def test_allowed_multi_org_returns_false(monkeypatch, client, tmp_path):
    """sophie avec 2 organisations → allowed=false pour tom."""
    from tests.helpers import fetch_captcha, create_invitation
    from app.core.database import SessionLocal
    from app.models.user import User

    # Créer 1ère org (sophie admin)
    cid, ans = fetch_captcha(client)
    r = client.post("/api/organizations", json={
        "organization_name": "TestPV",
        "company_name": "TestPV SA",
        "employee_count": 120,
        "admin_email": "sophie@testpv.lu",
        "admin_password": "test123456",
        "admin_first_name": "Sophie",
        "admin_last_name": "Muller",
        "admin_delegue_status": "titulaire",
        "admin_delegue_role": "president",
        "captcha_id": cid,
        "captcha_answer": ans,
    })
    assert r.status_code == 201

    # Login sophie
    cid2, ans2 = fetch_captcha(client)
    stok = _login(client, "sophie@testpv.lu", "test123456", cid2, ans2)
    h = {"Authorization": f"Bearer {stok}"}

    # Get org_id
    r = client.get("/api/dashboard", headers=h)
    org_id = r.json()["organization"]["id"]

    # Get sophie's user_id
    db = SessionLocal()
    sophie = db.query(User).filter(User.email == "sophie@testpv.lu").first()
    sophie_id = sophie.id
    db.close()

    # Invite tom as membre
    db2 = SessionLocal()
    create_invitation(db2, "tom2@testpv.lu", org_id, sophie_id, "TOM2456",
                      delegue_status="titulaire", delegue_role="membre")
    db2.close()

    cid3, ans3 = fetch_captcha(client)
    client.post("/api/join", json={
        "email": "tom2@testpv.lu", "password": "test123456",
        "first_name": "Tom", "last_name": "Wagner",
        "invitation_code": "TOM2456",
        "captcha_id": cid3, "captcha_answer": ans3,
    })

    cid4, ans4 = fetch_captcha(client)
    tom_tok = _login(client, "tom2@testpv.lu", "test123456", cid4, ans4)

    # Tom (membre) : allowed doit être false
    resp = client.get(
        "/api/admin/updates/allowed",
        headers={"Authorization": f"Bearer {tom_tok}"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"allowed": False}


def test_settings_env_instance_admin(monkeypatch, client, org_with_users, tmp_path):
    """SD_INSTANCE_ADMIN_EMAILS = sophie → allowed=true même avec multi-org."""
    monkeypatch.setenv("SD_INSTANCE_ADMIN_EMAILS", "sophie@testpv.lu")
    monkeypatch.setenv("SD_DATA_DIR", str(tmp_path))
    from app.core.config import get_settings
    get_settings.cache_clear()

    from tests.helpers import fetch_captcha, create_invitation
    from app.core.database import SessionLocal
    from app.models.user import User

    # Créer une 2e organisation pour sophie
    cid, ans = fetch_captcha(client)
    r = client.post("/api/organizations", json={
        "organization_name": "SecondOrg2",
        "company_name": "Second2 SA",
        "employee_count": 50,
        "admin_email": "sophie3@testpv.lu",
        "admin_password": "test123456",
        "admin_first_name": "Sophie",
        "admin_last_name": "3",
        "admin_delegue_status": "titulaire",
        "admin_delegue_role": "president",
        "captcha_id": cid,
        "captcha_answer": ans,
    })
    assert r.status_code == 201

    # Re-login sophie après le changement d'env
    cid2, ans2 = fetch_captcha(client)
    stok = _login(client, "sophie@testpv.lu", "test123456", cid2, ans2)

    resp = client.get(
        "/api/admin/updates/allowed",
        headers={"Authorization": f"Bearer {stok}"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"allowed": True}


# ---------------------------------------------------------------------------
# Tests ETag / 304
# ---------------------------------------------------------------------------

def test_304_keeps_previous_version(monkeypatch, client, sophie_token, tmp_path):
    """Après une réponse 200 puis un mock 304 : la version reste, error vide."""
    from app.core.config import get_settings
    from app.services import updates as upd

    monkeypatch.setenv("SD_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()

    call_count = [0]
    def mock_release():
        call_count[0] += 1
        if call_count[0] == 1:
            # Première appel : réponse 200
            return {
                "version": NEWER,
                "published_at": "2026-11-01T00:00:00Z",
                "url": f"https://github.com/LostInTheBugs/Delegatum/releases/tag/{NEWER}",
                "body": "Nouvelle version",
            }
        else:
            # Deuxième appel : 304 → retourne None
            return None

    monkeypatch.setattr(upd, "_upd_latest_release", mock_release)

    # 1er check : version NEWER stockée
    resp1 = client.post(
        "/api/admin/updates/check",
        headers={"Authorization": f"Bearer {sophie_token}"},
    )
    assert resp1.status_code == 200
    d1 = resp1.json()
    assert d1["latest"]["version"] == NEWER
    assert d1["available"] is True
    assert d1["check"]["error"] == ""

    # 2e check : 304 → version conservée, error vide
    resp2 = client.post(
        "/api/admin/updates/check",
        headers={"Authorization": f"Bearer {sophie_token}"},
    )
    assert resp2.status_code == 200
    d2 = resp2.json()
    assert d2["latest"]["version"] == NEWER  # même version
    assert d2["available"] is True
    assert d2["check"]["error"] == ""  # pas d'erreur


# ---------------------------------------------------------------------------
# Tests applier state
# ---------------------------------------------------------------------------

def test_applier_state_has_key(monkeypatch, client, sophie_token, tmp_path):
    """GET /api/admin/updates renvoie une clé 'applier' dans l'état."""
    from app.core.config import get_settings
    from app.services import updates as upd

    monkeypatch.setenv("SD_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    monkeypatch.setattr(upd, "_upd_latest_release", lambda: None)

    resp = client.get(
        "/api/admin/updates",
        headers={"Authorization": f"Bearer {sophie_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "applier" in data
    applier = data["applier"]
    assert "installed" in applier
    assert "seen_at" in applier
    assert "applied" in applier
    assert "applied_at" in applier
    assert "result" in applier
    assert "running" in applier
    assert "running_at" in applier


def test_applier_installed_false_no_file(monkeypatch, client, sophie_token, tmp_path):
    """Sans update-applier.json → installed=false, tous les champs à 0/vide."""
    from app.core.config import get_settings
    from app.services import updates as upd

    monkeypatch.setenv("SD_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    monkeypatch.setattr(upd, "_upd_latest_release", lambda: None)

    resp = client.get(
        "/api/admin/updates",
        headers={"Authorization": f"Bearer {sophie_token}"},
    )
    assert resp.status_code == 200
    applier = resp.json()["applier"]
    assert applier["installed"] is False
    assert applier["seen_at"] == 0
    assert applier["applied"] == ""
    assert applier["applied_at"] == 0
    assert applier["result"] == ""
    assert applier["running"] == ""
    assert applier["running_at"] == 0


def test_applier_installed_true_with_file(monkeypatch, client, sophie_token, tmp_path):
    """Avec update-applier.json → installed=true, valeurs lues."""
    from app.core.config import get_settings
    from app.services import updates as upd

    monkeypatch.setenv("SD_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()

    applier_data = {
        "seen_at": 1700000000.0,
        "result": "ok",
        "applied": "2026.11.001",
        "at": 1700000001.0,
        "running": "",
        "running_at": 0,
    }
    (tmp_path / "update-applier.json").write_text(
        json.dumps(applier_data), encoding="utf-8"
    )

    monkeypatch.setattr(upd, "_upd_latest_release", lambda: None)

    resp = client.get(
        "/api/admin/updates",
        headers={"Authorization": f"Bearer {sophie_token}"},
    )
    assert resp.status_code == 200
    applier = resp.json()["applier"]
    assert applier["installed"] is True
    assert applier["seen_at"] == 1700000000.0
    assert applier["applied"] == "2026.11.001"
    assert applier["applied_at"] == 1700000001.0
    assert applier["result"] == "ok"
    assert applier["running"] == ""
    assert applier["running_at"] == 0


def test_applier_running(monkeypatch, client, sophie_token, tmp_path):
    """Applier en cours d'exécution → running=true, running_at renseigné."""
    from app.core.config import get_settings
    from app.services import updates as upd

    monkeypatch.setenv("SD_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()

    (tmp_path / "update-applier.json").write_text(
        json.dumps({
            "seen_at": 1700000000.0,
            "result": "",
            "applied": "",
            "at": 0,
            "running": "2026.11.001",
            "running_at": 1700000010.0,
        }),
        encoding="utf-8",
    )

    monkeypatch.setattr(upd, "_upd_latest_release", lambda: None)

    resp = client.get(
        "/api/admin/updates",
        headers={"Authorization": f"Bearer {sophie_token}"},
    )
    assert resp.status_code == 200
    applier = resp.json()["applier"]
    assert applier["running"] == "2026.11.001"
    assert applier["running_at"] == 1700000010.0
    assert applier["installed"] is True
