# 🔌 Météo IA France — Backend

> 🇬🇧 **English version below** ([jump to English](#-météo-ia-france--backend-english))

[![Node.js](https://img.shields.io/badge/Node.js-22+-339933?logo=nodedotjs&logoColor=white)](https://nodejs.org/)
[![Express](https://img.shields.io/badge/Express-5-000000?logo=express&logoColor=white)](https://expressjs.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![PostGIS](https://img.shields.io/badge/PostGIS-3.4-336791?logo=postgresql&logoColor=white)](https://postgis.net/)

API REST Express qui expose les données de comparaison de prévisions météorologiques entre **GraphCast Operational** (Google DeepMind), **AROME** (Météo-France) et **ERA5** (ECMWF, vérité terrain). Le backend est **strictement en lecture seule** sur la DB PostgreSQL : il ne fait jamais d'inférence ni d'écriture, juste des `SELECT` optimisés via la vue unifiée `forecast_unified`.

---

## 📑 Sommaire

1. [Pitch](#-pitch)
2. [Quick start](#-quick-start)
3. [Architecture](#-architecture)
4. [Les 9 endpoints REST](#-les-9-endpoints-rest)
5. [Middlewares](#-middlewares)
6. [Schéma de base de données](#-schéma-de-base-de-données)
7. [Variables d'environnement](#-variables-denvironnement)
8. [Tests et debug](#-tests-et-debug)
9. [Stack technique détaillée](#-stack-technique-détaillée)
10. [Comment contribuer](#-comment-contribuer)

---

## 🎯 Pitch

Le backend Express est une **API REST stateless et idempotente** qui sert de pont entre la base PostgreSQL (alimentée par les pipelines Python) et le frontend React. Il a été choisi pour 3 raisons clés :

1. **Légèreté** : pas de calcul lourd côté backend, juste des `SELECT` SQL → Express suffit largement (pas besoin de FastAPI ni de Spring Boot)
2. **Cohérence stack** : un seul langage (TypeScript) pour tout le code applicatif (backend + frontend)
3. **Pattern éprouvé** : architecture héritée du projet précédent `ai-elec-conso`, déjà rodée

Le backend est volontairement **simple et lisible** : ~600 lignes de code TypeScript pour 9 endpoints. Pas de magie, pas d'ORM lourd (juste `node-postgres`), pas d'abstraction inutile.

---

## 🚀 Quick start

### Prérequis

- **Node.js 20+** et **npm** (testé avec Node 22, npm 10)
- **PostgreSQL 15+** avec **PostGIS 3.4** (extension géographique pour les requêtes spatiales)
- DB peuplée par les pipelines Python (étapes 2-7 du projet)

### Installation

```bash
cd backend
npm install
```

### Configuration

Copier le fichier exemple et adapter les valeurs :

```bash
cp .env.example .env
# Éditer .env avec les credentials PostgreSQL
```

### Lancement développement (avec hot-reload)

```bash
npm run dev
```

➡️ API accessible sur **http://localhost:3001**. Logs Morgan en console.

### Lancement production

```bash
npm run build       # Compile TypeScript → JavaScript dans dist/
npm start           # Lance node dist/index.js
```

### Premier test

```bash
# Vérifie que le backend répond
curl http://localhost:3001/api/health

# Compteurs DB + uptime
curl http://localhost:3001/api/status | jq

# Liste des timestamps GraphCast disponibles
curl "http://localhost:3001/api/forecast/available-times?source=graphcast" | jq
```

---

## 🧩 Architecture

```
backend/
├── src/
│   ├── index.ts                  # Entry point Express + middlewares globaux
│   ├── db.ts                     # Pool PostgreSQL + helpers de query
│   │
│   ├── routes/
│   │   ├── health.ts             # GET /api/health
│   │   ├── status.ts             # GET /api/status
│   │   ├── forecast.ts           # GET /api/forecast/* (4 endpoints)
│   │   ├── mae.ts                # GET /api/mae/* (2 endpoints)
│   │   └── heatmap.ts            # GET /api/heatmap/error
│   │
│   ├── middlewares/
│   │   ├── cache.ts              # Cache RAM avec TTL configurable
│   │   ├── rateLimit.ts          # 100 req/h/IP avec express-rate-limit
│   │   └── errorHandler.ts       # Handler central pour les erreurs DB
│   │
│   ├── services/
│   │   ├── forecastService.ts    # Logique métier des prévisions
│   │   └── maeService.ts         # Calcul d'agrégats MAE
│   │
│   └── types/
│       ├── forecast.ts           # Interfaces TypeScript des réponses API
│       └── db.ts                 # Types des résultats SQL bruts
│
├── tests/                        # Tests Jest + supertest (à venir v1.1)
├── .env.example                  # Template variables d'environnement
├── package.json
├── tsconfig.json
└── README.md                     # Ce fichier
```

### Principes architecturaux

#### 1. Stateless et idempotent

Le backend ne stocke **rien en local** (pas de session, pas de fichiers temporaires, pas de cookies). Tout l'état est dans PostgreSQL. Conséquence : on peut redémarrer le backend à n'importe quel moment, ou en faire tourner plusieurs instances en parallèle (load balancing futur), sans risque.

#### 2. Lecture seule sur la DB

Aucun endpoint ne fait de `INSERT`, `UPDATE` ou `DELETE`. Toutes les écritures viennent des **pipelines Python** (étapes 2-5 du projet). Cette séparation stricte garantit qu'un bug backend ne peut **jamais** corrompre les données.

#### 3. Vue SQL unifiée

Tous les endpoints lisent depuis la **vue `forecast_unified`** qui agrège les 3 sources (ERA5, AROME, GraphCast) avec un schéma uniforme. Les pipelines écrivent dans 3 tables séparées, mais le backend ne voit qu'une vue cohérente :

```sql
SELECT lat, lon, run_date, run_hour, forecast_hour, source, variable, value
FROM forecast_unified
WHERE run_date = '2026-04-21' AND run_hour = 0 AND forecast_hour = 24;
```

#### 4. Cache RAM avec TTL

Un middleware `cache.ts` maison stocke les réponses en RAM avec un TTL de 10 min par défaut (configurable). Avantage : les requêtes répétées des utilisateurs sur le même timestamp ne re-frappent pas la DB. Pas besoin de Redis pour le MVP.

---

## 🛣️ Les 9 endpoints REST

### `GET /api/health`

**Rôle** : test de connectivité (lifecheck pour PM2 / Nginx / monitoring)

```bash
curl http://localhost:3001/api/health
```

**Réponse** : `200 OK`

```json
{ "status": "ok", "timestamp": "2026-04-27T18:00:00Z" }
```

---

### `GET /api/status`

**Rôle** : statistiques globales (compteurs DB, état du cache, uptime serveur)

```bash
curl http://localhost:3001/api/status
```

**Réponse** : `200 OK`

```json
{
  "uptime_seconds": 14823,
  "node_version": "v22.7.0",
  "database": {
    "connected": true,
    "rows_total": 1962847,
    "rows_era5": 654216,
    "rows_arome": 654316,
    "rows_graphcast": 654315,
    "last_ingestion": "2026-04-27T08:00:00Z"
  },
  "cache": {
    "hits": 12453,
    "misses": 1827,
    "hit_rate": 0.872,
    "size_mb": 14.3
  }
}
```

**Cache** : 30 secondes (les compteurs ne changent pas vite)

---

### `GET /api/forecast/available-times`

**Rôle** : liste des `(date, hour)` disponibles pour une source donnée

**Query params** :
- `source` : `era5` | `arome` | `graphcast` (requis)

```bash
curl "http://localhost:3001/api/forecast/available-times?source=graphcast"
```

**Réponse** : `200 OK`

```json
{
  "source": "graphcast",
  "count": 124,
  "times": [
    { "date": "2026-04-21", "hour": 0 },
    { "date": "2026-04-21", "hour": 6 },
    { "date": "2026-04-21", "hour": 12 },
    ...
  ]
}
```

**Cache** : 5 min (la liste évolue à chaque ingestion)

**Usage frontend** : `useStaticData` (graphcast + arome) et `useHeatmapData` (era5, pour ne demander que les dates où la comparaison est possible)

---

### `GET /api/forecast/grid-points`

**Rôle** : liste des 2925 points GPS de la grille 0.25° couvrant la France métropolitaine

```bash
curl "http://localhost:3001/api/forecast/grid-points"
```

**Réponse** : `200 OK`

```json
{
  "count": 2925,
  "points": [
    { "lat": 41.0, "lon": -5.0 },
    { "lat": 41.0, "lon": -4.75 },
    ...
    { "lat": 51.5, "lon": 9.5 }
  ]
}
```

**Cache** : 1h (la grille ne change jamais)

---

### `GET /api/forecast/timeseries`

**Rôle** : séries temporelles d'une variable sur N jours pour un point GPS donné

**Query params** :
- `lat` : latitude (requis, doit être un point de la grille)
- `lon` : longitude (requis)
- `days` : nombre de jours (défaut : 7)
- `variable` : variable météo (défaut : `t2m_celsius`)

```bash
curl "http://localhost:3001/api/forecast/timeseries?lat=49&lon=2.5&days=7&variable=t2m_celsius"
```

**Réponse** : `200 OK`

```json
{
  "lat": 49.0,
  "lon": 2.5,
  "variable": "t2m_celsius",
  "unit": "°C",
  "days": 7,
  "series": {
    "era5": [
      { "timestamp": "2026-04-20T00:00:00Z", "value": 8.3 },
      ...
    ],
    "arome": [...],
    "graphcast": [...]
  }
}
```

**Cache** : 10 min

---

### `GET /api/forecast/:date/:hour`

**Rôle** : grille complète à un instant T (toutes variables, toutes sources)

**Path params** :
- `date` : format `YYYY-MM-DD`
- `hour` : format `HH` zero-padded (ex: `06`, pas `6`)

```bash
curl "http://localhost:3001/api/forecast/2026-04-21/00"
```

**Réponse** : `200 OK` (volumineux, ~5 MB pour la grille complète)

```json
{
  "date": "2026-04-21",
  "hour": 0,
  "variables": ["t2m_celsius", "wind_speed_10m_ms", ...],
  "data": [
    {
      "lat": 49.0,
      "lon": 2.5,
      "era5": { "t2m_celsius": 12.3, "wind_speed_10m_ms": 4.1, ... },
      "arome": { "t2m_celsius": 12.5, ... },
      "graphcast": { "t2m_celsius": 11.9, ... }
    },
    ...
  ]
}
```

**Cache** : 30 min

---

### `GET /api/mae/comparison`

**Rôle** : tableau MAE comparatif AROME vs GraphCast par variable, agrégé sur N jours

**Query params** :
- `horizon` : horizon de prévision (`6`, `12`, `18`, `24`) — requis
- `days` : période d'agrégation (défaut : 7)

```bash
curl "http://localhost:3001/api/mae/comparison?horizon=24&days=7"
```

**Réponse** : `200 OK`

```json
{
  "horizon_hours": 24,
  "days": 7,
  "variables": [
    {
      "name": "t2m_celsius",
      "label": "Température 2m",
      "unit": "°C",
      "arome": { "mae": 1.16, "bias": -0.08, "n_samples": 20475 },
      "graphcast": { "mae": 3.81, "bias": 0.92, "n_samples": 20475 },
      "ratio_graphcast_over_arome": 3.27
    },
    ...
  ]
}
```

**Cache** : 15 min

**Note** : pour `wind_direction_10m_deg`, le `bias` est forcé à `null` car la direction du vent est cyclique (0° = 360°), un biais moyen n'a pas de sens physique.

---

### `GET /api/mae/history`

**Rôle** : historique quotidien du MAE pour graphique d'évolution

**Query params** :
- `variable` : variable météo (défaut : `t2m_celsius`)
- `horizon` : horizon (défaut : `24`)
- `days` : période (défaut : `30`)

```bash
curl "http://localhost:3001/api/mae/history?variable=t2m_celsius&horizon=24&days=30"
```

**Réponse** : `200 OK`

```json
{
  "variable": "t2m_celsius",
  "horizon_hours": 24,
  "days": 30,
  "history": [
    { "date": "2026-03-29", "arome_mae": 1.21, "graphcast_mae": 3.94 },
    { "date": "2026-03-30", "arome_mae": 1.08, "graphcast_mae": 3.65 },
    ...
  ]
}
```

**Cache** : 30 min

---

### `GET /api/heatmap/error`

**Rôle** : grille spatiale des écarts |modèle - ERA5| pour un instant T (heatmap)

**Query params** :
- `source` : `arome` | `graphcast` (requis)
- `date` : `YYYY-MM-DD` (requis)
- `hour` : `HH` (requis)
- `variable` : variable météo (défaut : `t2m_celsius`)

```bash
curl "http://localhost:3001/api/heatmap/error?source=graphcast&date=2026-04-21&hour=18&variable=t2m_celsius"
```

**Réponse** : `200 OK`

```json
{
  "source": "graphcast",
  "date": "2026-04-21",
  "hour": 18,
  "variable": "t2m_celsius",
  "unit": "°C",
  "stats": { "mean_error": 2.34, "max_error": 7.82, "n_points": 2925 },
  "grid": [
    { "lat": 41.0, "lon": -5.0, "error": 1.23 },
    ...
  ]
}
```

**Cache** : 30 min

**Note importante** : la disponibilité dépend de **ERA5** qui a une latence de 6 jours. Le frontend utilise donc `available-times?source=era5` pour déterminer quelles dates peuvent être affichées en heatmap (cf. bug n°3 de l'étape 10).

---

### `POST /api/forecast/cache/clear` ⭐ (étape 11)

**Rôle** : invalider intégralement le cache `node-cache` du backend. Endpoint déclenché automatiquement par les pipelines Python après chaque ingestion DB réussie pour garantir la cohérence des données servies sans attendre l'expiration TTL.

```bash
curl -X POST http://localhost:3001/api/forecast/cache/clear
```

**Réponse** : `200 OK`

```json
{
  "stats_before": {
    "keys": 4,
    "hits": 287,
    "misses": 12,
    "ksize": 1024,
    "vsize": 51200
  },
  "cleared": true,
  "timestamp": "2026-04-28T16:31:42Z"
}
```

**Workflow d'invalidation automatique** :

```
Pipeline Python (era5/arome/graphcast/mae)
   ↓ ingestion DB réussie
   ↓
regenerate_frontend_json.py (hook utils)
   ↓ regénération JSON statique
   ↓
POST /api/forecast/cache/clear
   ↓ cache.flush()
   ↓
GET /api/forecast/available-times?source=arome
GET /api/forecast/available-times?source=graphcast
GET /api/forecast/available-times?source=era5
   ↓ pre-warming des 3 sources
   ✅ Cache à nouveau chaud, latence <200ms
```

**Sécurité** : pas d'authentification pour le MVP (endpoint accessible uniquement depuis localhost via le hook Python). En production, restreindre par middleware d'IP whitelist (à ajouter en étape 12).

---

## 🛡️ Middlewares

### Cache RAM (`middlewares/cache.ts`)

**Rôle** : éviter de re-frapper la DB pour des requêtes identiques répétées et garantir une latence sub-200 ms même en condition de charge.

**Implémentation** : `node-cache` (in-process, pas de Redis pour ce volume de trafic) avec TTL paramétrable par endpoint.

**Architecture du cache en 4 couches** (étape 11)

| Couche | Mécanisme | Effet |
|---|---|---|
| 1. TTL prolongé | TTL 1 h sur `/available-times` (vs 5 min ailleurs) | Les données ne changent que quotidiennement à 03h–06h Paris |
| 2. Invalidation hook | `POST /api/forecast/cache/clear` invoqué par les pipelines Python après ingestion DB | Cache cohérent dès la première requête post-ingestion |
| 3. Pre-warming | `preWarmCache()` async dans `server.js`, hydrate les 3 sources 1 s après `app.listen` | Premier visiteur ne paie jamais le cold cache (22 s en background au boot) |
| 4. Cron keep-alive | `*/30 6-22 * * * curl -s http://localhost:3001/api/forecast/available-times?source=arome` | Garde le cache chaud pendant les heures actives (gratuit, fail-safe) |

**Performance mesurée** :

| Métrique | Avant étape 11 | Après étape 11 | Gain |
|---|---|---|---|
| Latence 1er clic ville (cold) | 10–15 s | <200 ms | 50–75× |
| Refresh page mode API | 18 s | <200 ms | 90× |
| Cache hit | N/A | ~5 ms | — |

**Endpoint d'invalidation** :
```bash
POST /api/forecast/cache/clear
# Réponse : { "stats_before": {...}, "cleared": true, "timestamp": "..." }
```

**Pourquoi pas Redis ?** Pour ce volume de trafic, le cache in-process est suffisant et reste fail-safe au redémarrage grâce au pre-warming. Migration Redis envisagée seulement si load-balancing multi-instances Express (v1.2 roadmap).

### Rate limiting (`middlewares/rateLimit.ts`)

**Rôle** : protéger l'API contre les abus si elle est exposée publiquement.

**Configuration** :
- **100 requêtes / heure / IP** par défaut
- Identifiant : `req.ip` (Express trust proxy activé pour fonctionner derrière Nginx)
- Réponse en cas de dépassement : `429 Too Many Requests` avec header `Retry-After`
- Skip : `/api/health` (pour permettre les health checks PM2)

**Override par .env** :
```bash
RATE_LIMIT_MAX=1000          # 1000 req/h pour le dev
RATE_LIMIT_WINDOW_MS=3600000 # fenêtre de 1h en ms
```

### CORS (`cors` package)

**Rôle** : autoriser les appels depuis le frontend React.

**Configuration v1.0** :
- En dev : `localhost:5173` uniquement (whitelist explicite)
- En prod : domaine du frontend déployé (`https://meteo-ia-france.fr` par exemple)
- Override par `ALLOWED_ORIGINS` dans `.env`

⚠️ **Bug rencontré à l'étape 10** : si Vite démarre sur le port 5174 (5173 occupé), la requête est bloquée par CORS. Solution court terme : libérer le port 5173. Solution long terme (v1.1) : whitelist plus permissive en dev (regex `localhost:51\d{2}`).

### Logger (`morgan`)

**Rôle** : log toutes les requêtes HTTP.

**Format** : `dev` en local (coloré), `combined` en prod (parsable par les outils de monitoring).

### Error handler (`middlewares/errorHandler.ts`)

**Rôle** : centraliser le traitement des erreurs pour ne pas exposer les stack traces.

**Comportement** :
- `400` : query params manquants ou invalides
- `404` : ressource inexistante (date/hour pas en DB)
- `429` : rate limit dépassé
- `500` : erreur DB (le log Morgan capture le détail, le client reçoit un message générique)

> ⚠️ En v1.0 les stack traces remontent en réponse pour faciliter le debug. En v1.1, on les masquera (`NODE_ENV=production` → `details: undefined`).

---

## 🗄️ Schéma de base de données

### Tables principales (alimentées par les pipelines Python)

```sql
-- ERA5 (vérité terrain ECMWF, latence J-6)
CREATE TABLE era5_forecast (
  run_date DATE NOT NULL,
  run_hour SMALLINT NOT NULL,        -- 0, 6, 12, 18 (UTC)
  forecast_hour SMALLINT NOT NULL,   -- 0 toujours pour réanalyse
  lat NUMERIC(5,2) NOT NULL,
  lon NUMERIC(5,2) NOT NULL,
  variable VARCHAR(40) NOT NULL,
  value DOUBLE PRECISION,
  PRIMARY KEY (run_date, run_hour, forecast_hour, lat, lon, variable)
);

-- AROME (modèle régional Météo-France, latence 1-2h)
CREATE TABLE arome_forecast (...);  -- même schéma

-- GraphCast (IA fondation Google DeepMind, latence ~5-8 min CPU Mac)
CREATE TABLE graphcast_forecast (...);  -- même schéma
```

### Vue unifiée `forecast_unified`

```sql
CREATE VIEW forecast_unified AS
  SELECT *, 'era5' AS source FROM era5_forecast
  UNION ALL
  SELECT *, 'arome' AS source FROM arome_forecast
  UNION ALL
  SELECT *, 'graphcast' AS source FROM graphcast_forecast;
```

C'est la **seule** entrée de données du backend. Tous les endpoints SELECT depuis cette vue.

### Table MAE pré-calculée

```sql
CREATE TABLE mae_daily (
  run_date DATE NOT NULL,
  source VARCHAR(20) NOT NULL,        -- 'arome' ou 'graphcast'
  variable VARCHAR(40) NOT NULL,
  horizon_hours SMALLINT NOT NULL,    -- 6, 12, 18, 24
  mae DOUBLE PRECISION NOT NULL,
  bias DOUBLE PRECISION,              -- NULL pour wind_direction (cyclique)
  n_samples INTEGER NOT NULL,
  PRIMARY KEY (run_date, source, variable, horizon_hours)
);
```

Cette table est **calculée par le pipeline `scripts/mae/compute_mae.py`** après chaque ingestion ERA5. Le backend ne fait que lire.

### Index importants pour la performance

#### Index B-tree composites (étape 11 — gain 130×)

Trois index `(latitude, longitude, timestamp DESC)` ajoutés sur les tables de prédictions pour transformer le full scan en lookup O(log n) :

```sql
-- Étape 11 : indexation des 3 tables de prédictions par coordonnées
CREATE INDEX idx_arome_lat_lon_time
  ON arome_forecasts (latitude, longitude, "timestamp" DESC);

CREATE INDEX idx_era5_lat_lon_time
  ON era5_truth (latitude, longitude, "timestamp" DESC);

CREATE INDEX idx_graphcast_lat_lon_time
  ON graphcast_predictions (latitude, longitude, "timestamp" DESC);
```

**Impact mesuré** : `/api/forecast/timeseries?lat=46.25&lon=1.75` passe de **10 s à 77 ms** (gain 130×). Les 654K lignes ne sont plus scannées intégralement, l'index pré-trie par coordonnées.

#### Index spatial et MAE

```sql
-- Index spatial PostGIS pour requêtes par point GPS (timeseries, heatmap)
CREATE INDEX idx_era5_geo ON era5_forecast USING gist (
  ST_SetSRID(ST_MakePoint(lon, lat), 4326)
);

-- Index composite pour les agrégats MAE (mae/comparison)
CREATE INDEX idx_mae_daily_lookup ON mae_daily (run_date, horizon_hours, variable);
```

---

## ⚙️ Variables d'environnement

### `backend/.env`

```bash
# === Serveur ===
PORT=3001
NODE_ENV=development             # ou "production"

# === Base de données PostgreSQL ===
DATABASE_URL=postgresql://user:password@localhost:5432/meteo_ia
# OU séparément :
# DB_HOST=localhost
# DB_PORT=5432
# DB_NAME=meteo_ia
# DB_USER=meteo
# DB_PASSWORD=...

# === CORS ===
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5174

# === Rate limit ===
RATE_LIMIT_MAX=100               # 100 req/h/IP par défaut
RATE_LIMIT_WINDOW_MS=3600000     # 1h en ms

# === Cache ===
CACHE_TTL_MS=600000              # 10 min par défaut
CACHE_MAX_SIZE_MB=50             # limite RAM

# === Logging ===
LOG_LEVEL=info                   # debug | info | warn | error
```

⚠️ **Le fichier `.env` ne doit JAMAIS être commit** (présent dans `.gitignore`). Utiliser `.env.example` comme template.

---

## 🐳 Dockerisation V1.0 ⭐ NOUVEAU (29/04/2026)

Le backend Express est désormais entièrement conteneurisé pour le déploiement production. Cette section détaille le `Dockerfile`, le `.dockerignore` et les choix d'architecture.

### `backend/Dockerfile` — Single-stage Node 22 Alpine

```dockerfile
# Image de base : Node 22 LTS sur Alpine (légère et sécurisée)
FROM node:22-alpine

# Métadonnées
LABEL maintainer="Adéchola Émile KOUANDE <kadechola@gmail.com>"
LABEL project="meteo-ia-france"
LABEL component="backend-express-api"

# Working directory
WORKDIR /app

# Copier d'abord les manifests pour optimiser le cache des couches Docker
# (si package.json/lock ne changent pas, npm ci sera cached au prochain build)
COPY package.json package-lock.json ./

# Installer UNIQUEMENT les dépendances de production (pas de devDependencies)
# --omit=dev : pas de jest/supertest/nodemon dans l'image finale
# --no-audit --no-fund : silencieux + plus rapide
RUN npm ci --omit=dev --no-audit --no-fund && npm cache clean --force

# Copier le reste du code source (après npm ci pour cache)
COPY . .

# Sécurité : passer en utilisateur non-root (node user existe par défaut)
RUN chown -R node:node /app
USER node

# Port d'écoute (info pour Docker, ne fait rien d'autre)
EXPOSE 3001

# Healthcheck Docker : ping /api/health toutes les 30s
# Si 3 échecs consécutifs → container marqué "unhealthy"
# start_period 10s = délai de grâce avant 1er check (laisse le temps à Express de boot)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3001/api/health || exit 1

# Commande de démarrage (un seul process, pas de PM2 ni nodemon en prod)
CMD ["node", "server.js"]
```

**Caractéristiques** :
- 📦 **Image finale ~60 Mo** (Node 22 Alpine + dépendances minimales)
- 🔒 **User non-root** : `USER node` après `chown` (évite l'exécution en root par défaut)
- 🚀 **Cache Docker optimisé** : `package*.json` copiés AVANT le code source
- 🩺 **Healthcheck natif** : Docker connaît l'état réel du backend (pas juste "process up")
- 🎯 **Single-stage** : pas besoin de multi-stage car Node ne nécessite pas de "compilation" (contrairement à Vite/TypeScript)

### `backend/.dockerignore` — Exclusions critiques

```gitignore
# Ne PAS copier dans l'image
node_modules/      # Sera reconstruit par npm ci dans l'image
.env               # Secrets passés via variables compose, pas embarqués
.env.local
.env.production    # Surtout pas le .env de prod !
backup/            # Le dump 333 Mo n'a rien à faire dans le container backend
.git/              # Historique git inutile en runtime
.gitignore
logs/              # Régénérés au runtime
*.log
README.md          # Documentation, hors scope container
.DS_Store          # macOS
.vscode/
.idea/
coverage/          # Tests coverage
.nyc_output/
dist/              # Au cas où il y aurait un build artifact
```

→ **Avant `.dockerignore`** : image faisait ~450 Mo (avec `node_modules/` et `backup/` 333 Mo embarqués)
→ **Après `.dockerignore`** : image fait **~60 Mo** (gain ×7,5)

### Healthcheck `/api/health`

Le backend expose un endpoint `/api/health` consommé par le `HEALTHCHECK` Docker :

```javascript
// routes/healthRoutes.js
router.get('/health', async (req, res) => {
  try {
    // Test de connexion DB
    const result = await pool.query('SELECT NOW() as db_time');
    res.json({
      status: 'ok',
      message: 'API et DB opérationnelles',
      timestamp: new Date().toISOString(),
      uptime_seconds: Math.floor(process.uptime()),
    });
  } catch (err) {
    res.status(503).json({
      status: 'error',
      message: 'DB indisponible',
      details: err.message,
    });
  }
});
```

→ Le healthcheck **vérifie aussi la DB** (pas juste que le process Node tourne). Si Postgres tombe, le backend container est marqué `unhealthy` et redémarré automatiquement par Docker.

### Variables d'environnement injectées par Docker Compose

Quand le backend tourne dans Docker (via `docker-compose.yml`), ces variables sont injectées :

| Variable | Valeur dans le container | Source |
|---|---|---|
| `NODE_ENV` | `production` | docker-compose.yml |
| `PORT` | `3001` | docker-compose.yml |
| `DB_HOST` | **`postgres`** ⚠️ (nom du service compose, PAS `localhost`) | docker-compose.yml |
| `DB_PORT` | **`5432`** ⚠️ (port INTERNE Postgres, PAS le 5433 du host) | docker-compose.yml |
| `DB_NAME` | `meteo_ia_db` | `.env` racine projet |
| `DB_USER` | `meteo_user` | `.env` racine projet |
| `DB_PASSWORD` | (secret) | `.env` racine projet |
| `CORS_ORIGINS` | `https://meteo-ia.fr,https://www.meteo-ia.fr` | docker-compose.yml |
| `RATE_LIMIT_WINDOW_MIN` | `60` | docker-compose.yml |
| `RATE_LIMIT_MAX` | `100` | docker-compose.yml |
| `CACHE_TTL_SECONDS` | `600` | docker-compose.yml |

⚠️ **Piège classique évité** : dans le container backend, `DB_HOST` doit valoir `postgres` (le nom du service compose), pas `localhost`. Le réseau Docker résout `postgres` vers l'IP du container Postgres via DNS interne. Et `DB_PORT` = 5432 (port **dans** le container Postgres), pas 5433 (port mappé sur le host pour debug).

### Test du Dockerfile en isolation

```bash
# Build de l'image
cd backend
docker build -t meteo-ia-backend:test .

# Vérifier la taille
docker images meteo-ia-backend:test
# meteo-ia-backend   test   8c6fbe44b959   ~60 MB

# Lancer en isolation (DB pas démarrée → backend va échouer mais on voit qu'il boot)
docker run --rm -p 3001:3001 \
  -e NODE_ENV=production \
  -e PORT=3001 \
  -e DB_HOST=host.docker.internal \
  -e DB_PORT=5433 \
  -e DB_NAME=meteo_ia_db \
  -e DB_USER=meteo_user \
  -e DB_PASSWORD=mock \
  meteo-ia-backend:test
```

### Build et publish (workflow V1.1 prévu)

En V1.1, GitHub Actions construira automatiquement l'image à chaque push sur `main` :

```yaml
# .github/workflows/build-backend.yml (V1.1)
- name: Build & push backend image
  uses: docker/build-push-action@v5
  with:
    context: ./backend
    push: true
    tags: ghcr.io/adecholaA1/meteo-ia-backend:latest,ghcr.io/adecholaA1/meteo-ia-backend:${{ github.sha }}
```

---

## 🧪 Tests et debug

### Tests unitaires (à venir v1.1)

Le projet prévoit Jest + supertest pour tester les 9 endpoints :

```bash
npm test            # Lance la suite de tests
npm run test:watch  # Mode watch
npm run test:cov    # Avec coverage
```

### Test manuel rapide

```bash
# Vérifier toutes les routes en une commande
for route in health status \
  "forecast/available-times?source=graphcast" \
  "forecast/grid-points" \
  "forecast/timeseries?lat=49&lon=2.5" \
  "mae/comparison?horizon=24"; do
  echo "=== /api/$route ==="
  curl -s "http://localhost:3001/api/$route" | jq -r 'keys'
  echo ""
done
```

### Debug DB

Pour vérifier directement le contenu PostgreSQL :

```bash
# Compter les lignes par source
psql -U meteo -d meteo_ia -c "
  SELECT source, COUNT(*) FROM forecast_unified GROUP BY source;
"

# Voir les dates disponibles pour ERA5
psql -U meteo -d meteo_ia -c "
  SELECT DISTINCT run_date FROM era5_forecast ORDER BY run_date DESC LIMIT 10;
"
```

### Logs en production

PM2 redirige les logs dans `~/.pm2/logs/` :

```bash
pm2 logs meteo-backend --lines 100
pm2 monit                       # dashboard interactif
```

---

## 🛠️ Stack technique détaillée

| Catégorie | Choix | Version | Pourquoi |
|---|---|---|---|
| **Runtime** | Node.js | 22+ | LTS, performances natives |
| **Langage** | TypeScript | 5 | Type safety partagé avec le frontend |
| **Framework HTTP** | Express | 5 | Standard de facto Node.js, écosystème mature |
| **Driver SQL** | node-postgres (`pg`) | 8 | Client officiel PostgreSQL, support Pool natif |
| **Base de données** | PostgreSQL | 15 | Robuste, support JSON, partitioning natif |
| **Extension géo** | PostGIS | 3.4 | Index spatial GIST, requêtes par point GPS |
| **CORS** | `cors` | 2 | Standard Express |
| **Rate limit** | `express-rate-limit` | 7 | Memory store par défaut |
| **Logger** | `morgan` | 1 | Standard Express, format combined en prod |
| **Hot reload dev** | `tsx` | 4 | Plus rapide que ts-node + nodemon |
| **Build** | `tsc` natif | 5 | Pas besoin d'esbuild ou swc, Express est simple |
| **Process manager** | PM2 | 5 | Standard prod Node, monitoring inclus |

### Pourquoi pas FastAPI ?

Initialement le projet prévoyait Express + FastAPI (2 backends). Décision finale : **Express seul**, car :

| Critère | Express seul | Express + FastAPI |
|---|---|---|
| Complexité déploiement | 1 process | 2 processes |
| Cohérence stack | TypeScript partout | TS + Python |
| Performance backend | Identique (juste SELECT) | Identique |
| Justification calcul Python | ❌ Aucun calcul lourd | ❌ |

L'**inférence GraphCast** se fait dans les pipelines Python (offline, hors backend). Le backend ne fait que lire la DB → Express suffit largement.

---

## 🤝 Comment contribuer

### Démarrer un développement

```bash
git checkout -b feat/ma-feature
cd backend
npm install
cp .env.example .env  # adapter les credentials DB
npm run dev
```

### Conventions de code

- **TypeScript strict** : `strict: true` dans `tsconfig.json`, pas de `any` non justifié
- **Pas d'ORM** : SQL brut via `node-postgres`, plus prévisible et plus rapide
- **Routes minces** : la logique métier est dans `services/`, pas dans `routes/`
- **Async/await** partout, jamais de callbacks
- **Validation** : query params validés avant d'atteindre la DB
- **Cache approprié** : chaque nouvel endpoint définit son TTL en cohérence avec la fraîcheur attendue

### Conventions de commit

- `feat:` nouvel endpoint ou fonctionnalité
- `fix:` correction de bug
- `perf:` optimisation (index DB, cache, requête)
- `docs:` documentation
- `refactor:` refactoring
- `test:` tests
- `chore:` deps, config, CI

### Avant de pusher

```bash
npm run lint        # ESLint
npm run build       # Vérifie que la compilation TS passe
# npm test          # (à venir v1.1)
```

### Idées de contributions

- 🧪 **Tests unitaires Jest + supertest** (priorité v1.1)
- 🔐 **Authentification basique** (clé API en header) si l'API est exposée publiquement
- 📊 **Endpoint `graphcast_vs_arome`** (modèle vs modèle, sans vérité ERA5)
- 🔄 **Endpoint `POST /api/cache/flush`** (invalidation après ingestion)
- 📈 **Skill Score** vs climatologie persistante
- 🎯 **Bias correction GraphCast** par variable / région / saison appris sur ERA5
- 🌊 **CRPS / score de Brier** pour les précipitations
- 🚀 **Migration cache RAM → Redis** pour scaler horizontalement

---

# 🔌 Météo IA France — Backend (English)

> 🇫🇷 **Version française au-dessus** ([go to French](#-météo-ia-france--backend))

[![Node.js](https://img.shields.io/badge/Node.js-22+-339933?logo=nodedotjs&logoColor=white)](https://nodejs.org/)
[![Express](https://img.shields.io/badge/Express-5-000000?logo=express&logoColor=white)](https://expressjs.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![PostGIS](https://img.shields.io/badge/PostGIS-3.4-336791?logo=postgresql&logoColor=white)](https://postgis.net/)

REST Express API exposing weather forecast comparison data between **GraphCast Operational** (Google DeepMind), **AROME** (Météo-France), and **ERA5** (ECMWF, ground truth). The backend is **strictly read-only** on the PostgreSQL DB: it never runs inference or writes, just optimized `SELECT`s via the unified view `forecast_unified`.

---

## 📑 Table of contents

1. [Pitch](#-pitch-1)
2. [Quick start](#-quick-start-1)
3. [Architecture](#-architecture-1)
4. [The 9 REST endpoints](#-the-8-rest-endpoints)
5. [Middlewares](#-middlewares-1)
6. [Database schema](#-database-schema)
7. [Environment variables](#-environment-variables)
8. [Tests and debug](#-tests-and-debug)
9. [Detailed tech stack](#-detailed-tech-stack)
10. [How to contribute](#-how-to-contribute)

---

## 🎯 Pitch

The Express backend is a **stateless and idempotent REST API** that bridges the PostgreSQL database (fed by Python pipelines) and the React frontend. Chosen for 3 key reasons:

1. **Lightweight**: no heavy backend computation, just SQL `SELECT`s → Express is more than sufficient (no need for FastAPI or Spring Boot)
2. **Stack consistency**: a single language (TypeScript) for all application code (backend + frontend)
3. **Proven pattern**: architecture inherited from previous `ai-elec-conso` project, already battle-tested

The backend is intentionally **simple and readable**: ~600 lines of TypeScript code for 9 endpoints. No magic, no heavy ORM (just `node-postgres`), no unnecessary abstraction.

---

## 🚀 Quick start

### Prerequisites

- **Node.js 20+** and **npm** (tested with Node 22, npm 10)
- **PostgreSQL 15+** with **PostGIS 3.4** (geo extension for spatial queries)
- DB populated by Python pipelines (project steps 2-7)

### Installation

```bash
cd backend
npm install
```

### Configuration

Copy example file and adapt values:

```bash
cp .env.example .env
# Edit .env with PostgreSQL credentials
```

### Development launch (with hot-reload)

```bash
npm run dev
```

➡️ API accessible on **http://localhost:3001**. Morgan logs in console.

### Production launch

```bash
npm run build       # Compile TypeScript → JavaScript in dist/
npm start           # Run node dist/index.js
```

### First test

```bash
# Verify backend responds
curl http://localhost:3001/api/health

# DB counters + uptime
curl http://localhost:3001/api/status | jq

# List of GraphCast available timestamps
curl "http://localhost:3001/api/forecast/available-times?source=graphcast" | jq
```

---

## 🧩 Architecture

```
backend/
├── src/
│   ├── index.ts                  # Entry point Express + global middlewares
│   ├── db.ts                     # PostgreSQL pool + query helpers
│   │
│   ├── routes/
│   │   ├── health.ts             # GET /api/health
│   │   ├── status.ts             # GET /api/status
│   │   ├── forecast.ts           # GET /api/forecast/* (4 endpoints)
│   │   ├── mae.ts                # GET /api/mae/* (2 endpoints)
│   │   └── heatmap.ts            # GET /api/heatmap/error
│   │
│   ├── middlewares/
│   │   ├── cache.ts              # RAM cache with configurable TTL
│   │   ├── rateLimit.ts          # 100 req/h/IP with express-rate-limit
│   │   └── errorHandler.ts       # Central handler for DB errors
│   │
│   ├── services/
│   │   ├── forecastService.ts    # Forecast business logic
│   │   └── maeService.ts         # MAE aggregation logic
│   │
│   └── types/
│       ├── forecast.ts           # TypeScript interfaces for API responses
│       └── db.ts                 # Raw SQL result types
│
├── tests/                        # Jest + supertest tests (coming v1.1)
├── .env.example
├── package.json
├── tsconfig.json
└── README.md                     # This file
```

### Architectural principles

#### 1. Stateless and idempotent

The backend stores **nothing locally** (no session, no temp files, no cookies). All state is in PostgreSQL. Consequence: backend can be restarted at any time, or run multiple instances in parallel (future load balancing), without risk.

#### 2. Read-only on DB

No endpoint does `INSERT`, `UPDATE`, or `DELETE`. All writes come from **Python pipelines** (project steps 2-5). This strict separation guarantees a backend bug can **never** corrupt data.

#### 3. Unified SQL view

All endpoints read from the **`forecast_unified` view** which aggregates the 3 sources (ERA5, AROME, GraphCast) with a uniform schema. Pipelines write to 3 separate tables, but backend sees only a coherent view:

```sql
SELECT lat, lon, run_date, run_hour, forecast_hour, source, variable, value
FROM forecast_unified
WHERE run_date = '2026-04-21' AND run_hour = 0 AND forecast_hour = 24;
```

#### 4. RAM cache with TTL

A homemade `cache.ts` middleware stores responses in RAM with a 10min default TTL (configurable). Benefit: repeated user requests on the same timestamp don't re-hit the DB. No need for Redis for the MVP.

---

## 🛣️ The 9 REST endpoints

### `GET /api/health`

**Role**: connectivity test (lifecheck for PM2 / Nginx / monitoring)

```bash
curl http://localhost:3001/api/health
```

**Response**: `200 OK` → `{ "status": "ok", "timestamp": "2026-04-27T18:00:00Z" }`

---

### `GET /api/status`

**Role**: global statistics (DB counters, cache state, server uptime)

```bash
curl http://localhost:3001/api/status
```

**Response**: `200 OK` with `uptime_seconds`, `database` (rows per source, last_ingestion), `cache` (hits, misses, hit_rate, size_mb)

**Cache**: 30 seconds (counters don't change quickly)

---

### `GET /api/forecast/available-times`

**Role**: list of `(date, hour)` available for a given source

**Query params**: `source` = `era5` | `arome` | `graphcast` (required)

**Cache**: 5 min (list evolves with each ingestion)

**Frontend usage**: `useStaticData` (graphcast + arome) and `useHeatmapData` (era5, to only request dates where comparison is possible)

---

### `GET /api/forecast/grid-points`

**Role**: list of 2925 GPS points on the 0.25° grid covering metropolitan France

**Cache**: 1h (grid never changes)

---

### `GET /api/forecast/timeseries`

**Role**: time series of a variable over N days for a given GPS point

**Query params**: `lat`, `lon` (required, must be a grid point), `days` (default: 7), `variable` (default: `t2m_celsius`)

**Cache**: 10 min

---

### `GET /api/forecast/:date/:hour`

**Role**: complete grid at a given instant T (all variables, all sources)

**Path params**: `date` (`YYYY-MM-DD`), `hour` (`HH` zero-padded, e.g., `06` not `6`)

**Cache**: 30 min

---

### `GET /api/mae/comparison`

**Role**: comparative MAE table AROME vs GraphCast per variable, aggregated over N days

**Query params**: `horizon` (`6`, `12`, `18`, `24`) — required, `days` (default: 7)

**Note**: for `wind_direction_10m_deg`, `bias` is forced to `null` because wind direction is cyclic (0° = 360°), an average bias has no physical meaning.

**Cache**: 15 min

---

### `GET /api/mae/history`

**Role**: daily MAE history for evolution chart

**Query params**: `variable`, `horizon`, `days` (default: 30)

**Cache**: 30 min

---

### `GET /api/heatmap/error`

**Role**: spatial error grid |model - ERA5| at a given instant T (heatmap)

**Query params**: `source` = `arome` | `graphcast`, `date`, `hour`, `variable`

**Important note**: availability depends on **ERA5** which has a 6-day latency. Frontend therefore uses `available-times?source=era5` to determine which dates can be displayed in heatmap (cf. step 10 bug #3).

**Cache**: 30 min

---

### `POST /api/forecast/cache/clear` ⭐ (step 11)

**Role**: fully invalidate the backend `node-cache`. Endpoint automatically triggered by Python pipelines after each successful DB ingestion to guarantee data consistency without waiting for TTL expiration.

```bash
curl -X POST http://localhost:3001/api/forecast/cache/clear
```

**Response**: `200 OK`

```json
{
  "stats_before": {
    "keys": 4,
    "hits": 287,
    "misses": 12,
    "ksize": 1024,
    "vsize": 51200
  },
  "cleared": true,
  "timestamp": "2026-04-28T16:31:42Z"
}
```

**Automatic invalidation workflow**:

```
Python pipeline (era5/arome/graphcast/mae)
   ↓ successful DB ingestion
   ↓
regenerate_frontend_json.py (utils hook)
   ↓ static JSON regeneration
   ↓
POST /api/forecast/cache/clear
   ↓ cache.flush()
   ↓
GET /api/forecast/available-times?source=arome
GET /api/forecast/available-times?source=graphcast
GET /api/forecast/available-times?source=era5
   ↓ pre-warming the 3 sources
   ✅ Cache warm again, latency <200ms
```

**Security**: no authentication for MVP (endpoint accessible only from localhost via the Python hook). In production, restrict via IP whitelist middleware (to be added in step 12).

---

## 🛡️ Middlewares

### RAM cache (`middlewares/cache.ts`)

**Role**: avoid re-hitting DB for identical repeated requests and guarantee sub-200ms latency even under load.

**Implementation**: `node-cache` (in-process, no Redis for this traffic volume) with TTL configurable per endpoint.

**4-layer cache architecture** (step 11)

| Layer | Mechanism | Effect |
|---|---|---|
| 1. Extended TTL | 1h TTL on `/available-times` (vs 5 min elsewhere) | Data only changes daily at 03:00–06:00 Paris time |
| 2. Invalidation hook | `POST /api/forecast/cache/clear` invoked by Python pipelines after DB ingestion | Cache consistent on first post-ingestion request |
| 3. Pre-warming | `preWarmCache()` async in `server.js`, hydrates the 3 sources 1s after `app.listen` | First visitor never pays cold cache (22s background at boot) |
| 4. Cron keep-alive | `*/30 6-22 * * * curl -s http://localhost:3001/api/forecast/available-times?source=arome` | Keeps cache warm during active hours (free, fail-safe) |

**Measured performance**:

| Metric | Before step 11 | After step 11 | Gain |
|---|---|---|---|
| First city click latency (cold) | 10–15 s | <200 ms | 50–75× |
| Page refresh API mode | 18 s | <200 ms | 90× |
| Cache hit | N/A | ~5 ms | — |

**Invalidation endpoint**:
```bash
POST /api/forecast/cache/clear
# Response: { "stats_before": {...}, "cleared": true, "timestamp": "..." }
```

**Why not Redis?** For this traffic volume, in-process cache is sufficient and remains fail-safe at restart thanks to pre-warming. Redis migration considered only if multi-instance Express load-balancing (v1.2 roadmap).

### Rate limiting (`middlewares/rateLimit.ts`)

**Role**: protect API from abuse if publicly exposed.

**Configuration**:
- **100 requests / hour / IP** by default
- Identifier: `req.ip` (Express trust proxy enabled to work behind Nginx)
- Response on overflow: `429 Too Many Requests` with `Retry-After` header
- Skip: `/api/health` (to allow PM2 health checks)

**Override via .env**:
```bash
RATE_LIMIT_MAX=1000
RATE_LIMIT_WINDOW_MS=3600000
```

### CORS (`cors` package)

**Role**: allow calls from React frontend.

**v1.0 configuration**:
- Dev: `localhost:5173` only (explicit whitelist)
- Prod: deployed frontend domain
- Override via `ALLOWED_ORIGINS` in `.env`

⚠️ **Bug encountered in step 10**: if Vite starts on port 5174 (5173 busy), request blocked by CORS. Short-term solution: free port 5173. Long-term solution (v1.1): more permissive whitelist in dev.

### Logger (`morgan`)

**Role**: log all HTTP requests.

**Format**: `dev` locally (colored), `combined` in prod (parsable by monitoring tools).

### Error handler (`middlewares/errorHandler.ts`)

**Role**: centralize error handling to not expose stack traces.

**Behavior**:
- `400`: missing or invalid query params
- `404`: nonexistent resource (date/hour not in DB)
- `429`: rate limit exceeded
- `500`: DB error (Morgan log captures details, client gets generic message)

> ⚠️ In v1.0, stack traces are returned in response for debug. v1.1 will mask them (`NODE_ENV=production` → `details: undefined`).

---

## 🗄️ Database schema

### Main tables (fed by Python pipelines)

```sql
-- ERA5 (ECMWF ground truth, J-6 latency)
CREATE TABLE era5_forecast (
  run_date DATE NOT NULL,
  run_hour SMALLINT NOT NULL,        -- 0, 6, 12, 18 (UTC)
  forecast_hour SMALLINT NOT NULL,   -- always 0 for reanalysis
  lat NUMERIC(5,2) NOT NULL,
  lon NUMERIC(5,2) NOT NULL,
  variable VARCHAR(40) NOT NULL,
  value DOUBLE PRECISION,
  PRIMARY KEY (run_date, run_hour, forecast_hour, lat, lon, variable)
);

-- AROME (Météo-France regional model, 1-2h latency)
CREATE TABLE arome_forecast (...);   -- same schema

-- GraphCast (Google DeepMind AI foundation, ~5-8 min CPU Mac latency)
CREATE TABLE graphcast_forecast (...); -- same schema
```

### Unified view `forecast_unified`

```sql
CREATE VIEW forecast_unified AS
  SELECT *, 'era5' AS source FROM era5_forecast
  UNION ALL
  SELECT *, 'arome' AS source FROM arome_forecast
  UNION ALL
  SELECT *, 'graphcast' AS source FROM graphcast_forecast;
```

Single backend data entry point. All endpoints SELECT from this view.

### Pre-computed MAE table

```sql
CREATE TABLE mae_daily (
  run_date DATE NOT NULL,
  source VARCHAR(20) NOT NULL,        -- 'arome' or 'graphcast'
  variable VARCHAR(40) NOT NULL,
  horizon_hours SMALLINT NOT NULL,    -- 6, 12, 18, 24
  mae DOUBLE PRECISION NOT NULL,
  bias DOUBLE PRECISION,              -- NULL for wind_direction (cyclic)
  n_samples INTEGER NOT NULL,
  PRIMARY KEY (run_date, source, variable, horizon_hours)
);
```

Computed by `scripts/mae/compute_mae.py` after each ERA5 ingestion. Backend only reads.

### Important indexes

#### B-tree composite indexes (step 11 — 130× gain)

Three `(latitude, longitude, timestamp DESC)` indexes added on prediction tables to transform full scan into O(log n) lookup:

```sql
-- Step 11: indexing the 3 prediction tables by coordinates
CREATE INDEX idx_arome_lat_lon_time
  ON arome_forecasts (latitude, longitude, "timestamp" DESC);

CREATE INDEX idx_era5_lat_lon_time
  ON era5_truth (latitude, longitude, "timestamp" DESC);

CREATE INDEX idx_graphcast_lat_lon_time
  ON graphcast_predictions (latitude, longitude, "timestamp" DESC);
```

**Measured impact**: `/api/forecast/timeseries?lat=46.25&lon=1.75` goes from **10s to 77ms** (130× gain). The 654K rows are no longer fully scanned, the index pre-sorts by coordinates.

#### Spatial and MAE indexes

```sql
-- PostGIS spatial index for GPS-point queries (timeseries, heatmap)
CREATE INDEX idx_era5_geo ON era5_forecast USING gist (
  ST_SetSRID(ST_MakePoint(lon, lat), 4326)
);

-- Composite index for MAE aggregates (mae/comparison)
CREATE INDEX idx_mae_daily_lookup ON mae_daily (run_date, horizon_hours, variable);
```

---

## ⚙️ Environment variables

### `backend/.env`

```bash
# === Server ===
PORT=3001
NODE_ENV=development             # or "production"

# === PostgreSQL database ===
DATABASE_URL=postgresql://user:password@localhost:5432/meteo_ia

# === CORS ===
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5174

# === Rate limit ===
RATE_LIMIT_MAX=100
RATE_LIMIT_WINDOW_MS=3600000

# === Cache ===
CACHE_TTL_MS=600000
CACHE_MAX_SIZE_MB=50

# === Logging ===
LOG_LEVEL=info
```

⚠️ `.env` must NEVER be committed (in `.gitignore`). Use `.env.example` as template.

---

## 🐳 V1.0 Dockerization ⭐ NEW (04/29/2026)

The Express backend is now fully containerized for production deployment. This section details the `Dockerfile`, `.dockerignore`, and architecture choices.

### `backend/Dockerfile` — Single-stage Node 22 Alpine

```dockerfile
# Base image: Node 22 LTS on Alpine (lightweight and secure)
FROM node:22-alpine

# Metadata
LABEL maintainer="Adéchola Émile KOUANDE <kadechola@gmail.com>"
LABEL project="meteo-ia-france"
LABEL component="backend-express-api"

# Working directory
WORKDIR /app

# Copy manifests first to optimize Docker layer caching
# (if package.json/lock don't change, npm ci will be cached on next build)
COPY package.json package-lock.json ./

# Install ONLY production dependencies (no devDependencies)
# --omit=dev: no jest/supertest/nodemon in final image
# --no-audit --no-fund: silent + faster
RUN npm ci --omit=dev --no-audit --no-fund && npm cache clean --force

# Copy rest of source (after npm ci for caching)
COPY . .

# Security: switch to non-root user (node user exists by default)
RUN chown -R node:node /app
USER node

# Listening port (info for Docker, doesn't do anything else)
EXPOSE 3001

# Docker healthcheck: ping /api/health every 30s
# 3 consecutive failures → container marked "unhealthy"
# start_period 10s = grace period before 1st check (lets Express boot)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3001/api/health || exit 1

# Startup command (single process, no PM2 or nodemon in prod)
CMD ["node", "server.js"]
```

**Characteristics**:
- 📦 **Final image ~60 MB** (Node 22 Alpine + minimal dependencies)
- 🔒 **Non-root user**: `USER node` after `chown` (avoids root execution by default)
- 🚀 **Optimized Docker cache**: `package*.json` copied BEFORE source code
- 🩺 **Native healthcheck**: Docker knows actual backend state (not just "process up")
- 🎯 **Single-stage**: no multi-stage needed since Node doesn't require "compilation" (unlike Vite/TypeScript)

### `backend/.dockerignore` — Critical exclusions

```gitignore
# Do NOT copy into image
node_modules/      # Will be rebuilt by npm ci inside image
.env               # Secrets passed via compose env vars, not embedded
.env.local
.env.production    # Especially not prod .env!
backup/            # The 333 MB dump has nothing to do in backend container
.git/              # Useless git history in runtime
.gitignore
logs/              # Regenerated at runtime
*.log
README.md          # Documentation, out of container scope
.DS_Store          # macOS
.vscode/
.idea/
coverage/          # Test coverage
.nyc_output/
dist/              # In case there's a build artifact
```

→ **Before `.dockerignore`**: image was ~450 MB (with `node_modules/` and `backup/` 333 MB embedded)
→ **After `.dockerignore`**: image is **~60 MB** (×7.5 reduction)

### `/api/health` healthcheck

Backend exposes an `/api/health` endpoint consumed by Docker `HEALTHCHECK`:

```javascript
// routes/healthRoutes.js
router.get('/health', async (req, res) => {
  try {
    // DB connection test
    const result = await pool.query('SELECT NOW() as db_time');
    res.json({
      status: 'ok',
      message: 'API and DB operational',
      timestamp: new Date().toISOString(),
      uptime_seconds: Math.floor(process.uptime()),
    });
  } catch (err) {
    res.status(503).json({
      status: 'error',
      message: 'DB unavailable',
      details: err.message,
    });
  }
});
```

→ Healthcheck **also verifies DB** (not just that Node process runs). If Postgres falls, backend container is marked `unhealthy` and auto-restarted by Docker.

### Environment variables injected by Docker Compose

When backend runs in Docker (via `docker-compose.yml`), these variables are injected:

| Variable | Value in container | Source |
|---|---|---|
| `NODE_ENV` | `production` | docker-compose.yml |
| `PORT` | `3001` | docker-compose.yml |
| `DB_HOST` | **`postgres`** ⚠️ (compose service name, NOT `localhost`) | docker-compose.yml |
| `DB_PORT` | **`5432`** ⚠️ (INTERNAL Postgres port, NOT host's 5433) | docker-compose.yml |
| `DB_NAME` | `meteo_ia_db` | project root `.env` |
| `DB_USER` | `meteo_user` | project root `.env` |
| `DB_PASSWORD` | (secret) | project root `.env` |
| `CORS_ORIGINS` | `https://meteo-ia.fr,https://www.meteo-ia.fr` | docker-compose.yml |
| `RATE_LIMIT_WINDOW_MIN` | `60` | docker-compose.yml |
| `RATE_LIMIT_MAX` | `100` | docker-compose.yml |
| `CACHE_TTL_SECONDS` | `600` | docker-compose.yml |

⚠️ **Classic pitfall avoided**: in backend container, `DB_HOST` must be `postgres` (compose service name), not `localhost`. Docker network resolves `postgres` to Postgres container's IP via internal DNS. And `DB_PORT` = 5432 (port **inside** Postgres container), not 5433 (port mapped to host for debug).

### Standalone Dockerfile testing

```bash
# Build image
cd backend
docker build -t meteo-ia-backend:test .

# Check size
docker images meteo-ia-backend:test
# meteo-ia-backend   test   8c6fbe44b959   ~60 MB

# Run standalone (DB not started → backend will fail but we see it boots)
docker run --rm -p 3001:3001 \
  -e NODE_ENV=production \
  -e PORT=3001 \
  -e DB_HOST=host.docker.internal \
  -e DB_PORT=5433 \
  -e DB_NAME=meteo_ia_db \
  -e DB_USER=meteo_user \
  -e DB_PASSWORD=mock \
  meteo-ia-backend:test
```

### Build and publish (V1.1 planned workflow)

In V1.1, GitHub Actions will automatically build the image on every push to `main`:

```yaml
# .github/workflows/build-backend.yml (V1.1)
- name: Build & push backend image
  uses: docker/build-push-action@v5
  with:
    context: ./backend
    push: true
    tags: ghcr.io/adecholaA1/meteo-ia-backend:latest,ghcr.io/adecholaA1/meteo-ia-backend:${{ github.sha }}
```

---

## 🧪 Tests and debug

### Unit tests (coming v1.1)

Project plans Jest + supertest to test the 9 endpoints:

```bash
npm test
npm run test:watch
npm run test:cov
```

### Quick manual test

```bash
for route in health status \
  "forecast/available-times?source=graphcast" \
  "forecast/grid-points" \
  "forecast/timeseries?lat=49&lon=2.5" \
  "mae/comparison?horizon=24"; do
  echo "=== /api/$route ==="
  curl -s "http://localhost:3001/api/$route" | jq -r 'keys'
done
```

### DB debug

```bash
psql -U meteo -d meteo_ia -c "
  SELECT source, COUNT(*) FROM forecast_unified GROUP BY source;
"
```

### Production logs

PM2 redirects logs to `~/.pm2/logs/`:

```bash
pm2 logs meteo-backend --lines 100
pm2 monit
```

---

## 🛠️ Detailed tech stack

| Category | Choice | Version | Why |
|---|---|---|---|
| **Runtime** | Node.js | 22+ | LTS, native performance |
| **Language** | TypeScript | 5 | Type safety shared with frontend |
| **HTTP framework** | Express | 5 | Node.js de facto standard, mature ecosystem |
| **SQL driver** | node-postgres (`pg`) | 8 | Official PostgreSQL client, native Pool support |
| **Database** | PostgreSQL | 15 | Robust, JSON support, native partitioning |
| **Geo extension** | PostGIS | 3.4 | GIST spatial index, GPS-point queries |
| **CORS** | `cors` | 2 | Express standard |
| **Rate limit** | `express-rate-limit` | 7 | Memory store by default |
| **Logger** | `morgan` | 1 | Express standard, combined format in prod |
| **Dev hot reload** | `tsx` | 4 | Faster than ts-node + nodemon |
| **Build** | native `tsc` | 5 | No need for esbuild/swc, Express is simple |
| **Process manager** | PM2 | 5 | Node prod standard, monitoring included |

### Why not FastAPI?

Initially the project planned Express + FastAPI (2 backends). Final decision: **Express only**, because:

| Criterion | Express only | Express + FastAPI |
|---|---|---|
| Deployment complexity | 1 process | 2 processes |
| Stack consistency | TypeScript everywhere | TS + Python |
| Backend performance | Identical (just SELECT) | Identical |
| Python compute justification | ❌ No heavy compute | ❌ |

**GraphCast inference** happens in Python pipelines (offline, outside backend). Backend just reads DB → Express is more than enough.

---

## 🤝 How to contribute

### Start a development

```bash
git checkout -b feat/my-feature
cd backend
npm install
cp .env.example .env
npm run dev
```

### Code conventions

- **Strict TypeScript**: `strict: true` in `tsconfig.json`, no unjustified `any`
- **No ORM**: raw SQL via `node-postgres`, more predictable and faster
- **Thin routes**: business logic in `services/`, not in `routes/`
- **Async/await** everywhere, never callbacks
- **Validation**: query params validated before reaching DB
- **Appropriate cache**: each new endpoint defines its TTL based on expected freshness

### Commit conventions

- `feat:` new endpoint or feature
- `fix:` bug fix
- `perf:` optimization (DB index, cache, query)
- `docs:` documentation
- `refactor:` refactoring
- `test:` tests
- `chore:` deps, config, CI

### Before pushing

```bash
npm run lint
npm run build
# npm test (coming v1.1)
```

### Welcome contribution ideas

- 🧪 **Jest + supertest unit tests** (v1.1 priority)
- 🔐 **Basic authentication** (API key in header) if API is publicly exposed
- 📊 **`graphcast_vs_arome` endpoint** (model vs model, no ERA5 truth)
- 🔄 **`POST /api/cache/flush` endpoint** (invalidation after ingestion)
- 📈 **Skill Score** vs persistent climatology
- 🎯 **GraphCast bias correction** by variable / region / season learned on ERA5
- 🌊 **CRPS / Brier score** for precipitation
- 🚀 **RAM cache → Redis migration** for horizontal scaling

---

## 📜 License

This project is distributed under the **MIT license**. See [LICENSE](../LICENSE) for details.

## 📧 Contact

- 📧 **Email**: [kadechola@gmail.com](mailto:kadechola@gmail.com)
- 💼 **LinkedIn**: [linkedin.com/in/kadechola](https://www.linkedin.com/in/kadechola/)
- 💻 **Malt**: [malt.fr/profile/adecholaemilekkouande](https://www.malt.fr/profile/adecholaemilekkouande)
