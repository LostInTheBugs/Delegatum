# Delegatum — Gestion de votre délégation du personnel

🇬🇧 English version : [README.md](README.md) · 🇩🇪 [README.de.md](README.de.md) · 🇱🇺 [README.lb.md](README.lb.md)

Outil de gestion pour les **délégations du personnel** au Luxembourg (Code du travail, art. L.412-1 s.), conçu pour que les données ne quittent jamais votre organisation.

- 🔐 **Vos données restent chez vous** : auto-hébergé (Docker) ou **application de bureau** Windows/macOS — pas de cloud, pas de compte en ligne, pas de télémétrie.
- 🛡️ **Registre sécurité/santé** (L.414-14) : constats contresignés par le chef de service, **journal d'intégrité chaîné** (annulation motivée, jamais de suppression), **dossier ITM** (PDF imprimable + dossier d'intégrité JSON + CSV), **sceaux horodatés (RFC 3161)** et page de vérification publique — pensé pour l'inspection du travail.
- 🔏 **Procès-verbaux chiffrés dans votre navigateur** (AES-256-GCM) : le serveur ne voit jamais le clair ; coffre protégé par mot de passe et clé de récupération.
- 👥 Réunions et PV, heures de délégation (L.415-5), consultations (L.414-3), statistiques, élections (vote structurellement anonyme), tableau d'affichage, rapport annuel PDF.
- 🌍 Interface en 5 langues : **FR / EN / DE / PT / LB**.

## Essayer, installer

- 🎮 **Démo** : https://delegatum.cloudfr.net — comptes de test dans le [README](README.md#demo)
- 🖥️ **Application de bureau** : [dernières releases](https://github.com/LostInTheBugs/Delegatum/releases) (zips Windows/macOS ; guides d'utilisation FR/EN/DE/LB inclus)
- 🐳 **Auto-hébergé** : `docker compose up -d --build` puis `bash seed.sh` (détails dans le [README](README.md))

## Configuration

| Variable | Description | Défaut |
|----------|-------------|--------|
| `SD_PORT` | Port d'écoute du backend | `8005` |
| `SD_SECRET_KEY` | Clé de signature JWT — **requise** (l'app refuse de démarrer avec une valeur par défaut ou une clé < 32 caractères) | — |
| `SD_DATABASE_URL` | URL de la base (SQLite par défaut, PostgreSQL supporté) | `sqlite:///./data/staff_delegation.db` |
| `SD_INSTANCE_PROFILE` | Profil d'instance — restreint les modules disponibles (`dp` = tous, `sst`, `egalite`, `sst,egalite`) | `dp` |
| `SD_ACCESS_TOKEN_EXPIRE_MINUTES` | Durée de vie des tokens JWT | `1440` (24h) |
| `SD_INSTANCE_ADMIN_EMAILS` | Adresses e-mail des administrateurs d'instance (voir Mises à jour) ; vide = fallback admin mono-organisation | — |
| `SD_UPDATE_NO_BUILD` | `1` sur les petits serveurs pour refuser la reconstruction des images Docker | `0` |
| `SD_UPDATE_LOOP` | `0` pour désactiver la boucle de vérification en arrière-plan (le bouton 🔎 Vérifier fonctionne toujours) | `1` |

## Profil d'instance

`SD_INSTANCE_PROFILE` restreint les modules disponibles au démarrage (l'app refuse de démarrer avec une valeur invalide). Valeurs valides :

| Profil | Modules disponibles |
|--------|---------------------|
| `dp` (défaut) | Tous les modules — ensemble complet des fonctionnalités DP |
| `sst` | Tableau de bord, activités du domaine (sécurité/santé uniquement), heures, formation/protection, registre S&S (si `sst`) |
| `egalite` | Tableau de bord, activités du domaine (égalité uniquement), heures, formation/protection |
| `sst,egalite` | Tableau de bord, activités des deux domaines, heures, formation/protection, registre S&S (si `sst`) |

En profil délégué seul (`sst`, `egalite` ou `sst,egalite`), les modules suivants sont masqués : réunions/PV/coffre/archive, élections, consultations, statistiques, affichage, conformité, contact. Les fonctionnalités restantes sont : tableau de bord, activités du ou des domaines du profil, heures, formation/protection, et registre S&S (uniquement si `sst`).

## Mises à jour

Le module d'auto-mise-à-jour permet au serveur d'appliquer automatiquement les nouvelles versions : le service vérifie les releases GitHub à la cadence configurée, dépose une demande de mise-à-jour, et un service systemd sur l'hôte tire le tarball, reconstruit les images, lance Alembic et redémarre les conteneurs. L'application ne touche **jamais** à Docker — une barrière de sécurité volontaire.

- **Accès** : seuls les administrateurs d'instance peuvent demander/appliquer (liste `SD_INSTANCE_ADMIN_EMAILS` ou admin mono-organisation).
- **Sauvegarde** : avant chaque mise-à-jour, copie automatique de la base `.db` en `*.db.pre-<version>` ; 3 dernières conservées.
- **Garde no-build** : `SD_UPDATE_NO_BUILD=1` refuse la construction d'images sur petits serveurs.
- **Installation** : copiez `deploy/delegatum-update.service` et `.timer` dans `/etc/systemd/system/`, éditez `WorkingDirectory` et `User`, puis `systemctl enable --now delegatum-update.timer`.

## Documentation

- Guides détaillés (FR/DE/LB/EN) : https://cloudfr.net/docs/delegatum/
- RGPD : modèles fournis avec l'outil — [`docs/gdpr/`](docs/gdpr/README.fr.md)
- Sécurité : [SECURITY.md](SECURITY.md) · Modèle de menace : [THREAT-MODEL.md](THREAT-MODEL.md)

⚠️ Application expérimentale — fournie à titre de démonstration, ne constitue pas un conseil juridique et n'est pas garantie conforme à la législation luxembourgeoise. Pour toute question de droit du travail, consultez un professionnel qualifié ou la [Chambre des Salariés (CSL)](https://www.csl.lu).

Licence MIT — code source : github.com/LostInTheBugs/Delegatum
