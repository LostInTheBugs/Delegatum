"""Service statique du frontend compilé (SPA) — app de bureau (Delegatum Desktop).

En production web, le front est servi par nginx (image frontend) et le backend
ne voit jamais les fichiers statiques. L'app de bureau, elle, embarque le build
Vite et laisse le backend le servir lui-même sur 127.0.0.1.

Activé uniquement quand SD_STATIC_DIR pointe un dossier existant (posé par le
launcher desktop) — aucun effet sur les déploiements web existants.
"""
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

_INDEX = "index.html"


class SPAStaticFiles(StaticFiles):
    """StaticFiles avec repli SPA (React Router).

    Une route inconnue (« /dashboard ») renvoie index.html ; un chemin /api/*
    inconnu garde un 404 JSON — jamais l'index (les clients API ne doivent pas
    recevoir du HTML à la place d'une erreur).
    """

    async def get_response(self, path, scope):  # type: ignore[override]
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and not path.lstrip("/").startswith("api/"):
                return await super().get_response(_INDEX, scope)
            raise


def mount_spa(app: FastAPI, directory: str | os.PathLike | None) -> bool:
    """Monte le front compilé à la racine de `app` (APRÈS les routes /api).

    Retourne True si le montage a eu lieu, False si le dossier est absent
    (déploiement web classique). Ne lève jamais : un chemin invalide est
    simplement ignoré.
    """
    if not directory:
        return False
    try:
        if not Path(directory).is_dir():
            return False
        app.mount("/", SPAStaticFiles(directory=str(directory), html=True), name="spa")
        return True
    except Exception:  # noqa: BLE001 — le service de l'app ne doit jamais planter ici
        return False
