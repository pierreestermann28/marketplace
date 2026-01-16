# V1.1 Audit

## Objectif
Cartographier l’existant par rapport aux besoins de la V1.1 afin d’identifier les zones à compléter (à faire) ou à remettre à plat (refactor). Ce document couvre les modèles, les endpoints clés, les droits et l’infrastructure.

## 1. Modèles

| Modèle | Existant | À faire pour V1.1 | Refactor / Attention |
| --- | --- | --- | --- |
| `mediahub.BatchUpload` | Stocke le propriétaire, le statut (pending/running/done/failed), les compteurs, méthodes `mark_*`, et expose désormais `processed_count`/progress. | Ajouter des champs de validation (IA), verrou de traitement + notifications des erreurs, meilleure visibilité sur les fichiers rejetés ; la torsion `processing_status` (HTMX + bouton retry) garantit un monitoring fiable. | Le mixin `BatchOwnerMixin` centralise l’accès, mais on pourrait grouper les `detected_items` par lot + état pour réduire les `count`. |
| `mediahub.MediaAsset` | Lie chaque upload d’image à son lot, conserve les métadonnées/empreinte. | Gérer les videos & keyframes comme ressources first-class (actuellement commentées), indexer les hashes pour éviter les doublons et réutiliser les analyses déjà faites. | Unifier les métadonnées JSON, documenter `source`. |
| `ingestion.DetectedItem` | Status évoluent de PENDING -> USER_* -> ADMIN_* -> EDITED, stocke IA (title, description, category), metadata JSON, lien listing. | Réutiliser les suggestions via le hash SHA-256 des `MediaAsset`, limiter la création de nouveaux items IA gratuits (limite mensuelle). | Peut-être séparer `confidence`/`price` en objet, ajouter event logging pour audit. |
| `listings.Listing` | Statuts, vues, réservations, vues, favoris, search alert, réservation/réservé/reservation accepted, contacts. | Documenter `available_from`/`view_count`, consolider `ListingReminder`/`SearchAlert`, ajouter “public status” (AVAILABLE/RESERVED/SOLD/ARCHIVED) pour gouverner la visibilité, et fournir actions vendeur (Mark Sold, Archive, Unarchive). | Certains champs (AI summary, source_type) sont déjà prêts pour V1.1 ; surveiller les triggers `refresh_reservation_state`. |
| `messaging.Conversation` & `Message` | Convo en lien listing, message simple text/attachment, HTMX-friendly. | Ajouter signal pour blocages anti-spam (déjà en place), générer log d’acceptation pour stats. | Possibilité de transformer `Message` en thread + tags (spam détecté). |
| `accounts.UserEntitlement` | Nouvelle source de vérité pour `is_premium` + quotas (listings/détection) ; créée à la volée à la création d’un utilisateur. | Normaliser `can_publish_listing`/`can_generate_detected_items`, permettre d’étendre les quotas premium et injecter la durée d’abonnement. | Prévoir un connecteur Stripe (webhook) pour mettre `is_premium` à jour depuis les abonnements. |
| `Subscription` | **Non implémenté**. | Créer un modèle (user + plan + statut + next_billing) si on veut ajouter un “subscribe” service plus tard. | Bloqueurs : définir stratégie pricing/tiers avant implémentation. |

## 2. Endpoints / Processus

