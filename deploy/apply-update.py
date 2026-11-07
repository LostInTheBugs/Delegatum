#!/usr/bin/env python3
"""Delegatum — applicateur de mise à jour (côté hôte).

La demande est déposée par l'administration du site dans le volume Docker
(`sd-data` → `/app/data/update-request.json`). Ce script, lancé par le timer
systemd `delegatum-update.timer`, applique.

    python3 deploy/apply-update.py            # applique la demande en attente (s'il y en a)
    python3 deploy/apply-update.py --dry-run  # ne change rien : montre ce qui serait fait

Le volume `sd-data` est monté dans le conteneur backend à `/app/data`.
Toutes les lectures/écritures de fichiers d'échange passent par
`docker compose exec -T backend …`.

Écrit `data/update-applier.json` (battement de cœur + dernier résultat, lu
par le site via `_upd_state()`) et journalise dans `deploy/update.log`.
"""
from __future__ import annotations

import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
COMPOSE = APP_DIR / "docker-compose.yml"
COMPOSE_ENV = APP_DIR / ".env"
LOG = APP_DIR / "deploy" / "update.log"
LOCK_PATH = Path("/tmp/delegatum-update.lock")

# Regex pour les tags Delegatum : 2026.11.001 ou 2026.11.001-c2
VERSION_RE = re.compile(r"^\d{4}\.\d{2}\.\d{3}(-c\d+)?$")
REPO = "LostInTheBugs/Delegatum"

DRY = "--dry-run" in sys.argv


# ── helpers ──────────────────────────────────────────────────────────

def log(message: str) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"[{stamp}] {message}\n")
    print(f"[{stamp}] {message}", flush=True)


def _compose_exec(*cmd: str, _stdin: str | None = None) -> str:
    """Exécuter une commande dans le conteneur backend, retourner stdout.
    Si _stdin est fourni, le transfère via stdin du conteneur."""
    proc_cmd = ["docker", "compose", "exec", "-T", "backend", *cmd]
    kwargs: dict = {
        "cwd": APP_DIR,
        "capture_output": True,
        "text": True,
        "timeout": 120,
    }
    if _stdin is not None:
        kwargs["input"] = _stdin
    res = subprocess.run(proc_cmd, **kwargs)
    if res.returncode != 0:
        err = (res.stderr or res.stdout).strip()
        raise RuntimeError(f"docker compose exec — code {res.returncode} : {err[-500:]}")
    return res.stdout


