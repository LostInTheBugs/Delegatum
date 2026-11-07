"""Routes API — self-update. Préfixe /api/admin/updates."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_instance_admin
from app.core.database import get_db
from app.core.version import VERSION
from app.models import User
from app.services import updates as upd

# ── Protected routes (instance admin only) ──────────────────────────
router = APIRouter(
    prefix="/api/admin/updates",
    tags=["self-update"],
    dependencies=[Depends(require_instance_admin)],
)


@router.get("")
def get_update_state():
    """État complet des mises à jour."""
    return upd._upd_state()


@router.post("/check")
def check_update():
    """Force une vérification et retourne le nouvel état."""
    return upd._upd_run_check()


@router.post("/apply")
def apply_update():
    """Demande l'application de la dernière version disponible.

    Retourne 409 si aucune version n'est disponible ou si une demande est déjà en attente.
    """
    st = upd._upd_state()
    if not st["available"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Aucune mise à jour disponible",
        )
    if st["request"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Une demande est déjà en attente",
        )
    upd._upd_request_write(st["latest"]["version"], "demande manuelle")
    return upd._upd_state()


class SettingsBody(BaseModel):
    upd_check_h: int
    upd_apply_auto: bool


@router.put("/settings")
def update_settings(body: SettingsBody):
    """Modifie les paramètres de vérification et d'application automatique."""
    if body.upd_check_h not in upd.UPD_CHECK_VALUES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"upd_check_h doit être dans {upd.UPD_CHECK_VALUES}",
        )
    upd._upd_set({
        "upd_check_h": str(body.upd_check_h),
        "upd_apply_auto": "1" if body.upd_apply_auto else "0",
    })
    return upd._upd_state()


# ── Public authenticated route ─────────────────────────────────────
allowed_router = APIRouter(prefix="/api/admin/updates", tags=["self-update"])


@allowed_router.get("/allowed")
def get_update_allowed(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retourne {\"allowed\": true|false} — accessible à tout utilisateur connecté."""
    try:
        require_instance_admin(user=user, db=db)
        return {"allowed": True}
    except HTTPException as exc:
        if exc.status_code == status.HTTP_403_FORBIDDEN:
            return {"allowed": False}
        raise
