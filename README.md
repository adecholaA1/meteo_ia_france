# 🌦️ Météo IA France

> 🇬🇧 **English version below** ([jump to English](#-france-ai-weather))

**Plateforme open-source de comparaison de modèles de prévision météorologique pour le secteur de l'énergie.**

Comparaison quotidienne sur la France métropolitaine de **GraphCast Operational** (Google DeepMind, IA de fondation), **AROME** (Météo-France, modèle physique régional) et **ERA5** (ECMWF, vérité terrain de référence) — avec dashboard React interactif, API Express, pipelines Python et page Méthodologie publique.

[![Licence MIT](https://img.shields.io/badge/Licence-MIT-blue.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Node.js 20](https://img.shields.io/badge/Node.js-20%2B-339933?logo=node.js&logoColor=white)](https://nodejs.org/)
[![React 19](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![PostgreSQL 15](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![JAX](https://img.shields.io/badge/JAX-DeepMind-FF6F00)](https://github.com/google/jax)

---

## 📑 Sommaire

1. [Pitch en 3 lignes](#-pitch-en-3-lignes)
2. [Démo](#-démo)
3. [Résultats clés](#-résultats-clés)
4. [Documentation](#-documentation)
5. [Quick start (3 commandes)](#-quick-start-3-commandes)
6. [Stack technique](#-stack-technique)
7. [Le journey du projet](#-le-journey-du-projet)
8. [Les 11 étapes en détail](#-les-11-étapes-en-détail)
9. [Les 6 plus gros défis et leur résolution](#-les-6-plus-gros-défis-et-leur-résolution)
10. [Ce que j'ai appris](#-ce-que-jai-appris)
11. [Roadmap](#-roadmap-v11--v20--v30)
12. [Comment contribuer](#-comment-contribuer)
13. [Licence & contact](#-licence--contact)

---

## 🎯 Pitch en 3 lignes

> Si tu travailles dans le secteur de l'énergie (éolien, solaire, trading), savoir **quel modèle météo te donne les prévisions les plus fiables** sur ta zone géographique est critique. Météo IA France répond à cette question pour la France métropolitaine, en comparant en continu un modèle IA généraliste (GraphCast) à un modèle physique régional (AROME), avec ERA5 comme vérité terrain.

L'objectif n'est pas de remplacer un fournisseur commercial mais de fournir une **plateforme transparente, reproductible et open-source** pour évaluer les performances réelles des modèles.

---

## 🎬 Démo

🌐 **URL de production** : `https://meteo-ia.fr` 

📸 **Captures d'écran**

| Dashboard principal | Page Méthodologie |
|---|---|
| Carte interactive France + 6 graphiques temps série + tableau MAE | 8 sections : glossaire, variables, sources, comparatif, limitations, roadmap, architecture |

🎥 **GIF démo** : *(à venir après le déploiement)*

---

## 🏆 Résultats clés

Sur la France métropolitaine, à horizon 24 h, sur 3 jours d'évaluation (17–19 avril 2026, **35 100 paires de mesures par variable et par modèle**) :

| Variable | GraphCast vs ERA5 (MAE) | AROME vs ERA5 (MAE) | Ratio AROME / GraphCast |
|---|---|---|---|
| 🌡️ Température 2 m (°C) | **3.81** | **1.16** | **AROME 3.3× plus précis** |
| 🌬️ Vitesse vent 10 m (m/s) | 1.38 | 0.83 | AROME 1.7× plus précis |
| 🧭 Direction vent 10 m (°) ⚙️ | 67.55 | 33.89 | AROME 2.0× plus précis |
| ☁️ Pression mer (hPa) | 3.44 | 0.39 | **AROME 8.7× plus précis** |
| 🌧️ Précipitations 6 h (mm) | 0.22 | 0.19 | AROME 1.2× plus précis |
| ☀️ TOA solaire (W/m²) | 0.00 | 0.00 | identique (variable astronomique) |

⚙️ La direction du vent utilise un **MAE circulaire** (cf. [BENCHMARKS.md](./BENCHMARKS.md)).

➡️ **AROME devance GraphCast Operational sur les 5 variables comparables**, avec des facteurs allant de 1.2× à 8.7×. Ces résultats sont cohérents avec la littérature : les modèles IA fondation sans spécialisation régionale n'égalent pas les modèles physiques régionaux à courte/moyenne échéance.

📊 **Détails complets** : voir [BENCHMARKS.md](./BENCHMARKS.md)

---

## 📚 Documentation

Le projet adopte une **hiérarchie claire de documentation** sur 3 niveaux :

| Document | Rôle | Audience |
|---|---|---|
| 🌟 [README.md](./README.md) (ce fichier) | Vision globale + journey + portfolio | Recruteur LinkedIn, contributeur open-source |
| 🏛️ [ARCHITECTURE.md](./ARCHITECTURE.md) | Architecture technique end-to-end + décisions | Architecte, dev qui rejoint le projet |
| 📊 [BENCHMARKS.md](./BENCHMARKS.md) | Résultats mesurés + méthodologie scientifique | Data scientist, journaliste tech, recruteur data |
| 🐍 [scripts/README.md](./scripts/README.md) | Doc des 4 pipelines Python | Dev qui touche aux pipelines |
| 🟢 [backend/README.md](./backend/README.md) | Doc des 8 endpoints REST | Dev qui touche au backend |
| 🟢 [backend/BENCHMARKS.md](./backend/BENCHMARKS.md) | Chiffres mesurés via l'API | Dev backend |
| 🟣 [frontend/README.md](./frontend/README.md) | Doc des composants React | Dev qui touche au frontend |

🌐 **Page Méthodologie publique** : `/fr/methodologie` ou `/en/methodology` directement sur le dashboard, avec 8 sections détaillées (glossaire de 16 sigles, 6 variables expliquées, 3 sources comparées, tableau comparatif côte-à-côte, limitations v1.0, roadmap v2.0, stack technique).

---

## 🚀 Quick start (3 commandes)

### Prérequis

- Docker Desktop (pour PostgreSQL + PostGIS)
- Python 3.11 + Conda (pour les pipelines)
- Node.js 20+ (pour backend + frontend)

### Lancement local

```bash
# 1. Cloner le repo et lancer la base de données
git clone https://github.com/kouande/meteo_ia_france.git && cd meteo_ia_france
docker-compose up -d                      # PostgreSQL 15 + PostGIS sur port 5433

# 2. Installer et lancer le backend (port 3001)
cd backend && npm install && cp .env.example .env && npm run dev

# 3. Installer et lancer le frontend (port 5173)
cd ../frontend && npm install && npm run dev
```

Ouvre `http://localhost:5173/fr` dans ton navigateur.

### Bonus : régénérer les données depuis les sources

```bash
conda env create -f environment.yml && conda activate meteo_ia
python -m era5.run_daily_pipeline      # ECMWF CDS API
python -m arome.run_daily_pipeline     # data.gouv.fr
python -m graphcast_gfs.run_daily_pipeline  # NOMADS NOAA + inférence GraphCast
python -m mae.run_daily_pipeline       # Calcul des MAE
```

---

## 🛠️ Stack technique

### Backend & data engineering
- **Python 3.11** (env conda `meteo_ia`)
- **xarray, pandas, numpy, scipy** — manipulation de données scientifiques
- **cdsapi, httpx, requests** — téléchargement ERA5 / NOMADS / data.gouv.fr
- **eccodes, cfgrib** — parsing GRIB2
- **JAX + GraphCast** (open weights DeepMind) — inférence IA météo
- **PostgreSQL 15 + PostGIS 3.4** (Docker, port 5433)
- **Node.js 20 + Express 4** — API REST (8 endpoints)
- **node-cache** TTL 600s, **helmet, CORS, rate-limiter** — sécurité

### Frontend
- **React 19 + TypeScript 5**
- **Vite 8** — build et HMR ultra-rapide
- **Tailwind CSS v4 + shadcn/ui** (Radix preset Nova)
- **Recharts** — courbes temps série synchronisées
- **Leaflet** — carte interactive France (Stadia Alidade Smooth Dark)
- **react-router-dom v7** — routing FR/EN + page Méthodologie
- **TanStack Query v5** — client HTTP managé (cache, retry, dedup) ⭐ *étape 10*
- **Pattern hybride API runtime / JSON statique** — bascule transparente via `<DataSourceContext>` ⭐ *étape 10*
- **Light + Dark mode** — palette OKLCH style Claude

### Déploiement & DevOps (V1.0)
- **Docker** (24+) + **Docker Compose** v2 — orchestration des 3 services (postgres, backend, frontend) sur réseau Docker isolé
- **Backend Dockerfile** single-stage `node:22-alpine` (~60 Mo, user non-root, healthcheck `/api/health`)
- **Frontend Dockerfile** multi-stage `node:22-alpine` builder + `nginx:1.27-alpine` production (~23 Mo)
- **Nginx du container frontend** — gzip, cache assets, SPA fallback React Router, **reverse proxy `/api/*` → backend container**
- **PostgreSQL 15 + PostGIS 3.4** (image `postgis/postgis:15-3.4-alpine`) avec auto-init du backup `.sql` (333 Mo) au 1er démarrage
- **Healthchecks Docker** sur les 3 services (`pg_isready`, `wget /api/health`, `wget /nginx-health`) avec `depends_on: condition: service_healthy`
- **Volume nommé `meteo_ia_pg_data`** pour persistance des données entre redémarrages
- **VPS OVH Ubuntu 24** (production) — déploiement HTTPS via **Nginx host + Certbot Let's Encrypt** (en cours)
- **Cron UTC sur l'OS du VPS** — orchestration des 4 pipelines Python quotidiens
- 🟡 **CI/CD GitHub Actions** : prévu V1.1 (build Docker auto sur push, lint, typecheck, tests, deploy)
- 🟡 **Tests unitaires Jest + Vitest + pytest** : prévus V1.1 (cf. roadmap)

---

## 📈 Le déroulement du projet

### Pourquoi ce projet ?

Avec l'arrivée fracassante des modèles IA météorologiques en 2023-2024 (GraphCast, Pangu-Weather, ClimaX, Aurora), une question pratique s'impose pour le secteur de l'énergie : **est-ce que ces nouveaux modèles surpassent vraiment les modèles physiques régionaux établis ?**

La réponse n'est ni oui ni non — elle dépend de la zone géographique, des variables d'intérêt, des horizons de prévision, et de si le modèle a été spécialisé localement ou non. Ce projet apporte une **réponse mesurée, reproductible et transparente** pour la France métropolitaine, en mettant en place un pipeline end-to-end qui compare quotidiennement GraphCast vs AROME, avec ERA5 comme étalon.

### Ce qu'il fait

- 📡 **Télécharge et ingère** quotidiennement 4 sources de données (GFS, ERA5, AROME, GraphCast)
- 🧠 **Lance l'inférence GraphCast Operational** sur la grille France (~5-8 min CPU sur Mac Intel)
- 📊 **Calcule MAE / RMSE / Bias** sur 6 variables × 4 horizons × 2 925 points GPS chaque jour
- 🌐 **Expose 8 endpoints REST** pour interroger les données et métriques
- 📱 **Affiche un dashboard interactif** avec carte heatmap, 6 courbes temps série et tableau comparatif
- 📚 **Documente publiquement** la méthodologie sur une page web bilingue (FR + EN)
- 🔒 **Reste 100% open-source** — code, données, méthodologie, résultats

---

## 🗺️ Les 11 étapes en détail

### 🟢 Étape 1 — Setup environnement & exploration sources

**Durée** : 2 jours · **État** : ✅ Terminée

Mise en place de l'environnement conda `meteo_ia` (Python 3.11 + xarray, JAX, eccodes), exploration des 3 sources candidates (ERA5 via CDS, AROME via data.gouv.fr, GraphCast via open weights DeepMind), choix de la grille France 0.25° (2 925 points GPS = 45 lat × 65 lon couvrant lat 41.0–51.5 et lon -5.5–9.0).

**Décision clé** : utiliser le format **LONG** (1 ligne = 1 variable × 1 timestamp × 1 point GPS) plutôt que WIDE en base de données, pour permettre l'ajout de nouvelles variables sans modifier le schéma.

---

### 🟢 Étape 2 — Pipeline ERA5 (vérité terrain)

**Durée** : 3 jours · **État** : ✅ Terminée

Construction du pipeline `era5/` qui télécharge depuis l'**ECMWF Climate Data Store** (CDS API) les 5 variables natives (t2m, u10, v10, msl, tp) sur la grille France à 1 h de pas de temps. Calcul des variables dérivées (`wind_speed_10m_ms`, `wind_direction_10m_deg`, `tp_6h_mm` cumulé sur 6 heures glissantes).

**Décision clé** : prendre une **latence J-6** par sécurité (au lieu du J-5 annoncé officiellement par ECMWF), car les dernières heures du J-5 sont parfois encore en cours de production à 16h UTC.

**Bug résolu** : `download_format: unarchived` non respecté par le CDS → forcer le post-traitement local (`unzip` + `xarray.open_dataset`).

---

### 🟢 Étape 3 — Inférence GraphCast Operational

**Durée** : 8 jours (le plus gros défi du projet) · **État** : ✅ Terminée

Mise en place du pipeline `graphcast_gfs/` :
1. **Téléchargement GFS NOMADS** (NOAA) : 28 fichiers GRIB2 par run (T-6h + T0 × 14 niveaux atmosphériques)
2. **Pré-traitement** : normalisation des unités, interpolation spatiale 0.25°, conversion en NetCDF compatible GraphCast
3. **Inférence GraphCast Operational** (open weights DeepMind, JAX) : ~5–8 min sur CPU Mac Intel pour 4 horizons (+6h, +12h, +18h, +24h)
4. **Export CSV** : 4 horizons × 8 variables × 2 925 points = **93 600 lignes par jour**
5. **Ingestion DB** avec `INSERT ON CONFLICT` idempotent

**Choix techniques** :
- **JAX au lieu de PyTorch** (imposé par GraphCast)
- **Inférence batch via cron**, pas API on-demand (CPU lent)
- **Conserver tous les runs** en DB plutôt que supprimer les anciens (utile pour analyse de dégradation par horizon)

---

### 🟢 Étape 4 — Pipeline AROME (Météo-France)

**Durée** : 4 jours · **État** : ✅ Terminée

Construction du pipeline `arome/` qui télécharge depuis **data.gouv.fr** (open data Météo-France) les 4 fichiers GRIB2 SP1 quotidiens (échéances 00H06H, 07H12H, 13H18H, 19H24H), réalise un ré-échantillonnage spatial de la résolution native AROME (0.025° ≈ 2.5 km) vers la grille commune 0.25°, puis ingère en DB.

**Compromis volontaire (limitation v1.0)** : AROME natif est à 0.025° mais on ré-échantillonne à 0.25° pour aligner la grille avec ERA5/GraphCast. **AROME perd 90% de sa résolution spatiale** dans cette opération — il est donc désavantagé dans la comparaison. La résolution native sera réintroduite en v2.0.

---

### 🟢 Étape 5 — Pipeline MAE (calcul des métriques)

**Durée** : 2 jours · **État** : ✅ Terminée

Construction du pipeline `mae/` qui réalise un `INNER JOIN` SQL entre les tables `arome_forecasts`, `graphcast_predictions` et `era5_truth` sur `(timestamp, variable_name, latitude, longitude)`, calcule **MAE / RMSE / Bias** pour chaque combinaison (variable × horizon × comparaison) sur les 2 925 points, et stocke le tout dans `mae_metrics`.

**Correction critique post-v1.0** : implémentation d'un **MAE circulaire** pour `wind_direction_10m_deg` :
```python
abs_error = min(|pred - vérité| mod 360, 360 - |pred - vérité| mod 360)
```
Avant : MAE moyen wind_direction reporté à ~110° (artefact des bordures 0°/360°).
Après : MAE = **34° pour AROME, 68° pour GraphCast** (cohérent avec benchmarks ECMWF de 20–40°).

Le `bias` pour les variables cycliques est forcé à `NULL` car n'a pas d'interprétation physique simple.

---

### 🟢 Étape 6 — Schéma DB PostgreSQL + PostGIS

**Durée** : 1 jour · **État** : ✅ Terminée

Définition du schéma final dans `scripts/sql/init_db_schema.sql` :
- **4 tables** : `era5_truth`, `arome_forecasts`, `graphcast_predictions`, `mae_metrics`
- **2 vues** `*_fresh` qui filtrent automatiquement le run le plus récent par tuple `(timestamp, variable_name, lat, lon)`
- **Index composites** sur `(timestamp, lat, lon)` pour requêtes rapides
- **UNIQUE constraints** pour idempotence des `INSERT ON CONFLICT`
- **`TIMESTAMP WITH TIME ZONE`** stocké en UTC, conversion vers Europe/Paris au niveau frontend
- **Fonction `utc_to_paris(ts)`** disponible pour requêtes manuelles

**Volumétrie observée** : ~1.96 M lignes au 25/04/2026, croissance ~100 Mo/mois.

---

### 🟢 Étape 7 — Orchestration des pipelines

**Durée** : 2 jours · **État** : ✅ Terminée

Mise en place des `run_daily_pipeline.py` orchestrateurs pour chaque module (4 pipelines indépendants). Convention de logging unifiée, gestion des erreurs avec retry 3× / pause 30 min, génération de rapports d'exécution. Documentation complète dans `scripts/README.md`.

**Crontab UTC prévu en production** :
```
 0  1 * * *  graphcast_gfs.run_daily_pipeline  # cible run 18z, dispo vers 1h UTC
30  1 * * *  arome.run_daily_pipeline          # AROME run 18z dispo vers 1h30 UTC
 0  2 * * *  era5.run_daily_pipeline           # cible J-6
 0  3 * * *  mae.run_daily_pipeline            # après ERA5
```

---

### 🟢 Étape 8 — Backend Express (8 endpoints REST)

**Durée** : 3 jours · **État** : ✅ Terminée

Construction du backend `backend/` (Node.js 20 + Express 4) avec architecture MVC classique : `routes/` + `controllers/` + `middleware/` + `config/`. Pas de Prisma/TypeORM — SQL brut via `pg` pour transparence et performance.

**8 endpoints exposés** :

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/health` | Healthcheck pour PM2/UptimeRobot/Nginx |
| GET | `/api/status` | Compteurs des 4 tables + stats cache + uptime |
| GET | `/api/forecast/available-times` | Liste `(date, hour)` disponibles par source |
| GET | `/api/forecast/grid-points` | 2925 points GPS (appelé une fois au load) |
| GET | `/api/forecast/timeseries` ⭐ | 7 jours × 6 variables × 3 sources pour 1 point GPS |
| GET | `/api/forecast/:date/:hour` | Grille complète à instant T pour 1 source/variable |
| GET | `/api/mae/comparison` ⭐ | Tableau MAE latest + moyenne 7 jours |
| GET | `/api/mae/history` | Évolution quotidienne du MAE pour 1 variable |
| GET | `/api/heatmap/error` | Grille d'écart spatial `(source - era5)` |

**Sécurité v1.0** : `helmet`, `CORS` configurable, `express-rate-limit` 100 req/h/IP, `node-cache` TTL 600s pour réduire la charge DB.

📚 Documentation complète : [backend/README.md](./backend/README.md) + [backend/BENCHMARKS.md](./backend/BENCHMARKS.md)

---

### 🟢 Étape 9 — Frontend React (le plus gros chantier)

**Durée** : 6 jours · **État** : ✅ Terminée

Construction du frontend `frontend/` avec un dashboard interactif complet et une page Méthodologie publique.

**Composants livrés** :

| Composant | Description |
|---|---|
| **Header** | Logo, titre bilingue, horloge live UTC+1/UTC+2 (DST automatique), toggle dark/light, switch FR/EN |
| **Carte France interactive** | Fond Stadia Alidade Smooth Dark + 103 villes principales avec heatmap colorée (CircleMarker visible) + 10 pins 📍 sur les plus grandes villes + tooltips riches au survol (nom, AROME/GraphCast, ERA5 vérité, écart absolu) + 3 dropdowns (source/variable/timestamp) + 4 timestamps disponibles + zoom modal sans superposition |
| **Tableau MAE** | 4 horizons (h6/h12/h18/h24) × 6 variables, ratio coloré, mode zoom |
| **6 ChartCards** | Une par variable météo, courbes temps série synchronisées (curseur partagé), 3 sources superposées, axes adaptatifs, mode zoom, légendes interactives |
| **ZoomDialog** | Modal universel pour la carte, le tableau MAE et les charts |
| **Footer** | Sources colorées, copyright, version v1.0, **lien Méthodologie** + lien GitHub |
| **Page Méthodologie** ⭐ | 8 sections complètes : À propos, Glossaire (16 sigles), 6 variables, 3 sources colorées, tableau comparatif 14 lignes, 5 limitations v1.0, roadmap v2.0, architecture (5 cards avec Backend explicite) |

**Stack & conventions** :
- React 19 + TypeScript 5 + Vite 8
- Tailwind CSS v4 + shadcn/ui (Radix preset Nova)
- Recharts pour les courbes, Leaflet pour la carte
- Bilingue 100% FR/EN avec routes séparées (`/fr`, `/en`, `/fr/methodologie`, `/en/methodology`)
- Light + Dark mode (palette OKLCH style Claude)
- 4 timestamps réels (00h, 06h, 12h, 18h UTC)

**Bugs résolus pendant l'étape** :
- Z-index Leaflet vs Radix (`data-slot="select-content"` à 9999)
- Format `hour` backend exigeait `06` mais script envoyait `6` → `String(t.hour).padStart(2, "0")`
- Tailwind v4 et accolades CSS cassées (12/12 équilibrées finales)
- Sensibilité du hover sur les points de carte (CircleMarker invisible radius=14 par-dessus)

📚 Documentation : [frontend/README.md](./frontend/README.md)

---

### 🟢 Étape 10 — Pattern hybride API runtime / JSON statique

**Durée** : 1 jour · **État** : ✅ Terminé

Connexion du frontend React à l'API Express (`localhost:3001`), avec une approche **plus mature qu'un simple branchement runtime** : on conserve le mode JSON statique existant et on ajoute un **mode API runtime à côté**, avec **bascule transparente en live** entre les deux.

**Pourquoi ce choix architectural** :

| Cas d'usage | Mode recommandé | Pourquoi |
|---|---|---|
| 🌐 Production publique (CDN, GitHub Pages, démo LinkedIn) | 💾 JSON statique | Performance, hébergement gratuit, fonctionne offline |
| 🔧 Démo pédagogique en live (recruteurs) | 🟢 API runtime | Devtools réseau visibles, requêtes traceables |
| 🐛 Debug local (modification DB, vérification immédiate) | 🟢 API runtime | Pas besoin de rebuild après chaque ingestion |
| 📱 Utilisateur sur 4G mobile | 💾 JSON statique | Économise data + plus rapide |
| 🛡️ Backend tombé en panne | 💾 JSON statique (fallback) | L'app continue de fonctionner |

**Composants livrés** :

| Composant | Rôle |
|---|---|
| `services/apiService.ts` ⭐ | Service typé : 9 méthodes vers les 8 endpoints Express, gestion d'erreur unifiée, query params, types TypeScript stricts |
| `contexts/DataSourceContext.tsx` ⭐ | Context React qui gère le mode actif (`useApi: boolean`) avec lecture de `VITE_USE_API` au démarrage et fonction `toggleDataSource()` pour bascule live |
| `hooks/useStaticData.ts` 🔄 | Hook hybride : charge depuis l'API ou depuis `/data/sample_forecast.json` selon le contexte, sans modification de l'API publique |
| `hooks/useHeatmapData.ts` 🔄 | Idem pour les heatmaps : API runtime ou `/data/heatmaps/{variable}.json` |
| `components/layout/DataSourceToggle.tsx` ⭐ | Bouton 📡/💾 dans le header pour basculer en live |
| `main.tsx` 🔄 | Ajout `<QueryClientProvider>` (TanStack Query v5 + DevTools dev) + `<DataSourceProvider>` |
| `.env` ⭐ | Variable `VITE_USE_API=false` (mode statique par défaut en prod) |

**Principe d'abstraction réussi** : aucun composant consommateur (`FranceMap`, `MaeTableCard`, `ChartCard`) n'a été modifié. Les hooks gardent leur API publique `{ data, loading, error }` et la bascule se fait en interne. Cette séparation est le **vrai cœur architectural** de l'étape.

**TanStack Query v5 installé** : `QueryClient` configuré avec staleTime 5min, gcTime 30min, retry 2 (backoff exponentiel). Pas encore consommé directement par les hooks (option allégée : `useStaticData` et `useHeatmapData` quasi inchangés), mais **prêt à l'emploi** pour les futurs hooks dédiés.

**3 vrais bugs identifiés grâce à la confrontation API/frontend** :

| # | Bug | Cause | Solution |
|---|---|---|---|
| 1 | **CORS multi-port** | Vite tournait sur 5174 (5173 occupé par autre process), backend autorisait seulement 5173 | Libération du port 5173 (à terme : whitelist CORS plus permissive en dev) |
| 2 | **Coordonnées Paris** | Frontend envoyait `lat=48.85, lon=2.35` (Paris exact), backend ne trouvait rien sur la grille 0.25° | Alignement sur la grille la plus proche : `lat=49, lon=2.5` |
| 3 | **Latence ERA5 J-6** | Frontend demandait la heatmap pour `2026-04-27 18h` mais ERA5 n'a pas encore cette date → 404 | Utiliser `available-times?source=era5` au lieu de `?source=arome` (ERA5 contraint la disponibilité des comparaisons) |

**Démonstration visible** : ouvrir le dashboard, cliquer sur le toggle 📡 dans le header → les requêtes vers `localhost:3001/api/...` apparaissent dans le panneau Réseau du navigateur. Cliquer à nouveau → retour au mode statique (`/data/sample_forecast.json`). Bascule transparente sans rebuild.

📚 Documentation détaillée : [frontend/README.md](./frontend/README.md) (FR + EN)

---

### 🟢 Étape 11 — Pipeline d'acquisition automatisée des données météo brutes

**Durée** : ~3 jours · **État** : ✅ Terminée

Cette étape établit le **socle d'acquisition continue de données météorologiques** qui alimente l'ensemble de la plateforme. L'objectif : garantir que la base PostgreSQL soit enrichie quotidiennement de données fraîches issues de 3 sources (ERA5, AROME, GraphCast Operational), avec ingestion fiable, idempotente et traçable.

#### 11.1 — Quatre pipelines Python d'acquisition

Chaque source dispose de son pipeline orchestré indépendant (`scripts/{source}/run_daily_pipeline.py`) qui enchaîne 3 à 5 étapes selon la source :

| Pipeline | Étapes | Volumétrie quotidienne |
|---|---|---|
| **ERA5** | Fetch CDS Copernicus → Export CSV (cumuls 6 h + variables dérivées) → Ingestion DB | ~93 600 lignes |
| **AROME** | Fetch GRIB2 data.gouv.fr → Parse NetCDF → Export CSV → Ingestion DB | ~93 600 lignes |
| **GraphCast** | Fetch GDAS GFS NOMADS → Parse NetCDF → Inférence JAX → Export CSV → Ingestion DB | ~93 600 lignes |
| **MAE** | Lecture prédictions DB → Lecture vérité ERA5 DB → Calcul métriques → UPSERT MAE | ~64 lignes/jour |

Chaque pipeline supporte un **mode auto** (calcul de la date cible) et un **mode manuel** (`--date YYYY-MM-DD`) pour le backfill historique. Mode `--skip-existing` pour ne pas re-télécharger ce qui est déjà sur disque, mode `--no-db` pour debug sans toucher la base.

#### 11.2 — Acquisition robuste avec retry et idempotence

Chaque étape critique (fetch CDS, parse GRIB2, ingestion DB) est encapsulée dans un décorateur `retry()` avec **3 tentatives × pause 30 minutes** (configuration production). Cette stratégie absorbe les pannes transitoires côté API (CDS Copernicus surchargé, NOMADS en maintenance) sans perte d'exécution.

L'ingestion en base utilise un **UPSERT idempotent** sur la contrainte unique `(latitude, longitude, timestamp, variable_name)` : si le pipeline est ré-exécuté pour une même date, les données sont mises à jour plutôt que dupliquées. Cette propriété est critique pour la reprise après incident.

#### 11.3 — Schéma PostgreSQL pour données brutes

Les 3 tables principales adoptent un **format LONG dénormalisé** (1 ligne par variable × point × timestamp) pour faciliter l'évolution future du schéma sans migration :

```sql
CREATE TABLE era5_truth (
    id SERIAL PRIMARY KEY,
    "timestamp" TIMESTAMP WITH TIME ZONE NOT NULL,
    latitude NUMERIC(9, 6) NOT NULL,
    longitude NUMERIC(9, 6) NOT NULL,
    variable_name VARCHAR(50) NOT NULL,  -- t2m_celsius, u10_ms, msl_hpa, ...
    value NUMERIC(15, 6),
    run_date TIMESTAMP WITH TIME ZONE,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (timestamp, latitude, longitude, variable_name)
);
-- Index B-tree composite pour les requêtes par point GPS
CREATE INDEX idx_era5_lat_lon_time
  ON era5_truth (latitude, longitude, "timestamp" DESC);
```

Schéma similaire pour `arome_forecasts` et `graphcast_predictions`. Vues `*_fresh` qui renvoient uniquement le dernier run par date pour les requêtes frontend, les anciens runs étant conservés pour l'analyse historique.

#### 11.4 — Logging structuré centralisé

Helper partagé `scripts/utils/logging_setup.py` exposant `setup_pipeline_logging(source_name)`. Configure simultanément :
- Console (`StreamHandler` sur `stdout`) — pour suivre en direct
- Fichier (`FileHandler(mode="a", encoding="utf-8")`) — historique cumulatif

Quatre fichiers permanents dans `logs/` : `arome.log`, `era5.log`, `graphcast.log`, `mae.log`. Chaque exécution ajoute en append (pas d'écrasement), avec un banner `🚀 Nouveau run de pipeline : {SOURCE}` au début pour visualiser les frontières entre exécutions. Format ISO `YYYY-MM-DD HH:MM:SS [LEVEL] message` pour parsing facile par outils de log management.

#### 11.5 — Sécurité des credentials

Les informations sensibles (clé API CDS Copernicus, mot de passe DB) sont externalisées dans :
- `~/.cdsapirc` pour Copernicus (convention officielle de la lib `cdsapi`)
- `backend/.env` pour la base PostgreSQL (pattern dotenv standard)
- Variables d'environnement `BACKEND_URL`, `DATABASE_URL` pour la portabilité entre dev/prod

Aucun secret n'est versionné dans Git (`.gitignore` exhaustif).

#### 🎁 Bonus accomplis lors de cette étape

Au-delà de l'acquisition automatisée stricto sensu, cette étape a été l'occasion de consolider plusieurs aspects de la plateforme. Ces livrables sont **au-delà de la spec** mais élèvent le projet au niveau production :

| Bonus | Description | Impact mesuré |
|---|---|---|
| **Phase A** — Badge ville sur ChartCards | Chaque graphique affiche `📍 {cityName}` via layout flexbox 3 zones | Lisibilité immédiate de la localisation sur les 6 graphiques |
| **Phase B** — Carte interactive synchronisée aux courbes | `SelectedCityContext` (React Context) + TanStack Query + snap grille 0.25° | Navigation géo-temporelle fluide entre la carte et les 6 ChartCards |
| **Index PostgreSQL B-tree composites** | 3 index `(latitude, longitude, timestamp DESC)` sur les tables de prédictions | Latence `/timeseries` : 10 s → 77 ms (gain **130×**) |
| **Cache backend 4 couches** | TTL 1 h sur `/available-times` + endpoint `POST /cache/clear` + pre-warming au boot + cron keep-alive | Refresh page mode API : 18 s → <200 ms (gain **90×**), cache hit ~5 ms |
| **Wind direction → bar chart** | Variable circulaire ne se prête pas au line chart (zigzags artificiels 0°/360°). Bar chart + axe Y avec labels cardinaux + tooltip enrichi + légende 8 secteurs | Visualisation correcte de la direction du vent, plus de zigzags |
| **Footer 3 colonnes** avec lien KAEK | `grid-cols-[1fr_auto_1fr]` pour layout responsive | Lien KAEK toujours centré, copyright sans wrap |
| **Correctif 100 → 103 villes** | Mise à jour `i18n/fr.ts`, `i18n/en.ts`, `lib/franceCities.ts` | Cohérence de l'UI avec la liste réelle |

📚 Documentation détaillée : [scripts/README.md](./scripts/README.md), [ARCHITECTURE.md](./ARCHITECTURE.md), [BACKEND.md](./BACKEND.md), [FRONTEND.md](./FRONTEND.md)

---

### 🟢 Étape 12 — Dockerisation complète & déploiement V1.0 ⭐ NOUVEAU (29/04/2026)

**État** : 🟢 Dockerisation locale 100% terminée · 🔜 Déploiement VPS en cours

**Pitch** : passage du projet d'un environnement local fragile (chaque service lancé manuellement) à une **infrastructure dockerisée production-grade** orchestrée par `docker-compose`, prête à être déployée sur le VPS OVH avec un seul commit. Cette étape concrétise le saut "code de dev" → "produit déployable".

#### 12.1 — Trois Dockerfiles taillés pour la production

**Backend Express** (`backend/Dockerfile`, single-stage, ~60 Mo) :
- Image de base `node:22-alpine` (légère, sécurisée)
- Utilisateur `node` non-root (sécurité runtime)
- `npm ci --omit=dev` (pas de devDependencies en prod)
- `EXPOSE 3001` + `HEALTHCHECK` qui ping `/api/health` toutes les 30s
- `.dockerignore` exclut `node_modules`, `.env`, `backup/`, `.git`, `logs`

**Frontend React/Vite** (`frontend/Dockerfile`, multi-stage, ~23 Mo) :
- Stage 1 — **Builder** : `node:22-alpine`, lance `npm run build` avec `tsc -b && vite build`
- Stage 2 — **Production** : `nginx:1.27-alpine` qui sert uniquement le `dist/` final
- Build args injectés à la compilation : `VITE_USE_API=true`, `VITE_API_URL=""` (URL relative)
- Vérification post-build : test que `/app/dist/index.html` existe (échec rapide sinon)

**PostgreSQL + PostGIS** (image officielle `postgis/postgis:15-3.4-alpine`) :
- Auto-init au 1er démarrage via volume mount du backup `meteo_ia_db.sql` (333 Mo) sur `/docker-entrypoint-initdb.d/01-init.sql`
- Volume nommé `meteo_ia_pg_data` pour persistance des données entre redémarrages
- Healthcheck `pg_isready` toutes les 10s avec `start_period: 30s` (le temps que l'init du backup termine au 1er run)

#### 12.2 — Orchestration via `docker-compose.yml`

Un fichier unique à la racine du projet (~130 lignes commentées en français) qui orchestre les **3 services** sur un réseau Docker isolé `meteo_ia_network` :

```yaml
services:
  postgres:    # port host 5433 → interne 5432 (5432 occupé par autre projet)
  backend:     # port host 3001 → interne 3001
               # depends_on: postgres healthy (attend l'init avant de démarrer)
               # DB_HOST=postgres (résolution DNS interne Docker)
               # DB_PORT=5432 (port INTERNE, pas le 5433 du host)
  frontend:    # port host 8080 → interne 80 (Nginx)
               # depends_on: backend
               # build args: VITE_USE_API=true, VITE_API_URL=""
```

**Bénéfices concrets** :
- ✅ Un seul `docker compose up -d --build` lance toute la stack
- ✅ Chaque service redémarre automatiquement (`restart: unless-stopped`)
- ✅ Variables d'environnement centralisées dans `.env` (racine projet)
- ✅ Healthchecks Docker garantissent que le backend ne démarre **que** quand Postgres est prêt
- ✅ Volume persistant : les données survivent aux `docker compose down` (sauf `down -v`)

#### 12.3 — Reverse proxy Nginx `/api/*` → backend

Configuration `frontend/nginx.conf` enrichie avec **3 fonctions critiques** :

1. **Compression gzip** — `gzip on; gzip_types text/css application/javascript application/json;`
2. **Cache des assets versionnés** — `location ~* \.(css|js|woff2)$ { expires 1y; add_header Cache-Control "public, immutable"; }`
3. **Reverse proxy `/api/*` → `backend:3001`** :

```nginx
location /api/ {
    proxy_pass http://backend:3001;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_connect_timeout 30s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
}
```

→ Le frontend peut faire des appels relatifs (`fetch('/api/forecast/...')`), Nginx du container frontend transmet automatiquement vers le container backend via le DNS interne Docker. **Pas besoin de `VITE_API_URL` absolu.**

#### 12.4 — 80 erreurs TypeScript corrigées (refactoring qualité)

Le passage à `tsc --noEmit` strict en build Docker a révélé **~80 erreurs TypeScript pré-existantes** non détectées en mode dev (Vite tolérant). Toutes corrigées proprement en 4 phases :

| Phase | Cause racine | Erreurs | Solution |
|---|---|---|---|
| **1** | Variables/imports inutilisés | 6 | Nettoyage manuel dans `ChartCard.tsx`, `FranceMap.tsx` |
| **2** | Type `TimeseriesPoint` désaligné backend ↔ frontend | 3 | Réécriture `frontend/src/types/forecast.ts` (suppression suffixes `_value` obsolètes) |
| **3** | Type `Translations` non exporté depuis `i18n/fr.ts` | ~62 | Ajout `export type Translations = DeepStringify<typeof fr>` + helper récursif `DeepStringify<T>` qui rend les literal types en `string` génériques |
| **3 bis** | Type `MethodologyFr` inutilisable (literal types `as const`) | 8 | Réécriture complète `methodology.fr.ts` avec interface `MethodologyTranslations` explicite + 8 sous-types exportés (`GlossaryEntry`, `VariableItem`, `SourceCard`, etc.), suppression du `as const` |
| **3 ter** | Composants `methodology/*.tsx` importaient l'ancien type | 12 | `sed` global remplaçant `MethodologyFr` → `MethodologyTranslations` dans 8 fichiers |
| **4** | Warning `tsconfig.app.json` "baseUrl deprecated" | 1 | Ajout `"ignoreDeprecations": "6.0"` |

→ Désormais `tsc --noEmit` passe sans aucune erreur. La couche `npm run build` du Dockerfile frontend valide systématiquement la qualité TS à chaque image.

#### 12.5 — Bug critique résolu : doublon `/api/api/`

**Symptôme** : après dockerisation, le dashboard affichait `❌ Erreur de chargement — HTTP 404 sur /api/forecast/available-times` malgré un backend qui répondait correctement aux `curl` directs.

**Diagnostic** : la console réseau du navigateur révélait `localhost:8080/api/api/forecast/...` (double `/api/api/`). Cause racine : le code frontend faisait `${BASE_URL}${path}` avec `BASE_URL = "/api"` (issu de `VITE_API_URL=/api`) et `path = "/api/forecast"` (déjà préfixé), résultat : `/api/api/forecast`.

**Fix** : `VITE_API_URL=""` (chaîne vide) dans `docker-compose.yml`. Le code reconstruit alors `${""}${"/api/forecast"}` = `/api/forecast` ✅. Le proxy Nginx route ensuite vers `backend:3001/api/forecast`. Tests `curl` confirment que toutes les routes répondent maintenant en 200 OK depuis le container frontend.

#### 12.6 — Configuration prod : `.env.production.example`

Création d'un **template documenté** (~8 Ko, commenté en français) qui sera commité sur GitHub avec **valeurs factices** (`CHANGEME`). Sur le VPS, on copie ce template vers `.env.production` et on remplit les vraies valeurs (mots de passe générés via `openssl rand -base64 32`).

**Variables couvertes** :
- 🗄️ PostgreSQL (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)
- ⚙️ Backend (NODE_ENV=production, PORT, CORS_ORIGINS=https://meteo-ia.fr, rate-limit, cache TTL)
- 🎨 Frontend (VITE_USE_API=true, VITE_API_URL="")
- 🌐 Domaine (DOMAIN=meteo-ia.fr, CERTBOT_EMAIL pour alertes Let's Encrypt)
- 🐍 Pipelines Python (CDS_API_KEY pour ERA5, NOAA_USER_AGENT pour NOMADS)

#### 12.7 — `.gitignore` enrichi

Refonte du `.gitignore` racine (de 189 octets à 4,7 Ko) couvrant :
- 🔒 Secrets : `.env`, `.env.production`, avec exception `!.env.production.example`
- 🐍 Python : `venv/`, `__pycache__/`, `*.pyc`
- 📦 Node : `node_modules/`, `npm-debug.log`
- 🎨 Build frontend : `dist/`, `frontend/.vite/`
- 🤖 GraphCast : `*.npz`, `.graphcast_cache/` (modèle ~5,5 Go)
- 📊 Données régénérables : `data/`, `output/`, `logs/`
- 🐳 Docker : `*.backup`, `docker-compose.override.yml`
- 🚨 Exception critique : `!backend/backup/meteo_ia_db.sql` (gardé pour Git LFS)

#### 12.8 — Domaine acheté : `meteo-ia.fr`

Acquisition du domaine **`meteo-ia.fr`**. Choix du `.fr` plutôt que `.com` ou sous-domaine de `ai-elec-conso.fr` (autre projet déjà déployé) pour :
- 🎯 **Branding pro** : URL courte, mémorable, dédiée
- 🇫🇷 **Cohérence géographique** : projet centré France
- 💼 **Crédibilité B2B** : domaine séparé évite la confusion avec d'autres projets

#### 12.9 — Validation locale 100% fonctionnelle

```bash
$ docker compose up -d --build
[+] Running 4/4
 ✔ Network meteo_ia_network          Created
 ✔ Container meteo_ia_pg_db_compose  Healthy   6.4s
 ✔ Container meteo_ia_backend        Started   6.5s
 ✔ Container meteo_ia_frontend       Started   6.4s

$ docker compose ps
NAME                     STATUS                       PORTS
meteo_ia_backend         Up About an hour (healthy)   0.0.0.0:3001->3001/tcp
meteo_ia_frontend        Up About an hour (healthy)   0.0.0.0:8080->80/tcp
meteo_ia_pg_db_compose   Up About an hour (healthy)   0.0.0.0:5433->5432/tcp

$ curl -s "http://localhost:8080/api/forecast/available-times?source=graphcast" | head -c 100
{"source":"graphcast","count":48,"times":[...]}  ✅
```

Dashboard **validé visuellement** sur `http://localhost:8080` : carte France, graphiques, scores MAE, toggle FR/EN, mode dark — tout fonctionne.

#### 🚧 Reste à faire pour boucler V1.0

- [ ] Configuration Git LFS pour le backup DB 333 Mo (1 commande : `git lfs track "backend/backup/*.sql"`)
- [ ] `git init` + premier commit + création repo GitHub `meteo_ia_france` (public)
- [ ] `git push -u origin main` (avec push LFS du dump 333 Mo)
- [ ] SSH VPS OVH (`vps-fd6225c4.vps.ovh.net`) + `git clone` + `docker compose --env-file .env.production up -d --build`
- [ ] Configuration DNS chez OVH : record A `meteo-ia.fr` → IP VPS (propagation ~1-4h)
- [ ] Nginx **host** sur le VPS (en plus du Nginx du container frontend) : reverse proxy `meteo-ia.fr` → `localhost:8080`
- [ ] Certbot Let's Encrypt : `certbot --nginx -d meteo-ia.fr -d www.meteo-ia.fr` pour HTTPS automatique
- [ ] Crontab UTC pour les 4 pipelines Python (acquisition data quotidienne)
- [ ] Création du fichier `DEPLOY.md` documentant la procédure complète

---

## 🎓 Les 6 plus gros défis et leur résolution

### 1. JAX sur Mac Intel CPU (8 jours d'inférences)

**Problème** : GraphCast Operational utilise JAX (pas PyTorch), et nécessite ~6 Go de RAM pour une inférence sur grille France. Pas de GPU sur Mac Intel.

**Solution** : Accepter une inférence CPU lente (~5–8 min par run), planifier en cron de nuit, conserver tous les runs en DB pour pouvoir analyser la dégradation par horizon a posteriori. Ne pas tenter d'API on-demand.

---

### 2. Latence ERA5 J-6 vs J-5 annoncée

**Problème** : ECMWF annonce officiellement une latence J-5 pour ERA5T, mais en réalité les dernières heures du J-5 sont parfois encore en cours de production à 16h UTC, ce qui fait échouer les téléchargements automatiques.

**Solution** : Prendre **J-6 par défaut** dans les pipelines (marge de sécurité de 24h). Les benchmarks sont donc évalués 6 jours après les prédictions, mais on a la garantie que les données sont stables.

---

### 3. MAE cyclique pour wind_direction

**Problème** : MAE linéaire naïf donnait ~110° d'erreur moyenne sur la direction du vent (artefact mathématique des bordures 0°/360°), inutilisable.

**Solution** : Implémenter un MAE circulaire avec `min(|a-b| mod 360, 360 - |a-b| mod 360)`. Résultat : 34° pour AROME, 68° pour GraphCast — cohérent avec les benchmarks ECMWF (20–40°). Le `bias` est forcé à `NULL` car n'a pas d'interprétation physique simple pour les variables cycliques.

---

### 4. Format LONG vs WIDE en DB

**Problème** : Format WIDE (1 colonne par variable) = ajouter une variable nécessite un `ALTER TABLE` et de modifier tous les pipelines. Format LONG (1 ligne par variable × point × instant) = simple `INSERT` mais SQL plus complexe.

**Solution** : Choisir LONG pour l'évolutivité (ajouter `total_cloud_cover` en v1.1 ne demande aucune modification du schéma). SQL légèrement plus complexe accepté en échange de la robustesse architecturale. Pattern standard en data engineering météo.

---

### 5. Z-index Leaflet vs Radix dropdowns

**Problème** : Les dropdowns shadcn/Radix s'ouvraient **derrière** les tooltips Leaflet de la carte. Tooltips et dropdowns ne pouvaient pas coexister.

**Solution** : CSS global `[data-slot="select-content"]` à `z-index: 9999 !important` pour passer au-dessus de Leaflet (qui culmine à ~1000). Idem pour `[data-slot="dialog-content"]` et `[data-slot="dialog-overlay"]` à 9998/9999. Hiérarchie z-index propre établie pour tout le projet.

---

### 6. Confrontation API runtime ↔ frontend (étape 10)

**Problème** : En passant du mode JSON statique au mode API runtime, **3 vrais bugs invisibles en mode statique** sont apparus :
1. **CORS multi-port** : Vite démarrait sur 5174 (port 5173 occupé), backend autorisait seulement 5173 → toutes les requêtes API bloquées par CORS
2. **Coordonnées Paris** : frontend envoyait `lat=48.85, lon=2.35` (Paris exact), backend cherchait sur la grille 0.25° et ne trouvait rien → tableaux vides retournés
3. **Latence ERA5 J-6** : frontend demandait la heatmap pour `2026-04-27 18h` mais ERA5 a une latence de 6 jours → 404 systématique sur les comparaisons

**Solution** : Le **mode hybride (API runtime + JSON statique)** a permis d'identifier ces problèmes avant la production. Pour chaque bug : (1) libération du port 5173 et plan d'élargissement CORS en dev ; (2) alignement coordonnées Paris sur la grille la plus proche `lat=49, lon=2.5` ; (3) appel de `available-times?source=era5` au lieu de `?source=arome` pour ne demander que les dates où la comparaison est possible.

**Leçon retenue** : un mode hybride n'est pas seulement utile pour la flexibilité opérationnelle (CDN vs API live). C'est aussi un **outil de validation du contrat backend** qui révèle des incohérences qui resteraient cachées avec un seul mode.

---

### 7. Latence backend 10 secondes sur cold cache (étape 11)

**Problème** : Au premier clic sur une ville, le tableau MAE et les courbes mettaient **10 à 15 secondes** à apparaître. Le profilage curl par endpoint a révélé deux causes additives : (a) absence d'index `(latitude, longitude, timestamp)` sur les 3 tables de prédictions (full scan sur 654K lignes) et (b) endpoint `/available-times` faisant un `GROUP BY` + `ARRAY_AGG(DISTINCT...)` non indexable, exécuté 3 fois par chargement de page (× 3 sources).

**Solution architecturale en deux temps** :

1. **Indexation B-tree composite** sur les 3 tables : `CREATE INDEX idx_arome_lat_lon_time ON arome_forecasts (latitude, longitude, "timestamp" DESC)`. Gain mesuré : 10 s → 77 ms (130×).
2. **Cache en 4 couches** : TTL 1 h sur `/available-times` (les données ne changent que quotidiennement) + endpoint `POST /cache/clear` invoqué automatiquement par le hook `regenerate_frontend_json.py` après ingestion + pre-warming au démarrage backend (les 3 sources hydratées 1 s après `app.listen`) + cron keep-alive (`*/30 6-22 * * *`).

**Résultat final** : refresh page mode API passe de 18 s à <200 ms (90×). Cache hit ~5 ms.

**Leçon retenue** : un index `B-tree` composite sur les 3 colonnes les plus filtrées (latitude, longitude, timestamp) résout 80 % des problèmes de performance sur des tables analytiques de moins de 10M de lignes. Le cache n'est qu'un complément pour les requêtes agrégatives non indexables.

---

### 8. Wind direction : la trahison du line chart sur variable circulaire (étape 11)

**Problème** : La courbe wind_direction tracée en `LineChart` (Recharts) créait des zigzags artificiels au passage 0° / 360°. Quand le vent passait de 357° à 5° (rotation réelle de 8° via le nord), Recharts traçait une diagonale géante de 357° vers 5° comme s'il y avait eu une rotation de 352° dans l'autre sens. Visuel inexploitable.

**Solution courte qui n'a pas marché** : essayer d'insérer des `null` dans la série dès qu'un saut > 180° était détecté (`Math.abs(cur - pre) > 180 ? null : cur`). Échec : créait des trous mais introduisait des artefacts dépendants du seuil choisi (180° trop strict, 120° trop laxiste).

**Solution finale (refonte)** : reconnaître que la wind direction est une **variable circulaire**, pas linéaire. Une courbe interpolée n'a pas de sens physique pour cette variable. Passage en `BarChart` uniquement pour wind_direction (les 5 autres variables restent en `LineChart`). Chaque barre devient une mesure indépendante, plus aucune interpolation visuelle. Améliorations associées : axe Y avec labels cardinaux (`360°N`, `270°O/W`, `180°S`, `90°E`, `0°N`), tooltip enrichi (`351° N`), légende des 8 secteurs sous le graphique.

**Leçon retenue** : avant de chercher une solution algorithmique à un problème de visualisation, se demander si **la nature de la variable** est compatible avec le type de graphique choisi. Une variable circulaire ne se met pas en line chart, point.

---

## 💡 À savoir

### 🌍 Météorologie numérique
- **NWP (Numerical Weather Prediction)** : équations physiques, conditions initiales, assimilation de données satellite/sol
- **Réanalyses ERA5** : différence entre prévision et réanalyse, latence, vérité terrain
- **Modèles régionaux vs globaux** : AROME 2.5 km, ARPEGE global, ECMWF HRES
- **Variables dérivées** : wind_speed depuis u/v, TOA solaire (Spencer 1971)
- **Conventions de cumul** : `tp_6h` glissant vs `tp` instantané, attention aux pas de temps

### 🤖 Modèles IA fondation pour la météo
- **GraphCast** : architecture Graph Neural Network, formation sur ERA5 puis fine-tuning GFS
- **GraphCast Operational** : version utilisée en production (zero-shot sur GFS NOMADS)
- **JAX** : compilation JIT, immuabilité fonctionnelle (différent de PyTorch)
- **Open weights** : disponibilité des poids DeepMind sous licence permissive
- **Limitations zero-shot** : performance dégradée hors zone d'entraînement spécialisée

### 🛠️ Data engineering
- **Pipelines orchestrés** : `run_daily_pipeline.py` par module, cron, retry, idempotence
- **Format GRIB2** vs NetCDF, parsing avec eccodes/cfgrib
- **Téléchargements asynchrones** : httpx pour NOMADS, cdsapi pour ERA5
- **Format LONG en DB** : un schéma qui évolue sans `ALTER TABLE`
- **UPSERT idempotent** via `INSERT ON CONFLICT DO UPDATE`
- **Vues filtrantes** `*_fresh` pour gérer les multi-runs

### 🌐 Full-stack moderne
- **React 19** + Suspense + nouveaux hooks
- **Tailwind v4** : nouvelle syntaxe, Vite plugin natif
- **shadcn/ui** : architecture "copy-paste" plutôt que dépendance
- **Recharts** : courbes temps série synchronisées, légendes interactives, axes adaptatifs
- **Leaflet** : couches multiples, fonds Stadia, tooltips riches
- **i18n bilingue** : architecture FR/EN avec routes séparées
- **Light + Dark mode** : palette OKLCH (CSS Color Level 4)

### 📚 Documentation rigoureuse
- **3 niveaux** : README racine, README par module, BENCHMARKS
- **Bilingue systématique** (FR puis EN avec "English version below")
- **Vivante** : ARCHITECTURE.md à jour à chaque étape
- **Page web publique** : Méthodologie accessible aux non-développeurs
- **Reproductibilité** : commandes curl pour vérifier les chiffres

---

## 🔮 Roadmap v1.1 / v2.0 / v3.0

### v1.1 — Court terme (post-déploiement)
- ✅ MAE circulaire pour `wind_direction` (déjà fait)
- 🟡 Comparaison `graphcast_vs_arome` (modèle vs modèle, sans vérité)
- 🟡 Endpoint `POST /api/cache/flush` (invalidation après ingestion)
- 🟡 Tests unitaires Jest + supertest sur le backend
- 🟡 Authentification basique (clé API en header) si l'API est exposée publiquement
- 🟡 Hide error stack traces en production

### v2.0 — Moyen terme
- 🟡 **Fine-tuning Pangu-Weather (Huawei) sur la France** : architecture hiérarchique 1h/3h/6h/24h, dataset ERA5 régional (gain attendu 30-50% selon littérature)
- 🟡 **Ensembling Pangu-Weather + AROME** (moyenne pondérée par variable)
- 🟡 **AROME résolution native 0.025°** : retrouver la haute résolution régionale (~2.5 km)
- 🟡 **Multi-runs quotidiens** : 4 à 8 runs/jour avec rafraîchissement des prévisions
- 🟡 **Pas de temps horaire** : capter cycles diurnes et fronts météo rapides
- 🟡 **Ajout `total_cloud_cover`** pour calcul GHI au sol (production photovoltaïque réelle)
- 🟡 **Variables 3D** : vent à 100m pour parcs éoliens

### v3.0 — Long terme
- 🟡 **ClimaX (Microsoft) fine-tuné** : foundation model alternatif à GraphCast / Pangu-Weather, fine-tunable sur données régionales France
- 🟡 Production photovoltaïque calculée avec modèle PV (GHI + température cellule)
- 🟡 Production éolienne calculée avec courbe de puissance turbines
- 🟡 Authentification utilisateur, plans payants, dashboards personnalisés par parc/région
- 🟡 Alertes temps réel sur déviations significatives entre modèles
- 🟡 API publique avec quotas et SLA

---

## 🤝 Comment contribuer

Les contributions sont les bienvenues ! Que vous soyez météorologue, data scientist, développeur ou simplement curieux du sujet, voici comment participer :

### Issues & bug reports

1. Vérifiez d'abord les [issues existantes](https://github.com/kouande/meteo_ia_france/issues)
2. Créez une nouvelle issue avec le template approprié
3. Décrivez précisément le problème (étapes pour reproduire, environnement, logs)

### Pull requests

1. Fork le projet
2. Créez une branche descriptive : `git checkout -b feat/ma-super-feature`
3. Respectez la convention de commit : `feat:`, `fix:`, `docs:`, `refactor:`, `test:`
4. Mettez à jour la documentation impactée (README du module + ARCHITECTURE.md si archi)
5. Ouvrez la PR avec une description claire

### Idées de contribution

- 🌍 Traduction des README et de l'interface dans d'autres langues (DE, ES, IT)
- 🤖 Ajout de nouveaux modèles IA (Pangu-Weather, ClimaX, Aurora)
- 📊 Nouvelles métriques (ACC, CRPS pour ensembles)
- 🗺️ Extension à d'autres zones géographiques (Europe, Mondial)
- 🧪 Tests unitaires et tests d'intégration

---

## 📜 Licence & contact

### Licence

Ce projet est distribué sous **licence MIT**. Voir le fichier [LICENSE](./LICENSE) pour les détails.

```
MIT License

Copyright (c) 2026 Adechola Emile KOUANDE

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
```

### Contact

Si vous avez des questions, des suggestions, ou si vous souhaitez collaborer :

- 📧 **Email** : [kadechola@gmail.com](mailto:kadechola@gmail.com)
- 💼 **LinkedIn** : [linkedin.com/in/kadechola](https://www.linkedin.com/in/kadechola/)
- 🎯 **Malt** : [malt.fr/profile/adecholaemilekkouande](https://www.malt.fr/profile/adecholaemilekkouande)

### Remerciements

- **ECMWF** pour ERA5 et le Climate Data Store (accès gratuit)
- **NOAA** pour GFS et NOMADS (accès gratuit)
- **Météo-France** pour AROME via data.gouv.fr (open data)
- **Google DeepMind** pour les open weights de GraphCast
- **La communauté open-source** pour Python, JAX, React, PostgreSQL, et tous les outils utilisés

---

<br/>

# 🌦️ France AI Weather

> 🇫🇷 **Version française au-dessus** ([go to French](#-météo-ia-france))

**Open-source platform for comparing weather forecast models for the energy sector.**

Daily comparison over metropolitan France of **GraphCast Operational** (Google DeepMind, AI foundation model), **AROME** (Météo-France, regional physical model), and **ERA5** (ECMWF, ground truth reference) — with interactive React dashboard, Express API, Python pipelines, and public Methodology page.

---

## 📑 Table of contents

1. [3-line pitch](#-3-line-pitch)
2. [Demo](#-demo)
3. [Key results](#-key-results)
4. [Documentation](#-documentation-1)
5. [Quick start (3 commands)](#-quick-start-3-commands)
6. [Tech stack](#-tech-stack)
7. [The project journey](#-the-project-journey)
8. [The 11 steps in detail](#-the-11-steps-in-detail)
9. [The 6 biggest challenges and how I solved them](#-the-6-biggest-challenges-and-how-i-solved-them)
10. [What I learned](#-what-i-learned)
11. [Roadmap](#-roadmap-v11--v20--v30-1)
12. [How to contribute](#-how-to-contribute)
13. [License & contact](#-license--contact)

---

## 🎯 3-line pitch

> If you work in the energy sector (wind, solar, trading), knowing **which weather model gives you the most reliable forecasts** for your geographic area is critical. France AI Weather answers this question for metropolitan France by continuously comparing a generalist AI model (GraphCast) against a regional physical model (AROME), with ERA5 as ground truth.

The goal isn't to replace commercial providers but to provide a **transparent, reproducible, open-source platform** to evaluate real model performance.

---

## 🎬 Demo

🌐 **Production URL**: `https://meteo-ia.fr` 

📸 **Screenshots**

| Main dashboard | Methodology page |
|---|---|
| Interactive France map + 6 time-series charts + MAE table | 8 sections: glossary, variables, sources, comparison, limitations, roadmap, architecture |

🎥 **Demo GIF**: *(coming after deployment)*

---

## 🏆 Key results

Over metropolitan France, at 24-hour horizon, on 3 evaluation days (April 17–19, 2026, **35,100 measurement pairs per variable per model**):

| Variable | GraphCast vs ERA5 (MAE) | AROME vs ERA5 (MAE) | Ratio AROME / GraphCast |
|---|---|---|---|
| 🌡️ Temperature 2 m (°C) | **3.81** | **1.16** | **AROME 3.3× more accurate** |
| 🌬️ Wind speed 10 m (m/s) | 1.38 | 0.83 | AROME 1.7× more accurate |
| 🧭 Wind direction 10 m (°) ⚙️ | 67.55 | 33.89 | AROME 2.0× more accurate |
| ☁️ Sea-level pressure (hPa) | 3.44 | 0.39 | **AROME 8.7× more accurate** |
| 🌧️ Precipitation 6 h (mm) | 0.22 | 0.19 | AROME 1.2× more accurate |
| ☀️ TOA solar (W/m²) | 0.00 | 0.00 | identical (astronomical variable) |

⚙️ Wind direction uses a **circular MAE** (see [BENCHMARKS.md](./BENCHMARKS.md)).

➡️ **AROME outperforms GraphCast Operational on all 5 comparable variables**, with factors ranging from 1.2× to 8.7×. Results consistent with literature: foundation AI models without regional specialization don't match regional physical models at short/medium range.

📊 **Full details**: see [BENCHMARKS.md](./BENCHMARKS.md)

---

## 📚 Documentation

The project adopts a **clear 3-level documentation hierarchy**:

| Document | Role | Audience |
|---|---|---|
| 🌟 [README.md](./README.md) (this file) | Global vision + journey + portfolio | LinkedIn recruiter, open-source contributor |
| 🏛️ [ARCHITECTURE.md](./ARCHITECTURE.md) | End-to-end technical architecture + decisions | Architect, developer joining the project |
| 📊 [BENCHMARKS.md](./BENCHMARKS.md) | Measured results + scientific methodology | Data scientist, tech journalist, data recruiter |
| 🐍 [scripts/README.md](./scripts/README.md) | Documentation of the 4 Python pipelines | Pipeline developer |
| 🟢 [backend/README.md](./backend/README.md) | Documentation of the 8 REST endpoints | Backend developer |
| 🟢 [backend/BENCHMARKS.md](./backend/BENCHMARKS.md) | Numbers measured via the API | Backend developer |
| 🟣 [frontend/README.md](./frontend/README.md) | React component documentation | Frontend developer |

🌐 **Public Methodology page**: `/fr/methodologie` or `/en/methodology` directly on the dashboard, with 8 detailed sections (16-acronym glossary, 6 variables explained, 3 sources compared, side-by-side comparison table, v1.0 limitations, v2.0 roadmap, technical stack).

---

## 🚀 Quick start (3 commands)

### Prerequisites

- Docker Desktop (for PostgreSQL + PostGIS)
- Python 3.11 + Conda (for pipelines)
- Node.js 20+ (for backend + frontend)

### Local launch

```bash
# 1. Clone the repo and start the database
git clone https://github.com/kouande/meteo_ia_france.git && cd meteo_ia_france
docker-compose up -d                      # PostgreSQL 15 + PostGIS on port 5433

# 2. Install and start the backend (port 3001)
cd backend && npm install && cp .env.example .env && npm run dev

# 3. Install and start the frontend (port 5173)
cd ../frontend && npm install && npm run dev
```

Open `http://localhost:5173/en` in your browser.

### Bonus: regenerate data from sources

```bash
conda env create -f environment.yml && conda activate meteo_ia
python -m era5.run_daily_pipeline      # ECMWF CDS API
python -m arome.run_daily_pipeline     # data.gouv.fr
python -m graphcast_gfs.run_daily_pipeline  # NOMADS NOAA + GraphCast inference
python -m mae.run_daily_pipeline       # MAE computation
```

---

## 🛠️ Tech stack

### Backend & data engineering
- **Python 3.11** (conda env `meteo_ia`)
- **xarray, pandas, numpy, scipy** — scientific data manipulation
- **cdsapi, httpx, requests** — ERA5 / NOMADS / data.gouv.fr download
- **eccodes, cfgrib** — GRIB2 parsing
- **JAX + GraphCast** (DeepMind open weights) — AI weather inference
- **PostgreSQL 15 + PostGIS 3.4** (Docker, port 5433)
- **Node.js 20 + Express 4** — REST API (8 endpoints)
- **node-cache** TTL 600s, **helmet, CORS, rate-limiter** — security

### Frontend
- **React 19 + TypeScript 5**
- **Vite 8** — ultra-fast build and HMR
- **Tailwind CSS v4 + shadcn/ui** (Radix Nova preset)
- **Recharts** — synchronized time-series curves
- **Leaflet** — interactive France map (Stadia Alidade Smooth Dark)
- **react-router-dom v7** — FR/EN routing + Methodology page
- **TanStack Query v5** — managed HTTP client (cache, retry, dedup) ⭐ *step 10*
- **Hybrid pattern API runtime / static JSON** — transparent switching via `<DataSourceContext>` ⭐ *step 10*
- **Light + Dark mode** — Claude-style OKLCH palette

### Deployment & DevOps (V1.0)
- **Docker** (24+) + **Docker Compose** v2 — orchestration of 3 services (postgres, backend, frontend) on isolated Docker network
- **Backend Dockerfile** single-stage `node:22-alpine` (~60 MB, non-root user, healthcheck `/api/health`)
- **Frontend Dockerfile** multi-stage `node:22-alpine` builder + `nginx:1.27-alpine` production (~23 MB)
- **Frontend container's Nginx** — gzip, asset caching, React Router SPA fallback, **reverse proxy `/api/*` → backend container**
- **PostgreSQL 15 + PostGIS 3.4** (image `postgis/postgis:15-3.4-alpine`) with auto-init of the `.sql` backup (333 MB) on first startup
- **Docker healthchecks** on all 3 services (`pg_isready`, `wget /api/health`, `wget /nginx-health`) with `depends_on: condition: service_healthy`
- **Named volume `meteo_ia_pg_data`** for data persistence between restarts
- **OVH VPS Ubuntu 24** (production) — HTTPS deployment via **Nginx host + Certbot Let's Encrypt** (in progress)
- **Cron UTC on VPS OS** — orchestration of 4 daily Python pipelines
- 🟡 **CI/CD GitHub Actions**: planned V1.1 (auto Docker build on push, lint, typecheck, tests, deploy)
- 🟡 **Unit tests Jest + Vitest + pytest**: planned V1.1 (see roadmap)

---

## 📈 The project journey

### Why this project?

With the dramatic arrival of AI weather models in 2023-2024 (GraphCast, Pangu-Weather, ClimaX, Aurora), a practical question arises for the energy sector: **do these new models really outperform established regional physical models?**

The answer is neither yes nor no — it depends on the geographic area, variables of interest, forecast horizons, and whether the model has been locally specialized. This project provides a **measured, reproducible, transparent answer** for metropolitan France by setting up an end-to-end pipeline that compares GraphCast vs AROME daily, with ERA5 as the standard.

### What it does

- 📡 **Downloads and ingests** 4 data sources daily (GFS, ERA5, AROME, GraphCast)
- 🧠 **Runs GraphCast Operational inference** on the France grid (~5-8 min CPU on Mac Intel)
- 📊 **Computes MAE / RMSE / Bias** on 6 variables × 4 horizons × 2,925 GPS points daily
- 🌐 **Exposes 8 REST endpoints** to query data and metrics
- 📱 **Displays an interactive dashboard** with heatmap, 6 time-series charts, and comparison table
- 📚 **Publicly documents** methodology on a bilingual web page (FR + EN)
- 🔒 **Stays 100% open-source** — code, data, methodology, results

---

## 🗺️ The 11 steps in detail

### 🟢 Step 1 — Environment setup & source exploration

**Duration**: 2 days · **State**: ✅ Done

Setup of the conda environment `meteo_ia` (Python 3.11 + xarray, JAX, eccodes), exploration of the 3 candidate sources (ERA5 via CDS, AROME via data.gouv.fr, GraphCast via DeepMind open weights), choice of the France 0.25° grid (2,925 GPS points = 45 lat × 65 lon covering lat 41.0–51.5 and lon -5.5–9.0).

**Key decision**: use **LONG format** (1 row = 1 variable × 1 timestamp × 1 GPS point) rather than WIDE in the database, to allow adding new variables without modifying the schema.

---

### 🟢 Step 2 — ERA5 pipeline (ground truth)

**Duration**: 3 days · **State**: ✅ Done

Construction of the `era5/` pipeline that downloads from the **ECMWF Climate Data Store** (CDS API) the 5 native variables (t2m, u10, v10, msl, tp) on the France grid at 1-hour time step. Computation of derived variables (`wind_speed_10m_ms`, `wind_direction_10m_deg`, `tp_6h_mm` cumulated over 6 sliding hours).

**Key decision**: take a **D-6 latency** by safety (instead of the officially announced D-5 by ECMWF), since the last hours of D-5 are sometimes still being produced at 16:00 UTC.

**Resolved bug**: `download_format: unarchived` not respected by CDS → force local post-processing (`unzip` + `xarray.open_dataset`).

---

### 🟢 Step 3 — GraphCast Operational inference

**Duration**: 8 days (the biggest challenge of the project) · **State**: ✅ Done

Implementation of the `graphcast_gfs/` pipeline:
1. **GFS NOMADS download** (NOAA): 28 GRIB2 files per run (T-6h + T0 × 14 atmospheric levels)
2. **Pre-processing**: unit normalization, 0.25° spatial interpolation, conversion to GraphCast-compatible NetCDF
3. **GraphCast Operational inference** (DeepMind open weights, JAX): ~5-8 min on Mac Intel CPU for 4 horizons (+6h, +12h, +18h, +24h)
4. **CSV export**: 4 horizons × 8 variables × 2,925 points = **93,600 rows per day**
5. **DB ingestion** with idempotent `INSERT ON CONFLICT`

**Technical choices**:
- **JAX over PyTorch** (imposed by GraphCast)
- **Batch inference via cron**, not on-demand API (CPU is slow)
- **Keep all runs** in DB rather than deleting old ones (useful for horizon-degradation analysis)

---

### 🟢 Step 4 — AROME pipeline (Météo-France)

**Duration**: 4 days · **State**: ✅ Done

Construction of the `arome/` pipeline that downloads from **data.gouv.fr** (Météo-France open data) the 4 daily SP1 GRIB2 files (timesteps 00H06H, 07H12H, 13H18H, 19H24H), performs spatial resampling from native AROME resolution (0.025° ≈ 2.5 km) to the common 0.25° grid, then ingests into DB.

**Voluntary trade-off (v1.0 limitation)**: native AROME is 0.025° but we resample to 0.25° to align the grid with ERA5/GraphCast. **AROME loses 90% of its spatial resolution** in this operation — it is therefore disadvantaged in the comparison. Native resolution will be reintroduced in v2.0.

---

### 🟢 Step 5 — MAE pipeline (metrics computation)

**Duration**: 2 days · **State**: ✅ Done

Construction of the `mae/` pipeline that performs an SQL `INNER JOIN` between the `arome_forecasts`, `graphcast_predictions`, and `era5_truth` tables on `(timestamp, variable_name, latitude, longitude)`, computes **MAE / RMSE / Bias** for each (variable × horizon × comparison) combination over the 2,925 points, and stores everything in `mae_metrics`.

**Critical post-v1.0 fix**: implementation of a **circular MAE** for `wind_direction_10m_deg`:
```python
abs_error = min(|pred - truth| mod 360, 360 - |pred - truth| mod 360)
```
Before: average wind_direction MAE reported at ~110° (artifact of 0°/360° boundaries).
After: MAE = **34° for AROME, 68° for GraphCast** (consistent with ECMWF benchmarks of 20-40°).

The `bias` for cyclic variables is forced to `NULL` since it has no simple physical interpretation.

---

### 🟢 Step 6 — PostgreSQL + PostGIS DB schema

**Duration**: 1 day · **State**: ✅ Done

Definition of the final schema in `scripts/sql/init_db_schema.sql`:
- **4 tables**: `era5_truth`, `arome_forecasts`, `graphcast_predictions`, `mae_metrics`
- **2 views** `*_fresh` that automatically filter the most recent run per `(timestamp, variable_name, lat, lon)` tuple
- **Composite indexes** on `(timestamp, lat, lon)` for fast queries
- **UNIQUE constraints** for `INSERT ON CONFLICT` idempotence
- **`TIMESTAMP WITH TIME ZONE`** stored in UTC, conversion to Europe/Paris at frontend level
- **`utc_to_paris(ts)` function** available for manual queries

**Observed volume**: ~1.96M rows as of 04/25/2026, growth ~100 MB/month.

---

### 🟢 Step 7 — Pipeline orchestration

**Duration**: 2 days · **State**: ✅ Done

Implementation of `run_daily_pipeline.py` orchestrators for each module (4 independent pipelines). Unified logging convention, error handling with 3× retry / 30-min pause, execution report generation. Complete documentation in `scripts/README.md`.

**UTC crontab planned for production**:
```
 0  1 * * *  graphcast_gfs.run_daily_pipeline  # target run 18z, available around 1:00 UTC
30  1 * * *  arome.run_daily_pipeline          # AROME run 18z available around 22:00 UTC
 0  2 * * *  era5.run_daily_pipeline           # target D-6
 0  3 * * *  mae.run_daily_pipeline            # after ERA5
```

---

### 🟢 Step 8 — Express backend (8 REST endpoints)

**Duration**: 3 days · **State**: ✅ Done

Construction of the `backend/` (Node.js 20 + Express 4) with classic MVC architecture: `routes/` + `controllers/` + `middleware/` + `config/`. No Prisma/TypeORM — raw SQL via `pg` for transparency and performance.

**8 exposed endpoints**:

| Method | Route | Role |
|---|---|---|
| GET | `/api/health` | Healthcheck for PM2/UptimeRobot/Nginx |
| GET | `/api/status` | 4 table counts + cache stats + uptime |
| GET | `/api/forecast/available-times` | List `(date, hour)` available per source |
| GET | `/api/forecast/grid-points` | 2925 GPS points (called once on load) |
| GET | `/api/forecast/timeseries` ⭐ | 7 days × 6 variables × 3 sources for 1 GPS point |
| GET | `/api/forecast/:date/:hour` | Full grid at instant T for 1 source/variable |
| GET | `/api/mae/comparison` ⭐ | Latest MAE table + 7-day average |
| GET | `/api/mae/history` | Daily MAE evolution for 1 variable |
| GET | `/api/heatmap/error` | Spatial error grid `(source - era5)` |

**v1.0 security**: `helmet`, configurable `CORS`, `express-rate-limit` 100 req/h/IP, `node-cache` TTL 600s to reduce DB load.

📚 Full documentation: [backend/README.md](./backend/README.md) + [backend/BENCHMARKS.md](./backend/BENCHMARKS.md)

---

### 🟢 Step 9 — React frontend (the biggest work)

**Duration**: 6 days · **State**: ✅ Done

Construction of the `frontend/` with a complete interactive dashboard and a public Methodology page.

**Delivered components**:

| Component | Description |
|---|---|
| **Header** | Logo, bilingual title, live UTC+1/UTC+2 clock (automatic DST), dark/light toggle, FR/EN switch |
| **Interactive France map** | Stadia Alidade Smooth Dark background + 100 main cities with colored heatmap (visible CircleMarker) + 10 pins 📍 on the largest cities + rich tooltips on hover (name, AROME/GraphCast, ERA5 truth, absolute error) + 3 dropdowns (source/variable/timestamp) + 4 timestamps available + zoom modal without overlay |
| **MAE table** | 4 horizons (h6/h12/h18/h24) × 6 variables, colored ratio, zoom mode |
| **6 ChartCards** | One per weather variable, synchronized time-series curves (shared cursor), 3 sources superimposed, adaptive axes, zoom mode, interactive legends |
| **ZoomDialog** | Universal modal for the map, MAE table, and charts |
| **Footer** | Colored sources, copyright, version v1.0, **Methodology link** + GitHub link |
| **Methodology page** ⭐ | 8 complete sections: About, Glossary (16 acronyms), 6 variables, 3 colored sources, 14-row comparison table, 5 v1.0 limitations, v2.0 roadmap, architecture (5 cards with explicit Backend) |

**Stack & conventions**:
- React 19 + TypeScript 5 + Vite 8
- Tailwind CSS v4 + shadcn/ui (Radix Nova preset)
- Recharts for charts, Leaflet for the map
- 100% bilingual FR/EN with separate routes (`/fr`, `/en`, `/fr/methodologie`, `/en/methodology`)
- Light + Dark mode (Claude-style OKLCH palette)
- 4 real timestamps (00h, 06h, 12h, 18h UTC)

**Bugs resolved during the step**:
- Z-index Leaflet vs Radix (`data-slot="select-content"` at 9999)
- Backend `hour` format required `06` but script sent `6` → `String(t.hour).padStart(2, "0")`
- Tailwind v4 and broken CSS braces (12/12 final balanced)
- Hover sensitivity on map points (invisible CircleMarker radius=14 over)

📚 Documentation: [frontend/README.md](./frontend/README.md)

---

### 🟢 Step 10 — Hybrid pattern API runtime / static JSON

**Duration**: 1 day · **State**: ✅ Done

Connection of the React frontend to the Express API (`localhost:3001`), with a **more mature approach than a simple runtime binding**: we keep the existing static JSON mode and add an **API runtime mode alongside**, with **transparent live switching** between the two.

**Why this architectural choice**:

| Use case | Recommended mode | Why |
|---|---|---|
| 🌐 Public production (CDN, GitHub Pages, LinkedIn demo) | 💾 Static JSON | Performance, free hosting, works offline |
| 🔧 Live pedagogical demo (recruiters) | 🟢 API runtime | Visible network devtools, traceable requests |
| 🐛 Local debug (DB modification, immediate verification) | 🟢 API runtime | No rebuild after each ingestion |
| 📱 4G mobile user | 💾 Static JSON | Saves data + faster |
| 🛡️ Backend down | 💾 Static JSON (fallback) | App keeps working |

**Delivered components**:

| Component | Role |
|---|---|
| `services/apiService.ts` ⭐ | Typed service: 9 methods to the 8 Express endpoints, unified error handling, query params, strict TypeScript types |
| `contexts/DataSourceContext.tsx` ⭐ | React context managing active mode (`useApi: boolean`) with `VITE_USE_API` reading at startup and `toggleDataSource()` function for live switching |
| `hooks/useStaticData.ts` 🔄 | Hybrid hook: loads from API or from `/data/sample_forecast.json` according to context, without modifying public API |
| `hooks/useHeatmapData.ts` 🔄 | Same for heatmaps: API runtime or `/data/heatmaps/{variable}.json` |
| `components/layout/DataSourceToggle.tsx` ⭐ | 📡/💾 button in header for live switching |
| `main.tsx` 🔄 | Added `<QueryClientProvider>` (TanStack Query v5 + DevTools in dev) + `<DataSourceProvider>` |
| `.env` ⭐ | `VITE_USE_API=false` variable (static mode by default in prod) |

**Successful abstraction principle**: no consumer component (`FranceMap`, `MaeTableCard`, `ChartCard`) was modified. Hooks keep their `{ data, loading, error }` public API and switching happens internally. This separation is the **real architectural core** of the step.

**TanStack Query v5 installed**: `QueryClient` configured with 5min staleTime, 30min gcTime, 2 retries (exponential backoff). Not yet directly consumed by hooks (lightweight option: `useStaticData` and `useHeatmapData` mostly unchanged), but **ready for use** for future dedicated hooks.

**3 real bugs identified through API/frontend confrontation**:

| # | Bug | Cause | Solution |
|---|---|---|---|
| 1 | **Multi-port CORS** | Vite ran on 5174 (5173 busy by another process), backend allowed only 5173 | Free port 5173 (long-term: more permissive CORS whitelist in dev) |
| 2 | **Paris coordinates** | Frontend sent `lat=48.85, lon=2.35` (exact Paris), backend found nothing on 0.25° grid | Alignment on closest grid: `lat=49, lon=2.5` |
| 3 | **ERA5 J-6 latency** | Frontend requested heatmap for `2026-04-27 18h` but ERA5 doesn't have this date yet → 404 | Use `available-times?source=era5` instead of `?source=arome` (ERA5 constrains comparison availability) |

**Visible demonstration**: open the dashboard, click the 📡 toggle in the header → requests to `localhost:3001/api/...` appear in the browser's Network panel. Click again → return to static mode (`/data/sample_forecast.json`). Transparent switching without rebuild.

📚 Detailed documentation: [frontend/README.md](./frontend/README.md) (FR + EN)

---

### 🟢 Step 11 — Automated weather raw data acquisition pipeline

**Duration**: ~3 days · **State**: ✅ Completed

This step establishes the **continuous weather data acquisition foundation** that feeds the entire platform. Goal: ensure the PostgreSQL database is enriched daily with fresh data from 3 sources (ERA5, AROME, GraphCast Operational), with reliable, idempotent and traceable ingestion.

#### 11.1 — Four Python acquisition pipelines

Each source has its own orchestrated pipeline (`scripts/{source}/run_daily_pipeline.py`) chaining 3 to 5 steps depending on the source:

| Pipeline | Steps | Daily volume |
|---|---|---|
| **ERA5** | Fetch CDS Copernicus → Export CSV (6h cumulatives + derived variables) → DB ingestion | ~93,600 rows |
| **AROME** | Fetch GRIB2 data.gouv.fr → Parse NetCDF → Export CSV → DB ingestion | ~93,600 rows |
| **GraphCast** | Fetch GDAS GFS NOMADS → Parse NetCDF → JAX inference → Export CSV → DB ingestion | ~93,600 rows |
| **MAE** | Read predictions DB → Read ground truth ERA5 DB → Compute metrics → MAE UPSERT | ~64 rows/day |

Each pipeline supports an **auto mode** (target date computation) and a **manual mode** (`--date YYYY-MM-DD`) for historical backfill. `--skip-existing` mode to avoid re-downloading what's already on disk, `--no-db` mode for debug without touching the database.

#### 11.2 — Robust acquisition with retry and idempotence

Each critical step (CDS fetch, GRIB2 parse, DB ingestion) is wrapped in a `retry()` decorator with **3 attempts × 30-minute pause** (production configuration). This strategy absorbs transient API failures (CDS Copernicus overloaded, NOMADS in maintenance) without execution loss.

DB ingestion uses an **idempotent UPSERT** on the unique constraint `(latitude, longitude, timestamp, variable_name)`: if the pipeline is re-executed for the same date, data is updated rather than duplicated. This property is critical for incident recovery.

#### 11.3 — PostgreSQL schema for raw data

The 3 main tables adopt a **denormalized LONG format** (1 row per variable × point × timestamp) to facilitate future schema evolution without migration:

```sql
CREATE TABLE era5_truth (
    id SERIAL PRIMARY KEY,
    "timestamp" TIMESTAMP WITH TIME ZONE NOT NULL,
    latitude NUMERIC(9, 6) NOT NULL,
    longitude NUMERIC(9, 6) NOT NULL,
    variable_name VARCHAR(50) NOT NULL,  -- t2m_celsius, u10_ms, msl_hpa, ...
    value NUMERIC(15, 6),
    run_date TIMESTAMP WITH TIME ZONE,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (timestamp, latitude, longitude, variable_name)
);
-- B-tree composite index for GPS-point queries
CREATE INDEX idx_era5_lat_lon_time
  ON era5_truth (latitude, longitude, "timestamp" DESC);
```

Similar schema for `arome_forecasts` and `graphcast_predictions`. `*_fresh` views that return only the latest run per date for frontend queries, with old runs preserved for historical analysis.

#### 11.4 — Centralized structured logging

Shared helper `scripts/utils/logging_setup.py` exposing `setup_pipeline_logging(source_name)`. Configures simultaneously:
- Console (`StreamHandler` on `stdout`) — for live tracking
- File (`FileHandler(mode="a", encoding="utf-8")`) — cumulative history

Four permanent files in `logs/`: `arome.log`, `era5.log`, `graphcast.log`, `mae.log`. Each execution appends (no overwrite), with a banner `🚀 Nouveau run de pipeline : {SOURCE}` at the start to visualize boundaries between executions. ISO format `YYYY-MM-DD HH:MM:SS [LEVEL] message` for easy parsing by log management tools.

#### 11.5 — Credentials security

Sensitive information (CDS Copernicus API key, DB password) is externalized in:
- `~/.cdsapirc` for Copernicus (official `cdsapi` library convention)
- `backend/.env` for the PostgreSQL database (standard dotenv pattern)
- `BACKEND_URL`, `DATABASE_URL` environment variables for dev/prod portability

No secret is versioned in Git (exhaustive `.gitignore`).

#### 🎁 Bonus deliverables completed during this step

Beyond automated acquisition strictly speaking, this step was the opportunity to consolidate several aspects of the platform. These deliverables are **beyond the spec** but elevate the project to production level:

| Bonus | Description | Measured impact |
|---|---|---|
| **Phase A** — City badge on ChartCards | Each chart displays `📍 {cityName}` via 3-zone flexbox layout | Immediate location readability across the 6 charts |
| **Phase B** — Interactive map synchronized with charts | `SelectedCityContext` (React Context) + TanStack Query + 0.25° grid snap | Smooth geo-temporal navigation between map and 6 ChartCards |
| **PostgreSQL B-tree composite indexes** | 3 `(latitude, longitude, timestamp DESC)` indexes on prediction tables | `/timeseries` latency: 10s → 77ms (**130×** gain) |
| **4-layer backend cache** | 1h TTL on `/available-times` + `POST /cache/clear` endpoint + boot pre-warming + cron keep-alive | Page refresh API mode: 18s → <200ms (**90×** gain), cache hit ~5ms |
| **Wind direction → bar chart** | Circular variable doesn't fit line chart (artificial 0°/360° zigzags). Bar chart + Y-axis with cardinal labels + enhanced tooltip + 8-sector legend | Correct wind direction visualization, no more zigzags |
| **3-column footer** with KAEK link | `grid-cols-[1fr_auto_1fr]` for responsive layout | KAEK link always centered, copyright without wrap |
| **Fix 100 → 103 cities** | Update `i18n/fr.ts`, `i18n/en.ts`, `lib/franceCities.ts` | UI consistency with actual list |

📚 Detailed documentation: [scripts/README.md](./scripts/README.md), [ARCHITECTURE.md](./ARCHITECTURE.md), [BACKEND.md](./BACKEND.md), [FRONTEND.md](./FRONTEND.md)

---

### 🟢 Step 12 — Full dockerization & V1.0 deployment 

**State**: 🟢 Local dockerization 100% complete · 🔜 VPS deployment in progress

**Pitch**: moving the project from a fragile local environment (each service launched manually) to a **production-grade dockerized infrastructure** orchestrated by `docker-compose`, ready to be deployed on the OVH VPS with a single commit. This step concretizes the leap from "dev code" to "deployable product".

#### 12.1 — Three production-ready Dockerfiles

**Express backend** (`backend/Dockerfile`, single-stage, ~60 MB):
- Base image `node:22-alpine` (lightweight, secure)
- Non-root `node` user (runtime security)
- `npm ci --omit=dev` (no devDependencies in prod)
- `EXPOSE 3001` + `HEALTHCHECK` pinging `/api/health` every 30s
- `.dockerignore` excludes `node_modules`, `.env`, `backup/`, `.git`, `logs`

**React/Vite frontend** (`frontend/Dockerfile`, multi-stage, ~23 MB):
- Stage 1 — **Builder**: `node:22-alpine`, runs `npm run build` with `tsc -b && vite build`
- Stage 2 — **Production**: `nginx:1.27-alpine` serving only the final `dist/`
- Build args injected at compile time: `VITE_USE_API=true`, `VITE_API_URL=""` (relative URL)
- Post-build verification: tests that `/app/dist/index.html` exists (fast failure otherwise)

**PostgreSQL + PostGIS** (official image `postgis/postgis:15-3.4-alpine`):
- Auto-init on first startup via volume mount of backup `meteo_ia_db.sql` (333 MB) on `/docker-entrypoint-initdb.d/01-init.sql`
- Named volume `meteo_ia_pg_data` for data persistence between restarts
- Healthcheck `pg_isready` every 10s with `start_period: 30s` (time for backup init to complete on first run)

#### 12.2 — Orchestration via `docker-compose.yml`

A single file at the project root (~130 lines commented in French) orchestrating the **3 services** on an isolated Docker network `meteo_ia_network`:

```yaml
services:
  postgres:    # host port 5433 → internal 5432 (5432 used by another project)
  backend:     # host port 3001 → internal 3001
               # depends_on: postgres healthy (waits for init before starting)
               # DB_HOST=postgres (Docker internal DNS resolution)
               # DB_PORT=5432 (INTERNAL port, not host's 5433)
  frontend:    # host port 8080 → internal 80 (Nginx)
               # depends_on: backend
               # build args: VITE_USE_API=true, VITE_API_URL=""
```

**Concrete benefits**:
- ✅ A single `docker compose up -d --build` launches the entire stack
- ✅ Each service auto-restarts (`restart: unless-stopped`)
- ✅ Centralized environment variables in `.env` (project root)
- ✅ Docker healthchecks ensure backend only starts **when** Postgres is ready
- ✅ Persistent volume: data survives `docker compose down` (except `down -v`)

#### 12.3 — Nginx reverse proxy `/api/*` → backend

`frontend/nginx.conf` configuration enriched with **3 critical functions**:

1. **Gzip compression** — `gzip on; gzip_types text/css application/javascript application/json;`
2. **Versioned asset caching** — `location ~* \.(css|js|woff2)$ { expires 1y; add_header Cache-Control "public, immutable"; }`
3. **Reverse proxy `/api/*` → `backend:3001`**:

```nginx
location /api/ {
    proxy_pass http://backend:3001;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_connect_timeout 30s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
}
```

→ The frontend can make relative calls (`fetch('/api/forecast/...')`), Nginx of the frontend container automatically forwards to the backend container via Docker's internal DNS. **No need for absolute `VITE_API_URL`.**

#### 12.4 — 80 TypeScript errors fixed (quality refactoring)

Switching to strict `tsc --noEmit` in Docker build revealed **~80 pre-existing TypeScript errors** undetected in dev mode (Vite tolerant). All cleanly fixed in 4 phases:

| Phase | Root cause | Errors | Solution |
|---|---|---|---|
| **1** | Unused variables/imports | 6 | Manual cleanup in `ChartCard.tsx`, `FranceMap.tsx` |
| **2** | `TimeseriesPoint` type mismatch backend ↔ frontend | 3 | Rewrite `frontend/src/types/forecast.ts` (removed obsolete `_value` suffixes) |
| **3** | `Translations` type not exported from `i18n/fr.ts` | ~62 | Added `export type Translations = DeepStringify<typeof fr>` + recursive helper `DeepStringify<T>` rendering literal types as generic `string` |
| **3 bis** | Unusable `MethodologyFr` type (literal types `as const`) | 8 | Complete rewrite of `methodology.fr.ts` with explicit `MethodologyTranslations` interface + 8 exported sub-types (`GlossaryEntry`, `VariableItem`, `SourceCard`, etc.), removed `as const` |
| **3 ter** | `methodology/*.tsx` components imported the old type | 12 | Global `sed` replacing `MethodologyFr` → `MethodologyTranslations` in 8 files |
| **4** | `tsconfig.app.json` warning "baseUrl deprecated" | 1 | Added `"ignoreDeprecations": "6.0"` |

→ Now `tsc --noEmit` passes with zero errors. The frontend Dockerfile's `npm run build` layer systematically validates TS quality at every image build.

#### 12.5 — Critical bug solved: `/api/api/` doubling

**Symptom**: after dockerization, the dashboard displayed `❌ Loading error — HTTP 404 on /api/forecast/available-times` despite backend correctly responding to direct `curl` requests.

**Diagnosis**: browser network console revealed `localhost:8080/api/api/forecast/...` (double `/api/api/`). Root cause: frontend code did `${BASE_URL}${path}` with `BASE_URL = "/api"` (from `VITE_API_URL=/api`) and `path = "/api/forecast"` (already prefixed), result: `/api/api/forecast`.

**Fix**: `VITE_API_URL=""` (empty string) in `docker-compose.yml`. The code then rebuilds `${""}${"/api/forecast"}` = `/api/forecast` ✅. The Nginx proxy then routes to `backend:3001/api/forecast`. `curl` tests confirm all routes now respond 200 OK from the frontend container.

#### 12.6 — Production config: `.env.production.example`

Creation of a **documented template** (~8 KB, commented in French) that will be committed on GitHub with **placeholder values** (`CHANGEME`). On the VPS, this template is copied to `.env.production` and filled with real values (passwords generated via `openssl rand -base64 32`).

**Variables covered**:
- 🗄️ PostgreSQL (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)
- ⚙️ Backend (NODE_ENV=production, PORT, CORS_ORIGINS=https://meteo-ia.fr, rate-limit, cache TTL)
- 🎨 Frontend (VITE_USE_API=true, VITE_API_URL="")
- 🌐 Domain (DOMAIN=meteo-ia.fr, CERTBOT_EMAIL for Let's Encrypt alerts)
- 🐍 Python pipelines (CDS_API_KEY for ERA5, NOAA_USER_AGENT for NOMADS)

#### 12.7 — Enriched `.gitignore`

Refactored root `.gitignore` (from 189 bytes to 4.7 KB) covering:
- 🔒 Secrets: `.env`, `.env.production`, with exception `!.env.production.example`
- 🐍 Python: `venv/`, `__pycache__/`, `*.pyc`
- 📦 Node: `node_modules/`, `npm-debug.log`
- 🎨 Frontend build: `dist/`, `frontend/.vite/`
- 🤖 GraphCast: `*.npz`, `.graphcast_cache/` (~5.5 GB model)
- 📊 Regenerable data: `data/`, `output/`, `logs/`
- 🐳 Docker: `*.backup`, `docker-compose.override.yml`
- 🚨 Critical exception: `!backend/backup/meteo_ia_db.sql` (kept for Git LFS)

#### 12.8 — Domain registered: `meteo-ia.fr`

Acquisition of the **`meteo-ia.fr`**. Choice of `.fr` over `.com` or subdomain of `ai-elec-conso.fr` (another already deployed project) for:
- 🎯 **Pro branding**: short, memorable, dedicated URL
- 🇫🇷 **Geographic consistency**: France-focused project
- 💼 **B2B credibility**: separate domain avoids confusion with other projects

#### 12.9 — Local validation 100% functional

```bash
$ docker compose up -d --build
[+] Running 4/4
 ✔ Network meteo_ia_network          Created
 ✔ Container meteo_ia_pg_db_compose  Healthy   6.4s
 ✔ Container meteo_ia_backend        Started   6.5s
 ✔ Container meteo_ia_frontend       Started   6.4s

$ docker compose ps
NAME                     STATUS                       PORTS
meteo_ia_backend         Up About an hour (healthy)   0.0.0.0:3001->3001/tcp
meteo_ia_frontend        Up About an hour (healthy)   0.0.0.0:8080->80/tcp
meteo_ia_pg_db_compose   Up About an hour (healthy)   0.0.0.0:5433->5432/tcp

$ curl -s "http://localhost:8080/api/forecast/available-times?source=graphcast" | head -c 100
{"source":"graphcast","count":48,"times":[...]}  ✅
```

Dashboard **visually validated** on `http://localhost:8080`: France map, charts, MAE scores, FR/EN toggle, dark mode — everything works.

#### 🚧 Remaining tasks to wrap up V1.0

- [ ] Git LFS configuration for the 333 MB DB backup (1 command: `git lfs track "backend/backup/*.sql"`)
- [ ] `git init` + first commit + creation of GitHub repo `meteo_ia_france` (public)
- [ ] `git push -u origin main` (with LFS push of the 333 MB dump)
- [ ] SSH OVH VPS (`vps-fd6225c4.vps.ovh.net`) + `git clone` + `docker compose --env-file .env.production up -d --build`
- [ ] DNS configuration at OVH: A record `meteo-ia.fr` → VPS IP (propagation ~1-4h)
- [ ] Nginx **host** on the VPS (in addition to frontend container's Nginx): reverse proxy `meteo-ia.fr` → `localhost:8080`
- [ ] Certbot Let's Encrypt: `certbot --nginx -d meteo-ia.fr -d www.meteo-ia.fr` for automatic HTTPS
- [ ] UTC crontab for the 4 Python pipelines (daily data acquisition)
- [ ] Creation of `DEPLOY.md` file documenting the complete procedure

---

## 🎓 The 6 biggest challenges and how I solved them

### 1. JAX on Mac Intel CPU (8 days of inferences)

**Problem**: GraphCast Operational uses JAX (not PyTorch) and requires ~6 GB of RAM for inference on the France grid. No GPU on Mac Intel.

**Solution**: Accept slow CPU inference (~5-8 min per run), schedule night cron, keep all runs in DB to enable post-hoc horizon-degradation analysis. Don't attempt on-demand API.

---

### 2. ERA5 latency D-6 vs announced D-5

**Problem**: ECMWF officially announces D-5 latency for ERA5T, but in reality the last hours of D-5 are sometimes still being produced at 16:00 UTC, causing automatic downloads to fail.

**Solution**: Take **D-6 by default** in pipelines (24h safety margin). Benchmarks are therefore evaluated 6 days after predictions, but we have the guarantee that data is stable.

---

### 3. Circular MAE for wind_direction

**Problem**: Naive linear MAE gave ~110° average error on wind direction (mathematical artifact of 0°/360° boundaries), unusable.

**Solution**: Implement circular MAE with `min(|a-b| mod 360, 360 - |a-b| mod 360)`. Result: 34° for AROME, 68° for GraphCast — consistent with ECMWF benchmarks (20-40°). The `bias` is forced to `NULL` since it has no simple physical interpretation for cyclic variables.

---

### 4. LONG vs WIDE format in DB

**Problem**: WIDE format (1 column per variable) = adding a variable requires `ALTER TABLE` and modifying all pipelines. LONG format (1 row per variable × point × instant) = simple `INSERT` but more complex SQL.

**Solution**: Choose LONG for evolutivity (adding `total_cloud_cover` in v1.1 requires no schema modification). Slightly more complex SQL accepted in exchange for architectural robustness. Standard pattern in weather data engineering.

---

### 5. Z-index Leaflet vs Radix dropdowns

**Problem**: shadcn/Radix dropdowns opened **behind** Leaflet map tooltips. Tooltips and dropdowns couldn't coexist.

**Solution**: Global CSS `[data-slot="select-content"]` at `z-index: 9999 !important` to pass over Leaflet (which peaks at ~1000). Same for `[data-slot="dialog-content"]` and `[data-slot="dialog-overlay"]` at 9998/9999. Clean z-index hierarchy established for the entire project.

---

### 6. API runtime ↔ frontend confrontation (step 10)

**Problem**: Switching from static JSON mode to API runtime mode, **3 real bugs invisible in static mode** appeared:
1. **Multi-port CORS**: Vite started on 5174 (port 5173 busy), backend allowed only 5173 → all API requests blocked by CORS
2. **Paris coordinates**: frontend sent `lat=48.85, lon=2.35` (exact Paris), backend searched on 0.25° grid and found nothing → empty arrays returned
3. **ERA5 J-6 latency**: frontend requested heatmap for `2026-04-27 18h` but ERA5 has 6-day latency → systematic 404 on comparisons

**Solution**: The **hybrid mode (API runtime + static JSON)** allowed identifying these problems before production. For each bug: (1) free port 5173 and CORS broadening plan in dev; (2) align Paris coordinates on closest grid point `lat=49, lon=2.5`; (3) call `available-times?source=era5` instead of `?source=arome` to only request dates where comparison is possible.

**Lesson learned**: A hybrid mode isn't only useful for operational flexibility (CDN vs live API). It's also a **backend contract validation tool** that reveals inconsistencies which would remain hidden with a single mode.

---

### 7. 10-second backend latency on cold cache (step 11)

**Problem**: On the first city click, the MAE table and charts took **10 to 15 seconds** to appear. Per-endpoint curl profiling revealed two additive causes: (a) absence of `(latitude, longitude, timestamp)` index on the 3 prediction tables (full scan over 654K rows) and (b) the `/available-times` endpoint performing a non-indexable `GROUP BY` + `ARRAY_AGG(DISTINCT...)`, executed 3 times per page load (× 3 sources).

**Two-step architectural solution**:

1. **Composite B-tree indexing** on the 3 tables: `CREATE INDEX idx_arome_lat_lon_time ON arome_forecasts (latitude, longitude, "timestamp" DESC)`. Measured gain: 10s → 77ms (130×).
2. **4-layer cache**: 1h TTL on `/available-times` (data only changes daily) + `POST /cache/clear` endpoint invoked automatically by the `regenerate_frontend_json.py` hook after ingestion + startup pre-warming (the 3 sources hydrated 1s after `app.listen`) + cron keep-alive (`*/30 6-22 * * *`).

**Final result**: page refresh in API mode goes from 18s to <200ms (90×). Cache hit ~5ms.

**Lesson learned**: A composite B-tree index on the 3 most-filtered columns (latitude, longitude, timestamp) solves 80% of performance issues on analytical tables under 10M rows. Cache is only a complement for non-indexable aggregative queries.

---

### 8. Wind direction: the line chart betrayal on circular variables (step 11)

**Problem**: The wind_direction curve drawn as a `LineChart` (Recharts) created artificial zigzags at 0°/360° crossings. When wind passed from 357° to 5° (real 8° rotation through north), Recharts drew a giant diagonal from 357° to 5° as if there had been a 352° rotation in the opposite direction. Visually unusable.

**Short solution that didn't work**: try inserting `null` values in the series whenever a jump > 180° was detected (`Math.abs(cur - pre) > 180 ? null : cur`). Failed: created gaps but introduced threshold-dependent artifacts (180° too strict, 120° too lax).

**Final solution (rework)**: recognize that wind direction is a **circular variable**, not linear. An interpolated curve has no physical meaning for this variable. Switch to `BarChart` only for wind_direction (the 5 other variables remain in `LineChart`). Each bar becomes an independent measurement, no more visual interpolation. Associated improvements: Y-axis with cardinal labels (`360°N`, `270°W/O`, `180°S`, `90°E`, `0°N`), enhanced tooltip (`351° N`), 8-sector legend below the chart.

**Lesson learned**: before seeking an algorithmic solution to a visualization problem, ask whether **the nature of the variable** is compatible with the chart type chosen. A circular variable doesn't go in a line chart, period.

---

## 💡 Good to Know

### 🌍 Numerical weather prediction
- **NWP (Numerical Weather Prediction)**: physical equations, initial conditions, satellite/ground data assimilation
- **ERA5 reanalyses**: difference between forecast and reanalysis, latency, ground truth
- **Regional vs global models**: AROME 2.5 km, ARPEGE global, ECMWF HRES
- **Derived variables**: wind_speed from u/v, TOA solar (Spencer 1971)
- **Accumulation conventions**: `tp_6h` sliding vs `tp` instantaneous, beware of time steps

### 🤖 AI foundation models for weather
- **GraphCast**: Graph Neural Network architecture, training on ERA5 then GFS fine-tuning
- **GraphCast Operational**: production version (zero-shot on GFS NOMADS)
- **JAX**: JIT compilation, functional immutability (different from PyTorch)
- **Open weights**: availability of DeepMind weights under permissive license
- **Zero-shot limitations**: degraded performance outside specialized training area

### 🛠️ Data engineering
- **Orchestrated pipelines**: `run_daily_pipeline.py` per module, cron, retry, idempotence
- **GRIB2 vs NetCDF format**, parsing with eccodes/cfgrib
- **Asynchronous downloads**: httpx for NOMADS, cdsapi for ERA5
- **LONG format in DB**: a schema that evolves without `ALTER TABLE`
- **Idempotent UPSERT** via `INSERT ON CONFLICT DO UPDATE`
- **Filtering views** `*_fresh` to handle multi-runs

### 🌐 Modern full-stack
- **React 19** + Suspense + new hooks
- **Tailwind v4**: new syntax, native Vite plugin
- **shadcn/ui**: "copy-paste" architecture rather than dependency
- **Recharts**: synchronized time-series, interactive legends, adaptive axes
- **Leaflet**: multiple layers, Stadia backgrounds, rich tooltips
- **Bilingual i18n**: FR/EN architecture with separate routes
- **Light + Dark mode**: OKLCH palette (CSS Color Level 4)

### 📚 Rigorous documentation
- **3 levels**: root README, per-module README, BENCHMARKS
- **Systematic bilingual** (FR then EN with "English version below")
- **Living**: ARCHITECTURE.md updated at each step
- **Public web page**: Methodology accessible to non-developers
- **Reproducibility**: curl commands to verify numbers

---

## 🔮 Roadmap v1.1 / v2.0 / v3.0

### v1.1 — Short term (post-deployment)

**🧪 Quality & tests** (major upcoming work)
- 🟡 **Backend unit tests**: Jest + supertest on the 9 REST endpoints
- 🟡 **Frontend unit tests**: Vitest + React Testing Library on critical hooks and components
- 🟡 **Pipeline integration tests**: pytest on Python pipelines (era5, arome, graphcast_gfs, mae)
- 🟡 **Pre-commit hooks**: Husky + lint-staged + Prettier + ESLint
- 🟡 **Codecov**: code coverage tracking (target 70% V1.1, 85% V2.0)

**🤖 GitHub Actions CI/CD**
- 🟡 `lint-typecheck` workflow on every PR (tsc --noEmit + ESLint + Prettier check)
- 🟡 `build-docker` workflow that builds the 2 Docker images on push to main
- 🟡 `test` workflow running Jest + Vitest + pytest
- 🟡 `deploy` workflow that SSHs to VPS and runs `git pull && docker compose up -d --build` (auto-deploy)

**⚡ GraphCast architectural refactoring**
- 🟡 **Dedicated GraphCast FastAPI** (`graphcast_api/`, port 8001): pull inference out of the cron pipeline to make it on-demand
- 🟡 Orchestration script `forecasting_pipeline/trigger_and_ingest_forecast.py` calling the API instead of in-process execution
- 🟡 Refactor GraphCast `run_daily_pipeline.py` to use the API rather than load the model on every run

**🔬 Weather metrics improvements**
- ✅ Circular MAE for `wind_direction` (already done in V1.0)
- 🟡 `graphcast_vs_arome` comparison (model vs model, no truth)
- 🟡 **Normalized Skill Score** vs persistent climatology (standard meteorology metric)
- 🟡 **GraphCast bias correction** by variable / region / season offset learned on ERA5
- 🟡 **CRPS / Brier score** segmented by thresholds for rigorous precipitation evaluation

**🛡️ Security & robustness**
- 🟡 `POST /api/cache/flush` endpoint (invalidation after ingestion)
- 🟡 Basic authentication (API key in header) if API is publicly exposed
- 🟡 Hide error stack traces in production (`NODE_ENV=production` → `details: undefined`)
- 🟡 More permissive CORS whitelist in dev (regex `localhost:51\d{2}`)

**📦 Optional: split monorepo into 4 repos**
- 🟡 `meteo-ia-france-pipelines` (Python pipelines + DB schema)
- 🟡 `meteo-ia-france-api` (GraphCast FastAPI)
- 🟡 `meteo-ia-france-backend` (Express)
- 🟡 `meteo-ia-france-frontend` (React + Vite)

### v2.0 — Medium term
- 🟡 **Pangu-Weather (Huawei) fine-tuning on France**: hierarchical 1h/3h/6h/24h architecture, regional ERA5 dataset (expected gain 30-50% per literature)
- 🟡 **Pangu-Weather + AROME ensembling** (per-variable weighted average)
- 🟡 **AROME native 0.025° resolution**: regain regional high resolution (~2.5 km)
- 🟡 **Multiple daily runs**: 4 to 8 runs/day with forecast refresh
- 🟡 **Hourly time step**: capture diurnal cycles and fast weather fronts
- 🟡 **Add `total_cloud_cover`** for ground GHI computation (real PV production)
- 🟡 **3D variables**: wind at 100m for wind farms

### v3.0 — Long term
- 🟡 **ClimaX (Microsoft) fine-tuned**: alternative foundation model to GraphCast / Pangu-Weather, fine-tunable on French regional data
- 🟡 PV production calculated with PV model (GHI + cell temperature)
- 🟡 Wind production calculated with turbine power curve
- 🟡 User authentication, paid plans, personalized dashboards per farm/region
- 🟡 Real-time alerts on significant deviations between models
- 🟡 Public API with quotas and SLA

---

## 🤝 How to contribute

Contributions are welcome! Whether you're a meteorologist, data scientist, developer, or simply curious about the topic, here's how to participate:

### Issues & bug reports

1. First check [existing issues](https://github.com/kouande/meteo_ia_france/issues)
2. Create a new issue with the appropriate template
3. Precisely describe the problem (steps to reproduce, environment, logs)

### Pull requests

1. Fork the project
2. Create a descriptive branch: `git checkout -b feat/my-cool-feature`
3. Respect the commit convention: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`
4. Update impacted documentation (module README + ARCHITECTURE.md if architecture)
5. Open the PR with a clear description

### Contribution ideas

- 🌍 Translation of READMEs and interface in other languages (DE, ES, IT)
- 🤖 Adding new AI models (Pangu-Weather, ClimaX, Aurora)
- 📊 New metrics (ACC, CRPS for ensembles)
- 🗺️ Extension to other geographic areas (Europe, Worldwide)
- 🧪 Unit tests and integration tests

---

## 📜 License & contact

### License

This project is distributed under the **MIT License**. See [LICENSE](./LICENSE) for details.

### Contact

If you have questions, suggestions, or want to collaborate:

- 📧 **Email**: [kadechola@gmail.com](mailto:kadechola@gmail.com)
- 💼 **LinkedIn**: [linkedin.com/in/kadechola](https://www.linkedin.com/in/kadechola/)
- 🎯 **Malt**: [malt.fr/profile/adecholaemilekkouande](https://www.malt.fr/profile/adecholaemilekkouande)

### Acknowledgments

- **ECMWF** for ERA5 and the Climate Data Store (free access)
- **NOAA** for GFS and NOMADS (free access)
- **Météo-France** for AROME via data.gouv.fr (open data)
- **Google DeepMind** for GraphCast open weights
- **The open-source community** for Python, JAX, React, PostgreSQL, and all the tools used

---

<br/>

**🌦️ Météo IA France — Projet open-source · v1.0 · April 2026**
