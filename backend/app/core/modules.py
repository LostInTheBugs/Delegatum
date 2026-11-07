"""Modules fonctionnels activables/désactivables par organisation.

Chaque module regroupe un ensemble de pages/routes. L'admin choisit ceux
qui sont actifs (GET/PUT /api/organization/modules). Les routes des modules
désactivés renvoient 403 (dépendance `require_module` dans deps.py) et la
navigation frontend masque les liens correspondants.

Convention : `enabled_modules` sur Organization = liste JSON de noms de
modules. `None` ou liste vide = TOUS les modules actifs (rétrocompatibilité).

Profil d'instance (SD_INSTANCE_PROFILE) :
- `dp` (défaut) : toutes les fonctionnalités de la DP.
- `sst` : délégué sécurité et santé seul.
- `egalite` : délégué à l'égalité seul.
- `sst,egalite` : les deux délégués seuls.
"""

# Modules optionnels (tout le reste du cœur — réunions, PV/coffre, membres,
# invitations, dashboard — reste toujours actif).
ALL_MODULES: list[str] = [
    "elections",          # Élections L.413
    "time_tracking",      # Mes heures
    "notices",            # Tableau d'affichage L.414-16
    "compliance",         # Cockpit conformité
    "consultations",      # Consultations L.414-3
    "workforce_stats",    # Stats semestrielles L.414-3 + rapport annuel
    "delegate_activities",# Activités délégués désignés
    "legal",              # Formation L.415-9, protection
    "safety_register",    # Registre sécurité-santé (sorti de legal)
    "meetings",           # Réunions + PV + coffre + archive + liens de partage
    "contact",            # Page contact DP
]

# Profils d'instance : quels modules sont disponibles pour chaque profil
PROFILE_MODULES: dict[str, set[str]] = {
    "dp": set(ALL_MODULES),
    "sst": {"time_tracking", "delegate_activities", "legal", "safety_register"},
    "egalite": {"time_tracking", "delegate_activities", "legal"},
    "egalite,sst": {"time_tracking", "delegate_activities", "legal", "safety_register"},
}

# Domaines de délégués disponibles pour chaque profil
PROFILE_DOMAINS: dict[str, set[str]] = {
    "dp": {"securite_sante", "egalite"},
    "sst": {"securite_sante"},
    "egalite": {"egalite"},
    "egalite,sst": {"securite_sante", "egalite"},
}


def _parse_profile(raw: str) -> str:
    """Normaliser le profil : enlever espaces, trier les valeurs."""
    parts = [p for p in raw.replace(" ", "").split(",") if p]
    parts.sort()
    return ",".join(parts)


def instance_modules() -> set[str]:
    """Modules disponibles pour le profil d'instance courant."""
    from app.core.config import get_settings
    raw = get_settings().instance_profile
    key = _parse_profile(raw)
    result = PROFILE_MODULES.get(key)
    if result is None:
        raise ValueError(
            f"Profil d'instance inconnu : « {raw} » (normalisé : « {key} »). "
            f"Valeurs acceptées : {', '.join(sorted(PROFILE_MODULES))}"
        )
    return result


def instance_domains() -> set[str]:
    """Domaines de délégués disponibles pour le profil d'instance courant."""
    from app.core.config import get_settings
    raw = get_settings().instance_profile
    key = _parse_profile(raw)
    result = PROFILE_DOMAINS.get(key)
    if result is None:
        raise ValueError(
            f"Profil d'instance inconnu : « {raw} » (normalisé : « {key} »). "
            f"Valeurs acceptées : {', '.join(sorted(PROFILE_DOMAINS))}"
        )
    return result


def enabled_modules_of(enabled_modules: str | list | None) -> set[str]:
    """Résout la liste effective des modules actifs d'une organisation.

    None / vide / liste invalide → tous les modules du profil (rétrocompatibilité).
    Sinon : intersection (modules de l'org) ∩ (modules du profil d'instance).
    """
    from app.core.config import get_settings

    instance_mods = instance_modules()

    if not enabled_modules:
        # Aucune restriction org → tous les modules du profil
        return instance_mods

    if isinstance(enabled_modules, list):
        org_mods = {m for m in enabled_modules if m in ALL_MODULES}
        return org_mods & instance_mods

    # stockage texte (JSON string) — migration avant normalisation
    import json
    try:
        data = json.loads(enabled_modules)
    except (ValueError, TypeError):
        return instance_mods

    if not isinstance(data, list):
        return instance_mods

    org_mods = {m for m in data if m in ALL_MODULES}
    return org_mods & instance_mods
