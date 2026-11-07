"""Tests unitaires de deploy/apply-update.py — fonctions pures, sans Docker ni réseau."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Charger le script par chemin (pas un package installé).
_SCRIPT_PATH = Path(__file__).resolve().parent.parent.parent / "deploy" / "apply-update.py"
_spec = importlib.util.spec_from_file_location("apply_update", _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None, "impossible de charger le script"
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

validate_version = _mod.VERSION_RE.match


# ── validation de version ───────────────────────────────────────────

class TestValidateVersion:
    @pytest.mark.parametrize("tag", [
        "2026.11.001",
        "2026.11.001-c1",
        "2026.11.001-c12",
        "2099.12.999",
        "2099.12.999-c9",
    ])
    def test_valide(self, tag: str) -> None:
        assert validate_version(tag) is not None

    @pytest.mark.parametrize("tag", [
        "",
        "latest",
        "v2026.11.001",
        "2026.11.1",       # trop peu de digits
        "2026.1.001",      # mois sur 1 chiffre
        "26.11.001",       # année sur 2 chiffres
        "2026.11.001-",    # tiret final
        "2026.11.001-abc", # suffixe non numérique
        "2026.11.001--c1", # double tiret
        "abc",
    ])
    def test_refuse(self, tag: str) -> None:
        assert validate_version(tag) is None


# ── détection de SD_UPDATE_NO_BUILD ─────────────────────────────────

def _make_module(tmpdir: Path, env_lines: str = "") -> object:
    """Créer une instance du module avec APP_DIR et COMPOSE_ENV pointant vers tmpdir."""
    spec = importlib.util.spec_from_file_location("nu", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.APP_DIR = tmpdir
    m.COMPOSE_ENV = tmpdir / ".env"
    if env_lines:
        (tmpdir / ".env").write_text(env_lines)
    return m


class TestHasNoBuildFlag:
    def test_env_var_1(self) -> None:
        """SD_UPDATE_NO_BUILD=1 dans l'environnement du processus."""
        m = _make_module(Path(tempfile.mkdtemp()), "")
        with patch.dict(os.environ, {"SD_UPDATE_NO_BUILD": "1"}, clear=False):
            assert m._has_no_build_flag() is True

    def test_env_var_true(self) -> None:
        m = _make_module(Path(tempfile.mkdtemp()), "")
        with patch.dict(os.environ, {"SD_UPDATE_NO_BUILD": "true"}, clear=False):
            assert m._has_no_build_flag() is True

    def test_env_var_yes(self) -> None:
        m = _make_module(Path(tempfile.mkdtemp()), "")
        with patch.dict(os.environ, {"SD_UPDATE_NO_BUILD": "yes"}, clear=False):
            assert m._has_no_build_flag() is True

    def test_dotenv_1(self) -> None:
        """SD_UPDATE_NO_BUILD=1 dans le fichier .env."""
        tmp = Path(tempfile.mkdtemp())
        m = _make_module(tmp, "SD_PORT=8005\nSD_UPDATE_NO_BUILD=1\nDB_URL=sqlite:///x\n")
        assert m._has_no_build_flag() is True

    def test_dotenv_true(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        m = _make_module(tmp, "SD_UPDATE_NO_BUILD=true\n")
        assert m._has_no_build_flag() is True

    def test_dotenv_commented_ignored(self) -> None:
        """SD_UPDATE_NO_BUILD commenté ne doit pas compter."""
        tmp = Path(tempfile.mkdtemp())
        m = _make_module(tmp, "# SD_UPDATE_NO_BUILD=1\nSD_PORT=8005\n")
        assert m._has_no_build_flag() is False

    def test_absent(self) -> None:
        """Aucune indication de SD_UPDATE_NO_BUILD."""
        tmp = Path(tempfile.mkdtemp())
        m = _make_module(tmp, "SD_PORT=8005\nDB_URL=sqlite:///x\n")
        assert m._has_no_build_flag() is False

    def test_no_env_file(self) -> None:
        """Pas de fichier .env du tout."""
        tmp = Path(tempfile.mkdtemp())
        m = _make_module(tmp, "")  # .env créé vide mais existe
        assert m._has_no_build_flag() is False


# ── liste des fichiers préservés ─────────────────────────────────────

class TestPreservedFiles:
    """Le rsync exclut .env, docker-compose.override.yml, data/, .git, __pycache__."""

    def test_excludes_configures_exclusions(self) -> None:
        """Vérifier que _rsync contient bien les exclusions attendues."""
        import inspect
        src = inspect.getsource(_mod._rsync)
        for exc in [".env", "docker-compose.override.yml", "data/", ".git", "__pycache__"]:
            assert f'--exclude' in src and exc in src, f"{exc} non exclu"


# ── rotation des sauvegardes ────────────────────────────────────────

class TestBackupRotation:
    """Simuler _backup_dbs et la rotation avec un mock de _compose_exec."""

    def test_rotation_trois_maintenues(self) -> None:
        """Ne garder que les 3 plus récentes sauvegardes par base."""
        tmp = Path(tempfile.mkdtemp())
        spec = importlib.util.spec_from_file_location("rot1", _SCRIPT_PATH)
        assert spec is not None
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        m.APP_DIR = tmp
        m.COMPOSE_ENV = tmp / ".env"
        (tmp / ".env").write_text("")

        calls: list[list[str]] = []

        def mock_exec(*cmd: str, _stdin: str | None = None) -> str:
            calls.append(list(cmd))
            if "find" in cmd and "-maxdepth" in cmd:
                return "/app/data/staff_delegation.db\n"
            if "cp" in cmd:
                return ""
            if "ls" in cmd:
                return (
                    "staff_delegation.db\n"
                    "staff_delegation.db.pre-2026.08.001\n"
                    "staff_delegation.db.pre-2026.09.001\n"
                    "staff_delegation.db.pre-2026.10.001\n"
                    "staff_delegation.db.pre-2026.11.001\n"
                )
            return ""

        m._compose_exec = mock_exec

        try:
            result = m._backup_dbs("2026.11.001")
        except Exception as e:
            import traceback
            traceback.print_exc()

        # 4 backups retournés par ls, garder 3 → supprimer 1
        rm_calls = [c for c in calls if c[0:2] == ["rm", "-f"]]
        pre_rm = [c for c in rm_calls if "staff_delegation.db.pre-" in c[-1]]
        assert len(pre_rm) == 1, f"Attendu 1 suppression, obtenu {len(pre_rm)} (rm_calls={rm_calls})"

    def test_deux_sauvegardes_pas_de_rotation(self) -> None:
        """Avec 2 sauvegardes existantes + 1 nouvelle = 3, aucune suppression."""
        tmp = Path(tempfile.mkdtemp())
        spec = importlib.util.spec_from_file_location("rot2", _SCRIPT_PATH)
        assert spec is not None
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        m.APP_DIR = tmp
        m.COMPOSE_ENV = tmp / ".env"
        (tmp / ".env").write_text("")

        calls: list[list[str]] = []

        def mock_exec(*cmd: str, _stdin: str | None = None) -> str:
            calls.append(list(cmd))
            if "find" in cmd:
                return "/app/data/staff_delegation.db\n"
            if "cp" in cmd:
                return ""
            if "ls" in cmd:
                # 3 sauvegardes + DB = exactement 3, pas de rotation
                return (
                    "staff_delegation.db\n"
                    "staff_delegation.db.pre-2026.09.001\n"
                    "staff_delegation.db.pre-2026.10.001\n"
                    "staff_delegation.db.pre-2026.11.001\n"
                )
            return ""

        m._compose_exec = mock_exec

        m._backup_dbs("2026.11.001")

        rm_calls = [c for c in calls if c[0:2] == ["rm", "-f"]]
        assert len(rm_calls) == 0, f"Aucune suppression attendue, obtenu {len(rm_calls)}"

    def test_cinq_sauvegardes_supprime_deux(self) -> None:
        """5 sauvegardes existantes + 1 nouvelle = 6, supprime 3 (en garde 3)."""
        tmp = Path(tempfile.mkdtemp())
        spec = importlib.util.spec_from_file_location("rot3", _SCRIPT_PATH)
        assert spec is not None
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        m.APP_DIR = tmp
        m.COMPOSE_ENV = tmp / ".env"
        (tmp / ".env").write_text("")

        calls: list[list[str]] = []

        def mock_exec(*cmd: str, _stdin: str | None = None) -> str:
            calls.append(list(cmd))
            if "find" in cmd:
                return "/app/data/staff_delegation.db\n"
            if "cp" in cmd:
                return ""
            if "ls" in cmd:
                return (
                    "staff_delegation.db\n"
                    "staff_delegation.db.pre-2026.06.001\n"
                    "staff_delegation.db.pre-2026.07.001\n"
                    "staff_delegation.db.pre-2026.08.001\n"
                    "staff_delegation.db.pre-2026.09.001\n"
                    "staff_delegation.db.pre-2026.10.001\n"
                    "staff_delegation.db.pre-2026.11.001\n"
                )
            return ""

        m._compose_exec = mock_exec

        m._backup_dbs("2026.11.001")

        rm_calls = [c for c in calls if c[0:2] == ["rm", "-f"]]
        pre_rm = [c for c in rm_calls if "staff_delegation.db.pre-" in c[-1]]
        assert len(pre_rm) == 3, f"Attendu 3 suppressions, obtenu {len(pre_rm)}"


# ── battement de cœur (heartbeat) ────────────────────────────────────

class TestHeartbeat:
    """Le battement ne doit pas écraser le champ result."""

    def test_heartbeat_ne_change_pas_result(self) -> None:
        """write_status(seen_only=True) n'écrit que seen_at, pas result."""
        tmp = Path(tempfile.mkdtemp())
        spec = importlib.util.spec_from_file_location("beat", _SCRIPT_PATH)
        assert spec is not None
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        m.APP_DIR = tmp
        m.COMPOSE_ENV = tmp / ".env"
        (tmp / ".env").write_text("")

        calls: list[tuple] = []

        def mock_exec(*cmd: str, _stdin: str | None = None) -> str:
            calls.append((cmd, _stdin))
            return ""  # simulate empty existing state

        m._compose_exec = mock_exec
        # simuler un résultat existant
        m.write_status(result="ok")
        calls.clear()

        # battement de cœur
        m.write_status(seen_only=True)

        # 2 appels : lecture + écriture
        assert len(calls) == 2

        # lecture → données vides
        assert calls[0][0] == ("cat", "/app/data/update-applier.json")
        assert calls[0][1] is None

        # écriture → seulement seen_at, pas result
        data = json.loads(calls[1][1])
        assert "result" not in data
        assert "seen_at" in data
        assert isinstance(data["seen_at"], float)


# ── échec de sauvegarde ───────────────────────────────────────────────

class TestBackupFailure:
    """Sauvegarde en échec → apply_update ne télécharge pas."""

    def test_backup_echec_retourne_erreur(self) -> None:
        """Si _backup_dbs échoue, apply_update ne télécharge rien."""
        tmp = Path(tempfile.mkdtemp())
        spec = importlib.util.spec_from_file_location("bf", _SCRIPT_PATH)
        assert spec is not None
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        m.APP_DIR = tmp
        m.COMPOSE_ENV = tmp / ".env"
        m.DRY = False
        (tmp / ".env").write_text("")
        (tmp / ".env").touch()

        # _backup_dbs échoue toujours
        m._backup_dbs = lambda version: (_ for _ in ()).throw(
            RuntimeError("backup impossible")
        )

        try:
            result = m.apply_update("2026.11.001")
        except Exception as exc:
            result = f"échec : {exc}"

        assert result != "ok"
        assert "backup impossible" in result
