# RGPD — Modèles pour votre délégation (Delegatum)

🇬🇧 [English](README.en.md) · 🇩🇪 [Deutsch](README.de.md) · 🇱🇺 [Lëtzebuergesch](README.lb.md)

> ⚠️ **Modèle, pas un conseil juridique.** À adapter à votre situation et à valider avec votre conseil, votre délégué à la protection des données (DPO) ou la [CNPD](https://cnpd.public.lu). Les durées suggérées sont des **recommandations par défaut**. Delegatum est fourni à titre expérimental (voir l'avertissement du README principal).

Une délégation du personnel traite des données de salariés sans avoir de service juridique — l'obligation RGPD s'applique pourtant dès le premier traitement. Ces modèles fournissent un point de départ concret.

## 1. Qui est responsable du traitement ?

- **L'éditeur de Delegatum ne traite aucune donnée** : l'outil n'est pas un service en ligne — pas de cloud, pas de télémétrie, aucune transmission vers l'extérieur.
- **Le responsable du traitement est votre organisation** (la délégation — le cas échéant avec l'employeur, selon qui héberge l'outil).
- Si l'outil tourne sur une infrastructure de l'employeur, l'administrateur technique peut accéder aux données stockées — **sauf le contenu des procès-verbaux**, chiffré dans le navigateur (le serveur ne voit jamais le clair). À documenter dans votre analyse de risque (voir le [modèle de menace](../../THREAT-MODEL.md)).

## 2. Registre des activités de traitement (art. 30) — modèle à adapter

| Finalité | Personnes | Données | Base légale (suggestion) | Conservation (recommandée) |
|---|---|---|---|---|
| Gestion des membres de la délégation | Membres, suppléants | Identité, coordonnées, photo, rôle, délibérations | Mission légale de la délégation (Code du travail L.412-1 s.) | Mandature + 5 ans |
| Suivi des heures de délégation | Membres | Heures, activités, exports CSV | Mission légale (L.415-5) | 5 ans |
| Réunions et procès-verbaux | Membres ; direction (sections partagées) | Présence, ordre du jour, PV | Mission légale (L.415-6 s.) | Mandature + 5 ans |
| Registre sécurité & santé | Délégué S&S, chefs de service (contreseing) | Constats, lieux, dates, suites (peut contenir des données de santé/incidents) | Mission légale (L.414-14) ; consultation ITM | Mandature + 5 ans (à valider) |
| Consultations de l'employeur | Membres | Avis, échanges, délais | Mission légale (L.414-3) | 5 ans |
| Élections | Salariés | Candidatures ; résultats agrégés (vote structurellement anonyme — aucun lien votant/choix) | Mission légale (L.413-1 s.) | Jusqu'à la fin des contestations + 5 ans |
| Tableau d'affichage virtuel | Tout le personnel | Communications de la délégation (lecture seule pour le personnel) | Intérêt légitime (information du personnel) | Mandature |
| Notifications par email | Membres, invités | Adresses, contenus (.eml/SMTP) | Mission légale / intérêt légitime | 12 mois |
| Journal de sécurité et sauvegardes | Utilisateurs | Journaux techniques, sauvegardes chiffrées | Intérêt légitime (sécurité) | 30 jours (rotation) |

## 3. Durées de conservation — repères pratiques

- **Principe** : ne pas conserver plus longtemps que nécessaire. Les données de la délégation s'alignent naturellement sur la **mandature**, plus un délai pour les litiges (recommandation : + 5 ans maximum).
- **Fin de mandature** : exporter ce qui doit être transmis, puis **purger** ce qui n'a plus de base légale — une donnée sans utilité ni obligation doit disparaître.
- **Sauvegardes** : rotation courte (30 jours), support chiffré, hors du poste. Une sauvegarde oubliée est une violation potentielle.
- **Registre S&S** : c'est un registre légal — sa conservation doit être validée avec votre conseil/l'ITM (recommandation par défaut : mandature + 5 ans).

## 4. AIPD (art. 35) — faut-il en faire une ?

**Screening rapide** (documentez vos réponses, cette page peut servir de trace) :

- traitement **à grande échelle** ? — une délégation = petite échelle ;
- **données de santé** ? — possibles via le registre S&S, mais pas à grande échelle ni à des fins de soins ;
- **suivi systématique** de personnes ? — non (pas de profilage) ;
- **personnes vulnérables**, croisement de données, décisions automatisées ? — non.

→ Pour une délégation typique, une AIPD n'est **généralement pas requise**. Si votre situation cumule plusieurs critères (ou en cas de doute), une trame simplifiée :

1. **Description** du traitement et de sa nécessité (finalités, données, flux, personnes) ;
2. **Proportionnalité** (base légale, minimisation, durées) ;
3. **Risques** pour les personnes (accès non autorisé, divulgation, perte) ;
4. **Mesures** : chiffrement des PV, intégrité du registre, contrôle d'accès, sauvegardes ;
5. **Avis** du DPO/conseil, date, révision.

## 5. Ce que l'outil fait pour protéger les données

- **Procès-verbaux chiffrés côté navigateur** (AES-256-GCM) : le serveur ne détient jamais le clair ni le mot de passe du coffre. Conservez la **clé de récupération** hors ligne (coffre/coffret).
- **Registre S&S** : intégrité chaînée (SHA-256) + **sceaux RFC 3161**. Conservez les **emails de scellement hors du serveur** (boîte du bureau) et exportez régulièrement le dossier ITM. La protection contre une altération dépend de ces copies externes.
- **Aucun transfert** de données vers l'éditeur de l'outil.
- Recommandations d'exploitation : HTTPS, comptes nominatifs, MFA pour les administrateurs, sauvegardes chiffrées, postes verrouillés.

## 6. En cas de violation de données (art. 33-34)

1. **Qualifier et documenter** (fiche d'incident : date, nature, données et personnes concernées, conséquences, mesures prises).
2. **Notifier l'autorité** — au Luxembourg, la **CNPD** — sous **72 h** si un risque existe pour les personnes ; informer les personnes concernées si le risque est élevé.
3. **Exemples de causes** : accès non autorisé, perte d'un PC (version bureau), sauvegarde égarée, email envoyé au mauvais destinataire.
4. À noter : le **contenu des PV étant chiffré**, son exposition n'est pas automatiquement une violation à risque élevé — mais la perte des clés, elle, l'est.

## Ressources

- CNPD — https://cnpd.public.lu · Guichet.lu — fiches RGPD
- [THREAT-MODEL.md](../../THREAT-MODEL.md) — limites techniques documentées de l'outil
- [SECURITY.md](../../SECURITY.md) — signaler un problème de sécurité
