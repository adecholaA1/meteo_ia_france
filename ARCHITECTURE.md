# 🏛️ Météo IA France — Architecture

> 🇬🇧 **English version below** ([jump to English](#-météo-ia-france--architecture-english))

Document décrivant l'architecture technique globale du projet Météo IA France : pipelines de données, base de données, backend API, frontend, déploiement. À garder à jour à chaque évolution majeure.

---

## 📑 Sommaire

1. [Vision & contexte](#-vision--contexte)
2. [Vue d'ensemble](#-vue-densemble)
3. [Pipelines de données](#-pipelines-de-données)
4. [Base de données](#-base-de-données)
5. [Backend API](#-backend-api)
6. [Frontend](#-frontend)
7. [Déploiement & production](#-déploiement--production)
8. [Décisions techniques majeures](#-décisions-techniques-majeures)
9. [Évolutions futures](#-évolutions-futures)

---

## 🎯 Vision & contexte

**Météo IA France** est une plateforme de prévision météorologique à destination du **secteur de l'énergie** (éolien, solaire, trading), qui compare :
- **GraphCast Operational** (Google DeepMind, IA fondation)
- **AROME** (Météo-France, modèle physique régional)
- **ERA5** (ECMWF, vérité terrain de référence)

L'objectif n'est pas de remplacer les fournisseurs commerciaux mais de fournir une **plateforme open-source de comparaison transparente** des modèles, avec un focus géographique France métropolitaine (grille 0.25°, 2 925 points).

---

## 🌐 Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────────┐
│                  Browser utilisateur (France)                   │
│  React 19 + Vite 8 + TypeScript 5 + Tailwind v4 + shadcn        │
│  Recharts + Leaflet (Stadia Smooth Dark) + react-router-dom v7  │
│  Bilingue FR/EN · Light + Dark mode · Page Méthodologie         │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS (JSON statique pré-généré)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    VPS OVH Ubuntu 24                            │
│  ┌──────────────────┐    ┌─────────────────────────────────┐   │
│  │  Nginx + Certbot │───▶│  Express (port 3001) + PM2      │   │
│  │  HTTPS + routing │    │  8 routes API + CORS + cache    │   │
│  └──────────────────┘    └────────┬────────────────────────┘   │
│                                   │ SQL                         │
│                                   ▼                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │         PostgreSQL 15 + PostGIS 3.4 (Docker)            │   │
│  │  graphcast_predictions / arome_forecasts /              │   │
│  │  era5_truth / mae_metrics                               │   │
│  └────────────────────────────▲────────────────────────────┘   │
│                               │ INSERT                          │
│  ┌────────────────────────────┴────────────────────────────┐   │
│  │           Pipelines Python (cron UTC)                   │   │
│  │  23h30 GraphCast · 00h00 AROME · 08h00 ERA5 · 09h00 MAE│   │
│  │  → hook post-ingestion : regenerate frontend JSON      │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                           ▲
                           │ HTTP
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────────┐       ┌────────────┐      ┌─────────────┐
   │  GFS   │       │  ECMWF CDS │      │ Météo-France│
   │ NOMADS │       │   (ERA5)   │      │   (AROME)   │
   └────────┘       └────────────┘      └─────────────┘
```

### Principe d'isolation

Le système est organisé en **couches strictement isolées** :

| Couche | Rôle | Communique avec |
|---|---|---|
| Sources externes | Fournissent les données brutes | (rien — appelées par les pipelines) |
| Pipelines Python | Téléchargent, traitent, ingèrent | Sources externes + DB |
| PostgreSQL | Stocke toutes les données | Pipelines (INSERT) + Backend (SELECT) |
| Backend Express | Lit la DB, expose en JSON | DB + Frontend |
| Frontend React | Affiche, visualise, interagit | Backend uniquement |

➡️ Aucune couche ne saute une étape. Le backend ne lance jamais d'inférence Python. Le frontend ne parle jamais directement à PostgreSQL.

---

## 🔄 Pipelines de données

3 pipelines indépendants alimentent la DB, chacun avec son propre `run_daily_pipeline.py` orchestrateur, lancé par cron quotidien.

### Pipeline GraphCast (IA)

```
GFS NOMADS (NOAA)
    │
    ▼ téléchargement 28 fichiers GRIB2 (T-6h + T0 × 14 niveaux)
fetch_gdas_france.py
    │
    ▼ normalisation, interpolation 0.25°
preprocess_graphcast_input.py
    │
    ▼ inférence GraphCast Operational 13 niveaux (~5-8 min CPU Mac)
run_graphcast_inference.py
    │  → predictions à T+6h, +12h, +18h, +24h
    ▼ export CSV (4 horizons × 8 vars × 2 925 points = 93 600 lignes/jour)
export_graphcast_csv.py
    │
    ▼ INSERT ON CONFLICT vers DB
ingest_graphcast_to_db.py
    │
    ▼
PostgreSQL.graphcast_predictions
```

**Fréquence** : 1 run/jour à 23h30 UTC (cible : run 18z UTC, publié vers 22h UTC).

### Pipeline ERA5 (vérité terrain)

```
ECMWF CDS API
    │
    ▼ téléchargement J + J-1 (5 variables, 24h horaires)
fetch_era5.py
    │
    ▼ cumul tp_6h, calcul wind_speed/direction/toa, sélection 4 timestamps
export_era5_csv.py
    │
    ▼ INSERT ON CONFLICT
ingest_era5_to_db.py
    │
    ▼
PostgreSQL.era5_truth
```

**Fréquence** : 1 run/jour à 08h UTC, cible J-6 (latence ECMWF de ~5 jours).

### Pipeline AROME (Météo-France)

```
data.gouv.fr (Météo-France PNT)
    │
    ▼ téléchargement 4 fichiers GRIB2 SP1 (00H06H, 07H12H, 13H18H, 19H24H)
fetch_arome.py
    │
    ▼ ré-échantillonnage 0.025° → 0.25°, cumul tp_6h, variables dérivées
export_arome_csv.py
    │
    ▼ INSERT ON CONFLICT
ingest_arome_to_db.py
    │
    ▼
PostgreSQL.arome_forecasts
```

**Fréquence** : 1 run/jour à 00h UTC (run AROME 18z UTC dispo vers 22h UTC).

### Pipeline MAE

```
PostgreSQL (3 tables sources)
    │
    ▼ JOIN sur (timestamp, variable_name, latitude, longitude)
calc_mae.py
    │
    ▼ calcul MAE / RMSE / Bias par (variable, horizon, comparison)
ingest_mae_to_db.py
    │
    ▼
PostgreSQL.mae_metrics
```

**Fréquence** : 1 run/jour à 09h UTC (après ERA5).

---

## 💾 Base de données

### Schéma : 4 tables + 2 vues

#### `era5_truth`
```sql
id, timestamp, variable_name, unit, latitude, longitude, value, created_at
UNIQUE (timestamp, variable_name, latitude, longitude)
```

#### `arome_forecasts` et `graphcast_predictions`
```sql
id, run_timestamp, forecast_horizon_h, timestamp,
variable_name, unit, latitude, longitude, value, created_at
UNIQUE (run_timestamp, timestamp, variable_name, latitude, longitude)
```

#### `mae_metrics` (1 seule table pour toutes les comparaisons)
```sql
id, comparison VARCHAR(30),  -- 'graphcast_vs_era5', 'arome_vs_era5'
evaluation_date DATE, variable_name, forecast_horizon_h,
mae, rmse, bias, sample_count, computed_at
UNIQUE (comparison, evaluation_date, variable_name, forecast_horizon_h)
```

#### Vues de "fraîcheur"
```sql
-- Garde uniquement la prédiction la plus récente par tuple
CREATE VIEW arome_forecasts_fresh AS
  SELECT DISTINCT ON (timestamp, variable_name, latitude, longitude) *
  FROM arome_forecasts
  ORDER BY timestamp, variable_name, latitude, longitude, run_timestamp DESC;

-- Idem pour GraphCast
CREATE VIEW graphcast_predictions_fresh AS ...
```

### Variables stockées

| Variable | Unité | Origine | Notes |
|---|---|---|---|
| `t2m_celsius` | °C | Native | Conversion K → °C |
| `u10_ms` | m/s | Native | Composante zonale du vent |
| `v10_ms` | m/s | Native | Composante méridienne du vent |
| `msl_hpa` | hPa | Native | Conversion Pa → hPa |
| `tp_6h_mm` | mm | Native + cumul | Cumul 6h calculé |
| `wind_speed_10m_ms` | m/s | Calculée | √(u² + v²) |
| `wind_direction_10m_deg` | ° | Calculée | atan2(-u, -v) |
| `toa_wm2` | W/m² | Calculée | Astronomique (Spencer 1971) |

### Format LONG vs WIDE

Le projet utilise un **format LONG** (1 ligne = 1 variable × 1 timestamp × 1 point GPS) plutôt que WIDE (1 colonne par variable). Choix justifié par :
- ✅ Évolutivité : ajouter une variable = ajouter des lignes, pas modifier le schéma
- ✅ Standard data engineering météo
- ✅ Conformité avec l'énoncé officiel du projet (`variable_name VARCHAR(50)`)

### Format de stockage temporel

Toutes les colonnes timestamp sont en **`TIMESTAMP WITH TIME ZONE`** stockées en **UTC**. La conversion vers Europe/Paris se fait au niveau du frontend.

Une fonction PostgreSQL utilitaire est disponible : `utc_to_paris(ts TIMESTAMPTZ)` pour les requêtes manuelles.

### Volumétrie

| Table | Lignes/jour | Lignes au 25/04/2026 |
|---|---|---|
| graphcast_predictions | 93 600 | 842 400 |
| arome_forecasts | 93 600 | 842 400 |
| era5_truth | 93 600 | 280 800 (ERA5 a une latence) |
| mae_metrics | ~24 | 192 |
| **Total** | **~280 000** | **~1.96 M** |

Croissance attendue : **~100 Mo/mois** sur PostgreSQL (négligeable).

---

## 🔌 Backend API

Cf. [backend/README.md](./backend/README.md) pour les détails complets. Résumé :

- **Stack** : Express 5 + node-postgres + cors + morgan + rate-limit
- **8 endpoints** : health, status, forecast (4), mae (2), heatmap (1)
- **Cache** : middleware maison, RAM, TTL 10 min par défaut
- **Sécurité v1.0** : rate limit 100 req/h/IP, CORS configurable, pas d'auth
- **Port** : 3001 (configurable via `.env`)

Le backend est volontairement **sans état** (aucune session, aucun fichier local) et **idempotent** : on peut le redémarrer à tout moment sans perdre de données.

---

## 🎨 Frontend

> ✅ **Étape 9 terminée** — dashboard React + page Méthodologie publique livrés.

### Stack technique

| Composant | Choix | Pourquoi |
|---|---|---|
| Framework | **React 19** + TypeScript 5 | Concurrent rendering, Suspense, hooks modernes |
| Build tool | **Vite 8** | HMR ultra-rapide, build optimisé natif TS |
| Styling | **Tailwind CSS v4** + plugin Vite natif | Atomic CSS, dark mode classe `dark`, palette OKLCH |
| Composants | **shadcn/ui** (preset Radix Nova) | Architecture copy-paste, pas de dépendance lourde |
| Charts | **Recharts** | Courbes synchronisées, légendes interactives, axes adaptatifs |
| Carte | **react-leaflet 4** + Leaflet 1.9 | Carte interactive, fond Stadia Alidade Smooth Dark |
| Routing | **react-router-dom v7** | Routes bilingues séparées (`/fr`, `/en`, `/fr/methodologie`, `/en/methodology`) |
| Client HTTP | `fetch` natif + bascule API/JSON statique | Pattern hybride étape 10 : runtime API (Express) ou JSON statique build-time |
| State management API | **TanStack Query v5** (`@tanstack/react-query`) | QueryClient configuré (staleTime 5min, gcTime 30min, retry 2), prêt pour usage cache/dedup futur |

### Architecture des composants

```
frontend/src/
├── components/
│   ├── layout/
│   │   ├── Header.tsx          # logo + horloge live UTC+1/+2 (DST auto) + toggle dark/light + switch FR/EN
│   │   └── Footer.tsx          # sources colorées + lien Méthodologie + lien GitHub
│   ├── map/
│   │   ├── FranceMap.tsx       # 103 villes heatmap + 10 pins + tooltips riches + 3 dropdowns + 4 timestamps
│   │   └── ZoomDialog.tsx      # modal universel (carte / MAE / charts)
│   ├── charts/
│   │   ├── ChartCard.tsx       # 1 par variable, 3 sources superposées, curseur synchronisé
│   │   └── MaeTableCard.tsx    # 4 horizons (h6/h12/h18/h24) × 6 variables, ratio coloré
│   └── methodology/            # ⭐ page Méthodologie publique (8 sections)
│       ├── AboutSection.tsx
│       ├── GlossarySection.tsx       # 16 sigles expliqués
│       ├── VariablesSection.tsx      # 6 variables détaillées
│       ├── SourcesSection.tsx        # 3 sources avec bord coloré (ERA5 #1E73E8, AROME #1D9E75, GraphCast #F08C3D)
│       ├── ComparisonTable.tsx       # 14 lignes côte-à-côte
│       ├── LimitationsSection.tsx    # 5 limitations v1.0 numérotées
│       ├── RoadmapSection.tsx        # v2.0 (Pangu-Weather fine-tuné, AROME natif, multi-runs, horaire) + v3.0 (ClimaX)
│       └── TechStackSection.tsx      # 5 cards : Pipelines, DB, Backend ⭐, Frontend, DevOps
├── routes/
│   ├── DashboardPage.tsx       # / (FR) ou /en (EN)
│   └── MethodologyPage.tsx     # /fr/methodologie ou /en/methodology
├── i18n/
│   ├── methodology.fr.ts       # données FR (~217 lignes, 14 KB)
│   └── methodology.en.ts       # données EN (~217 lignes, 13 KB)
├── lib/
│   ├── timezone.ts             # gestion DST automatique UTC+1/UTC+2
│   ├── numberFormat.ts         # locale FR/EN sur les chiffres
│   └── colors.ts               # palette OKLCH + couleurs sources
└── data/                       # JSON statique pré-généré au build
    ├── timeseries-paris.json
    ├── mae.json
    ├── grid-points.json
    └── heatmap/                # 6 fichiers × 4 timestamps × 2 sources
        ├── t2m_celsius.json (1873 KB)
        ├── wind_speed_10m_ms.json (1848 KB)
        ├── wind_direction_10m_deg.json (1919 KB)
        ├── msl_hpa.json (1980 KB)
        ├── tp_6h_mm.json (1645 KB)
        └── toa_wm2.json (1738 KB)
```

### Génération du JSON statique

Plutôt que de servir les données via API en runtime, le frontend embarque un **JSON statique pré-généré au build**. Ce choix offre :

- ✅ **Performance** : aucun appel API au chargement, tout est inline
- ✅ **Cache navigateur** efficace (immuable jusqu'au prochain build)
- ✅ **Hébergement statique** possible (CDN, GitHub Pages)
- ✅ **Rejouabilité** : la version `v1.0` peut toujours être consultée même si les données évoluent

Un script Node.js `scripts/generate_static_data.mjs` interroge le backend Express et écrit les fichiers JSON dans `frontend/src/data/`. Ce script est appelé automatiquement après l'ingestion CSV dans le pipeline backend (hook post-ingestion), ce qui garantit que le frontend est toujours synchronisé avec la dernière version des données.

### Pages livrées

#### 1. Dashboard principal (`/fr` ou `/en`)

- **Header** : titre "Météo IA France" / "France AI Weather", horloge live (DST auto FR : UTC+1 hiver, UTC+2 été), toggle dark/light, switch FR ↔ EN avec préservation de la route
- **Carte France interactive** :
  - Fond Stadia Alidade Smooth Dark (zoom 6, centré sur Saintes)
  - 103 villes principales avec **heatmap colorée** (CircleMarker visible, palette adaptative par variable)
  - 10 **pins 📍** sur les plus grandes villes (Paris, Lyon, Marseille, Toulouse, Bordeaux, Nantes, Rennes, Lille, Strasbourg, Nice)
  - Tooltips riches au survol : nom de ville, AROME, GraphCast, ERA5 vérité, écart absolu, écart relatif
  - 3 dropdowns en overlay (source / variable / timestamp) avec z-index 9999 pour passer au-dessus de Leaflet
  - 4 timestamps disponibles (00h, 06h, 12h, 18h UTC = 02h, 08h, 14h, 20h heure de Paris en été)
  - Mode zoom modal (sans superposition de carte)
- **Tableau MAE** : 4 horizons (h6/h12/h18/h24) × 6 variables, ratio AROME/GraphCast coloré (vert si AROME meilleur, gris si comparable, rouge si GraphCast meilleur), mode zoom
- **6 ChartCards** : un par variable météo, courbes Recharts temps série synchronisées (curseur partagé entre toutes les cards), 3 sources superposées (ERA5 vérité en pointillés, AROME plein, GraphCast plein), axes adaptatifs avec locale FR/EN, mode zoom
- **Footer** : sources colorées (ECMWF / Météo-France / DeepMind avec leur couleur officielle), copyright, version v1.0, **lien "Méthodologie" / "Methodology"** entre version et "Source code" GitHub

#### 2. Page Méthodologie publique (`/fr/methodologie` ou `/en/methodology`) ⭐

8 sections accessibles aux non-développeurs :

1. **À propos** — vision du projet et public cible
2. **Glossaire** — 16 sigles expliqués en plain-text (NWP, MAE, RMSE, Bias, ERA5, AROME, GraphCast, GFS, GRIB, NetCDF, GHI, TOA, OKLCH, etc.)
3. **Variables expliquées** — 6 cards détaillées (t2m, wind_speed, wind_direction, msl, tp_6h, toa) avec unité, plage typique, conversion, intérêt énergie
4. **Sources comparées** — 3 cards avec bord coloré 3px (ERA5 bleu #1E73E8, AROME vert #1D9E75, GraphCast orange #F08C3D), description + lien officiel
5. **Tableau comparatif** — 14 lignes côte-à-côte (résolution, fréquence, latence, type de modèle, etc.) entre les 3 sources
6. **Limitations v1.0** — 5 limitations numérotées (orange, encadrées) : AROME ré-échantillonné, période 3 jours seulement, latence ERA5, MAE par défaut sur 24h, pas de fine-tuning
7. **Roadmap v2.0 / v3.0** — v2.0 : fine-tuning de Pangu-Weather, AROME résolution native, multi-runs quotidiens, pas horaire ; v3.0 : ClimaX fine-tuné
8. **Stack technique** — 5 cards (Pipelines vert, DB bleu, **Backend orange ⭐**, Frontend violet, DevOps gris) avec liste de technologies

### Conventions UX

- **Bilingue 100%** : FR puis EN, basculement instantané, URL différentes (pas de querystring `?lang=fr`)
- **Light + Dark mode** : palette OKLCH style Claude (les couleurs s'adaptent automatiquement, pas de duplication CSS)
- **Timezone** : tous les timestamps backend sont en UTC, le frontend convertit vers Europe/Paris avec gestion DST automatique
- **Responsive** : breakpoints Tailwind (mobile / tablet / desktop), carte qui s'adapte au viewport
- **Accessibilité** : navigation clavier complète, aria-labels sur les interactions, contrastes WCAG AA

### Bugs résolus pendant l'étape 9

| # | Bug | Solution |
|---|---|---|
| 1 | Z-index Leaflet vs Radix dropdowns (dropdowns ouverts derrière la carte) | CSS global `[data-slot="select-content"]` à `z-index: 9999 !important` |
| 2 | Backend exigeait format `06` mais script de génération JSON envoyait `6` | `String(t.hour).padStart(2, "0")` dans `generate_static_data.mjs` |
| 3 | Tailwind v4 et accolades CSS cassées (compilation HMR qui plantait) | Vérification `12/12` accolades équilibrées + `npx vite optimize` |
| 4 | Hover insensible sur les points de carte (CircleMarker trop petit) | Ajout d'un CircleMarker invisible `radius=14` par-dessus chaque point visible |
| 5 | Mode zoom MAE qui se superposait à la carte | `<Dialog>` Radix avec overlay 9998 et content 9999 |

📚 Documentation : [frontend/README.md](./frontend/README.md) (FR + EN détaillé)

---

## 🔌 Étape 10 — Pattern hybride API runtime / JSON statique

> ✅ **Étape 10 terminée** — connexion frontend ↔ backend Express avec bascule transparente entre 2 sources de données.

### Vision

L'étape 10 connecte le frontend React au backend Express, mais avec une approche **plus mature qu'un simple branchement runtime** : on ajoute le mode **API runtime** **à côté** du mode **JSON statique** existant, et on permet de basculer entre les deux **en live**, sans rebuild ni redéploiement.

Cette flexibilité est essentielle pour 3 cas d'usage :

| Cas | Mode recommandé | Pourquoi |
|---|---|---|
| 🌐 Production publique (CDN, GitHub Pages, démo LinkedIn) | 💾 JSON statique | Performance, hébergement gratuit, fonctionne offline |
| 🔧 Démonstration pédagogique en live | 🟢 API runtime | Devtools réseau visibles, requêtes traceables |
| 🐛 Debug local (modification DB, vérification immédiate) | 🟢 API runtime | Pas besoin de rebuild après chaque ingestion |
| 📱 Utilisateur sur 4G mobile | 💾 JSON statique | Économise data + plus rapide |
| 🔬 Multi-runs quotidiens (v2.0) | 🟢 API runtime | Données qui bougent en cours de journée |
| 🛡️ Backend tombé en panne | 💾 JSON statique (fallback) | L'app continue de fonctionner |

### Mécanisme de bascule

Le mode actif est contrôlé par **2 niveaux** :

1. **Variable d'environnement** `VITE_USE_API` au build (valeur par défaut)
   - `VITE_USE_API=false` → mode JSON statique au démarrage
   - `VITE_USE_API=true` (ou non défini) → mode API runtime au démarrage
2. **Toggle UI live** dans le header (override à la volée)
   - Bouton 📡 (Wifi vert) = mode API actif
   - Bouton 💾 (Database gris) = mode JSON statique actif
   - Au clic, l'app re-fetch immédiatement les données depuis la nouvelle source

### Architecture des nouveaux fichiers

```
frontend/src/
├── contexts/
│   └── DataSourceContext.tsx     # ⭐ Context React qui gère useApi + toggleDataSource
├── services/
│   └── apiService.ts             # ⭐ 9 méthodes typées vers les 8 endpoints Express
├── hooks/
│   ├── useStaticData.ts          # 🔄 Modifié : bascule API/static en interne
│   └── useHeatmapData.ts         # 🔄 Modifié : bascule API/static en interne
└── components/layout/
    ├── DataSourceToggle.tsx      # ⭐ Bouton toggle 📡/💾 dans le header
    └── Header.tsx                # 🔄 Modifié : ajout DataSourceToggle
```

### Abstraction des composants

**Aucun composant consommateur n'a été modifié** lors de l'étape 10. Les composants `FranceMap`, `MaeTableCard`, `ChartCard` continuent d'appeler `useStaticData()` et `useHeatmapData()` exactement comme avant. La bascule est totalement transparente :

```typescript
// FranceMap.tsx - inchangé étape 9 → étape 10
const { data, loading, error } = useStaticData()
// La fonction du hook est désormais : "charge les données selon le mode actif"
```

### TanStack Query v5

Le projet installe `@tanstack/react-query` et configure un `QueryClient` à la racine de l'app (`main.tsx`), avec des défauts robustes (staleTime 5min, gcTime 30min, retry 2 avec backoff exponentiel, refetchOnWindowFocus désactivé). À l'étape 10, **les hooks ne consomment pas encore `useQuery()` directement** (l'option allégée a permis de garder `useStaticData` et `useHeatmapData` quasi inchangés). TanStack reste cependant **prêt à l'emploi** pour les futurs hooks dédiés (par exemple `useApiHistory` pour des graphiques d'historique MAE), bénéficiant alors automatiquement du cache, du dedup et des retries.

### 3 vrais bugs identifiés et corrigés grâce au mode hybride

Le mode API runtime a confronté le frontend au contrat réel du backend, ce qui a révélé 3 problèmes invisibles en mode statique :

| # | Bug | Cause | Solution |
|---|---|---|---|
| 1 | **CORS multi-port** | Vite démarrait sur 5174 (5173 occupé), backend autorisait seulement 5173 | Libération du port 5173 (à terme : whitelist CORS plus permissive en dev) |
| 2 | **Coordonnées Paris** | Frontend envoyait `lat=48.85, lon=2.35` (Paris exact), backend ne trouvait rien sur la grille 0.25° | Alignement sur la grille la plus proche : `lat=49, lon=2.5` |
| 3 | **Latence ERA5 J-6** | Frontend demandait la heatmap pour `2026-04-27 18h` mais ERA5 n'a pas encore cette date → 404 | Utiliser `available-times?source=era5` au lieu de `?source=arome` (ERA5 contraint la disponibilité des comparaisons) |

### Endpoints Express consommés en mode API

| Endpoint | Usage frontend | Hook |
|---|---|---|
| `GET /api/health` | Test connectivité | (à venir page monitoring) |
| `GET /api/status` | Compteurs DB + cache + uptime | `useStaticData` |
| `GET /api/forecast/available-times` | Liste timestamps disponibles | `useStaticData` (graphcast + arome), `useHeatmapData` (era5) |
| `GET /api/forecast/grid-points` | 2925 points GPS de la grille | `useStaticData` |
| `GET /api/forecast/timeseries` | Séries temporelles 7j Paris | `useStaticData` |
| `GET /api/forecast/:date/:hour` | Grille complète à instant T | (à venir) |
| `GET /api/mae/comparison` | Tableau MAE (4 horizons) | `useStaticData` (×4 appels h6/h12/h18/h24) |
| `GET /api/mae/history` | Historique quotidien MAE | (à venir) |
| `GET /api/heatmap/error` | Heatmap d'écart spatial | `useHeatmapData` |

📚 Documentation détaillée :
- [frontend/README.md](./frontend/README.md) — détail des hooks, contexts, services
- [backend/README.md](./backend/README.md) — détail des 8 endpoints Express

---

## 🚀 Déploiement & production

> ✅ Étape 12 (dockerisation locale) terminée · 🔜 Déploiement VPS en cours · Domaine `meteo-ia.fr`

### 🐳 Architecture Docker V1.0 (étape 12)

Le projet est désormais entièrement orchestré par **Docker Compose** : un seul fichier `docker-compose.yml` à la racine déploie l'ensemble de la stack (3 containers + 1 réseau + 1 volume persistant) avec une seule commande.

#### Topologie des 3 services

```
┌────────────────────────────────────────────────────────────────────┐
│ Réseau Docker isolé : meteo_ia_network (driver bridge)             │
│                                                                    │
│  ┌──────────────────┐   ┌──────────────────┐   ┌────────────────┐  │
│  │  meteo_ia_       │   │  meteo_ia_       │   │  meteo_ia_     │  │
│  │  frontend        │   │  backend         │   │  pg_db_compose │  │
│  │                  │   │                  │   │                │  │
│  │  nginx:1.27      │──▶│  node:22         │──▶│  postgis:15    │  │
│  │  (multi-stage)   │   │  (single-stage)  │   │  (alpine)      │  │
│  │                  │   │                  │   │                │  │
│  │  Port 80→8080    │   │  Port 3001→3001  │   │  Port 5432→5433│  │
│  │  ~23 Mo image    │   │  ~60 Mo image    │   │  ~250 Mo image │  │
│  │  HC: nginx-health│   │  HC: /api/health │   │  HC: pg_isready│  │
│  └──────────────────┘   └──────────────────┘   └────────────────┘  │
│                                                                    │
│  Volume persistant : meteo_ia_pg_data (données PG entre restarts)  │
│  Bind mount init   : backend/backup/meteo_ia_db.sql (333 Mo)       │
└────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ depends_on: condition: service_healthy
                                  │ (postgres healthy → backend démarre)
                                  ▼
                            Backend démarre QUE quand
                            Postgres répond à pg_isready
```

#### Fichiers livrés

| Fichier | Rôle | Taille |
|---|---|---|
| `backend/Dockerfile` | Image backend single-stage `node:22-alpine` + user non-root | ~60 Mo |
| `backend/.dockerignore` | Exclut `node_modules`, `.env`, `backup/`, `.git`, `logs` | — |
| `frontend/Dockerfile` | Image frontend multi-stage (builder Vite + prod Nginx) | ~23 Mo |
| `frontend/nginx.conf` | Config Nginx : gzip + cache assets + SPA fallback + **proxy /api/** | — |
| `frontend/.dockerignore` | Exclut `node_modules`, `dist/`, `.env`, `.git` | — |
| `docker-compose.yml` | Orchestration 3 services + healthchecks + volume + réseau | ~7,8 Ko (130 lignes commentées) |
| `.env` (racine) | Credentials Postgres locaux (NON commité) | — |
| `.env.production.example` | Template prod commité avec valeurs `CHANGEME` | ~8 Ko |
| `.gitignore` (racine) | 4,7 Ko couvrant secrets, builds, cache GraphCast, exception backup .sql | ~4,7 Ko |

#### Reverse proxy `/api/*` dans Nginx du container frontend

Configuration critique de `frontend/nginx.conf` qui résout le problème "comment le frontend appelle le backend dans Docker" :

```nginx
# Reverse proxy /api/* → backend container
location /api/ {
    proxy_pass http://backend:3001;     # "backend" = nom du service compose
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_connect_timeout 30s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
}

# SPA fallback (React Router)
location / {
    try_files $uri $uri/ /index.html;
}
```

→ Le navigateur fait `fetch('/api/forecast/...')` (URL relative), Nginx du container frontend intercepte et **transmet à `backend:3001`** via le DNS interne Docker. Le frontend n'a donc **pas besoin** de connaître l'URL absolue du backend (`VITE_API_URL=""`).

### Cible : VPS OVH Ubuntu 24

| Composant | Outil | Rôle | Statut V1.0 |
|---|---|---|---|
| Container DB | `postgis/postgis:15-3.4-alpine` | PostgreSQL + PostGIS isolé, healthcheck | ✅ Dockerisé |
| Container backend | `meteo-ia-backend:1.0.0` (custom image) | API Express, healthcheck | ✅ Dockerisé |
| Container frontend | `meteo-ia-frontend:1.0.0` (custom image) | Nginx + assets statiques + reverse proxy `/api/` | ✅ Dockerisé |
| Orchestration | Docker Compose v2 | Stack complète en 1 commande | ✅ |
| Reverse proxy host | Nginx **système** sur le VPS (séparé des containers) | HTTPS, routing par sous-domaine | 🔜 À configurer |
| Certificat TLS | Certbot (Let's Encrypt) | HTTPS auto-renouvelé pour `meteo-ia.fr` | 🔜 À configurer |
| Cron | crontab UTC sur l'OS du VPS (PAS dans Docker) | Lance les 4 pipelines Python quotidiens | 🔜 À configurer |
| Process manager | ❌ Plus de PM2 (remplacé par `restart: unless-stopped` Docker) | Auto-restart natif Docker | ✅ |

### Crontab prévu (UTC, sur l'OS du VPS)

```
 0  1 * * *  cd /opt/meteo_ia_france && conda run -n meteo_ia python -m graphcast_gfs.run_daily_pipeline
30  1 * * *  cd /opt/meteo_ia_france && conda run -n meteo_ia python -m arome.run_daily_pipeline
 0  2 * * *  cd /opt/meteo_ia_france && conda run -n meteo_ia python -m era5.run_daily_pipeline
 0  3 * * *  cd /opt/meteo_ia_france && conda run -n meteo_ia python -m mae.run_daily_pipeline
```

### Ressources serveur

- **VPS-2 OVH** : 4 Go RAM ⚠️ (GraphCast inference besoin ~6 Go → swap obligatoire)
- **Disque** : 80 Go SSD (croissance DB ~100 Mo/mois, NetCDF/GRIB ~2 Go/mois avec rotation)
- **Bande passante** : illimitée (utile pour télécharger ERA5/AROME quotidiennement)


### Procédure de déploiement V1.0

```bash
# 1. SSH sur le VPS OVH
ssh ubuntu@vps-fd6225c4.vps.ovh.net

# 2. Cloner le repo (avec Git LFS pour le dump 333 Mo)
git clone https://github.com/adecholaA1/meteo_ia_france.git
cd meteo_ia_france

# 3. Créer le .env de production avec les vraies valeurs
cp .env.production.example .env.production
nano .env.production
# - Générer DB_PASSWORD via : openssl rand -base64 32
# - Renseigner CDS_API_KEY (https://cds.climate.copernicus.eu/api-how-to)
# - Vérifier CORS_ORIGINS=https://meteo-ia.fr

# 4. Lancer la stack dockerisée
docker compose --env-file .env.production up -d --build

# 5. Vérifier que tout tourne
docker compose ps
curl http://localhost:8080/api/health

# 6. Configurer Nginx host (NON dockerisé) pour reverse proxy meteo-ia.fr → 8080
sudo nano /etc/nginx/sites-available/meteo-ia.fr
# server { server_name meteo-ia.fr www.meteo-ia.fr;
#          location / { proxy_pass http://localhost:8080; ... } }

# 7. HTTPS via Certbot
sudo certbot --nginx -d meteo-ia.fr -d www.meteo-ia.fr --email kadechola@gmail.com

# 8. Configurer la crontab pour les pipelines Python
crontab -e
# (coller le bloc cron ci-dessus)
```

---

## 🎓 Décisions techniques majeures

### 1. JAX au lieu de PyTorch
Choix imposé par GraphCast (Google DeepMind utilise JAX). Avantage : compilation JIT performante. Inconvénient : pas de GPU sur VPS OVH → on accepte une inférence CPU lente (~5–8 min) avec cron.

### 2. Inférence batch via cron, pas API on-demand
GraphCast prend ~5–8 min par inférence sur CPU. Une API on-demand serait inutilisable. Choix : on calcule à l'avance, on stocke en DB, le backend ne fait que lire.

### 3. Express au lieu de FastAPI pour le backend
Initialement prévu : Express + FastAPI. Décision finale : Express seul, car le backend ne fait que SELECT SQL — pas de calcul lourd qui justifierait Python. Pattern hérité du projet précédent ai-elec-conso (éprouvé).

### 4. Format LONG en DB
Voir section [Base de données](#-base-de-données) ci-dessus. Justifié par évolutivité.

### 5. Calcul astronomique de TOA
Plutôt que d'utiliser les valeurs natives de chaque source (qui peuvent diverger), on calcule TOA nous-mêmes avec la formule de Spencer 1971. Garantit la cohérence inter-sources et évite tout biais artificiel.

### 6. Vues "fresh" plutôt que suppression des runs anciens
On conserve **toutes** les prédictions en DB (utile pour analyse de dégradation par horizon, debug). Le frontend lit des **vues** qui filtrent automatiquement le run le plus récent. Pas de suppression destructive.

### 7. ERA5 avec latence J-6 (pas J-5)
ECMWF annonce officiellement une latence J-5, mais la réalité observée est que les dernières heures du J-5 sont parfois encore en cours de production à 16h UTC. On prend J-6 par sécurité dans les pipelines.

### 8. Grille 0.25° non filtrée (terre + mer)
On garde les 2 925 points (terre + mer) en DB. Le filtrage terre/mer est une question **visuelle** traitée côté frontend dès l'étape 9 : la heatmap n'affiche que les 103 villes principales (toutes terrestres) avec marker visible, mais les 2 925 points restent disponibles dans le tooltip et la couche zoom. Cette approche évite la duplication de données entre DB et frontend, tout en préservant un rendu visuel propre.

### 9. MAE circulaire pour les variables angulaires
La direction du vent étant une grandeur cyclique (0° = 360°), le pipeline `scripts/mae/compute_mae.py` applique une distance angulaire minimale `min(|a-b| mod 360, 360 - |a-b| mod 360)` pour `wind_direction_10m_deg`, déclarée dans une constante `CYCLIC_VARIABLES` extensible. Le `bias` est forcé à `NULL` pour cette variable (pas d'interprétation physique simple sur un angle). Cette correction a divisé par ~3 les MAE reportés sur la direction du vent en les ramenant dans les normes ECMWF (~30° pour AROME, ~70° pour GraphCast).

### 10. JSON statique pré-généré pour le frontend
Plutôt que de servir les données via API en runtime, le frontend embarque un **JSON statique pré-généré au build** par `scripts/generate_static_data.mjs`. Avantages : aucun appel API au chargement (performance), cache navigateur immuable, hébergement statique possible (CDN / GitHub Pages), rejouabilité de la version `v1.0` même si les données évoluent. Ce script est appelé automatiquement après l'ingestion CSV (hook post-ingestion backend) pour garantir la synchronisation. Trade-off accepté : la mise à jour du frontend nécessite un re-build, mais ce build prend ~30 s et peut être déclenché par cron ou GitHub Actions.

### 11. Pattern hybride API runtime / JSON statique (étape 10)
Plutôt que de remplacer le mode statique par un mode API runtime, le frontend conserve **les deux** et permet de basculer entre eux. Cette flexibilité offre : performance maximale par défaut (mode statique pour la prod CDN), démonstration pédagogique en live (mode API pour les recruteurs), debug local efficace (pas de rebuild après ingestion), fallback gracieux (si backend tombé, le statique fonctionne toujours). Le toggle est contrôlé par 2 niveaux : variable d'env `VITE_USE_API` au build + bouton UI dans le header. Les composants consommateurs sont totalement agnostiques — un seul hook (`useStaticData`) orchestre la bascule en interne. Trade-off accepté : un peu plus de code (3 fichiers nouveaux : `DataSourceContext`, `apiService`, `DataSourceToggle`) mais gain énorme en flexibilité opérationnelle.

### 12. Cache backend en 4 couches + indexation B-tree composite (étape 11)
Le diagnostic curl par endpoint a révélé deux causes additives à la latence cold cache de 10–15 s sur le premier clic ville : (a) absence d'index `(latitude, longitude, timestamp)` sur les 3 tables de prédictions (full scan sur 654K lignes) et (b) endpoint `/available-times` exécutant un `GROUP BY` + `ARRAY_AGG(DISTINCT...)` non indexable, appelé 3 fois par chargement de page. La solution architecturale combine **indexation au niveau DB** (3 index B-tree composites, gain 130×) et **cache applicatif en 4 couches** (TTL 1 h sur `/available-times`, invalidation hook après ingestion, pre-warming au démarrage backend, cron keep-alive `*/30 6-22 * * *`). Pas de Redis : le `node-cache` in-process suffit pour ce volume de trafic et reste fail-safe au redémarrage grâce au pre-warming. Trade-off accepté : 22 s de pre-warming bloquant au boot du serveur Express, mais aucun visiteur ne paie le cold cache ensuite.

### 13. Carte interactive synchronisée aux courbes via React Context (étape 11)
La sélection d'une ville sur la carte Leaflet doit propager l'état à 6 ChartCards distinctes plus le ZoomDialog. Trois options architecturales évaluées : (a) prop drilling via le Dashboard (rejeté : 6+ niveaux de props), (b) state global Zustand (rejeté : sur-dimensionné pour un seul état partagé), (c) React Context dédié (retenu). Le `SelectedCityContext` expose `selectedCity` (état), `setSelectedCity` (action) et `chartsBandRef` (référence DOM pour le scroll). TanStack Query orchestre le caching des fetchs avec `queryKey: ["timeseries", lat, lon, 14]`, `staleTime: 5min`, `gcTime: 10min`. Coordonnées arbitraires snap-ées à la grille 0.25° via `Math.round(value/0.25)*0.25` avant requête (la DB ne contient que des multiples de 0.25°). Trade-off accepté : un peu de boilerplate (Provider + hook custom) mais découplage complet entre la carte et les charts.

### 14. Logs centralisés append-only par pipeline (étape 11)
Les 4 pipelines Python (`era5`, `arome`, `graphcast_gfs`, `mae`) avaient chacun leur `logging.basicConfig` dupliqué. Trois options évaluées pour la centralisation : (a) helper partagé dans `scripts/utils/logging_setup.py` (retenu), (b) variable d'environnement avec parsing en chaque pipeline (rejeté : pas DRY), (c) librairie tierce type Loguru (rejeté : dépendance supplémentaire pour un besoin simple). La fonction `setup_pipeline_logging(source_name)` configure simultanément un `StreamHandler` (console) et un `FileHandler(mode="a")` (fichier `logs/<source>.log` append cumulatif). Banner `🚀 Nouveau run de pipeline : {SOURCE}` au début de chaque exécution pour visualiser les frontières entre runs dans le fichier. Trade-off accepté : un import supplémentaire dans chaque pipeline mais source de vérité unique pour le format / chemin / mode.

---

## 🔮 Évolutions futures

### v1.1 (court terme, post-déploiement)
- Comparaison `graphcast_vs_arome` (modèle vs modèle, sans vérité)
- Endpoint `POST /api/cache/flush` (invalidation après ingestion)
- Tests unitaires Jest + supertest sur le backend
- **Skill Score normalisé** vs climatologie persistante (métrique standard météo)
- **Bias correction GraphCast** par offset variable / région / saison appris sur ERA5
- **CRPS / score de Brier** segmenté par seuils pour évaluer rigoureusement les précipitations
- Authentification basique (clé API en header) si l'API est exposée publiquement

### v2.0 (moyen terme)
- **Fine-tuning de Pangu-Weather** sur la France (dataset ERA5 régional)
- Ensembling Pangu-Weather + AROME (moyenne pondérée par variable)
- Ajout de `total_cloud_cover` pour calcul GHI au sol (production photovoltaïque réelle)
- Variables 3D (vent à 100m pour parcs éoliens)

### v3.0 (long terme)
- **ClimaX fine-tuné** comme modèle fondation alternatif à GraphCast / Pangu-Weather
- Production photovoltaïque calculée avec modèle PV (GHI + température)
- Production éolienne calculée avec courbe de puissance turbines
- Authentification utilisateur, plans payants, dashboards personnalisés

---

# 🏛️ Météo IA France — Architecture (English)

> 🇫🇷 **Version française au-dessus** ([go to French](#-météo-ia-france--architecture))

Document describing the global technical architecture of the Météo IA France project: data pipelines, database, backend API, frontend, deployment. To be kept up-to-date with every major evolution.

---

## 🎯 Vision & context

**Météo IA France** is a weather forecasting platform for the **energy sector** (wind, solar, trading), comparing:
- **GraphCast Operational** (Google DeepMind, AI foundation model)
- **AROME** (Météo-France, regional physical model)
- **ERA5** (ECMWF, reference ground truth)

The goal is not to replace commercial providers, but to provide an **open-source platform for transparent model comparison**, focused on metropolitan France (0.25° grid, 2,925 points).

---

## 🌐 System overview

See architecture diagram in French section above.

The system is organized in **strictly isolated layers**:

| Layer | Role | Talks to |
|---|---|---|
| External sources | Provide raw data | (nothing — pulled by pipelines) |
| Python pipelines | Download, process, ingest | External sources + DB |
| PostgreSQL | Stores all data | Pipelines (INSERT) + Backend (SELECT) |
| Express backend | Reads DB, exposes JSON | DB + Frontend |
| React frontend | Displays, visualizes, interacts | Backend only |

➡️ No layer skips a step. Backend never runs Python inference. Frontend never talks directly to PostgreSQL.

---

## 🔄 Data pipelines

3 independent pipelines feed the DB, each with its own `run_daily_pipeline.py` orchestrator, launched by daily cron.

| Pipeline | Source | Cron (UTC) | Output table |
|---|---|---|---|
| GraphCast | GFS NOMADS (NOAA) | 23:30 | `graphcast_predictions` |
| ERA5 | ECMWF CDS API | 08:00 (target J-6) | `era5_truth` |
| AROME | data.gouv.fr (Météo-France) | 00:00 | `arome_forecasts` |
| MAE | PostgreSQL JOIN | 09:00 | `mae_metrics` |

See French section for detailed pipeline diagrams.

---

## 💾 Database

**Stack**: PostgreSQL 15 + PostGIS 3.4 (Docker)

**Schema**: 4 tables + 2 views (see French section for full SQL)
- `era5_truth`, `arome_forecasts`, `graphcast_predictions`, `mae_metrics`
- Views `arome_forecasts_fresh` and `graphcast_predictions_fresh` filter the most recent run per tuple

**Storage format**: LONG (1 row = 1 variable × 1 timestamp × 1 GPS point)

**Timezone**: all timestamps in UTC (`TIMESTAMP WITH TIME ZONE`), conversion to Europe/Paris done at frontend level

**Volume** (as of 2026-04-25): ~1.96M rows total, growth ~100 MB/month

---

## 🔌 Backend API

See [backend/README.md](./backend/README.md) for full details.

- **Stack**: Express 5 + node-postgres + cors + morgan + rate-limit
- **8 endpoints**: health, status, forecast (4), mae (2), heatmap (1)
- **Cache**: in-house middleware, RAM, default TTL 10 min
- **v1.0 security**: 100 req/h/IP rate limit, configurable CORS, no auth
- **Port**: 3001

Backend is intentionally **stateless** and **idempotent**: can be restarted at any time without data loss.

---

## 🎨 Frontend

> ✅ **Step 9 completed** — React dashboard + public Methodology page delivered.

### Tech stack

| Component | Choice | Why |
|---|---|---|
| Framework | **React 19** + TypeScript 5 | Concurrent rendering, Suspense, modern hooks |
| Build tool | **Vite 8** | Ultra-fast HMR, native TS-optimized build |
| Styling | **Tailwind CSS v4** + native Vite plugin | Atomic CSS, `dark` class mode, OKLCH palette |
| Components | **shadcn/ui** (Radix Nova preset) | Copy-paste architecture, no heavy dependencies |
| Charts | **Recharts** | Synchronized curves, interactive legends, adaptive axes |
| Map | **react-leaflet 4** + Leaflet 1.9 | Interactive map, Stadia Alidade Smooth Dark background |
| Routing | **react-router-dom v7** | Separate bilingual routes (`/fr`, `/en`, `/fr/methodologie`, `/en/methodology`) |
| HTTP client | Native `fetch` + static JSON | No Axios dependency, JSON pre-generated at build |

### Component architecture

The frontend uses **static pre-generated JSON** rather than runtime API calls, for performance, browser cache efficiency, and replayability. A Node.js script `scripts/generate_static_data.mjs` queries the Express backend and writes JSON files to `frontend/src/data/`. This script is automatically called after CSV ingestion in the backend pipeline (post-ingestion hook), guaranteeing the frontend is always in sync with the latest data.

### Delivered pages

#### 1. Main dashboard (`/fr` or `/en`)

- **Header**: title "Météo IA France" / "France AI Weather", live clock (auto DST FR: UTC+1 winter, UTC+2 summer), dark/light toggle, FR ↔ EN switch with route preservation
- **Interactive France map**:
  - Stadia Alidade Smooth Dark background (zoom 6, centered on Saintes)
  - 103 main cities with **colored heatmap** (visible CircleMarker, adaptive palette per variable)
  - 10 **pins 📍** on the largest cities
  - Rich hover tooltips: city name, AROME, GraphCast, ERA5 truth, absolute error
  - 3 overlay dropdowns (source / variable / timestamp) with z-index 9999 to pass over Leaflet
  - 4 available timestamps (00h, 06h, 12h, 18h UTC)
  - Modal zoom mode (no map overlay)
- **MAE table**: 4 horizons (h6/h12/h18/h24) × 6 variables, colored AROME/GraphCast ratio, zoom mode
- **6 ChartCards**: one per weather variable, synchronized Recharts time-series curves (cursor shared across all cards), 3 superimposed sources, adaptive axes with FR/EN locale, zoom mode
- **Footer**: colored sources (ECMWF / Météo-France / DeepMind with their official colors), copyright, v1.0, **"Methodology" link** between version and "Source code" GitHub

#### 2. Public Methodology page (`/fr/methodologie` or `/en/methodology`) ⭐

8 sections accessible to non-developers:

1. **About** — project vision and target audience
2. **Glossary** — 16 acronyms explained in plain text (NWP, MAE, RMSE, Bias, ERA5, AROME, GraphCast, GFS, GRIB, NetCDF, GHI, TOA, OKLCH, etc.)
3. **Variables explained** — 6 detailed cards (t2m, wind_speed, wind_direction, msl, tp_6h, toa) with unit, typical range, conversion, energy interest
4. **Sources compared** — 3 cards with 3px colored borders (ERA5 blue #1E73E8, AROME green #1D9E75, GraphCast orange #F08C3D), description + official link
5. **Comparison table** — 14 side-by-side rows (resolution, frequency, latency, model type, etc.) between the 3 sources
6. **v1.0 limitations** — 5 numbered limitations (orange, framed): AROME resampled, only 3-day period, ERA5 latency, default MAE on 24h, no fine-tuning
7. **v2.0 / v3.0 roadmap** — v2.0: Pangu-Weather fine-tuning, AROME native resolution, multiple daily runs, hourly time step; v3.0: ClimaX fine-tuned
8. **Tech stack** — 5 cards (Pipelines green, DB blue, **Backend orange ⭐**, Frontend purple, DevOps gray) with technology lists

### UX conventions

- **100% bilingual**: FR then EN, instant switching, different URLs (no `?lang=fr` querystring)
- **Light + Dark mode**: Claude-style OKLCH palette (colors auto-adapt, no CSS duplication)
- **Timezone**: all backend timestamps in UTC, frontend converts to Europe/Paris with auto DST
- **Responsive**: Tailwind breakpoints (mobile / tablet / desktop), viewport-adaptive map
- **Accessibility**: full keyboard navigation, aria-labels on interactions, WCAG AA contrasts

### Bugs resolved during step 9

| # | Bug | Solution |
|---|---|---|
| 1 | Z-index Leaflet vs Radix dropdowns | Global CSS `[data-slot="select-content"]` at `z-index: 9999 !important` |
| 2 | Backend required `06` format but JSON script sent `6` | `String(t.hour).padStart(2, "0")` in `generate_static_data.mjs` |
| 3 | Tailwind v4 and broken CSS braces | `12/12` brace check + `npx vite optimize` |
| 4 | Insensitive hover on map points | Invisible CircleMarker `radius=14` overlay on each visible point |
| 5 | MAE zoom mode overlapping the map | Radix `<Dialog>` with overlay 9998 and content 9999 |

📚 Documentation: [frontend/README.md](./frontend/README.md)

---

📚 Documentation: [frontend/README.md](./frontend/README.md) (FR + EN detailed)

---

## 🔌 Step 10 — Hybrid pattern API runtime / static JSON

> ✅ **Step 10 completed** — frontend ↔ Express backend connection with transparent switching between 2 data sources.

### Vision

Step 10 connects the React frontend to the Express backend, but with a **more mature approach than a simple runtime binding**: we add **API runtime mode** **alongside** the existing **static JSON mode**, and allow live switching between the two, without rebuild or redeploy.

This flexibility serves 3 use cases:

| Case | Recommended mode | Why |
|---|---|---|
| 🌐 Public production (CDN, GitHub Pages, LinkedIn demo) | 💾 Static JSON | Performance, free hosting, works offline |
| 🔧 Live pedagogical demonstration | 🟢 API runtime | Visible network devtools, traceable requests |
| 🐛 Local debug (DB modification, immediate verification) | 🟢 API runtime | No rebuild after each ingestion |
| 📱 4G mobile user | 💾 Static JSON | Saves data + faster |
| 🔬 Multi-runs daily (v2.0) | 🟢 API runtime | Data changing throughout the day |
| 🛡️ Backend down | 💾 Static JSON (fallback) | App keeps working |

### Switching mechanism

Active mode is controlled at **2 levels**:

1. **Environment variable** `VITE_USE_API` at build (default value)
   - `VITE_USE_API=false` → static JSON mode at startup
   - `VITE_USE_API=true` (or undefined) → API runtime mode at startup
2. **Live UI toggle** in the header (override on the fly)
   - 📡 button (green Wifi) = API mode active
   - 💾 button (gray Database) = static JSON mode active
   - On click, app re-fetches data immediately from the new source

### New files architecture

```
frontend/src/
├── contexts/
│   └── DataSourceContext.tsx     # ⭐ React context managing useApi + toggleDataSource
├── services/
│   └── apiService.ts             # ⭐ 9 typed methods to the 8 Express endpoints
├── hooks/
│   ├── useStaticData.ts          # 🔄 Modified: API/static switching internally
│   └── useHeatmapData.ts         # 🔄 Modified: API/static switching internally
└── components/layout/
    ├── DataSourceToggle.tsx      # ⭐ Toggle button 📡/💾 in header
    └── Header.tsx                # 🔄 Modified: DataSourceToggle added
```

### Component abstraction

**No consumer component was modified** during step 10. Components like `FranceMap`, `MaeTableCard`, `ChartCard` keep calling `useStaticData()` and `useHeatmapData()` exactly as before. Switching is fully transparent — the hook's role is now: "load data according to the active mode".

### TanStack Query v5

The project installs `@tanstack/react-query` and configures a `QueryClient` at the app root (`main.tsx`), with robust defaults (5min staleTime, 30min gcTime, 2 retries with exponential backoff, refetchOnWindowFocus disabled). At step 10, **the hooks don't yet directly consume `useQuery()`** (the lightweight option kept `useStaticData` and `useHeatmapData` mostly unchanged). TanStack remains **ready for use** for future dedicated hooks (e.g. `useApiHistory` for MAE history charts), automatically benefiting from caching, deduplication, and retries.

### 3 real bugs identified and fixed thanks to hybrid mode

API runtime mode confronted the frontend with the real backend contract, revealing 3 issues invisible in static mode:

| # | Bug | Cause | Solution |
|---|---|---|---|
| 1 | **Multi-port CORS** | Vite started on 5174 (5173 busy), backend allowed only 5173 | Free port 5173 (long-term: more permissive CORS whitelist in dev) |
| 2 | **Paris coordinates** | Frontend sent `lat=48.85, lon=2.35` (exact Paris), backend found nothing on 0.25° grid | Alignment on closest grid point: `lat=49, lon=2.5` |
| 3 | **ERA5 J-6 latency** | Frontend requested heatmap for `2026-04-27 18h` but ERA5 doesn't have this date yet → 404 | Use `available-times?source=era5` instead of `?source=arome` (ERA5 constrains comparison availability) |

📚 Detailed documentation:
- [frontend/README.md](./frontend/README.md) — detail of hooks, contexts, services
- [backend/README.md](./backend/README.md) — detail of 8 Express endpoints

---

## 🚀 Deployment & production

> ✅ Step 12 (local dockerization) · 🔜 VPS deployment in progress · Domain `meteo-ia.fr` registered at OVH

### 🐳 Docker V1.0 architecture (step 12)

The project is now fully orchestrated by **Docker Compose**: a single `docker-compose.yml` file at the root deploys the entire stack (3 containers + 1 network + 1 persistent volume) with one command.

#### 3-service topology

```
┌────────────────────────────────────────────────────────────────────┐
│ Isolated Docker network: meteo_ia_network (bridge driver)          │
│                                                                    │
│  ┌──────────────────┐   ┌──────────────────┐   ┌────────────────┐  │
│  │  meteo_ia_       │   │  meteo_ia_       │   │  meteo_ia_     │  │
│  │  frontend        │   │  backend         │   │  pg_db_compose │  │
│  │                  │   │                  │   │                │  │
│  │  nginx:1.27      │──▶│  node:22         │──▶│  postgis:15    │  │
│  │  (multi-stage)   │   │  (single-stage)  │   │  (alpine)      │  │
│  │                  │   │                  │   │                │  │
│  │  Port 80→8080    │   │  Port 3001→3001  │   │  Port 5432→5433│  │
│  │  ~23 MB image    │   │  ~60 MB image    │   │  ~250 MB image │  │
│  │  HC: nginx-health│   │  HC: /api/health │   │  HC: pg_isready│  │
│  └──────────────────┘   └──────────────────┘   └────────────────┘  │
│                                                                    │
│  Persistent volume : meteo_ia_pg_data (PG data between restarts)   │
│  Init bind mount   : backend/backup/meteo_ia_db.sql (333 MB)       │
└────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ depends_on: condition: service_healthy
                                  │ (postgres healthy → backend starts)
                                  ▼
                            Backend only starts when
                            Postgres responds to pg_isready
```

#### Files delivered

| File | Role | Size |
|---|---|---|
| `backend/Dockerfile` | Backend single-stage image `node:22-alpine` + non-root user | ~60 MB |
| `backend/.dockerignore` | Excludes `node_modules`, `.env`, `backup/`, `.git`, `logs` | — |
| `frontend/Dockerfile` | Frontend multi-stage image (Vite builder + Nginx prod) | ~23 MB |
| `frontend/nginx.conf` | Nginx config: gzip + asset caching + SPA fallback + **/api/ proxy** | — |
| `frontend/.dockerignore` | Excludes `node_modules`, `dist/`, `.env`, `.git` | — |
| `docker-compose.yml` | Orchestration of 3 services + healthchecks + volume + network | ~7.8 KB (130 commented lines) |
| `.env` (root) | Local Postgres credentials (NOT committed) | — |
| `.env.production.example` | Production template committed with `CHANGEME` placeholders | ~8 KB |
| `.gitignore` (root) | 4.7 KB covering secrets, builds, GraphCast cache, .sql backup exception | ~4.7 KB |

#### Reverse proxy `/api/*` in frontend container's Nginx

Critical configuration of `frontend/nginx.conf` solving the "how does the frontend call the backend in Docker" problem:

```nginx
# Reverse proxy /api/* → backend container
location /api/ {
    proxy_pass http://backend:3001;     # "backend" = compose service name
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_connect_timeout 30s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
}

# SPA fallback (React Router)
location / {
    try_files $uri $uri/ /index.html;
}
```

→ Browser does `fetch('/api/forecast/...')` (relative URL), frontend container's Nginx intercepts and **forwards to `backend:3001`** via Docker's internal DNS. Frontend therefore **doesn't need** to know the backend's absolute URL (`VITE_API_URL=""`).

### Target: OVH VPS Ubuntu 24

| Component | Tool | Role | V1.0 status |
|---|---|---|---|
| DB container | `postgis/postgis:15-3.4-alpine` | PostgreSQL + PostGIS isolated, healthcheck | ✅ Dockerized |
| Backend container | `meteo-ia-backend:1.0.0` (custom image) | Express API, healthcheck | ✅ Dockerized |
| Frontend container | `meteo-ia-frontend:1.0.0` (custom image) | Nginx + static assets + `/api/` reverse proxy | ✅ Dockerized |
| Orchestration | Docker Compose v2 | Full stack in 1 command | ✅ |
| Host reverse proxy | **System** Nginx on VPS (separate from containers) | HTTPS, subdomain routing | 🔜 To configure |
| TLS certificate | Certbot (Let's Encrypt) | Auto-renewed HTTPS for `meteo-ia.fr` | 🔜 To configure |
| Cron | UTC crontab on VPS OS (NOT in Docker) | Runs 4 daily Python pipelines | 🔜 To configure |
| Process manager | ❌ No more PM2 (replaced by Docker `restart: unless-stopped`) | Native Docker auto-restart | ✅ |

### Planned crontab (UTC, on VPS OS)

```
 0  1 * * *  cd /opt/meteo_ia_france && conda run -n meteo_ia python -m graphcast_gfs.run_daily_pipeline
30  1 * * *  cd /opt/meteo_ia_france && conda run -n meteo_ia python -m arome.run_daily_pipeline
 0  2 * * *  cd /opt/meteo_ia_france && conda run -n meteo_ia python -m era5.run_daily_pipeline
 0  3 * * *  cd /opt/meteo_ia_france && conda run -n meteo_ia python -m mae.run_daily_pipeline
```

### Server resources

- **VPS-2 OVH**: 4 GB RAM ⚠️ (GraphCast inference needs ~6 GB → swap mandatory)
- **Disk**: 80 GB SSD (DB growth ~100 MB/month, NetCDF/GRIB ~2 GB/month with rotation)
- **Bandwidth**: unlimited (useful for daily ERA5/AROME downloads)
- **Coexistence**: VPS already hosts `ai-elec-conso.fr` (other project, ports 5432/8000 used). Host Nginx routes by subdomain.

### V1.0 deployment procedure (in progress)

```bash
# 1. SSH to OVH VPS
ssh ubuntu@vps-fd6225c4.vps.ovh.net

# 2. Clone repo (with Git LFS for the 333 MB dump)
git clone https://github.com/adecholaA1/meteo_ia_france.git
cd meteo_ia_france

# 3. Create production .env with real values
cp .env.production.example .env.production
nano .env.production
# - Generate DB_PASSWORD via: openssl rand -base64 32
# - Fill CDS_API_KEY (https://cds.climate.copernicus.eu/api-how-to)
# - Verify CORS_ORIGINS=https://meteo-ia.fr

# 4. Launch dockerized stack
docker compose --env-file .env.production up -d --build

# 5. Verify it's running
docker compose ps
curl http://localhost:8080/api/health

# 6. Configure host Nginx (NOT dockerized) for reverse proxy meteo-ia.fr → 8080
sudo nano /etc/nginx/sites-available/meteo-ia.fr
# server { server_name meteo-ia.fr www.meteo-ia.fr;
#          location / { proxy_pass http://localhost:8080; ... } }

# 7. HTTPS via Certbot
sudo certbot --nginx -d meteo-ia.fr -d www.meteo-ia.fr --email kadechola@gmail.com

# 8. Configure crontab for Python pipelines
crontab -e
# (paste cron block above)
```

---

## 🎓 Major technical decisions

1. **JAX over PyTorch** — imposed by GraphCast
2. **Cron batch inference, not on-demand API** — CPU inference takes 5–8 min
3. **Express only for backend** — no heavy compute justifies Python
4. **LONG format in DB** — schema evolution friendly
5. **Astronomical TOA computation** — guarantees inter-source consistency
6. **"Fresh" views, not destructive deletion** — keep all runs for analysis
7. **ERA5 latency J-6** — safety margin over official J-5
8. **Unfiltered 0.25° grid** — land/sea filtering is a frontend visual concern, handled in step 9 with a 103-main-city heatmap layer over the 2,925 raw grid
9. **Circular MAE for angular variables** — `scripts/mae/compute_mae.py` applies minimum angular distance for `wind_direction_10m_deg`, declared in an extensible `CYCLIC_VARIABLES` constant. `bias` forced to `NULL` (no simple physical meaning for a cyclic angle). Correction divided wind-direction MAE by ~3, bringing values into ECMWF norms (~30° AROME, ~70° GraphCast).
10. **Pre-generated static JSON for frontend** — rather than runtime API calls, the frontend embeds static JSON pre-generated at build by `scripts/generate_static_data.mjs`. Benefits: no API call on load (performance), immutable browser cache, static hosting possible (CDN / GitHub Pages), `v1.0` replayability even if data evolves. Hook post-ingestion in backend pipeline guarantees sync. Trade-off accepted: frontend update requires re-build (~30s), can be cron- or GitHub Actions-triggered.
11. **Hybrid pattern API runtime / static JSON (step 10)** — rather than replacing static mode with API runtime, the frontend keeps **both** and allows switching. Benefits: max performance by default (static for production CDN), live pedagogical demonstration (API for recruiters), efficient local debug (no rebuild after ingestion), graceful fallback (if backend down, static still works). Toggle controlled at 2 levels: `VITE_USE_API` env at build + UI button in header. Consumer components are fully agnostic — a single hook (`useStaticData`) orchestrates switching internally. Trade-off accepted: a bit more code (3 new files: `DataSourceContext`, `apiService`, `DataSourceToggle`) but huge gain in operational flexibility.
12. **4-layer backend cache + composite B-tree indexing (step 11)** — endpoint-level curl profiling revealed two additive causes for the 10–15s cold cache latency on first city click: (a) absence of `(latitude, longitude, timestamp)` index on the 3 prediction tables (full scan over 654K rows) and (b) `/available-times` endpoint executing a non-indexable `GROUP BY` + `ARRAY_AGG(DISTINCT...)`, called 3 times per page load. The architectural solution combines **DB-level indexing** (3 composite B-tree indexes, 130× gain) with **4-layer application cache** (1h TTL on `/available-times`, post-ingestion hook invalidation, pre-warming on backend startup, cron keep-alive `*/30 6-22 * * *`). No Redis: in-process `node-cache` is sufficient for this traffic volume and remains fail-safe at restart thanks to pre-warming. Trade-off accepted: 22s blocking pre-warming at Express server boot, but no visitor pays the cold cache afterward.
13. **Map-charts synchronization via React Context (step 11)** — selecting a city on the Leaflet map must propagate state to 6 distinct ChartCards plus the ZoomDialog. Three architectural options evaluated: (a) prop drilling via Dashboard (rejected: 6+ prop levels), (b) Zustand global state (rejected: oversized for a single shared state), (c) dedicated React Context (chosen). The `SelectedCityContext` exposes `selectedCity` (state), `setSelectedCity` (action) and `chartsBandRef` (DOM reference for scrolling). TanStack Query orchestrates fetch caching with `queryKey: ["timeseries", lat, lon, 14]`, `staleTime: 5min`, `gcTime: 10min`. Arbitrary coordinates snap to 0.25° grid via `Math.round(value/0.25)*0.25` before request (DB only contains multiples of 0.25°). Trade-off accepted: a bit of boilerplate (Provider + custom hook) but full decoupling between map and charts.
14. **Centralized append-only logs per pipeline (step 11)** — the 4 Python pipelines (`era5`, `arome`, `graphcast_gfs`, `mae`) each had their `logging.basicConfig` duplicated. Three centralization options evaluated: (a) shared helper in `scripts/utils/logging_setup.py` (chosen), (b) environment variable parsed in each pipeline (rejected: not DRY), (c) third-party library like Loguru (rejected: extra dependency for a simple need). The `setup_pipeline_logging(source_name)` function configures simultaneously a `StreamHandler` (console) and a `FileHandler(mode="a")` (cumulative append file `logs/<source>.log`). Banner `🚀 Nouveau run de pipeline : {SOURCE}` at the start of each run to visualize boundaries between executions in the file. Trade-off accepted: one extra import in each pipeline but single source of truth for format / path / mode.

---

## 🔮 Future evolutions

- **v1.1**: model-vs-model comparison (`graphcast_vs_arome`), cache flush endpoint, unit tests, **Skill Score** vs climatology, **GraphCast bias correction**, **CRPS/Brier** for precipitation
- **v2.0**: **Pangu-Weather fine-tuning** on France (regional ERA5 dataset), Pangu-Weather + AROME ensembling, total_cloud_cover for PV production, 3D variables (wind at 100m)
- **v3.0**: **ClimaX fine-tuned** as alternative foundation model, real PV/wind production via physical models, user accounts
