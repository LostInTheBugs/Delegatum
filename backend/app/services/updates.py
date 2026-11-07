"""Delegatum — self-update: compare avec la dernière release GitHub, vérification cadencée et
dépôt d'une demande que l'appliquateur hôte exécutera (l'app ne redémarre jamais ses conteneurs)."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.version import VERSION

# L'app ne peut PAS redémarrer ses conteneurs (elle n'a ni socket Docker ni privilèges, et c'est
# un choix de sécurité assumé). Elle vérifie donc les versions (lecture GitHub) et DÉPOSE une
# demande dans DATA_DIR ; un petit service de l'hôte (un timer systemd + script)
# l'applique. L'app affiche le dernier résultat de cette demande.
UPD_REPO = "LostInTheBugs/Delegatum"
UPD_CHECK_VALUES = (0, 1, 6, 12, 24, 168)  # heures entre deux vérifications
UPD_DEFAULTS = {"upd_check_h": "1", "upd_apply_auto": "0"}
_db_lock = threading.Lock()


def _upd_data_dir() -> Path:
    return Path(get_settings().data_dir)


def _upd_rows() -> dict:
    import sqlalchemy as sa
    with _db_lock:
        conn = SessionLocal()
        try:
            rows = conn.execute(sa.text("SELECT key, value, updated_at FROM update_config")).fetchall()
            return {r[0]: r[1] for r in rows}
        finally:
            conn.close()


def _upd_conf(key: str) -> str:
    return _upd_rows().get(key) or UPD_DEFAULTS.get(key, "")


def _upd_set(updates: dict) -> None:
    with _db_lock:
        conn = SessionLocal()
        try:
            import sqlalchemy as sa
            for key, value in updates.items():
                conn.execute(
                    sa.text(
                        "INSERT OR REPLACE INTO update_config (key, value, updated_at) VALUES (:key,:value,strftime('%Y-%m-%dT%H:%M:%f','now'))"
                    ),
                    {"key": str(key), "value": str(value)},
                )
            conn.commit()
        finally:
            conn.close()


def _upd_vtuple(version: str) -> tuple:
    """« 2026.11.001-c1 » → ((2026, 11, 1), 1) — comparer des versions du dépôt entre elles."""
    base, _, corr = str(version or "").strip().partition("-c")
    parts = []
    for piece in base.split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    try:
        corr_i = int(corr) if corr else 0
    except ValueError:
        corr_i = 0
    return (tuple(parts[:3]), corr_i)


def _upd_latest_release() -> dict | None:
    """Dernière release publiée du dépôt (réseau — ETag DB pour économiser le quota).

    Retourne None si GitHub renvoie 304 (pas de changement).
    """
    import urllib.request

    # Lire l'ETag stocké en BDD
    etag = _upd_rows().get("upd_etag")

    headers = {
        "User-Agent": f"Delegatum/{VERSION}",
        "Accept": "application/vnd.github+json",
    }
    # N'envoyer If-None-Match que si on a déjà une version stockée
    if etag:
        headers["If-None-Match"] = etag
    req = urllib.request.Request(
        f"https://api.github.com/repos/{UPD_REPO}/releases/latest",
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        if exc.code == 304:
            # Pas de changement : garder la version déjà stockée
            return None
        raise
    # Capturer l'ETag de la réponse et le stocker en BDD
    new_etag = resp.headers.get("ETag")
    if new_etag:
        _upd_set({"upd_etag": new_etag})
    tag = str(data.get("tag_name") or "").strip()
    if not tag:
        raise ValueError("release sans étiquette de version")
    body = str(data.get("body") or "")[:20000]
    return {
        "version": tag,
        "published_at": str(data.get("published_at") or ""),
        "url": str(
            data.get(
                "html_url",
                f"https://github.com/{UPD_REPO}/releases/tag/{tag}",
            )
        ),
        "body": body,
    }


def _upd_read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _upd_state() -> dict:
    rows = _upd_rows()
    latest_v = str(rows.get("upd_latest") or "")
    req = _upd_read_json(_upd_data_dir() / "update-request.json")
    app = _upd_read_json(_upd_data_dir() / "update-applier.json")
    available = bool(latest_v) and _upd_vtuple(latest_v) > _upd_vtuple(VERSION)
    try:
        check_h = int(float(_upd_conf("upd_check_h")))
    except (TypeError, ValueError):
        check_h = 1
    seen = float(app.get("seen_at") or 0)
    return {
        "current": VERSION,
        "latest": (
            {
                "version": latest_v,
                "published_at": str(rows.get("upd_latest_at") or ""),
                "url": str(rows.get("upd_latest_url") or ""),
                "body": str(rows.get("upd_latest_body") or ""),
            }
            if latest_v
            else None
        ),
        "available": available,
        "check": {
            "last_at": float(rows.get("upd_checked") or 0),
            "error": str(rows.get("upd_error") or ""),
        },
        "request": (
            {
                "version": str(req.get("version") or ""),
                "requested_at": float(req.get("at") or 0),
                "by": str(req.get("by") or ""),
            }
            if req.get("version")
            else None
        ),
        "applier": {
            "installed": seen > 0,
            "seen_at": seen,
            "applied": str(app.get("applied") or ""),
            "applied_at": float(app.get("at") or 0),
            "result": str(app.get("result") or ""),
            "running": str(app.get("running") or ""),
            "running_at": float(app.get("running_at") or 0),
        },
        "settings": {
            "upd_check_h": check_h,
            "upd_apply_auto": _upd_conf("upd_apply_auto") == "1",
        },
    }


def _upd_run_check() -> dict:
    """Vérifie la dernière release (cadence automatique ou bouton « Vérifier »)."""
    now = time.time()
    try:
        rel = _upd_latest_release()
        if rel is None:
            # 304 : pas de changement, mettre à jour le timestamp et vider l'erreur
            _upd_set({"upd_checked": str(now), "upd_error": ""})
        else:
            _upd_set(
                {
                    "upd_latest": rel["version"],
                    "upd_latest_at": rel["published_at"],
                    "upd_latest_url": rel["url"],
                    "upd_latest_body": rel.get("body", ""),
                    "upd_checked": str(now),
                    "upd_error": "",
                }
            )
    except Exception as exc:  # noqa: BLE001 — réseau/API : on note l'échec, rien ne casse
        err = f"{type(exc).__name__} : {exc}"[:200]
        _upd_set({"upd_checked": str(now), "upd_error": err})
    return _upd_state()


def _upd_request_write(version: str, by: str) -> None:
    (_upd_data_dir() / "update-request.json").write_text(
        json.dumps({"version": version, "at": time.time(), "by": by}, ensure_ascii=False),
        encoding="utf-8",
    )


def _upd_tick() -> None:
    """Cadence de vérification + application automatique (appelé par la boucle de fond)."""
    try:
        check_h = int(float(_upd_conf("upd_check_h")))
    except (TypeError, ValueError):
        check_h = 1
    st = _upd_state()
    due = check_h > 0 and (
        st["check"]["last_at"] == 0
        or time.time() - st["check"]["last_at"] >= check_h * 3600
    )
    if due:
        st = _upd_run_check()
    if st["available"] and st["settings"]["upd_apply_auto"] and not st["request"]:
        _upd_request_write(st["latest"]["version"], "application automatique")


def _update_loop() -> None:
    """Boucle de fond : premier passage après 30-120s (jitter), puis toutes les 10 min."""
    import random

    time.sleep(random.randint(30, 120))
    while True:
        try:
            _upd_tick()
        except Exception as exc:  # noqa: BLE001
            print(f"[updates] {exc}")
        time.sleep(600)
