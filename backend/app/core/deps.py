from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.modules import enabled_modules_of
from app.core.permissions import effective_level, is_access_expired
from app.core.security import decode_access_token
from app.models import User, UserRole

security = HTTPBearer()

# Méthodes de lecture vs écriture pour la matrice RBAC
_READ_METHODS = {"GET", "HEAD", "OPTIONS"}
_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def require_module(module: str):
    """FastAPI dependency factory : 403 si le module est désactivé pour l'org.

    Usage : `router = APIRouter(..., dependencies=[Depends(require_module("elections"))])`
    ou `def route(user: User = Depends(require_module("time_tracking")))`.
    Le module désactivé rend TOUTES les routes du router inaccessibles (403).
    """

    def _check(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
        if not user.organization_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Module désactivé")
        from app.models import Organization
        org = db.query(Organization).filter(Organization.id == user.organization_id).first()
        if org is None or module not in enabled_modules_of(org.enabled_modules):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Module désactivé")
        return user

    return _check


def require_access(module: str):
    """Dépendance RBAC : module actif + niveau d'accès selon méthode HTTP.

    1. Vérifie que le module est activé pour l'organisation (403 « Module désactivé »).
    2. Détermine le niveau requis : GET/HEAD → « read », POST/PUT/PATCH/DELETE → « write ».
    3. Compare au niveau effectif de l'utilisateur via effective_level()
       (403 « Droits insuffisants » si insuffisant).
    """

    def _check(request: Request, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)) -> User:
        # 1. Module actif pour l'org (seulement si module dans ALL_MODULES)
        #    "members" est un module du cœur, toujours actif — saut du check
        if not user.organization_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Module désactivé")
        from app.core.modules import ALL_MODULES
        if module in ALL_MODULES:
            from app.models import Organization
            org = db.query(Organization).filter(Organization.id == user.organization_id).first()
            if org is None or module not in enabled_modules_of(org.enabled_modules):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Module désactivé")

        # 2. Niveau requis selon la méthode HTTP
        if request.method in _WRITE_METHODS:
            required = "write"
        else:
            required = "read"

        # 3. Comparaison avec le niveau effectif
        current = effective_level(user, module, db)
        level_order = {"none": 0, "read": 1, "write": 2}
        if level_order.get(current, 0) < level_order.get(required, 0):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Droits insuffisants")

        return user

    return _check


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Extract and validate the current user from the JWT Bearer token."""
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide")

    # Reject MFA-pending tokens — they must complete the MFA step first
    if payload.get("typ") != "access" or payload.get("mfa") is True:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur non trouvé")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Compte désactivé")

    # Vérification expiration d'accès (RBAC)
    if is_access_expired(user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Accès expiré",
        )

    # Révocation JWT (ANALYSE-2026-08-24 §7) :
    # 1. jti révoqué (logout ciblé) → 401 ;
    # 2. version de sécurité du compte dépassée (retrait de membre, compte
    #    compromis) → 401. Les jetons émis AVANT cette fonctionnalité
    #    (sans claim `ver`) sont traités comme ver=0 : une révocation les
    #    invalide immédiatement — comportement voulu.
    jti = payload.get("jti")
    if jti:
        from app.models.jwt_revocation import JwtRevocation

        revoked = db.query(JwtRevocation).filter(JwtRevocation.jti == jti).first()
        if revoked is not None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token révoqué")
    if payload.get("ver", 0) != (user.token_version or 0):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token révoqué")
    return user


def require_instance_admin(
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> User:
    """Exige un administrateur d'instance.

    Règles (dans l'ordre) :
    1. Si SD_INSTANCE_ADMIN_EMAILS est non vide → l'email de l'utilisateur
       doit y figurer (liste séparée par des virgules).
    2. Sinon → l'utilisateur doit être admin ET l'instance ne doit contenir
       qu'une seule organisation.
    3. Sinon → 403.
    """
    from app.core.config import get_settings
    from app.models.organization import Organization

    settings = get_settings()
    admin_emails = [e.strip() for e in (settings.instance_admin_emails or "").split(",") if e.strip()]

    if admin_emails:
        if user.email not in admin_emails:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrateur d'instance requis",
            )
        return user

    # Fallback : admin mono-org uniquement
    if user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrateur d'instance requis",
        )
    org_count = db.query(Organization).count()
    if org_count != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrateur d'instance requis",
        )
    return user
