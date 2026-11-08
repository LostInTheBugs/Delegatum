"""Calcul des droits basés sur les rôles et la matrice rôles × modules.

Modèles légaux :
- `delegation` : délégué, bureau, président, DSS, DEG, salarié désigné
- `salarie_designe` : salarié désigné pour activités déléguées
- `rh` : service ressources humaines
- `itm` : inspecteur du travail et de la sécurité
- `police` : forces de police

Règles légales (durcies) :
- Les rôles extérieurs ne peuvent jamais obtenir `write`.
- Le module `meetings` est toujours `none` pour les rôles extérieurs.
- `admin` est toujours `write` et ne figure pas dans la matrice.
"""

import enum
from datetime import datetime, timezone
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.modules import ALL_MODULES, instance_modules
from app.models.user import AccountType


# ── Niveaux d'accès ────────────────────────────────────────────────


class AccessLevel(str, enum.Enum):
    none = "none"
    read = "read"
    write = "write"


# ── Valeurs par défaut adaptatives selon le profil d'instance ───────

# Tous les rôles de délégation ont write partout (comportement dp actuel).
# Les contrôles fins existants dans les routes continuent de limiter.
# `members` est ajouté à tous les rôles internes : sans lui l'organigramme
# serait inaccessible aux non-admins (règle R2).
_INTERNAL_WRITE_MODULES = set(ALL_MODULES) | {"members"}


def _internal_write_modules() -> dict[str, str]:
    return {m: AccessLevel.write.value for m in _INTERNAL_WRITE_MODULES}


def _exterior_defaults() -> dict[str, dict[str, str]]:
    """Permissions pour les rôles extérieurs (inchangées)."""
    return {
        # Salarié désigné : lecture sécurité + activités
        "salarie_designe": {
            "safety_register": AccessLevel.read.value,
            "delegate_activities": AccessLevel.read.value,
        },
        # RH : lecture sécurité + activités + stats
        "rh": {
            "safety_register": AccessLevel.read.value,
            "delegate_activities": AccessLevel.read.value,
            "workforce_stats": AccessLevel.read.value,
        },
        # ITM : lecture sécurité + conformité + activités
        "itm": {
            "safety_register": AccessLevel.read.value,
            "compliance": AccessLevel.read.value,
            "delegate_activities": AccessLevel.read.value,
        },
        # Police : lecture sécurité uniquement
        "police": {
            "safety_register": AccessLevel.read.value,
        },
    }


def default_permissions(instance_profile: str = "dp") -> dict[str, dict[str, str]]:
    """Retourne la matrice de permissions selon le profil d'instance.

    En `dp` : write partout pour les rôles internes (comportement actuel).
    En profil délégué : les rôles internes n'ont que `read` (+ `members`),
    `dss`/`deg` conservent `write` dans leur domaine respectif.
    """
    parsed = {p.strip() for p in instance_profile.split(",")} if instance_profile else {"dp"}

    if instance_profile == "dp":
        # Comportement classique : write partout pour les internes
        return {
            "delegue": _internal_write_modules(),
            "bureau": _internal_write_modules(),
            "president": _internal_write_modules(),
            "dss": _internal_write_modules(),
            "deg": _internal_write_modules(),
            "salarie": _internal_write_modules(),
            **_exterior_defaults(),
        }

    # Profil délégué : lecture seule pour les internes
    internal_read = {m: AccessLevel.read.value for m in _INTERNAL_WRITE_MODULES}
    result: dict[str, dict[str, str]] = {
        "delegue": internal_read.copy(),
        "bureau": internal_read.copy(),
        "president": internal_read.copy(),
        "salarie": internal_read.copy(),
    }

    # DSS : write si sst dans le profil
    if "sst" in parsed:
        result["dss"] = _internal_write_modules()

    # DEG : write si egalite dans le profil
    if "egalite" in parsed:
        result["deg"] = _internal_write_modules()

    result.update(_exterior_defaults())
    return result


# Alias pour la rétro-compatibilité (tests qui importent DEFAULT_PERMISSIONS)
DEFAULT_PERMISSIONS = default_permissions("dp")

# Modules toujours `none` pour les rôles extérieurs (règle dure)
EXTERIOR_FORBIDDEN_MODULES = {"meetings"}
# Niveau max pour les rôles extérieurs
EXTERIOR_MAX_LEVEL = AccessLevel.read


# ── Vérification d'expiration ────────────────────────────────────────


def is_access_expired(user) -> bool:
    """Retourne True si l'accès de l'utilisateur est expiré.

    Traite les deux formats de datetime stockés en base :
    - naïf (pas de fuseau) → interprété comme UTC.
    - fuseau (timezone-aware) → comparaison directe en UTC.
    """
    expires = getattr(user, "access_expires_at", None)
    if expires is None:
        return False
    now = datetime.now(timezone.utc)
    # Si la date est naïve, l'interpréter comme UTC
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires <= now


# ── Clés de rôle ───────────────────────────────────────────────────

