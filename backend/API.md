# NexFleet — API REST

Base URL : `http://127.0.0.1:5000/api` — format des réponses : JSON (UTF-8).
Serveur de production : waitress (voir `wsgi.py` et `run.bat`).

## Authentification

La plupart des routes exigent l'en-tête :

```
Authorization: Bearer <token>
```

- `POST /api/auth/register` — créer un compte. Le **premier** compte devient `admin`, les suivants `user`.
- `POST /api/auth/login` — `{ "username" | "email", "password" }` → `{ token, user }` (valide 7 jours).
- `GET /api/auth/me` — profil courant → `{ user: { id, username, email, role, created_at } }`.
- `PUT /api/auth/password` — `{ old_password, new_password }`.

Rôles : `admin` peut tout faire ; `user` ne peut pas gérer les utilisateurs, les paramètres, la sauvegarde ni les données de démo (`403` sinon).

Règles de mot de passe : 8 caractères minimum dont au moins un chiffre.

## Format d'erreur

Toute erreur renvoie un statut HTTP ≠ 2xx avec `{ "error": "message" }`.

---

## Véhicules

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/api/vehicles` | Liste. Filtres : `search`, `statut`, `carburant`, `site` (affectation). |
| `POST` | `/api/vehicles` | Créer. `immatriculation`, `marque`, `modele` requis ; `annee` 1970–2100 ; dates `AAAA-MM-JJ`. |
| `PUT` | `/api/vehicles/<id>` | Mettre à jour (champs de création tous envoyés). |
| `DELETE` | `/api/vehicles/<id>` | Supprimer (admin). Supprime aussi fichiers associés. |
| `GET` | `/api/vehicles/<id>/detail` | Détail + 10 derniers contrôles + 10 dernières maintenances. |
| `GET` | `/api/vehicles/<id>/pdf` | Fiche véhicule PDF. |

Champs d'un véhicule : `id, immatriculation, marque, modele, annee, type, carburant, kilometrage, vignette_exp, assurance_exp, ctrl_tech_exp, statut, affectation, photo, photo_thumb, created_at, alerts[]`.

### Photos (upload optimisé)

| Méthode | Route | Description |
|---|---|---|
| `POST` | `/api/vehicles/<id>/photo` | Multipart `photo` (image, 5 Mo max). Enregistre l'original **et** une miniature JPEG 320 px (`photo_thumb`, générée par Pillow). Réponse : `{ ok, photo, photo_thumb }`. |
| `DELETE` | `/api/vehicles/<id>/photo` | Supprime photo + miniature. |

> `photo_thumb` doit être utilisée par le frontend pour l'affichage des listes (`vehicleThumb`), l'original ne servant qu'à l'agrandissement.

### Documents

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/api/vehicles/<id>/documents` | Liste des documents. |
| `POST` | `/api/vehicles/<id>/documents` | Multipart `file` + optionnel `label` (10 Mo max ; pdf, images, office). |
| `DELETE` | `/api/documents/<id>` | Supprimer un document. |

### Relevés kilométriques

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/api/vehicles/<id>/odometer` | Historique des relevés. |
| `POST` | `/api/vehicles/<id>/odometer` | `{ kilometres, date?, note? }` |
| `DELETE` | `/api/odometer/<id>` | Supprimer un relevé. |

---

## Contrôles techniques

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/api/controls` | Liste globale (tri date DESC). |
| `GET` | `/api/controls/vehicle/<vid>` | Contrôles d'un véhicule. |
| `POST` | `/api/controls` | `{ vehicle_id, driver_id?, date?, type?, resultat?, notes?, items? }` (`resultat` par défaut `En cours`). |
| `PUT` | `/api/controls/<id>` | Mise à jour (envoyer `vehicle_id`). |
| `DELETE` | `/api/controls/<id>` | Supprimer. |

