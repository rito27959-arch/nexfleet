# NexFleet – Application mobile

Application Flutter (version mobile) de gestion de parc automobile, branchée sur
la même API que la version web (`backend/app.py`). Interface sombre, riche en
animations et micro-interactions : aurora animé, cartes glassmorphism, nombres
animés, transitions de pages, haptique, skeleton loading, toasts.

## Prérequis

- Flutter SDK récent (>= 3.27) : https://docs.flutter.dev/get-started/install
- Le backend doit être joignable depuis l'appareil (voir ci-dessous).

## Création du projet (à faire une seule fois)

Le code de l'app est déjà présent dans `lib/`. Il manque seulement les dossiers
plateformes (android/ios/web), générés par Flutter :

```bash
cd nexfleet_app
flutter create . --platforms=android,ios,web --project-name nexfleet_app
flutter pub get
```

## Lancer l'application

Sans configuration particulière, l'app pointe sur `http://127.0.0.1:5000`
(ou `http://10.0.2.2:5000` sur l'émulateur Android).

Pour cibler une autre API (machine du réseau local, serveur distant Docker) :

```bash
flutter run --dart-define=API_URL=http://192.168.1.50:5000
# version web
flutter run -d chrome --dart-define=API_URL=https://votre-domaine.com
```

> L'API doit accepter les requêtes cross-origin (CORS). Le backend Flask
> l'autorise déjà via `CORS(app)` configuré dans `backend/app.py`.

## Construire

```bash
flutter build apk --release --dart-define=API_URL=https://votre-domaine.com
flutter build ipa --release --dart-define=API_URL=https://votre-domaine.com
flutter build web --release --dart-define=API_URL=https://votre-domaine.com
```

## Structure

```
lib/
  main.dart                     Entrée : thème + SplashScreen
  config.dart                   URL de l'API (API_URL dart-define)
  core/
    api_client.dart             Requêtes HTTP (get/post/put/delete) + ApiException
    session.dart                Session partagée (token, user, logout)
    app_scope.dart              Variable globale `app`
    haptics.dart                Retours haptiques (pulse*)
    models.dart                 Modèles (Statistiques, Véhicule, Vidange, ...)
    theme.dart                  Palette, Motion (curves spring/elastic), theme Material
  widgets/
    aurora_background.dart      Fond aurora dessiné (CustomPainter)
    pressable.dart              ScaleTap : enfoncement + ressort au relâchement
    glass.dart                  GlassCard, GradientButton, FilterChipNex
    fx.dart                     AnimatedNumber, Shimmer/Skeleton, Staggered, SpringShow
    charts.dart                 Donut, barres, jauge
    toast.dart                  Toasts iOS (haut, ressort, barre de progression)
    empty_state.dart            État vide avec icône qui respire
  utils/format.dart             Nombres, dates, devise
  screens/
    splash_screen.dart          Splash avec logos élastiques
    login_screen.dart           Connexion (shake d'erreur, carte élastique)
    shell.dart                  Navigation 5 onglets (bounce élastique)
    dashboard/…                 KPIs, alertes, graphiques, prochaines vidanges
    vehicles/…                  Liste (Hero), fiche, création/édition
    vidanges/…                  Liste (glisser pour supprimer), ajout
    maintenance/…               Liste et ajout d'interventions
    drivers/…                   Liste et ajout de conducteurs
    profile/…                   Profil, mot de passe, déconnexion
```

## API couverte

- `POST /api/auth/login`, `PUT /api/auth/password`
- `GET /api/stats`, `GET /api/vehicles[/:id][/detail]`, `POST/PUT /api/vehicles`
- `GET /api/vidanges`, `GET /api/vidanges/stats`, `POST/DELETE /api/vidanges`
- `GET /api/maintenance`, `POST /api/maintenance`
- `GET /api/drivers`, `POST /api/drivers`

Toutes les mutations passent par un overlay de chargement et des toasts de
confirmation. La déconnexion efface la session locale (`shared_preferences`) et
revient à l'écran de connexion.