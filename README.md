# NexFleet — Gestion de Parc Automobile 🚛

Plateforme web complète de gestion de parc automobile, pensée « grand startup » :
**design sombre premium, glassmorphism, animations**, backend sécurisé (JWT + PBKDF2) et
**génération de fiches de contrôle et rapports en PDF professionnels**.

---

## ✨ Fonctionnalités

| Module | Description |
|---|---|
| **Tableau de bord** | KPIs animés, graphiques canvas (donut, barres, anneau), alertes d'échéances (assurance · vignette · contrôle technique) |
| **Véhicules** | CRUD complet, recherche + filtres, badges de statut, compte à rebours des échéances, génération de la **fiche de contrôle PDF** |
| **Conducteurs** | CRUD complet, n° de permis, validité du permis |
| **Contrôles** | Fiche de contrôle interactive (12 points, 3 états), historique par véhicule |
| **Maintenance** | Interventions, coûts, garages, coût total, catégories standardisées alignées sur le plan budgétaire |
| **Vidanges** | Suivi huile/filtre, prévision kilométrique |
| **Budget & Plan de maintenance** 🆕 | Import du **plan d'achat annuel réel** (.xlsx), comparaison **prévu vs réalisé** par catégorie et trimestre, alertes de dépassement, export Excel/PDF, budget prévisionnel glissant 30/60/90 jours |
| **Analytique (TCO)** 🆕 | Coût total de possession par véhicule, coût/km, coût/mois, classement, tendance mensuelle 12 mois, répartition par catégorie |
| **Maintenance prédictive** 🆕 | Prévisions basées sur l'**historique réel** de chaque véhicule (intervalle moyen constaté), pas seulement des règles fixes ; coût prévisionnel estimé |
| **Assistant intelligent** 🆕 | Répond en langage naturel aux questions sur le parc (échéances, budget, coûts...) ; réponses instantanées par règles locales fiables, avec bascule optionnelle vers **l'API Claude (Anthropic)** pour les questions ouvertes |
| **Notifications automatiques** 🆕 | Digest quotidien par e-mail (échéances, budget, maintenance prédictive) — SMTP configurable dans Paramètres, sans dépendance externe |
| **Rapports & PDF** | **Rapport complet du parc**, **fiches de contrôle**, **rapport vidanges**, **rapport budget** en PDF professionnel (bandeau, tableau, signatures, code-barres) |
| **Paramètres** | Changement de mot de passe, préférences de prévision, configuration SMTP, clé API assistant IA, données de démo, rôles & sécurité |

## 🧠 Fonctionnalités avancées (nouveau)

### Budget & Plan de maintenance préventive
Importez votre fichier **« Plan d'achat annuel »** (.xlsx — le même classeur que votre
service utilise, avec trimestres et montants en FCFA) depuis **Budget → Importer le plan**.
L'application détecte automatiquement l'année et les catégories (Moteur, Freinage, Pompes,
Administratif, Vidange, Pneumatique, Tôlerie, Batterie...) et compare en continu le budget
prévu aux dépenses réellement enregistrées dans Maintenance et Vidanges — avec alertes dès
qu'une catégorie approche ou dépasse son enveloppe.

### Maintenance prédictive
Les prévisions (page Maintenance, calendrier, tableau de bord) s'appuient désormais sur
l'**historique propre à chaque véhicule** (intervalle moyen réellement constaté entre ses
interventions) plutôt que sur des règles génériques identiques pour tout le parc, avec un
coût prévisionnel estimé pour chaque échéance à venir.

### Assistant intelligent
Cliquez sur l'icône 🤖 dans la barre du haut pour poser une question en français : « quelles
échéances arrivent bientôt ? », « où en est le budget ? », « quel véhicule coûte le plus
cher ? »... Les questions courantes obtiennent une réponse instantanée et 100 % fiable
(calculée directement depuis la base). Pour des réponses en langage libre sur toute question,
un administrateur peut activer l'IA avancée dans **Paramètres → Assistant IA** :
- soit via la variable d'environnement `ANTHROPIC_API_KEY` sur le serveur (recommandé),
- soit en saisissant la clé directement dans les paramètres (stockée dans la base locale).

### Notifications automatiques par e-mail
Dans **Paramètres → Notifications automatiques**, configurez votre serveur SMTP et activez
l'envoi d'un digest quotidien (échéances, alertes budget, maintenance prédictive) à une ou
plusieurs adresses. Un bouton « Envoyer un digest maintenant » permet de tester la
configuration immédiatement.

## 🛡️ Sécurité