def role_keys(user) -> set[str]:
    """Retourne l'ensemble des clés de rôle d'un utilisateur.

    Règles :
    - Comptes `delegation` : `delegue` (toujours), `bureau` si président/
      vice-président/secrétaire, `president` si président, `dss` si DSS,
      `deg` si DE, `salarie` si employé.
    - Comptes extérieurs : uniquement leur `account_type`.
    - `admin` en plus si `role == admin`.
    """
    keys: set[str] = set()
    role = getattr(user, "role", None)

    if user.account_type == AccountType.delegation:
        keys.add("delegue")
        # Bureau
        delegue_role = getattr(user, "delegue_role", None)
        if delegue_role in ("president", "vice_president", "secretaire"):
            keys.add("bureau")
        # Président
        if delegue_role == "president":
            keys.add("president")
        # DSS
        if getattr(user, "is_delegue_securite_sante", False):
            keys.add("dss")
        # DE
        if getattr(user, "is_delegue_egalite", False):
            keys.add("deg")
        # Salarié (employé)
        if getattr(user, "delegue_status", None) == "employe":
            keys.add("salarie")
    else:
        # Comptes extérieurs : leur account_type est la clé
        keys.add(user.account_type.value)

    if role == "admin":
        keys.add("admin")

    return keys


# ── Matrice de permissions ─────────────────────────────────────────


class PermissionMatrix(Base):
    """Matrice rôles × modules : niveau d'accès par org/role/module.

    unique constraint sur (organization_id, role_key, module).
    """
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    role_key = Column(String(50), nullable=False)
    module = Column(String(50), nullable=False)
    level = Column(String(10), nullable=False, default=AccessLevel.none.value)

    __table_args__ = (
        sa.UniqueConstraint("organization_id", "role_key", "module", name="uq_role_permission"),
    )

    def __repr__(self):
        return f"<PermissionMatrix org={self.organization_id} role={self.role_key} module={self.module} level={self.level}>"


# ── Niveau effectif ────────────────────────────────────────────────

def effective_level(user, module: str, db: Session) -> str:
    """Retourne le niveau d'accès effectif pour cet utilisateur sur ce module.

    Règles :
    - `admin` → toujours `write` (non modifiable).
    - Pour chaque clé de rôle : max (base > DEFAULT > none).
    - Rôles extérieurs : max = `read`, et `meetings` = toujours `none`.
    """
    role = getattr(user, "role", None)
    is_admin = role == "admin"

    if is_admin:
        return AccessLevel.write.value

    keys = role_keys(user)
    org_id = getattr(user, "organization_id", None)
    if org_id is None:
        return AccessLevel.none.value

    instance_mods = instance_modules()
    if module not in instance_mods and module != "members":
        return AccessLevel.none.value

    # Rôle extérieur : durcir le maximum
    is_exterior = user.account_type != AccountType.delegation

    best = AccessLevel.none
    for key in keys:
        # admin ne peut pas être modifié via la matrice
        if key == "admin":
            continue

        # Vérifier en base d'abord
        row = db.query(PermissionMatrix).filter(
            PermissionMatrix.organization_id == org_id,
            PermissionMatrix.role_key == key,
            PermissionMatrix.module == module,
        ).first()

        if row:
            level = AccessLevel(row.level)
            if level.value == AccessLevel.write.value:
                best = AccessLevel.write
            elif level.value == AccessLevel.read.value and best.value != AccessLevel.write.value:
                best = AccessLevel.read
        else:
            # Fallback sur les défauts (adaptatif selon profil d'instance)
            from app.core.config import get_settings
            try:
                settings = get_settings()
                org_profile = settings.instance_profile
            except RuntimeError:
                org_profile = "dp"
            defaults = default_permissions(org_profile).get(key, {})
            if module in defaults:
                level = AccessLevel(defaults[module])
                if level.value == AccessLevel.write.value:
                    best = AccessLevel.write
                elif level.value == AccessLevel.read.value and best.value != AccessLevel.write.value:
                    best = AccessLevel.read

    # Règles dures pour les rôles extérieurs
    if is_exterior:
        if best.value == AccessLevel.write.value:
            best = AccessLevel.read
        if module in EXTERIOR_FORBIDDEN_MODULES:
            best = AccessLevel.none

    return best.value


# ── Initialisation des valeurs par défaut ──────────────────────────

def init_default_permissions(org_id: int, db: Session) -> None:
    """Insère les permissions par défaut pour chaque (role_key, module)."""
    instance_mods = instance_modules()
    modules_to_use = set(instance_mods) | {"members"}

    from app.core.config import get_settings
    try:
        settings = get_settings()
        org_profile = settings.instance_profile
    except RuntimeError:
        org_profile = "dp"

    for role_key, modules in default_permissions(org_profile).items():
        for module in modules_to_use:
            existing = db.query(PermissionMatrix).filter(
                PermissionMatrix.organization_id == org_id,
                PermissionMatrix.role_key == role_key,
                PermissionMatrix.module == module,
            ).first()
            if existing is None:
                level = modules.get(module, AccessLevel.none.value)
                db.add(PermissionMatrix(
                    organization_id=org_id,
                    role_key=role_key,
                    module=module,
                    level=level,
                ))
    db.commit()