| Endpoint | Vue / Route | Existant | À faire / Notes |
| --- | --- | --- | --- |
| `POST /batches/create/` | `BatchUploadCreateView` | Upload de plusieurs fichiers, création `BatchUpload`, `ImageAsset` et `MediaAsset`, déclenchement `analyze_batch` celery. | Ajouter feedback UX (état d’analyse) et validation des formats “V1.1 ready”. |
| `GET /batches/<uuid>/processing/` | `BatchProcessingView` (+fragment) | Vue du statut + compteurs (pending/traité) avec HTMX : progression, message d’état et bouton de relance. | Maintenir la file HTMX/partial (auto actualisation, retry) et enrichir le monitoring (erreurs, blocage). |
| `GET /batches/<uuid>/swipe/` & `POST /items/<int>/approve|reject/` | `BatchSwipeView`, `BatchOwnerMixin`, `DetectedItemActionMixin` | Propriétaire seul, pagination + fragment, statuts USER_APPROVED/REJECTED. | Introduire `bulk-approve`, signaler items bloqués, ajouter logs. |
| `/batches/admin/swipe/` & fragments | `AdminSwipeView` + `DetectedItemAdminActionMixin` | Équipe staff peut approuver une fois que le vendeur a approuvé; `publish_detected_item` crée Listing. | Documenter workflow (stack `publish_detected_item`), ajouter tests de charge / quotas. |
| `/` (feed) | `HomeFeedView` | Filtre `Listing` strict sur le statut `PUBLISHED` avec pagination + HTMX partial ; badges “Disponible/Réservée” indiquent la disponibilité réelle. | Optimiser les annotations (seen/favoris) et documenter la nouvelle OLAP du badge statuts. |
| `/items/<slug>-<uuid>/` | `ListingDetailView` | Détail, `increment_view_count`, contact/médiation, seller info. | Maintenir slug canonique, car metadata SEO. Ajouter “coordonnées débloquées” et CTA “Contacter”. |
| `/messages/start/<uuid>/`, `/messages/<pk>/` | `ConversationStartView`, `ConversationDetailView` | Démarrage/détail de conversation (HTMX). Validation anti-spam/rate limit. | Ajouter journaux d’erreur, notifier admin en cas d’abus, prévoir webhooks. |
| `/messages/reserve/<pk>/` | `SellerReservationCreateView` | Permet au vendeur de placer une annonce en statut `RESERVED` pour l’acheteur d’une conversation (note, log, date). | S’assurer que les annulations posent la réservation à `AVAILABLE` et que les notifications sont visibles pour l’acheteur. |
| `/my/listings/` | `MyListingsView` | Tableau de bord vendeur listant toutes les annonces avec comptes par statut. | Ajouter des filtres “Disponibles/Réservées/Vendues/Archivées” et des actions rapides (Marquer vendue, Archiver, Désactiver la réservation) par ligne. |

## 3. Permissions

- **Owner-only swipe** : `BatchOwnerMixin` / `DetectedItemActionMixin` restreint `batch` aux uploads du `request.user`; usages admin utilisent `UserPassesTestMixin`.
- **Admin swipe** et approbations (`DetectedItemAdminApproveView/RejectView`) exigent `is_staff`.
- **Feed** : `HomeFeedView` ne montre que les statuts `PUBLISHED`, `RESERVED`, `RESERVATION_ACCEPTED` (flag `status_filter` à 3 états). Les autres statuts (draft/rejected) sont exclus, la pagination REST est publique.
- **Listing detail / contact** : seules les annonces `PUBLISHED|RESERVED|RESERVATION_ACCEPTED` sont accessibles. Les coordonnées sont verrouillées jusqu’à réservation ou paiement (`user_can_view_contact_info`).

## 4. Settings / Infrastructure

- Docker Compose (`docker-compose.yml`) orchestre : PostgreSQL 16, Redis 7, service `web` Django/HTMX, worker Celery, worker `flower`, loader `tailwind:watch`.
- Celery utilise `redis` en backend (via `.env` non exposé ici) et la commande `celery -A stillusefull worker --pool=solo`.
- `tailwind` service lance `npm run tailwind:watch`, liant les volumes `.:/app` + `/app/node_modules`.
- `docker/entrypoint.sh` assure un bootstrap commun (migrations/collectstatic). À valider pour V1.1 : mettre en place des seeders, ajouter healthchecks (web?). Déjà en place pour postgres/redis.

## 5. Tickets bloquants

1. **Canonical slug fail** : certaines URLs sans slug (ex `items/<id>/`) provoquent 404; besoin d’un redirect canonique.  
2. **Subscription model** : aucun dispositif ne suit les abonnements. Ajouter le modèle + vues avant d’activer un plan payant.  
3. **Messaging contact gating** : coordonnés + spams doivent être rejoints dès qu’on passe en production (v1.1). Validation déjà partiellement en place, mais il faut plus d’alertes.  
4. **Sitemap + SEO** : s’assurer que toutes les routes clés entrent dans `sitemap.xml` (ajout des pages catégories/villes + listings).  

Ce document peut servir de base pour découper les tickets V1.1. Besoin d’infos sur des sous-processus spécifiques ? On peut enchaîner une analyse plus détaillée (ex : `publish_detected_item`).
