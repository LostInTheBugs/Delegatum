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

- `SD_INSTANCE_PROFILE` : profil d'instance — restreint les modules disponibles (`dp` = tous, `sst`, `egalite`, ou `egalite,sst`). Défaut : `dp`.
- `SD_INSTANCE_ADMIN_EMAILS` : liste d'adresses e-mail séparées par des virgules autorisées comme administrateurs d'instance (voir Mises à jour) ; laissez vide pour le fallback admin mono-organisation.
- `SD_UPDATE_NO_BUILD` : `1` sur les petits serveurs pour refuser la reconstruction des images Docker — déployez des images construites ailleurs. Défaut : `0`.
- `SD_UPDATE_LOOP` : `0` pour désactiver la boucle de vérification en arrière-plan (le bouton 🔎 Vérifier de l'admin fonctionne toujours). Défaut : `1`.

## Mises à jour

Le module d'auto-mise-à jour permet au serveur d'appliquer automatiquement les nouvelles versions : le service vérifie les releases GitHub à la cadence configurée, dépose une demande de mise-à-jour, et un service systemd sur l'hôte tire le tarball, reconstruit les images, lance Alembic et redémarre les conteneurs. L'application ne touche **jamais** à Docker — une barrière de sécurité volontaire.

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