## Maintenance

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/api/maintenance` | Liste (avec `immatriculation`, `marque`, `modele`). |
| `POST` | `/api/maintenance` | `{ vehicle_id, type?, date?, cout?, garage?, notes? }` |
| `PUT` | `/api/maintenance/<id>` | Mise à jour (envoyer `vehicle_id`). |
| `DELETE` | `/api/maintenance/<id>` | Supprimer. |
| `GET` | `/api/maintenance/forecast` | Prochaines échéances calculées (km + délai par type). |

## Vidanges

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/api/vidanges` | Liste (avec `immatriculation`, `marque`, `modele`), filtre `?vehicle_id=`. |
| `POST` | `/api/vidanges` | `{ vehicle_id, date?, km?, huile?, quantite?, filtre?, cout?, garage?, notes?, prochaine_km? }` |
| `PUT` | `/api/vidanges/<id>` | Mise à jour (envoyer `vehicle_id`). |
| `DELETE` | `/api/vidanges/<id>` | Supprimer. |
| `GET` | `/api/vidanges/stats` | Total, coût cumulé, par véhicule, prévisions (`forecast` : prochaine vidange par véhicule, `due`). |
| `GET` | `/api/vidanges/pdf` | Rapport PDF (synthèse, coût par véhicule, détail). |

## Pneumatiques

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/api/vehicles/<vid>/tires` | Pneus du véhicule. |
| `POST` | `/api/vehicles/<vid>/tires` | `{ position, marque?, taille?, etat?, date_montage?, date_remplacement?, note? }` |
| `PUT` | `/api/tires/<id>` | Mise à jour. |
| `DELETE` | `/api/tires/<id>` | Supprimer. |

## Conducteurs

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/api/drivers` | Liste. |
| `POST` | `/api/drivers` | `{ nom, prenom, matricule?, email?, telephone?, permis?, permis_exp? }` |
| `PUT` | `/api/drivers/<id>` | Mise à jour (`nom`/`prenom` requis). |
| `DELETE` | `/api/drivers/<id>` | Supprimer. |

---

## Tableau de bord & suivi

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/api/stats` | Totaux (parc, statuts, conducteurs, contrôles), répartition carburant/marques/sites, `controls_by_month` (6 mois), `alerts`, coûts maintenance, `vidanges_total/count/year`. |
| `GET` | `/api/calendar/events` | Événements échéances (assurance, vignette, CT, permis) + vidanges. |
| `GET` | `/api/notifications` | Alertes échéances + 8 derniers événements d'audit. |
| `GET` | `/api/audit` | Journal d'activité. |

## Paramètres

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/api/settings` | `{ alert_threshold, forecast_km, vidange_alert_km }` |
| `PUT` | `/api/settings` | Admin. `{ alert_threshold (1–365), forecast_km (500–100000), vidange_alert_km (100–10000) }` |

## Utilisateurs (admin)

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/api/users` | Liste. |
| `POST` | `/api/users` | `{ username, email, password, role? }` |
| `PUT` | `/api/users/<id>/role` | `{ role: "admin" | "user" }` |
| `PUT` | `/api/users/<id>/password` | `{ password }` |
| `DELETE` | `/api/users/<id>` | Supprimer. |

## Données & sauvegarde

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/api/backup` | Admin. Sauvegarde SQLite complète (téléchargement `.db`). |
| `GET` | `/api/export` | `format=csv` ou `xlsx` (défaut), `entity=vehicles|drivers|controls|maintenance|vidanges|all`. |
| `GET` | `/api/import/template` | Gabarit d'import. |
| `POST` | `/api/import` | Multipart `file` (import CSV/XLSX). |
| `POST` | `/api/demo` | Admin. Génère des données de démo (refus si parc non vide, `409`). |

## Rapports PDF

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/api/parc/pdf` | État du parc complet (synthèse, véhicules, maintenance, vidanges). |
| `GET` | `/api/reports/monthly/pdf` | Rapport mensuel (contrôles + maintenance). |
| `GET` | `/api/vehicles/<id>/pdf` | Fiche d'un véhicule. |
| `GET` | `/api/vidanges/pdf` | Rapport des vidanges. |

## Divers

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/api/health` | Public. `{ ok, service, time }` |
| `GET` | `/static/<path>` | Fichiers statiques du frontend. |
| `GET` | `/uploads/<path>` | Fichiers uploadés (photos, miniatures, documents). |

---

## Tests

- Local : `test.bat` (racine) ou `python -m pytest` depuis `backend/`.
- CI : `.github/workflows/tests.yml` (Python 3.10–3.12, sur push/PR).
- La base de test est isolée dans un dossier temporaire (`backend/tests/conftest.py`) : aucune donnée réelle touchée.
