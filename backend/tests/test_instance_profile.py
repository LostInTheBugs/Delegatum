"""Tests — Instance Profile (ÉTAPE A)

Changement de profil dans un test :
- monkeypatch `SD_INSTANCE_PROFILE` via fixture `profile`
- la fixture vide le cache LRU de `get_settings` avant ET après
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
    # Teardown : restaurer l'original et vider le cache
    monkeypatch.delenv("SD_INSTANCE_PROFILE", raising=False)
    get_settings.cache_clear()


# ── 1. Profil invalide ─────────────────────────────────────────────


def test_invalid_profile_refused(profile):
    from app.core.config import assert_instance_profile_valid

    profile("bizarro")
    with pytest.raises(RuntimeError, match="SD_INSTANCE_PROFILE"):
        assert_instance_profile_valid()


# ── 2. Modules et domaines par profil ──────────────────────────────


def test_profile_sst_modules(profile):
    from app.core.modules import instance_modules, instance_domains

    profile("sst")
    mods = instance_modules()
    assert "safety_register" in mods
    assert "time_tracking" in mods
    assert "delegate_activities" in mods
    assert "legal" in mods
    assert "meetings" not in mods
    assert "elections" not in mods
    assert "consultations" not in mods
    assert "workforce_stats" not in mods
    assert "compliance" not in mods
    assert "contact" not in mods
    assert "notices" not in mods
    doms = instance_domains()
    assert doms == {"securite_sante"}


def test_profile_egalite_modules(profile):
    from app.core.modules import instance_modules, instance_domains

    profile("egalite")
    mods = instance_modules()
    assert "time_tracking" in mods
    assert "delegate_activities" in mods
    assert "legal" in mods
    assert "meetings" not in mods
    assert "safety_register" not in mods
    assert "elections" not in mods
    assert "consultations" not in mods
    assert "workforce_stats" not in mods
    assert "compliance" not in mods
    assert "contact" not in mods
    assert "notices" not in mods
    doms = instance_domains()
    assert doms == {"egalite"}


def test_profile_sst_egalite_modules(profile):
    from app.core.modules import instance_modules, instance_domains

    for order in ("sst,egalite", "egalite,sst"):
        profile(order)
        mods = instance_modules()
        assert "meetings" not in mods
        assert "elections" not in mods
        assert "safety_register" in mods
        doms = instance_domains()
        assert doms == {"securite_sante", "egalite"}


def test_profile_dp_tous_modules(profile):
    from app.core.modules import instance_modules, instance_domains, ALL_MODULES

    profile("dp")
    assert instance_modules() == set(ALL_MODULES)
    assert instance_domains() == {"securite_sante", "egalite"}


# ── 3. Gardes 403 par profil ──────────────────────────────────────


def test_sst_meetings_403(client, org_with_users, profile):
    profile("sst")
    r = client.get(
        "/api/meetings",
        headers={"Authorization": f"Bearer {org_with_users['sophie_token']}"},
    )
    assert r.status_code == 403


def test_sst_minutes_403(client, org_with_users, profile):
    profile("sst")
    r = client.get(
        "/api/meetings/minutes",
        headers={"Authorization": f"Bearer {org_with_users['sophie_token']}"},
    )
    assert r.status_code == 403


def test_sst_elections_403(client, org_with_users, profile):
    profile("sst")
    r = client.get(
        "/api/elections",
        headers={"Authorization": f"Bearer {org_with_users['sophie_token']}"},
    )
    assert r.status_code == 403


def test_sst_consultations_403(client, org_with_users, profile):
    profile("sst")
    r = client.get(
        "/api/consultations",
        headers={"Authorization": f"Bearer {org_with_users['sophie_token']}"},
    )
    assert r.status_code == 403


def test_sst_workforce_stats_403(client, org_with_users, profile):
    profile("sst")
    r = client.get(
        "/api/workforce-stats",
        headers={"Authorization": f"Bearer {org_with_users['sophie_token']}"},
    )
    assert r.status_code == 403


def test_sst_safety_register_200(client, org_with_users):
    from app.core.modules import instance_modules

    assert "safety_register" in instance_modules()
    r = client.get(
        "/api/safety-register",
        headers={"Authorization": f"Bearer {org_with_users['sophie_token']}"},
    )
    assert r.status_code in (200, 404)


def test_egalite_safety_register_403(client, org_with_users, profile):
    profile("egalite")
    r = client.get(
        "/api/safety-register",
        headers={"Authorization": f"Bearer {org_with_users['sophie_token']}"},
    )
    assert r.status_code == 403


def test_egalite_delegate_activities_400(client, org_with_users, profile):
    profile("egalite")
    r = client.post(
        "/api/delegate-activities",
        headers={"Authorization": f"Bearer {org_with_users['sophie_token']}"},
        json={
            "user_id": 1,
            "domain": "securite_sante",
            "category": "formation",
            "description": "test",
            "date": "2026-01-01T00:00:00",
        },
    )
    assert r.status_code == 400
    assert "hors profil" in r.json().get("detail", "").lower()


# ── 4. PUT modules hors profil ─────────────────────────────────────


def test_put_modules_hors_profil_400(client, org_with_users, profile):
    profile("sst")
    r = client.put(
        "/api/organization/modules",
        headers={"Authorization": f"Bearer {org_with_users['sophie_token']}"},
        json={"modules": ["meetings"]},
    )
    assert r.status_code == 400
    assert "non disponible" in r.json().get("detail", "").lower()


def test_put_modules_dp_ok(client, org_with_users):
    r = client.put(
        "/api/organization/modules",
        headers={"Authorization": f"Bearer {org_with_users['sophie_token']}"},
        json={"modules": ["meetings", "elections"]},
    )
    assert r.status_code == 200


# ── 5. GET modules expose profile info ─────────────────────────────


def test_get_modules_expose_profile(client, org_with_users, profile):
    profile("sst")
    r = client.get(
        "/api/organization/modules",
        headers={"Authorization": f"Bearer {org_with_users['sophie_token']}"},
    )
    data = r.json()
    assert data["profile"] == "sst"
    assert "securite_sante" in data["domains"]
    assert "egalite" not in data["domains"]
    assert "meetings" not in data["available"]
    assert "safety_register" in data["available"]


# ── 6. enabled_modules_of : intersection avec profil ───────────────


def test_enabled_modules_of_sst_intersects(profile):
    from app.core.modules import enabled_modules_of

    profile("sst")
    result = enabled_modules_of('["legal", "elections", "delegate_activities"]')
    assert "legal" in result
    assert "delegate_activities" in result
    assert "elections" not in result


def test_enabled_modules_of_null_returns_profile_modules(profile):
    from app.core.modules import enabled_modules_of, instance_modules

    profile("sst")
    assert enabled_modules_of(None) == instance_modules()


def test_enabled_modules_of_empty_string_returns_profile_modules(profile):
    from app.core.modules import enabled_modules_of

    profile("egalite")
    result = enabled_modules_of("")
    assert "legal" in result
    assert "elections" not in result
    assert "meetings" not in result


# ── 7. Invitation / désignation hors profil ────────────────────────


def test_invitation_egalite_hors_profil_sst(client, org_with_users, profile):
    profile("sst")
    r = client.post(
        "/api/invitations",
        headers={"Authorization": f"Bearer {org_with_users['sophie_token']}"},
        json={
            "email": "test@example.com",
            "first_name": "Jean",
            "last_name": "Dupont",
            "is_delegue_egalite": True,
        },
    )
    assert r.status_code == 400
    assert "hors profil" in r.json().get("detail", "").lower()


def test_designate_egalite_hors_profil_sst(client, org_with_users, profile):
    profile("sst")
    r = client.put(
        "/api/organization/members/1/designate",
        headers={"Authorization": f"Bearer {org_with_users['sophie_token']}"},
        json={"field": "egalite", "value": True},
    )
    assert r.status_code == 400


# ── 8. Dashboard ───────────────────────────────────────────────────


def test_dashboard_sst_ne_plante_pas(client, org_with_users, profile):
    profile("sst")
    r = client.get(
        "/api/dashboard",
        headers={"Authorization": f"Bearer {org_with_users['sophie_token']}"},
    )
    assert r.status_code == 200
    assert r.json()["organization"]["instance_profile"] == "sst"


def test_dashboard_dp_includes_all(client, org_with_users):
    r = client.get(
        "/api/dashboard",
        headers={"Authorization": f"Bearer {org_with_users['sophie_token']}"},
    )
    assert r.status_code == 200
    assert r.json()["organization"]["instance_profile"] == "dp"


# ── 9. Migration 20260801_0019 ─────────────────────────────────────


def _load_migration():
    """Importe le module de migration par son chemin fichier."""
    import importlib.util
    from pathlib import Path

    parent = Path(__file__).resolve().parent.parent
    p = parent / "alembic" / "versions" / "20260801_0019_instance_profile_migration.py"
    spec = importlib.util.spec_from_file_location(
        "migration_20260801_0019", str(p),
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Ne peut charger la migration : {p}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_migration_with_legal_adds_safety_register(db, org_with_users, capfd):
    """Avec 'legal' dans enabled_modules → migration ajoute 'meetings' + 'safety_register'."""
    from app.models.organization import Organization
    import json

    org_id = org_with_users["org_id"]
    org = db.query(Organization).filter(Organization.id == org_id).first()
    org.enabled_modules = json.dumps(["legal", "time_tracking"])
    db.commit()

    migration = _load_migration()
    migration._do_upgrade(db)
    db.commit()

    out = capfd.readouterr().out
    assert "1 organisation" in out

    db.expire_all()
    org = db.query(Organization).filter(Organization.id == org_id).first()
    mods = json.loads(org.enabled_modules)
    assert "meetings" in mods
    assert "safety_register" in mods


def test_migration_without_legal_adds_meetings_only(db, org_with_users, capfd):
    """Sans 'legal' → migration ajoute 'meetings' uniquement."""
    from app.models.organization import Organization
    import json

    org_id = org_with_users["org_id"]
    org = db.query(Organization).filter(Organization.id == org_id).first()
    org.enabled_modules = json.dumps(["time_tracking", "delegate_activities"])
    db.commit()

    migration = _load_migration()
    migration._do_upgrade(db)
    db.commit()

    out = capfd.readouterr().out
    assert "1 organisation" in out

    db.expire_all()
    org = db.query(Organization).filter(Organization.id == org_id).first()
    mods = json.loads(org.enabled_modules)
    assert "meetings" in mods
    assert "safety_register" not in mods


def test_migration_skips_null_modules(db, org_with_users, capfd):
    """enabled_modules NULL → migration ne modifie pas."""
    from app.models.organization import Organization

    org_id = org_with_users["org_id"]
    org = db.query(Organization).filter(Organization.id == org_id).first()
    org.enabled_modules = None
    db.commit()

    migration = _load_migration()
    migration._do_upgrade(db)
    db.commit()

    out = capfd.readouterr().out
    assert "0 organisation" in out

    db.expire_all()
    org = db.query(Organization).filter(Organization.id == org_id).first()
    assert org.enabled_modules is None


# ── 10. instance_domains dans les réponses ─────────────────────────


def test_dashboard_sst_domains(client, org_with_users, profile):
    """sst → domains = [\"securite_sante\"], profile = \"sst\"."""
    profile("sst")
    r = client.get(
        "/api/dashboard",
        headers={"Authorization": f"Bearer {org_with_users['sophie_token']}"},
    )
    data = r.json()
    assert data["organization"]["instance_domains"] == ["securite_sante"]
    assert data["organization"]["instance_profile"] == "sst"


def test_dashboard_dp_domains(client, org_with_users):
    """dp → domains = [\"egalite\", \"securite_sante\"], profile = \"dp\"."""
    r = client.get(
        "/api/dashboard",
        headers={"Authorization": f"Bearer {org_with_users['sophie_token']}"},
    )
    data = r.json()
    assert set(data["organization"]["instance_domains"]) == {"securite_sante", "egalite"}
    assert data["organization"]["instance_profile"] == "dp"


def test_dashboard_egalite_sst_domains(client, org_with_users, profile):
    """egalite,sst → domains = [\"egalite\", \"securite_sante\"]."""
    profile("egalite,sst")
    r = client.get(
        "/api/dashboard",
        headers={"Authorization": f"Bearer {org_with_users['sophie_token']}"},
    )
    data = r.json()
    assert set(data["organization"]["instance_domains"]) == {"securite_sante", "egalite"}
    assert data["organization"]["instance_profile"] == "egalite,sst"


# ── 11. Vérification Alembic ───────────────────────────────────────


def test_alembic_single_head():
    """Seule head Alembic = 0019_instance_profile_migration."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from pathlib import Path

    parent = Path(__file__).resolve().parent.parent
    alembic_cfg = Config(str(parent / "alembic.ini"))
    script = ScriptDirectory.from_config(alembic_cfg)
    heads = script.get_heads()
    assert len(heads) == 1
    assert heads[0] == "20260801_0019_instance_profile_migration"


def test_alembic_migration_chain(db, org_with_users, capfd):
    """Upgrade → downgrade → upgrade 0019 sur une DB fraîchement créée."""
    import json, tempfile, os, shutil, subprocess, sys
    from pathlib import Path

    # Créer une DB totalement neuve
    fd, path = tempfile.mkstemp(suffix=".db", prefix="sd_alembic_test_")
    os.close(fd)

    parent = Path(__file__).resolve().parent.parent
    try:
        SD = f"sqlite:///{path}"
        env = os.environ.copy()
        env["SD_DATABASE_URL"] = SD

        # Upgrade à head (crée toutes les tables + 0019)
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=str(parent), env=env, capture_output=True, text=True,
        )
        assert result.returncode == 0, f"upgrade head failed: {result.stderr}"

        # Downgrade -1 (de 0019 à 0018)
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "downgrade", "-1"],
            cwd=str(parent), env=env, capture_output=True, text=True,
        )
        assert result.returncode == 0, f"downgrade -1 failed: {result.stderr}"

        # Up head à nouveau
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=str(parent), env=env, capture_output=True, text=True,
        )
        assert result.returncode == 0, f"upgrade head again failed: {result.stderr}"
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