def _compose_up(*args: str) -> None:
    """Lancer `docker compose up …`."""
    res = subprocess.run(
        ["docker", "compose", "up", *args],
        cwd=APP_DIR,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    if res.returncode != 0:
        err = (res.stderr or res.stdout).strip()
        raise RuntimeError(f"docker compose up — code {res.returncode} : {err[-500:]}")


def write_status(seen_only: bool = False, **updates) -> None:
    """Écrire le JSON d'état dans le volume Docker.
    Si seen_only=True, n'écrit que seen_at (battement de cœur)."""
    if DRY:
        return
    data = {}
    try:
        raw = _compose_exec("cat", "/app/data/update-applier.json")
        data = json.loads(raw) if raw.strip() else {}
    except RuntimeError:
        pass
    data["seen_at"] = time.time()
    if not seen_only:
        data.update(updates)
    json_text = json.dumps(data, ensure_ascii=False)
    _compose_exec(
        "sh", "-c", "cat > /app/data/update-applier.json", _stdin=json_text
    )


def read_request() -> dict | None:
    """Lire la demande depuis le volume. Retourne None si absent."""
    try:
        raw = _compose_exec("cat", "/app/data/update-request.json")
        return json.loads(raw)
    except RuntimeError as exc:
        if "no such file" in str(exc).lower() or "not found" in str(exc).lower():
            return None
        raise


def delete_request() -> None:
    """Supprimer le fichier de demande."""
    if DRY:
        return
    try:
        _compose_exec("rm", "-f", "/app/data/update-request.json")
    except RuntimeError:
        pass


def _check_docker_available() -> bool:
    """Vérifier que Docker compose est opérationnel."""
    try:
        res = subprocess.run(
            ["docker", "compose", "ps"],
            cwd=APP_DIR,
            capture_output=True,
            text=True,
            timeout=15,
        )
        return res.returncode == 0
    except Exception:
        return False


def delete_status() -> None:
    """Supprimer le fichier d'état."""
    try:
        _compose_exec("rm", "-f", "/app/data/update-applier.json")
    except RuntimeError:
        pass


def _has_no_build_flag() -> bool:
    """Vérifier si SD_UPDATE_NO_BUILD=1 est actif."""
    # 1. variable d'environnement du processus
    if os.environ.get("SD_UPDATE_NO_BUILD", "").strip().lower() in ("1", "true", "yes"):
        return True
    # 2. clé dans le .env à côté du compose
    try:
        for line in COMPOSE_ENV.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#"):
                continue
            k, _, v = line.partition("=")
            if k.strip() == "SD_UPDATE_NO_BUILD" and v.strip().lower() in ("1", "true", "yes"):
                return True
    except OSError:
        pass
    return False


# ── DB helpers (dans le conteneur) ──────────────────────────────────

def _find_dbs() -> list[str]:
    """Lister les fichiers .db dans /app/data du conteneur."""
    raw = _compose_exec("find", "/app/data", "-maxdepth", "1", "-name", "*.db")
    return [l.strip() for l in raw.strip().splitlines() if l.strip()]


def _backup_dbs(version: str) -> list[str]:
    """Copier de sauvegarde chaque .db dans le conteneur, ne garder que
    les 3 sauvegardes les plus récentes par base."""
    dbs = _find_dbs()
    backups: list[str] = []
    for db in dbs:
        base = os.path.basename(db)  # ex: staff_delegation.db
        stamp = base + f".pre-{version}"
        backup_path = os.path.join(os.path.dirname(db), stamp)
        _compose_exec("cp", db, backup_path)
        backups.append(backup_path)
    # rotation : ne garder que les 3 plus récentes par base
    for db in dbs:
        base = os.path.basename(db)
        prefix = base + ".pre-"
        ls = _compose_exec("ls", "-1t", "/app/data")
        candidates = []
        for line in ls.strip().splitlines():
            name = line.strip()
            if name.startswith(prefix):
                candidates.append(os.path.join("/app/data", name))
        if len(candidates) > 3:
            for old in candidates[3:]:
                _compose_exec("rm", "-f", old)
    return backups


# ── rsync helpers ───────────────────────────────────────────────────

def _rsync(src: str, dst: str) -> None:
    """rsync de l'archive extraite vers le déploiement."""
    if shutil.which("rsync") is None:
        raise RuntimeError("rsync absent sur l'hôte")
    res = subprocess.run(
        ["rsync", "-a",
         "--exclude", ".env",
         "--exclude", "docker-compose.override.yml",
         "--exclude", "data/",
         "--exclude", ".git",
         "--exclude", "__pycache__",
         src, dst],
        cwd=APP_DIR,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if res.returncode != 0:
        raise RuntimeError(f"rsync — code {res.returncode} : {(res.stderr or res.stdout).strip()[-400:]}")


# ── version verification ────────────────────────────────────────────

def verify_version(version: str) -> None:
    """Vérifier que la version dans le conteneur correspond à la demande."""
    try:
        raw = _compose_exec("cat", "/app/app/core/version.py")
    except RuntimeError:
        raise RuntimeError("version.py absent du conteneur")
    m = re.search(r'VERSION\s*=\s*"([^"]+)"', raw)
    if not m:
        raise RuntimeError("VERSION non trouvée dans version.py")
    if m.group(1) != version:
        raise RuntimeError(
            f"version du conteneur = {m.group(1)}, attendu {version}"
        )


# ── apply ───────────────────────────────────────────────────────────

def apply_update(version: str) -> str:
    """Appliquer la mise à jour. Retourne 'ok' ou un message d'erreur."""
    # 1. SD_UPDATE_NO_BUILD
    if _has_no_build_flag():
        return (
            "refusé : construction interdite sur cet hôte "
            "(SD_UPDATE_NO_BUILD=1) — déployer des images construites ailleurs"
        )

    # 2. Sauvegardes DB
    try:
        backups = _backup_dbs(version)
        log(f"sauvegardes : {', '.join(backups)}")
    except RuntimeError as exc:
        log(f"erreur sauvegarde DB : {exc}")
        raise

    # 3. Téléchargement + extraction
    url = f"https://github.com/{REPO}/archive/refs/tags/{version}.tar.gz"
    log(f"télécharge {url}")
    tmp_dir = Path(tempfile.mkdtemp(prefix="delegatum-update-"))
    try:
        archive = tmp_dir / "src.tar.gz"
        resp = urllib.request.urlopen(url, timeout=120)
        archive.write_bytes(resp.read())

        extract_dir = tmp_dir / "src"
        with tarfile.open(archive) as tar:
            try:
                tar.extractall(str(extract_dir), filter="data")
            except TypeError:  # Python < 3.12
                tar.extractall(str(extract_dir))

        # Trouver la racine de l'archive (le dossier du tag)
        roots = [p for p in extract_dir.iterdir() if p.is_dir()]
        if not roots or not (roots[0] / "docker-compose.yml").exists():
            raise RuntimeError("archive inattendue (docker-compose.yml absent)")

        # 4. rsync par-dessus le déploiement
        _rsync(f"{roots[0]}/", f"{APP_DIR}/")
        log("rsync terminé")

        # 5. docker compose up -d --build
        _compose_up("-d", "--build")
        log("docker compose up -d --build terminé")

        # 6. alembic upgrade head
        try:
            _compose_exec("alembic", "upgrade", "head")
            log("alembic upgrade head terminé")
        except RuntimeError as exc:
            log(f"erreur alembic : {exc}")
            raise

        # 7. vérification version
        verify_version(version)
        log(f"version vérifiée = {version}")

        return "ok"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ── main ─────────────────────────────────────────────────────────────

def main() -> int:
    # Verrou
    lock_fh = LOCK_PATH.open("w")
    try:
        fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log("verrou détenu par une autre exécution — exit")
        return 0

    try:
        # Vérifier Docker (pour lire la demande, même en dry-run)
        if not _check_docker_available():
            log("Docker compose indisponible — le conteneur backend est-il en cours d'exécution ?")
            return 0

        # Battement de cœur permanent
        write_status(seen_only=True)

        # Lire la demande
        payload = read_request()
        if payload is None:
            return 0

        version = str(payload.get("version") or "").strip()
        by = str(payload.get("by") or "?")

        # Validation
        if not VERSION_RE.match(version):
            log(f"version refusée : {version!r}")
            delete_request()
            write_status(result=f"version refusée : {version[:60]}")
            return 1

        log(f"demande de {by} vers {version} ({'dry-run' if DRY else 'appli'})")
        write_status(result="en cours", running=version, running_at=time.time())

        # Appliquer
        if DRY:
            result = "dry-run ok"
            log("dry-run : tout irait bien")
        else:
            try:
                result = apply_update(version)
            except Exception as exc:  # noqa: BLE001
                result = f"échec : {exc}"[:300]
                log(f"ERREUR : {exc}")

        delete_request()
        write_status(applied=version if result == "ok" else "", at=time.time(),
                     result=result, running="", running_at=0)

        return 0 if result == "ok" else 1

    except Exception as exc:  # noqa: BLE001
        log(f"erreur inattendue : {exc}")
        try:
            write_status(result=f"erreur : {exc}"[:300], running="", running_at=0)
        except Exception:
            pass
        delete_request()
        return 1
    finally:
        fcntl.flock(lock_fh, fcntl.LOCK_UN)
        lock_fh.close()


if __name__ == "__main__":
    sys.exit(main())
