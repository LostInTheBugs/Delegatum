"""API de la matrice rôles × modules (R1).

- GET /api/organization/permissions → lecture (tout utilisateur delegation connecté)
- PUT /api/organization/permissions → écriture (admin uniquement)

Les modules listés sont les modules de l'instance + `members`.
Les rôles extérieurs (salarie_designe, rh, itm, police) ont des règles durcies.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.modules import ALL_MODULES, instance_modules
from app.core.permissions import (
    DEFAULT_PERMISSIONS,
    AccessLevel,
    EXTERIOR_FORBIDDEN_MODULES,
    PermissionMatrix,
    effective_level,
    init_default_permissions,
    role_keys,
)
from app.models import AccountType, User
from app.models.organization import Organization

router = APIRouter(prefix="/api/organization", tags=["permissions"])


# ── Modèles de requête/réponse ──────────────────────────────────────


class PermissionLevel(BaseModel):
    """Un niveau : none | read | write."""
    value: str

    @field_validator("value")
    @classmethod
    def _validate_level(cls, v: str) -> str:
        if v not in ("none", "read", "write"):
            raise ValueError(f"Niveau invalide : {v}. Attendu none | read | write")
        return v


class PermissionMatrixUpdate(BaseModel):
    """Structure {role_key: {module: level}} pour le PUT."""
    matrix: dict[str, dict[str, str]]


# ── GET ─────────────────────────────────────────────────────────────


@router.get("/permissions", response_model=dict)
def get_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retourne la matrice + défauts + modules disponibles (delegation uniquement)."""
    # L'utilisateur doit être de type delegation
    if current_user.account_type != AccountType.delegation:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux membres de la délégation",
        )

    instance_mods = instance_modules()
    modules = sorted(set(instance_mods) | {"members"})

    # Rôles connus (sans admin)
    roles = sorted(set(DEFAULT_PERMISSIONS.keys()) | {"admin"})

    # Matrice effective (rôle × module)
    matrix: dict[str, dict[str, str]] = {}
    for role in roles:
        matrix[role] = {}
        for module in modules:
            if role == "admin":
                # admin → toujours write, non lisible depuis la matrice
                matrix[role][module] = "write"
            else:
                # Simuler un user du rôle concerné pour effective_level
                # Les rôles extérieurs doivent avoir le account_type correspondant
                # afin que les règles dures (max=read, meetings=none) s'appliquent
                exterior_types = {"salarie_designe", "rh", "itm", "police"}
                if role in exterior_types:
                    acct = AccountType(role)
                else:
                    acct = AccountType.delegation
                from unittest.mock import MagicMock
                mock_user = MagicMock()
                mock_user.role = "member"
                mock_user.account_type = acct
                mock_user.organization_id = current_user.organization_id
                mock_user.delegue_role = None
                mock_user.is_delegue_securite_sante = False
                mock_user.is_delegue_egalite = False
                mock_user.delegue_status = None
                level = effective_level(mock_user, module, db)
                matrix[role][module] = level

    return {
        "roles": roles,
        "modules": modules,
        "matrix": matrix,
        "defaults": {k: dict(v) for k, v in DEFAULT_PERMISSIONS.items()},
    }


# ── PUT ─────────────────────────────────────────────────────────────


@router.put("/permissions", response_model=dict)
def update_permissions(
    body: PermissionMatrixUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Applique une nouvelle matrice (admin uniquement).

    Règles :
    - `admin` est toujours `write` et ignoré dans le payload.
    - Les rôles extérieurs : max = `read`, meetings = toujours `none`.
    - Tentative de write sur rôle extérieur → 422.
    - Tentative de changer meetings pour rôle extérieur → 422.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Réservé aux administrateurs",
        )

    matrix = body.matrix
    org_id = current_user.organization_id

    # Modules disponibles dans cette instance
    instance_mods = instance_modules()
    valid_modules = set(instance_mods) | {"members"}

    # Rôles extérieurs connus
    exterior_roles = {
        "salarie_designe",
        "rh",
        "itm",
        "police",
    }

    for role_key, modules in matrix.items():
        for module, level in modules.items():
            # Ignorer admin
            if role_key == "admin":
                continue

            # Module invalide
            if module not in valid_modules:
                raise HTTPException(
                    status_code=422,
                    detail=f"Module inconnu ou hors instance : {module}",
                )

            # Validation du niveau
            if level not in ("none", "read", "write"):
                raise HTTPException(
                    status_code=422,
                    detail=f"Niveau invalide : {level}",
                )

            # Règles dures pour les rôles extérieurs
            if role_key in exterior_roles:
                if level == "write":
                    raise HTTPException(
                        status_code=422,
                        detail=f"Le rôle {role_key} ne peut pas avoir write",
                    )
                if module in EXTERIOR_FORBIDDEN_MODULES and level != "none":
                    raise HTTPException(
                        status_code=422,
                        detail=f"Le module {module} est toujours none pour {role_key}",
                    )
                    # Ne pas appliquer

            # Appliquer en base
            existing = db.query(PermissionMatrix).filter(
                PermissionMatrix.organization_id == org_id,
                PermissionMatrix.role_key == role_key,
                PermissionMatrix.module == module,
            ).first()

            if existing:
                existing.level = level
            else:
                db.add(PermissionMatrix(
                    organization_id=org_id,
                    role_key=role_key,
                    module=module,
                    level=level,
                ))

    db.commit()

    # Retourner la nouvelle matrice effective
    return get_permissions(current_user, db)