- Authentification **JWT (HS256)** — expiration 7 jours, clé générée aléatoirement (`backend/.secret`, hors code)
- Mots de passe hachés **PBKDF2-SHA256** (sel aléatoire) via Werkzeug
- Requêtes SQL **100 % paramétrées** (anti-injection)
- Validation & échappement des entrées côté serveur **et** côté client
- Rôles : **administrateur** (création/suppression) vs **utilisateur** (consultation/édition)
- CORS configuré pour l'API

## 📁 Structure du projet

```
parc-automobile/
├── backend/
│   ├── app.py              # API REST Flask (routes, validations, sécurité)
│   ├── auth.py             # JWT, hachage, décorateurs admin
│   ├── db.py               # SQLite (stdlib)
│   ├── budget.py           # Import du plan de maintenance (.xlsx) + comparaison prévu/réalisé
│   ├── notify.py           # Digest e-mail automatique (SMTP stdlib) + planificateur
│   ├── assistant.py        # Assistant intelligent (règles locales + API Claude optionnelle)
│   ├── pdf.py               # Génération PDF (reportlab)
│   ├── requirements.txt
│   └── .secret             # généré à la 1re exécution (ne jamais commiter)
├── frontend/
│   ├── index.html          # SPA (connexion + application)
│   ├── css/style.css       # Design system & animations
│   ├── js/app.js           # JS fonctionnel (livré prêt à l'emploi)
│   └── ts/app.ts           # Source TypeScript équivalente + tsconfig.json
├── data/                   # Base SQLite (créée automatiquement)
├── uploads/                # Généré
├── setup.bat               # Installation Windows (venv + dépendances)
├── run.bat                 # Lancement serveur + navigateur
└── README.md
```

## 🚀 Installation & lancement

Prérequis : **Python 3.9+** (https://www.python.org/downloads/ — cochez « Add to PATH »).

```bat
:: 1. Installer (une seule fois)
setup.bat

:: 2. Lancer
run.bat
```

Puis ouvrez **http://127.0.0.1:5000**

> La **première inscription** crée automatiquement le compte **administrateur**.
> Après connexion, allez dans **Paramètres → Données de démonstration** pour charger un parc réaliste (10 véhicules, conducteurs, contrôles, maintenance).

Lancement manuel :

```bash
cd backend
python -m venv ../.venv
../.venv/Scripts/activate
pip install -r requirements.txt
python app.py
```

## 📄 Génération des PDF

- **Fiche de contrôle** : page Véhicules → bouton `📄`, ou Rapports → sélection d'un véhicule.
- **Rapport du parc** : page Rapports → bouton Télécharger.
- Les PDF sont générés côté serveur avec **ReportLab** : bandeau de titre, tableau véhicule, checklist de 12 points colorés, observations, zones de signature et **code-barres** de l'immatriculation.

## 🎨 Design & animations

- Thème sombre « aurora » : blobs dégradés flottants + grille
- Glassmorphism (backdrop blur), cartes en verre
- Préchargeur animé, compteurs animés, graphiques animés au canvas
- Tables au survol, modales avec ressort, toasts, badges clignotants sur échéances critiques
- Entièrement responsive (sidebar coulissante sur mobile)

## ⚙️ Compiler le TypeScript (optionnel)

Le JS fourni (`frontend/js/app.js`) fonctionne immédiatement. Pour recompiler depuis la source TS :

```bash
cd frontend/ts
npx tsc        # ou: npm i -g typescript && tsc
```

## 🔧 API principales

```
POST /api/auth/register        POST /api/auth/login
GET  /api/stats                GET /api/vehicles (filtres : search, statut, carburant)
POST /api/vehicles             PUT/DELETE /api/vehicles/<id>
GET  /api/vehicles/<id>/pdf    GET /api/parc/pdf
GET/POST /api/drivers          GET/POST /api/controls    GET/POST /api/maintenance
POST /api/demo                 PUT /api/auth/password

POST /api/budget/import        GET /api/budget/summary?annee=  GET /api/budget/export
GET  /api/maintenance/forecast GET /api/maintenance/forecast/budget
GET  /api/tco                  POST /api/assistant/ask
GET  /api/notify/config        POST /api/notify/send-digest
```

Toutes les routes (hors auth) exigent l'en-tête `Authorization: Bearer <jwt>`.

## 📌 Note

L'application sert aussi le frontend : `GET /` renvoie `frontend/index.html`.
En production : désactivez CORS `*`, servez via un reverse-proxy HTTPS (ex. Nginx) et passez `debug=False` (déjà le cas).
