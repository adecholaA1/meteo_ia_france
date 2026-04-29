# 🎨 Météo IA France — Frontend

> 🇬🇧 **English version below** ([jump to English](#-météo-ia-france--frontend-english))

[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-8-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v4-38B2AC?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![TanStack Query](https://img.shields.io/badge/TanStack_Query-v5-FF4154?logo=reactquery&logoColor=white)](https://tanstack.com/query/latest)

Application React qui visualise les comparaisons de prévisions météorologiques entre **GraphCast Operational** (Google DeepMind), **AROME** (Météo-France) et **ERA5** (ECMWF, vérité terrain). Dashboard interactif bilingue (FR/EN) avec carte de France, tableau MAE, charts synchronisés, et page Méthodologie publique.

---

## 📑 Sommaire

1. [Pitch](#-pitch)
2. [Quick start](#-quick-start)
3. [Architecture des composants](#-architecture-des-composants)
4. [Pattern hybride API runtime / JSON statique ⭐](#-pattern-hybride-api-runtime--json-statique-)
5. [Variables d'environnement](#-variables-denvironnement)
6. [Conventions UX](#-conventions-ux)
7. [Bugs résolus](#-bugs-résolus)
8. [Stack technique détaillée](#-stack-technique-détaillée)
9. [Comment contribuer](#-comment-contribuer)

---

## 🎯 Pitch

Le frontend offre **2 pages bilingues** :

- **Dashboard** (`/fr` ou `/en`) : carte de France interactive avec heatmap colorée sur 103 villes, tableau MAE comparatif sur 4 horizons (h6/h12/h18/h24), 6 ChartCards de séries temporelles synchronisées, et toggle live entre données API et données statiques pré-générées.
- **Méthodologie** (`/fr/methodologie` ou `/en/methodology`) : 8 sections accessibles aux non-développeurs (glossaire, variables expliquées, sources comparées, limitations, roadmap, stack technique).

Le dashboard supporte **deux modes de chargement de données** : l'API Express en runtime (mode développement et démonstration) ou un JSON statique pré-généré au build (mode production CDN). La bascule est transparente pour les composants et possible **en live via un bouton dans le header**.

---

## 🚀 Quick start

### Prérequis

- **Node.js 20+** et **npm** (testé avec Node 22, npm 10)
- (optionnel) Backend Express tournant sur `localhost:3001` pour le mode API runtime

### Installation

```bash
cd frontend
npm install
```

### Lancement développement

```bash
npm run dev
```

➡️ Application accessible sur **http://localhost:5173** (port par défaut Vite). Si le 5173 est occupé, Vite essaiera 5174 et au-delà — attention dans ce cas à la config CORS du backend.

### Build production

```bash
npm run build
```

Le résultat est généré dans `frontend/dist/`. C'est un site **100% statique** (pas de serveur Node nécessaire) qui peut être servi par n'importe quel serveur HTTP (Nginx, GitHub Pages, Vercel, Netlify…).

### Preview du build localement

```bash
npm run preview
```

➡️ Sert le contenu de `dist/` sur **http://localhost:4173** pour tester la version production avant déploiement.

### Régénération du JSON statique

Le mode JSON statique (par défaut en production) repose sur un fichier `frontend/public/data/sample_forecast.json` et 6 fichiers `frontend/public/data/heatmaps/*.json`. Pour les régénérer après une nouvelle ingestion en DB :

```bash
cd .. # remonter à la racine du projet
node scripts/generate_static_data.mjs
```

Le script interroge le backend Express, agrège les données, et écrit les JSON dans `frontend/public/data/`. Il prend ~5 secondes.

---

## 🧩 Architecture des composants

```
frontend/src/
├── main.tsx                     # entry point, QueryClientProvider + DataSourceProvider
├── App.tsx                      # routing react-router (FR/EN, Dashboard/Methodology)
│
├── routes/
│   ├── DashboardPage.tsx        # / (FR) ou /en (EN)
│   └── MethodologyPage.tsx      # /fr/methodologie ou /en/methodology
│
├── components/
│   ├── layout/
│   │   ├── Header.tsx           # logo, horloge live (DST auto), DataSourceToggle, ModeToggle, LanguageSwitcher
│   │   ├── Footer.tsx           # 4 sources colorées, copyright, liens v1.0 / Méthodologie / Code source
│   │   ├── DataSourceToggle.tsx # ⭐ bouton 📡/💾 bascule API/static (étape 10)
│   │   ├── ModeToggle.tsx       # dropdown clair/sombre/système
│   │   └── LanguageSwitcher.tsx # bouton FR/EN avec préservation route
│   │
│   ├── map/
│   │   ├── FranceMap.tsx        # carte Leaflet 103 villes + 10 pins + 3 dropdowns + tooltips riches
│   │   └── ZoomDialog.tsx       # modal universel (carte / MAE / charts)
│   │
│   ├── charts/
│   │   ├── ChartCard.tsx        # 1 par variable, 3 sources superposées, curseur synchronisé
│   │   └── MaeTableCard.tsx     # 4 horizons × 6 variables, ratio coloré
│   │
│   └── methodology/             # ⭐ 8 sections de la page Méthodologie
│       ├── AboutSection.tsx
│       ├── GlossarySection.tsx        # 16 sigles expliqués
│       ├── VariablesSection.tsx       # 6 variables détaillées
│       ├── SourcesSection.tsx         # 3 cards bord coloré
│       ├── ComparisonTable.tsx        # 14 lignes côte-à-côte
│       ├── LimitationsSection.tsx     # 5 limitations v1.0
│       ├── RoadmapSection.tsx         # v2.0 Pangu-Weather, v3.0 ClimaX
│       └── TechStackSection.tsx       # 5 cards (Pipelines, DB, Backend, Frontend, DevOps)
│
├── contexts/
│   ├── DataSourceContext.tsx    # ⭐ gère useApi + toggleDataSource (étape 10)
│   └── ThemeContext.tsx         # gère light/dark/system
│
├── services/
│   └── apiService.ts            # ⭐ 9 méthodes typées vers les 8 endpoints Express (étape 10)
│
├── hooks/
│   ├── useStaticData.ts         # 🔄 hook hybride API/static (étape 10)
│   └── useHeatmapData.ts        # 🔄 hook hybride pour heatmaps (étape 10)
│
├── i18n/
│   ├── index.ts                 # registre useT() + locales FR/EN
│   ├── fr.ts                    # traductions FR
│   ├── en.ts                    # traductions EN
│   ├── methodology.fr.ts        # ~217 lignes, 14 KB
│   └── methodology.en.ts        # ~217 lignes, 13 KB
│
├── lib/
│   ├── timezone.ts              # gestion DST automatique UTC+1/UTC+2
│   ├── numberFormat.ts          # locale FR/EN sur les chiffres
│   ├── colorScales.ts           # palette OKLCH + SOURCE_COLORS
│   └── utils.ts                 # cn() pour className conditionnelles (shadcn)
│
├── types/
│   └── forecast.ts              # types TypeScript partagés
│
└── components/ui/               # composants shadcn/ui (Button, Dialog, Select, etc.)

frontend/public/
└── data/
    ├── sample_forecast.json     # JSON statique principal (~7 MB)
    └── heatmaps/                # 6 fichiers, ~11 MB total
        ├── t2m_celsius.json
        ├── wind_speed_10m_ms.json
        ├── wind_direction_10m_deg.json
        ├── msl_hpa.json
        ├── tp_6h_mm.json
        └── toa_wm2.json
```

### Hiérarchie des providers (`main.tsx`)

```tsx
<StrictMode>
  <QueryClientProvider client={queryClient}>     // TanStack Query (cache/retry)
    <DataSourceProvider>                          // ⭐ bascule API/static
      <BrowserRouter>
        <ThemeProvider>                           // light/dark/system
          <App />
        </ThemeProvider>
      </BrowserRouter>
    </DataSourceProvider>
    <ReactQueryDevtools />                        // dev only
  </QueryClientProvider>
</StrictMode>
```

---

## 🔌 Pattern hybride API runtime / JSON statique ⭐

C'est **la spécificité architecturale principale** du frontend, livrée à l'étape 10 du projet.

### Pourquoi 2 modes ?

Plutôt que de remplacer un mode par l'autre, le frontend conserve **les deux** et permet de basculer entre eux selon le besoin :

| Cas d'usage | Mode recommandé | Raison |
|---|---|---|
| 🌐 Production publique (CDN, GitHub Pages, démo recruteur) | 💾 JSON statique | Performance, hébergement gratuit, fonctionne offline |
| 🔧 Démonstration pédagogique en live | 🟢 API runtime | Devtools réseau visibles, requêtes traceables |
| 🐛 Debug local après nouvelle ingestion DB | 🟢 API runtime | Pas besoin de rebuild |
| 📱 Utilisateur sur 4G mobile | 💾 JSON statique | Économise data + plus rapide |
| 🔬 Multi-runs quotidiens (v2.0) | 🟢 API runtime | Données qui bougent en cours de journée |
| 🛡️ Backend tombé en panne | 💾 JSON statique (fallback) | L'app continue de fonctionner |

### Architecture interne

```
┌──────────────────────────────────────────────┐
│  Composant (FranceMap, ChartCard, etc.)      │
│  → appelle useStaticData() / useHeatmapData()│
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│  Hook hybride                                │
│  → lit useDataSource().useApi                │
│  → choisit en interne entre :                │
└────────┬───────────────────────────┬─────────┘
         │                           │
         ▼                           ▼
┌────────────────┐         ┌──────────────────┐
│ apiService.ts  │         │ fetch /data/*.json│
│ (9 endpoints)  │         │ (build-time)     │
└────────────────┘         └──────────────────┘
```

### Le contrat des composants reste inchangé

```tsx
// FranceMap.tsx — IDENTIQUE avant et après l'étape 10
function FranceMap() {
  const { data, loading, error } = useStaticData()
  // → la fonction du hook est désormais : "charge selon le mode actif"
  // → le composant ne sait pas d'où viennent les données
}
```

### Bascule contrôlée à 2 niveaux

#### 1. Variable d'environnement (au démarrage)

```bash
# frontend/.env
VITE_USE_API=false   # mode JSON statique (recommandé pour la prod)
# VITE_USE_API=true  # mode API runtime (recommandé pour le dev)
```

#### 2. Toggle UI (en live, dans le header)

Le bouton 📡 / 💾 dans le header permet de basculer **sans rebuild** :

- 📡 **Wifi vert** = mode API runtime actif
- 💾 **Database gris** = mode JSON statique actif

Au clic, l'app re-fetch immédiatement les données depuis la nouvelle source. Visible en direct dans les **devtools réseau** du navigateur.

### Composants livrés à l'étape 10

| Fichier | Rôle |
|---|---|
| `services/apiService.ts` | 9 méthodes typées vers les 8 endpoints Express, gestion d'erreur unifiée, query params, types TypeScript stricts |
| `contexts/DataSourceContext.tsx` | Context React qui gère le mode actif (`useApi: boolean`) avec lecture de `VITE_USE_API` au démarrage et `toggleDataSource()` |
| `hooks/useStaticData.ts` | Hook hybride : charge depuis l'API ou depuis `/data/sample_forecast.json` selon le contexte |
| `hooks/useHeatmapData.ts` | Idem pour les heatmaps : API runtime ou `/data/heatmaps/{variable}.json` |
| `components/layout/DataSourceToggle.tsx` | Bouton 📡/💾 dans le header pour basculer en live |

### Endpoints Express consommés en mode API

| Endpoint | Hook | Usage |
|---|---|---|
| `GET /api/status` | `useStaticData` | Compteurs DB + cache + uptime |
| `GET /api/forecast/available-times?source=graphcast` | `useStaticData` | Liste timestamps GraphCast |
| `GET /api/forecast/available-times?source=arome` | `useStaticData` | Liste timestamps AROME |
| `GET /api/forecast/available-times?source=era5` | `useHeatmapData` | Timestamps où la comparaison est possible |
| `GET /api/forecast/grid-points` | `useStaticData` | 2925 points GPS de la grille |
| `GET /api/forecast/timeseries?lat=49&lon=2.5&days=7` | `useStaticData` | Séries temporelles 7j |
| `GET /api/mae/comparison?horizon={6,12,18,24}` | `useStaticData` | Tableau MAE (4 appels parallèles) |
| `GET /api/heatmap/error?...` | `useHeatmapData` | Heatmap d'écart spatial |

> 📚 Documentation backend : [BACKEND.md](../BACKEND.md)

### TanStack Query v5 installé (mais pas encore consommé directement)

Le projet installe `@tanstack/react-query` et configure un `QueryClient` à la racine de l'app :

```tsx
new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,    // 5 min : données fraîches sans refetch
      gcTime: 30 * 60 * 1000,      // 30 min : garde en cache après inactivité
      retry: 2,                    // 2 retries automatiques (backoff exponentiel)
      refetchOnWindowFocus: false, // pas de refetch au retour sur l'onglet
    },
  },
})
```

À l'étape 10, **les hooks ne consomment pas encore `useQuery()` directement** (option allégée : `useStaticData` et `useHeatmapData` quasi inchangés). TanStack reste **prêt à l'emploi** pour les futurs hooks dédiés.

> ℹ️ Les **DevTools TanStack Query** (bouton flottant en bas à droite) sont actives en développement uniquement. Automatiquement exclues du build production par Vite. Pour les retirer complètement avant le déploiement : `npm uninstall @tanstack/react-query-devtools` + retirer 2 lignes dans `main.tsx`.

---

## ⚙️ Variables d'environnement

Toutes les variables doivent être préfixées par `VITE_` pour être exposées au client par Vite.

### `frontend/.env`

```bash
# Source de données par défaut au démarrage
# - "false" = mode JSON statique (charge /data/sample_forecast.json)
# - "true"  = mode API runtime (appelle http://localhost:3001/api/...)
# - non définie = mode API runtime (default)
VITE_USE_API=false

# URL du backend Express (override le défaut http://localhost:3001)
# Utile pour pointer vers un backend déployé en production
# VITE_API_URL=https://api.meteo-ia-france.fr
```

### `frontend/.env.production` (recommandé pour la prod)

```bash
VITE_USE_API=false
# Pas besoin de VITE_API_URL si on est en mode statique
```

### `frontend/.env.development`

```bash
VITE_USE_API=true
# VITE_API_URL=http://localhost:3001 (default)
```

⚠️ **Restart Vite obligatoire** (Ctrl+C puis `npm run dev`) après toute modification de `.env`. Vite ne lit ces fichiers qu'au démarrage.

---

## 🎨 Conventions UX

### Bilingue 100% (FR / EN)

- **2 routes séparées** : `/fr` et `/en` (pas de querystring `?lang=fr`)
- Switch instantané dans le header avec **préservation de la route** (`/fr/methodologie` → `/en/methodology`)
- Hook `useT()` qui retourne les traductions de la locale courante
- Tous les libellés, dates, nombres et tooltips sont localisés

### Light + Dark mode

- Palette **OKLCH** style Claude (les couleurs s'adaptent automatiquement, pas de duplication CSS)
- 3 modes : Clair / Sombre / Système (suit les préférences OS)
- Persistance dans localStorage via `ThemeContext`
- Toggle dans le header via `<ModeToggle>`

### Timezone

- **Tous les timestamps backend sont en UTC** (`TIMESTAMP WITH TIME ZONE` côté DB)
- Le frontend convertit vers Europe/Paris avec **gestion DST automatique** via `lib/timezone.ts`
- L'horloge live du header affiche `UTC+1` (hiver) ou `UTC+2` (été)

### Responsive

- Breakpoints Tailwind : mobile (< 768px), tablet (768-1024px), desktop (> 1024px)
- Carte qui s'adapte au viewport
- Grilles qui passent de 3 colonnes à 1 colonne en mobile

### Accessibilité

- Navigation clavier complète (Tab, Enter, Esc)
- Aria-labels sur toutes les interactions
- Contrastes WCAG AA respectés en light + dark
- Sr-only sur les icônes purement décoratives

---

## 🐛 Bugs résolus

### Étape 9 (frontend initial)

| # | Bug | Solution |
|---|---|---|
| 1 | Z-index Leaflet vs Radix dropdowns (dropdowns derrière la carte) | CSS global `[data-slot="select-content"]` à `z-index: 9999 !important` |
| 2 | Backend exigeait format `06` mais script JSON envoyait `6` | `String(t.hour).padStart(2, "0")` dans `generate_static_data.mjs` |
| 3 | Tailwind v4 et accolades CSS cassées (HMR plantait) | Vérification `12/12` accolades équilibrées + `npx vite optimize` |
| 4 | Hover insensible sur les points de carte (CircleMarker trop petit) | CircleMarker invisible `radius=14` par-dessus chaque point visible |
| 5 | Mode zoom MAE qui se superposait à la carte | `<Dialog>` Radix avec overlay 9998 et content 9999 |

### Étape 10 (pattern hybride API)

| # | Bug | Cause | Solution |
|---|---|---|---|
| 1 | **CORS multi-port** | Vite tournait sur 5174 (5173 occupé), backend autorisait seulement 5173 | Libération du port 5173 (long terme : whitelist CORS plus permissive en dev) |
| 2 | **Coordonnées Paris** | Frontend envoyait `lat=48.85, lon=2.35` (Paris exact), backend ne trouvait rien sur la grille 0.25° | Alignement sur `lat=49, lon=2.5` (point grille le plus proche) |
| 3 | **Latence ERA5 J-6** | Frontend demandait la heatmap pour `2026-04-27 18h` mais ERA5 n'a pas encore cette date → 404 | Utiliser `available-times?source=era5` au lieu de `?source=arome` |

### Étape 11 (UX géo-temporelle + bug visualisation circulaire)

| # | Bug | Cause | Solution |
|---|---|---|---|
| 1 | **Wind direction zigzags 0°/360°** | Recharts `LineChart` interpolait en ligne droite entre 357° et 5° (rotation virtuelle de 352° dans le mauvais sens) | Passage en `BarChart` uniquement pour wind_direction (les 5 autres variables restent en `LineChart`). Branchement conditionnel via `isWindDirection` dans `ChartCard.tsx` |
| 2 | **Coordonnées arbitraires hors grille** | Carte Leaflet permet de cliquer n'importe où, mais DB ne contient que des multiples de 0.25° | Snap automatique via `Math.round(value/0.25)*0.25` dans `useTimeseriesData.ts` avant requête API |
| 3 | **Sync map ↔ charts via prop drilling** | 6+ niveaux de props pour propager `selectedCity` du Dashboard aux ChartCards | React Context dédié `SelectedCityContext` avec hook `useSelectedCity()` |
| 4 | **Cache backend trop court (5 min)** | TTL court forçait des recalculs `GROUP BY` non indexables 3× par chargement de page | TTL passé à 1 h + invalidation auto par hook Python + pre-warming au boot |

### Nouveautés UX étape 11

#### Phase A — Badge ville sur les ChartCards

Chaque graphique affiche désormais un badge `📍 {cityName}` (ex: `📍 Paris`) en plus du titre de variable. Layout en 3 zones via flexbox : titre à gauche, badge centré, contrôles à droite. `whitespace-nowrap` pour éviter le wrap du nom de ville. En mode zoom (`<Dialog>`), badge agrandi (text-base) et suppression du doublon de header (Option C : single source of truth, le header est dans le `DialogHeader`).

#### Phase B — Carte interactive synchronisée aux courbes

État partagé via `SelectedCityContext` (Provider en haut de `Dashboard.tsx`) :
- `selectedCity` : `FrenchCity | null`
- `setSelectedCity` : `(city: FrenchCity) => void`
- `chartsBandRef` : `RefObject<HTMLDivElement>`

Au clic sur une ville (`CircleMarker` ou `Marker` pin), `handleCityClick` dans `FranceMap.tsx` appelle `setSelectedCity(city)` puis `setTimeout(scrollToCharts, 100)` (le délai laisse React re-rendre les ChartCards avant le scroll). `scroll-mt-4` sur la div des charts pour offset cosmétique.

Hook `useTimeseriesData(lat, lon)` :
- Snap les coordonnées à la grille 0.25° via `Math.round(value/0.25)*0.25`
- TanStack Query : `queryKey: ["timeseries", snappedLat, snappedLon, 14]`, `staleTime: 5min`, `gcTime: 10min`
- Fallback Paris statique si erreur ou loading

#### Polish — Wind direction enrichi

- **Bar chart** : 3 barres fines groupées par timestamp (`barCategoryGap="30%"`, `barGap={1}`)
- **Axe Y** : domaine `[0, 360]`, ticks `[0, 90, 180, 270, 360]`, format collé `360°N`, `270°O` (FR) / `270°W` (EN)
- **Tooltip** : helper `getCardinal8(deg, locale)` ajoute la direction cardinale (`351° N`, `62° NE`)
- **Légende des 8 secteurs** sous le graphique : `N 337.5–22.5° · NE 22.5–67.5° · E 67.5–112.5° · SE 112.5–157.5° · S 157.5–202.5° · SO 202.5–247.5° · O 247.5–292.5° · NO 292.5–337.5°` (gras pour les abréviations, intervalles en muted, séparateurs `·`)

---

## 🐳 Dockerisation V1.0 ⭐ NOUVEAU (29/04/2026)

Le frontend React/Vite est désormais entièrement conteneurisé pour le déploiement production via une image Docker **multi-stage** ultra-légère (~23 Mo). Cette section détaille le `Dockerfile`, le `nginx.conf`, et la résolution du bug critique `/api/api/`.

### `frontend/Dockerfile` — Multi-stage builder + production

Le multi-stage est **critique** ici : on a besoin de Node + npm pour builder Vite (~150 Mo de toolchain), mais on ne veut **pas** ces outils dans l'image finale. Solution : 2 stages.

```dockerfile
# ════════════════════════════════════════════════════════════════════════════
# STAGE 1 — BUILDER : compile le bundle Vite avec Node 22
# ════════════════════════════════════════════════════════════════════════════
FROM node:22-alpine AS builder

# Build args injectés au moment du compose (pas du runtime !)
# Vite remplace ces variables dans le code JS au moment du build
ARG VITE_USE_API=true
ARG VITE_API_URL=""
ENV VITE_USE_API=$VITE_USE_API
ENV VITE_API_URL=$VITE_API_URL

WORKDIR /app

# Cache npm si package.json/lock inchangés
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# Copier le code source et builder
COPY . .

# Lance "tsc -b && vite build" → génère /app/dist
RUN npm run build

# Vérification : index.html doit exister, sinon le build a échoué silencieusement
RUN test -f /app/dist/index.html || (echo "❌ Build failed: dist/index.html missing" && exit 1)

# ════════════════════════════════════════════════════════════════════════════
# STAGE 2 — PRODUCTION : Nginx Alpine qui sert UNIQUEMENT le dist/
# ════════════════════════════════════════════════════════════════════════════
FROM nginx:1.27-alpine AS production

LABEL maintainer="Adéchola Émile KOUANDE <kadechola@gmail.com>"
LABEL project="meteo-ia-france"
LABEL component="frontend-react-nginx"

# Supprimer la config Nginx par défaut
RUN rm -f /etc/nginx/conf.d/default.conf

# Copier notre config Nginx custom (gzip + cache + SPA fallback + proxy /api/)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copier UNIQUEMENT le dist/ depuis le stage builder
# (pas de node_modules, pas de src/, pas de tsconfig, etc.)
COPY --from=builder /app/dist /usr/share/nginx/html

# Healthcheck Nginx via /nginx-health
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost/nginx-health || exit 1

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**Caractéristiques** :
- 📦 **Image finale ~23 Mo** (Nginx Alpine + bundle Vite seulement)
- 🚀 **Stage 1 jeté** après le build (les ~150 Mo de Node/npm/devDeps n'arrivent pas en prod)
- 🛡️ **Vérification post-build** : `test -f dist/index.html` empêche les images cassées en prod
- 🩺 **Healthcheck Nginx** : si Nginx crashe, Docker redémarre auto le container

### `frontend/nginx.conf` — Configuration Nginx du container

3 fonctionnalités critiques cohabitent dans cette config :

```nginx
server {
    listen 80;
    server_name localhost;

    # Racine = bundle Vite copié depuis le stage builder
    root /usr/share/nginx/html;
    index index.html;

    # ─────────────────────────────────────────────────────────────────────
    # 1. Compression gzip (réduit la taille des transferts de 70-90%)
    # ─────────────────────────────────────────────────────────────────────
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain text/css text/xml application/json
        application/javascript application/xml+rss
        application/atom+xml image/svg+xml;

    # ─────────────────────────────────────────────────────────────────────
    # 2. Cache agressif des assets versionnés (.css/.js avec hash dans nom)
    # ─────────────────────────────────────────────────────────────────────
    # Vite génère des fichiers comme index-CUbyodYm.css avec hash unique
    # → on peut les cacher 1 an car le hash change à chaque modification
    location ~* \.(css|js|woff2|svg|png|jpg|webp)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # index.html DOIT être no-cache (sinon les utilisateurs voient une vieille version
    # qui charge des assets supprimés → écran blanc)
    location = /index.html {
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        expires 0;
    }

    # ─────────────────────────────────────────────────────────────────────
    # 3. Reverse proxy /api/* → backend container ⭐ CRITIQUE
    # ─────────────────────────────────────────────────────────────────────
    # Quand le frontend appelle /api/forecast (URL relative), Nginx
    # transmet la requête au container "backend" sur son port 3001.
    # "backend" est le NOM DU SERVICE dans docker-compose.yml,
    # résolu via le DNS interne du réseau Docker.
    location /api/ {
        proxy_pass http://backend:3001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts généreux pour les requêtes heatmap (DB-intensive)
        proxy_connect_timeout 30s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # ─────────────────────────────────────────────────────────────────────
    # 4. SPA fallback : toute route → /index.html (React Router prend le relais)
    # ─────────────────────────────────────────────────────────────────────
    location / {
        try_files $uri $uri/ /index.html;
    }

    # ─────────────────────────────────────────────────────────────────────
    # 5. Endpoint healthcheck dédié (utilisé par Docker HEALTHCHECK)
    # ─────────────────────────────────────────────────────────────────────
    location = /nginx-health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

### Build args Vite — `VITE_API_URL=""` (le piège évité)

**ATTENTION CRITIQUE** : `VITE_API_URL` doit valoir **chaîne vide** `""`, **pas** `/api`.

#### Pourquoi ?

Le code frontend `apiService.ts` construit les URLs ainsi :

```typescript
const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:3001"
const url = new URL(`${BASE_URL}${path}`)
```

Et les `path` passés par les hooks commencent **déjà** par `/api/...` :

```typescript
fetchAvailableTimes() → path = "/api/forecast/available-times"
fetchTimeseries()     → path = "/api/forecast/timeseries"
```

| `VITE_API_URL` | URL finale construite | Résultat |
|---|---|---|
| `"/api"` ❌ | `/api` + `/api/forecast/...` = **`/api/api/forecast/...`** | 404 (route doublée) |
| `""` ✅ | `""` + `/api/forecast/...` = **`/api/forecast/...`** | 200 (proxy nginx route OK) |
| `"http://localhost:3001"` (dev) | `http://localhost:3001/api/forecast/...` | 200 (mode dev sans proxy) |

#### Bug rencontré et résolu pendant la dockerisation

**Symptôme** : dashboard affichait `❌ Erreur de chargement — HTTP 404 sur /api/forecast/available-times` malgré un backend qui répondait correctement aux `curl` directs.

**Diagnostic** : la console réseau du navigateur (DevTools) révélait `localhost:8080/api/api/forecast/...` (double `/api/api/`).

**Fix** : modifier `docker-compose.yml` :
```yaml
# AVANT (BUG)
VITE_API_URL: "/api"

# APRÈS (FIX)
VITE_API_URL: ""
```

Puis `docker compose down && docker compose up -d --build` pour reconstruire l'image avec la nouvelle build arg.

### `frontend/.dockerignore`

```gitignore
# Build artifacts (régénérés dans le stage builder)
dist/
.vite/

# Dépendances (régénérées par npm ci dans le stage builder)
node_modules/

# Secrets (passés via build args, pas embarqués)
.env
.env.local
.env.production
.env.development

# Git
.git/
.gitignore

# OS / IDE
.DS_Store
.vscode/
.idea/

# Tests
coverage/
.nyc_output/

# Documentation hors scope container
README.md
*.md

# Logs
*.log
logs/
```

→ Réduit le contexte de build envoyé au daemon Docker (gain de temps : 4,5 Ko transférés au lieu de plusieurs Mo).

### 80 erreurs TypeScript corrigées pendant la dockerisation

Le passage à `tsc -b` strict en build Docker a révélé ~80 erreurs TS pré-existantes que Vite tolérait en mode dev. Toutes corrigées proprement (cf. section "Bugs résolus" plus bas et la section dédiée dans `README.md` § Étape 12).

### Validation locale

```bash
# Build de l'image
cd frontend
docker build -t meteo-ia-frontend:test .

# Vérifier la taille (~23 Mo)
docker images meteo-ia-frontend:test

# Lancer en isolation (sans backend → erreurs API attendues, mais UI affichée)
docker run --rm -d -p 8080:80 --name fe-test meteo-ia-frontend:test

# Tester
curl -I http://localhost:8080/                # 200 OK + index.html
curl http://localhost:8080/nginx-health       # "healthy"
curl -I http://localhost:8080/methodologie    # 200 OK (SPA fallback)

# Nettoyer
docker stop fe-test
```

---

## 🛠️ Stack technique détaillée

| Catégorie | Choix | Version | Pourquoi |
|---|---|---|---|
| **Framework** | React | 19 | Concurrent rendering, Suspense, hooks modernes |
| **Langage** | TypeScript | 5 | Type safety, autocomplétion VS Code |
| **Build tool** | Vite | 8 | HMR ultra-rapide, build optimisé natif TS |
| **Styling** | Tailwind CSS | v4 + plugin Vite natif | Atomic CSS, dark mode classe `dark`, palette OKLCH |
| **Composants UI** | shadcn/ui | preset Radix Nova | Architecture copy-paste, pas de dépendance lourde |
| **Charts** | Recharts | latest | Courbes synchronisées, légendes interactives, axes adaptatifs |
| **Carte** | react-leaflet + Leaflet | 4 / 1.9 | Carte interactive, fond Stadia Alidade Smooth Dark |
| **Routing** | react-router-dom | v7 | Routes bilingues séparées (FR/EN, Dashboard/Methodology) |
| **State HTTP** | TanStack Query | v5 | Cache, retry, dedup, devtools (étape 10) |
| **Client HTTP** | `fetch` natif | — | Pas de dépendance Axios, suffit pour les besoins |
| **Icônes** | lucide-react | latest | Tree-shakable, cohérent avec shadcn/ui |
| **Date/timezone** | `Intl.DateTimeFormat` natif | — | Pas de dépendance moment/date-fns, gestion DST native |

---

## 🤝 Comment contribuer

### Démarrer un développement

```bash
git checkout -b feat/ma-feature
cd frontend
npm install
npm run dev
```

### Conventions de code

- **TypeScript strict** : pas de `any` non justifié
- **Composants fonctionnels** uniquement (pas de class components)
- **Hooks personnalisés** dans `hooks/` quand la logique est réutilisable
- **Imports absolus** via `@/` (configuré dans `tsconfig.json`)
- **Bilingue obligatoire** : tout texte affiché doit avoir sa version FR + EN dans `i18n/`
- **Dark mode obligatoire** : tout nouveau composant doit fonctionner en light + dark

### Conventions de commit

- `feat:` nouvelle fonctionnalité
- `fix:` correction de bug
- `docs:` documentation
- `refactor:` refactoring sans changement fonctionnel
- `style:` CSS, mise en forme
- `test:` ajout/modification de tests

### Avant de pusher

```bash
npm run lint     # ESLint
npm run build    # Vérifie que le build passe sans erreur TypeScript
```

### Idées de contributions bienvenues

- 🌍 Traduction dans d'autres langues (DE, ES, IT)
- 📊 Nouveaux types de visualisation (histogrammes d'erreur, scatter plots)
- 🗺️ Extension à d'autres zones géographiques (Europe, Mondial)
- 🧪 Tests unitaires avec Vitest + React Testing Library
- 📱 Optimisations responsive mobile

---

# 🎨 Météo IA France — Frontend (English)

> 🇫🇷 **Version française au-dessus** ([go to French](#-météo-ia-france--frontend))

[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-8-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v4-38B2AC?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![TanStack Query](https://img.shields.io/badge/TanStack_Query-v5-FF4154?logo=reactquery&logoColor=white)](https://tanstack.com/query/latest)

React application that visualizes weather forecast comparisons between **GraphCast Operational** (Google DeepMind), **AROME** (Météo-France), and **ERA5** (ECMWF, ground truth). Bilingual interactive dashboard (FR/EN) with France map, MAE table, synchronized charts, and a public Methodology page.

---

## 📑 Table of contents

1. [Pitch](#-pitch-1)
2. [Quick start](#-quick-start-1)
3. [Component architecture](#-component-architecture)
4. [Hybrid pattern API runtime / static JSON ⭐](#-hybrid-pattern-api-runtime--static-json-)
5. [Environment variables](#-environment-variables)
6. [UX conventions](#-ux-conventions)
7. [Bugs resolved](#-bugs-resolved)
8. [Detailed tech stack](#-detailed-tech-stack)
9. [How to contribute](#-how-to-contribute)

---

## 🎯 Pitch

The frontend offers **2 bilingual pages**:

- **Dashboard** (`/fr` or `/en`): interactive France map with colored heatmap on 103 cities, MAE comparative table on 4 horizons (h6/h12/h18/h24), 6 synchronized time-series ChartCards, and live toggle between API data and pre-generated static data.
- **Methodology** (`/fr/methodologie` or `/en/methodology`): 8 sections accessible to non-developers (glossary, variables explained, sources compared, limitations, roadmap, technical stack).

The dashboard supports **two data loading modes**: the Express API at runtime (development and demonstration mode) or a static JSON pre-generated at build (CDN production mode). Switching is transparent for components and possible **live via a button in the header**.

---

## 🚀 Quick start

### Prerequisites

- **Node.js 20+** and **npm** (tested with Node 22, npm 10)
- (optional) Express backend running on `localhost:3001` for API runtime mode

### Installation

```bash
cd frontend
npm install
```

### Development launch

```bash
npm run dev
```

➡️ Application accessible on **http://localhost:5173** (Vite default port). If 5173 is busy, Vite will try 5174 and beyond — be aware of backend CORS configuration in this case.

### Production build

```bash
npm run build
```

Result generated in `frontend/dist/`. It's a **100% static site** (no Node server required) that can be served by any HTTP server (Nginx, GitHub Pages, Vercel, Netlify…).

### Local build preview

```bash
npm run preview
```

➡️ Serves `dist/` content on **http://localhost:4173** to test production version before deployment.

### Static JSON regeneration

Static JSON mode (default in production) relies on `frontend/public/data/sample_forecast.json` and 6 files `frontend/public/data/heatmaps/*.json`. To regenerate them after a new DB ingestion:

```bash
cd .. # back to project root
node scripts/generate_static_data.mjs
```

The script queries the Express backend, aggregates the data, and writes JSON to `frontend/public/data/`. Takes ~5 seconds.

---

## 🧩 Component architecture

```
frontend/src/
├── main.tsx                     # entry point, QueryClientProvider + DataSourceProvider
├── App.tsx                      # react-router routing (FR/EN, Dashboard/Methodology)
│
├── routes/
│   ├── DashboardPage.tsx        # / (FR) or /en (EN)
│   └── MethodologyPage.tsx      # /fr/methodologie or /en/methodology
│
├── components/
│   ├── layout/
│   │   ├── Header.tsx           # logo, live clock (auto DST), DataSourceToggle, ModeToggle, LanguageSwitcher
│   │   ├── Footer.tsx           # 4 colored sources, copyright, links v1.0 / Methodology / Source code
│   │   ├── DataSourceToggle.tsx # ⭐ button 📡/💾 API/static switch (step 10)
│   │   ├── ModeToggle.tsx       # light/dark/system dropdown
│   │   └── LanguageSwitcher.tsx # FR/EN button with route preservation
│   │
│   ├── map/
│   │   ├── FranceMap.tsx        # Leaflet map 103 cities + 10 pins + 3 dropdowns + rich tooltips
│   │   └── ZoomDialog.tsx       # universal modal (map / MAE / charts)
│   │
│   ├── charts/
│   │   ├── ChartCard.tsx        # 1 per variable, 3 sources superimposed, synchronized cursor
│   │   └── MaeTableCard.tsx     # 4 horizons × 6 variables, colored ratio
│   │
│   └── methodology/             # ⭐ 8 sections of the Methodology page
│       ├── AboutSection.tsx
│       ├── GlossarySection.tsx
│       ├── VariablesSection.tsx
│       ├── SourcesSection.tsx
│       ├── ComparisonTable.tsx
│       ├── LimitationsSection.tsx
│       ├── RoadmapSection.tsx
│       └── TechStackSection.tsx
│
├── contexts/
│   ├── DataSourceContext.tsx    # ⭐ manages useApi + toggleDataSource (step 10)
│   └── ThemeContext.tsx         # manages light/dark/system
│
├── services/
│   └── apiService.ts            # ⭐ 9 typed methods to the 8 Express endpoints (step 10)
│
├── hooks/
│   ├── useStaticData.ts         # 🔄 hybrid hook API/static (step 10)
│   └── useHeatmapData.ts        # 🔄 hybrid hook for heatmaps (step 10)
│
├── i18n/
│   ├── index.ts                 # useT() registry + FR/EN locales
│   ├── fr.ts
│   ├── en.ts
│   ├── methodology.fr.ts
│   └── methodology.en.ts
│
├── lib/
│   ├── timezone.ts              # automatic DST handling UTC+1/UTC+2
│   ├── numberFormat.ts          # FR/EN locale on numbers
│   ├── colorScales.ts           # OKLCH palette + SOURCE_COLORS
│   └── utils.ts                 # cn() for conditional className (shadcn)
│
├── types/
│   └── forecast.ts              # shared TypeScript types
│
└── components/ui/               # shadcn/ui components (Button, Dialog, Select, etc.)

frontend/public/
└── data/
    ├── sample_forecast.json     # main static JSON (~7 MB)
    └── heatmaps/                # 6 files, ~11 MB total
```

### Provider hierarchy (`main.tsx`)

```tsx
<StrictMode>
  <QueryClientProvider client={queryClient}>     // TanStack Query (cache/retry)
    <DataSourceProvider>                          // ⭐ API/static switching
      <BrowserRouter>
        <ThemeProvider>                           // light/dark/system
          <App />
        </ThemeProvider>
      </BrowserRouter>
    </DataSourceProvider>
    <ReactQueryDevtools />                        // dev only
  </QueryClientProvider>
</StrictMode>
```

---

## 🔌 Hybrid pattern API runtime / static JSON ⭐

This is **the main architectural specificity** of the frontend, delivered in step 10 of the project.

### Why 2 modes?

Rather than replacing one mode with the other, the frontend keeps **both** and allows switching according to need:

| Use case | Recommended mode | Reason |
|---|---|---|
| 🌐 Public production (CDN, GitHub Pages, recruiter demo) | 💾 Static JSON | Performance, free hosting, works offline |
| 🔧 Live pedagogical demonstration | 🟢 API runtime | Visible network devtools, traceable requests |
| 🐛 Local debug after new DB ingestion | 🟢 API runtime | No rebuild needed |
| 📱 4G mobile user | 💾 Static JSON | Saves data + faster |
| 🔬 Multi-runs daily (v2.0) | 🟢 API runtime | Data changing throughout the day |
| 🛡️ Backend down | 💾 Static JSON (fallback) | App keeps working |

### Internal architecture

```
┌──────────────────────────────────────────────┐
│  Component (FranceMap, ChartCard, etc.)      │
│  → calls useStaticData() / useHeatmapData()  │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│  Hybrid hook                                 │
│  → reads useDataSource().useApi              │
│  → internally chooses between:               │
└────────┬───────────────────────────┬─────────┘
         │                           │
         ▼                           ▼
┌────────────────┐         ┌──────────────────┐
│ apiService.ts  │         │ fetch /data/*.json│
│ (9 endpoints)  │         │ (build-time)     │
└────────────────┘         └──────────────────┘
```

### Components contract remains unchanged

```tsx
// FranceMap.tsx — IDENTICAL before and after step 10
function FranceMap() {
  const { data, loading, error } = useStaticData()
  // → hook's role is now: "load data according to active mode"
  // → component doesn't know where data comes from
}
```

### Switching controlled at 2 levels

#### 1. Environment variable (at startup)

```bash
# frontend/.env
VITE_USE_API=false   # static JSON mode (recommended for prod)
# VITE_USE_API=true  # API runtime mode (recommended for dev)
```

#### 2. UI toggle (live, in header)

The 📡 / 💾 button in header allows switching **without rebuild**:

- 📡 **Green Wifi** = API runtime mode active
- 💾 **Gray Database** = static JSON mode active

On click, app re-fetches data immediately from new source. Visible live in browser **network devtools**.

### Components delivered in step 10

| File | Role |
|---|---|
| `services/apiService.ts` | 9 typed methods to the 8 Express endpoints, unified error handling, query params, strict TypeScript types |
| `contexts/DataSourceContext.tsx` | React context managing active mode (`useApi: boolean`) with `VITE_USE_API` reading at startup and `toggleDataSource()` |
| `hooks/useStaticData.ts` | Hybrid hook: loads from API or `/data/sample_forecast.json` according to context |
| `hooks/useHeatmapData.ts` | Same for heatmaps: API runtime or `/data/heatmaps/{variable}.json` |
| `components/layout/DataSourceToggle.tsx` | 📡/💾 button in header for live switching |

### Express endpoints consumed in API mode

| Endpoint | Hook | Usage |
|---|---|---|
| `GET /api/status` | `useStaticData` | DB counters + cache + uptime |
| `GET /api/forecast/available-times?source=graphcast` | `useStaticData` | GraphCast timestamps |
| `GET /api/forecast/available-times?source=arome` | `useStaticData` | AROME timestamps |
| `GET /api/forecast/available-times?source=era5` | `useHeatmapData` | Timestamps where comparison is possible |
| `GET /api/forecast/grid-points` | `useStaticData` | 2925 GPS grid points |
| `GET /api/forecast/timeseries?lat=49&lon=2.5&days=7` | `useStaticData` | 7-day time series |
| `GET /api/mae/comparison?horizon={6,12,18,24}` | `useStaticData` | MAE table (4 parallel calls) |
| `GET /api/heatmap/error?...` | `useHeatmapData` | Spatial error heatmap |

> 📚 Backend documentation: [BACKEND.md](../BACKEND.md)

### TanStack Query v5 installed (but not yet directly consumed)

The project installs `@tanstack/react-query` and configures a `QueryClient` at app root with robust defaults (5min staleTime, 30min gcTime, 2 retries with exponential backoff, refetchOnWindowFocus disabled).

In step 10, **hooks don't yet directly consume `useQuery()`** (lightweight option: `useStaticData` and `useHeatmapData` mostly unchanged). TanStack remains **ready for use** for future dedicated hooks.

> ℹ️ **TanStack Query DevTools** (floating button bottom-right) are active in development only. Automatically excluded from production build by Vite. To remove completely before deployment: `npm uninstall @tanstack/react-query-devtools` + remove 2 lines in `main.tsx`.

---

## ⚙️ Environment variables

All variables must be prefixed with `VITE_` to be exposed to client by Vite.

### `frontend/.env`

```bash
# Default data source at startup
# - "false" = static JSON mode
# - "true"  = API runtime mode
# - undefined = API runtime mode (default)
VITE_USE_API=false

# Express backend URL (overrides default http://localhost:3001)
# VITE_API_URL=https://api.meteo-ia-france.fr
```

⚠️ **Vite restart mandatory** (Ctrl+C then `npm run dev`) after any `.env` modification.

---

## 🎨 UX conventions

### 100% bilingual (FR / EN)

- **2 separate routes**: `/fr` and `/en` (no `?lang=fr` querystring)
- Instant switch in header with **route preservation**
- `useT()` hook returns translations of current locale
- All labels, dates, numbers, and tooltips are localized

### Light + Dark mode

- **OKLCH** Claude-style palette (colors auto-adapt, no CSS duplication)
- 3 modes: Light / Dark / System (follows OS preferences)
- localStorage persistence via `ThemeContext`
- Toggle in header via `<ModeToggle>`

### Timezone

- **All backend timestamps in UTC** (`TIMESTAMP WITH TIME ZONE` DB-side)
- Frontend converts to Europe/Paris with **automatic DST handling** via `lib/timezone.ts`
- Header live clock shows `UTC+1` (winter) or `UTC+2` (summer)

### Responsive

- Tailwind breakpoints: mobile (< 768px), tablet (768-1024px), desktop (> 1024px)
- Map adapts to viewport
- Grids switch from 3 columns to 1 column on mobile

### Accessibility

- Full keyboard navigation (Tab, Enter, Esc)
- Aria-labels on all interactions
- WCAG AA contrasts in light + dark
- Sr-only on purely decorative icons

---

## 🐛 Bugs resolved

### Step 9 (initial frontend)

| # | Bug | Solution |
|---|---|---|
| 1 | Z-index Leaflet vs Radix dropdowns | Global CSS `[data-slot="select-content"]` at `z-index: 9999 !important` |
| 2 | Backend required `06` format but JSON script sent `6` | `String(t.hour).padStart(2, "0")` in `generate_static_data.mjs` |
| 3 | Tailwind v4 broken CSS braces (HMR crash) | `12/12` brace check + `npx vite optimize` |
| 4 | Insensitive hover on map points | Invisible CircleMarker `radius=14` overlay |
| 5 | MAE zoom mode overlapping map | Radix `<Dialog>` with overlay 9998 and content 9999 |

### Step 10 (hybrid API pattern)

| # | Bug | Cause | Solution |
|---|---|---|---|
| 1 | **Multi-port CORS** | Vite ran on 5174 (5173 busy), backend allowed only 5173 | Free port 5173 (long-term: more permissive CORS whitelist in dev) |
| 2 | **Paris coordinates** | Frontend sent `lat=48.85, lon=2.35`, backend found nothing on 0.25° grid | Alignment on `lat=49, lon=2.5` (closest grid point) |
| 3 | **ERA5 J-6 latency** | Frontend requested heatmap for `2026-04-27 18h` but ERA5 doesn't have this date yet → 404 | Use `available-times?source=era5` instead of `?source=arome` |

### Step 11 (geo-temporal UX + circular visualization bug)

| # | Bug | Cause | Solution |
|---|---|---|---|
| 1 | **Wind direction zigzags 0°/360°** | Recharts `LineChart` interpolated linearly between 357° and 5° (virtual 352° rotation in the wrong direction) | Switch to `BarChart` only for wind_direction (5 other variables stay in `LineChart`). Conditional branching via `isWindDirection` in `ChartCard.tsx` |
| 2 | **Off-grid arbitrary coordinates** | Leaflet map allows clicking anywhere, but DB only contains 0.25° multiples | Automatic snap via `Math.round(value/0.25)*0.25` in `useTimeseriesData.ts` before API request |
| 3 | **Map ↔ charts sync via prop drilling** | 6+ prop levels to propagate `selectedCity` from Dashboard to ChartCards | Dedicated React Context `SelectedCityContext` with `useSelectedCity()` hook |
| 4 | **Backend cache too short (5 min)** | Short TTL forced non-indexable `GROUP BY` recomputations 3× per page load | TTL raised to 1h + auto-invalidation via Python hook + boot pre-warming |

### Step 11 UX features

#### Phase A — City badge on ChartCards

Each chart now displays a `📍 {cityName}` badge (e.g., `📍 Paris`) alongside the variable title. 3-zone flexbox layout: title left, centered badge, controls right. `whitespace-nowrap` to prevent city name wrapping. In zoom mode (`<Dialog>`), badge enlarged (text-base) and header duplicate removed (Option C: single source of truth, header is in `DialogHeader`).

#### Phase B — Interactive map synchronized with charts

Shared state via `SelectedCityContext` (Provider at top of `Dashboard.tsx`):
- `selectedCity`: `FrenchCity | null`
- `setSelectedCity`: `(city: FrenchCity) => void`
- `chartsBandRef`: `RefObject<HTMLDivElement>`

On city click (`CircleMarker` or `Marker` pin), `handleCityClick` in `FranceMap.tsx` calls `setSelectedCity(city)` then `setTimeout(scrollToCharts, 100)` (delay lets React re-render ChartCards before scrolling). `scroll-mt-4` on charts div for cosmetic offset.

`useTimeseriesData(lat, lon)` hook:
- Snaps coordinates to 0.25° grid via `Math.round(value/0.25)*0.25`
- TanStack Query: `queryKey: ["timeseries", snappedLat, snappedLon, 14]`, `staleTime: 5min`, `gcTime: 10min`
- Static Paris fallback on error or loading

#### Polish — Enhanced wind direction

- **Bar chart**: 3 thin bars grouped per timestamp (`barCategoryGap="30%"`, `barGap={1}`)
- **Y-axis**: domain `[0, 360]`, ticks `[0, 90, 180, 270, 360]`, collated format `360°N`, `270°W` (EN) / `270°O` (FR)
- **Tooltip**: `getCardinal8(deg, locale)` helper adds cardinal direction (`351° N`, `62° NE`)
- **8-sector legend** below the chart: `N 337.5–22.5° · NE 22.5–67.5° · E 67.5–112.5° · SE 112.5–157.5° · S 157.5–202.5° · SW 202.5–247.5° · W 247.5–292.5° · NW 292.5–337.5°` (bold abbreviations, intervals in muted, separators `·`)

---

## 🐳 V1.0 Dockerization ⭐ NEW (04/29/2026)

The React/Vite frontend is now fully containerized for production deployment via an ultra-lightweight **multi-stage** Docker image (~23 MB). This section details the `Dockerfile`, `nginx.conf`, and resolution of the critical `/api/api/` bug.

### `frontend/Dockerfile` — Multi-stage builder + production

Multi-stage is **critical** here: we need Node + npm to build Vite (~150 MB of toolchain), but we **don't** want these tools in the final image. Solution: 2 stages.

```dockerfile
# ════════════════════════════════════════════════════════════════════════════
# STAGE 1 — BUILDER: compiles Vite bundle with Node 22
# ════════════════════════════════════════════════════════════════════════════
FROM node:22-alpine AS builder

# Build args injected at compose time (NOT runtime!)
# Vite replaces these variables in JS code at build time
ARG VITE_USE_API=true
ARG VITE_API_URL=""
ENV VITE_USE_API=$VITE_USE_API
ENV VITE_API_URL=$VITE_API_URL

WORKDIR /app

# Cache npm if package.json/lock unchanged
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# Copy source and build
COPY . .

# Runs "tsc -b && vite build" → generates /app/dist
RUN npm run build

# Verification: index.html must exist, otherwise build silently failed
RUN test -f /app/dist/index.html || (echo "❌ Build failed: dist/index.html missing" && exit 1)

# ════════════════════════════════════════════════════════════════════════════
# STAGE 2 — PRODUCTION: Nginx Alpine serving ONLY dist/
# ════════════════════════════════════════════════════════════════════════════
FROM nginx:1.27-alpine AS production

LABEL maintainer="Adéchola Émile KOUANDE <kadechola@gmail.com>"
LABEL project="meteo-ia-france"
LABEL component="frontend-react-nginx"

# Remove default Nginx config
RUN rm -f /etc/nginx/conf.d/default.conf

# Copy our custom Nginx config (gzip + cache + SPA fallback + /api/ proxy)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy ONLY dist/ from builder stage
# (no node_modules, no src/, no tsconfig, etc.)
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx healthcheck via /nginx-health
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost/nginx-health || exit 1

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**Characteristics**:
- 📦 **Final image ~23 MB** (Nginx Alpine + Vite bundle only)
- 🚀 **Stage 1 discarded** after build (~150 MB of Node/npm/devDeps don't reach prod)
- 🛡️ **Post-build verification**: `test -f dist/index.html` prevents broken images in prod
- 🩺 **Nginx healthcheck**: if Nginx crashes, Docker auto-restarts the container

### `frontend/nginx.conf` — Container Nginx configuration

3 critical features coexist in this config:

```nginx
server {
    listen 80;
    server_name localhost;

    # Root = Vite bundle copied from builder stage
    root /usr/share/nginx/html;
    index index.html;

    # ─────────────────────────────────────────────────────────────────────
    # 1. Gzip compression (reduces transfer size by 70-90%)
    # ─────────────────────────────────────────────────────────────────────
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain text/css text/xml application/json
        application/javascript application/xml+rss
        application/atom+xml image/svg+xml;

    # ─────────────────────────────────────────────────────────────────────
    # 2. Aggressive caching of versioned assets (.css/.js with hash in name)
    # ─────────────────────────────────────────────────────────────────────
    # Vite generates files like index-CUbyodYm.css with unique hash
    # → can cache 1 year because hash changes on every modification
    location ~* \.(css|js|woff2|svg|png|jpg|webp)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # index.html MUST be no-cache (otherwise users see old version
    # loading deleted assets → blank screen)
    location = /index.html {
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        expires 0;
    }

    # ─────────────────────────────────────────────────────────────────────
    # 3. Reverse proxy /api/* → backend container ⭐ CRITICAL
    # ─────────────────────────────────────────────────────────────────────
    # When frontend calls /api/forecast (relative URL), Nginx forwards
    # request to "backend" container on its port 3001.
    # "backend" is the SERVICE NAME in docker-compose.yml,
    # resolved via Docker's internal network DNS.
    location /api/ {
        proxy_pass http://backend:3001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Generous timeouts for heatmap requests (DB-intensive)
        proxy_connect_timeout 30s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # ─────────────────────────────────────────────────────────────────────
    # 4. SPA fallback: any route → /index.html (React Router takes over)
    # ─────────────────────────────────────────────────────────────────────
    location / {
        try_files $uri $uri/ /index.html;
    }

    # ─────────────────────────────────────────────────────────────────────
    # 5. Dedicated healthcheck endpoint (used by Docker HEALTHCHECK)
    # ─────────────────────────────────────────────────────────────────────
    location = /nginx-health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

### Vite build args — `VITE_API_URL=""` (the avoided pitfall)

**CRITICAL WARNING**: `VITE_API_URL` must be **empty string** `""`, **not** `/api`.

#### Why?

Frontend code `apiService.ts` builds URLs as:

```typescript
const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:3001"
const url = new URL(`${BASE_URL}${path}`)
```

And `path` passed by hooks **already** starts with `/api/...`:

```typescript
fetchAvailableTimes() → path = "/api/forecast/available-times"
fetchTimeseries()     → path = "/api/forecast/timeseries"
```

| `VITE_API_URL` | Final URL built | Result |
|---|---|---|
| `"/api"` ❌ | `/api` + `/api/forecast/...` = **`/api/api/forecast/...`** | 404 (doubled route) |
| `""` ✅ | `""` + `/api/forecast/...` = **`/api/forecast/...`** | 200 (nginx proxy routes OK) |
| `"http://localhost:3001"` (dev) | `http://localhost:3001/api/forecast/...` | 200 (dev mode without proxy) |

#### Bug encountered and resolved during dockerization

**Symptom**: dashboard displayed `❌ Loading error — HTTP 404 on /api/forecast/available-times` despite backend correctly responding to direct `curl` requests.

**Diagnosis**: browser network console (DevTools) revealed `localhost:8080/api/api/forecast/...` (double `/api/api/`).

**Fix**: modify `docker-compose.yml`:
```yaml
# BEFORE (BUG)
VITE_API_URL: "/api"

# AFTER (FIX)
VITE_API_URL: ""
```

Then `docker compose down && docker compose up -d --build` to rebuild image with new build arg.

### `frontend/.dockerignore`

```gitignore
# Build artifacts (regenerated in builder stage)
dist/
.vite/

# Dependencies (regenerated by npm ci in builder stage)
node_modules/

# Secrets (passed via build args, not embedded)
.env
.env.local
.env.production
.env.development

# Git
.git/
.gitignore

# OS / IDE
.DS_Store
.vscode/
.idea/

# Tests
coverage/
.nyc_output/

# Documentation out of container scope
README.md
*.md

# Logs
*.log
logs/
```

→ Reduces build context sent to Docker daemon (time savings: 4.5 KB transferred instead of several MB).

### 80 TypeScript errors fixed during dockerization

Switching to strict `tsc -b` in Docker build revealed ~80 pre-existing TS errors that Vite tolerated in dev mode. All cleanly fixed (cf. "Resolved bugs" section below and dedicated section in `README.md` § Step 12).

### Local validation

```bash
# Build image
cd frontend
docker build -t meteo-ia-frontend:test .

# Check size (~23 MB)
docker images meteo-ia-frontend:test

# Run standalone (no backend → expected API errors, but UI displayed)
docker run --rm -d -p 8080:80 --name fe-test meteo-ia-frontend:test

# Test
curl -I http://localhost:8080/                # 200 OK + index.html
curl http://localhost:8080/nginx-health       # "healthy"
curl -I http://localhost:8080/methodologie    # 200 OK (SPA fallback)

# Cleanup
docker stop fe-test
```

---

## 🛠️ Detailed tech stack

| Category | Choice | Version | Why |
|---|---|---|---|
| **Framework** | React | 19 | Concurrent rendering, Suspense, modern hooks |
| **Language** | TypeScript | 5 | Type safety, VS Code autocompletion |
| **Build tool** | Vite | 8 | Ultra-fast HMR, native TS-optimized build |
| **Styling** | Tailwind CSS | v4 + native Vite plugin | Atomic CSS, `dark` class mode, OKLCH palette |
| **UI components** | shadcn/ui | Radix Nova preset | Copy-paste architecture, no heavy dependencies |
| **Charts** | Recharts | latest | Synchronized curves, interactive legends, adaptive axes |
| **Map** | react-leaflet + Leaflet | 4 / 1.9 | Interactive map, Stadia Alidade Smooth Dark background |
| **Routing** | react-router-dom | v7 | Separate bilingual routes (FR/EN, Dashboard/Methodology) |
| **HTTP state** | TanStack Query | v5 | Cache, retry, dedup, devtools (step 10) |
| **HTTP client** | Native `fetch` | — | No Axios dependency, sufficient |
| **Icons** | lucide-react | latest | Tree-shakable, consistent with shadcn/ui |
| **Date/timezone** | Native `Intl.DateTimeFormat` | — | No moment/date-fns dependency, native DST handling |

---

## 🤝 How to contribute

### Start a development

```bash
git checkout -b feat/my-feature
cd frontend
npm install
npm run dev
```

### Code conventions

- **Strict TypeScript**: no unjustified `any`
- **Functional components** only (no class components)
- **Custom hooks** in `hooks/` when logic is reusable
- **Absolute imports** via `@/` (configured in `tsconfig.json`)
- **Bilingual mandatory**: any displayed text must have FR + EN version in `i18n/`
- **Dark mode mandatory**: any new component must work in light + dark

### Commit conventions

- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation
- `refactor:` refactoring without functional change
- `style:` CSS, formatting
- `test:` test addition/modification

### Before pushing

```bash
npm run lint     # ESLint
npm run build    # Verifies build passes without TypeScript errors
```

### Welcome contribution ideas

- 🌍 Translation in other languages (DE, ES, IT)
- 📊 New visualization types (error histograms, scatter plots)
- 🗺️ Extension to other geographical areas (Europe, Worldwide)
- 🧪 Unit tests with Vitest + React Testing Library
- 📱 Responsive mobile optimizations

---

## 📜 License

This project is distributed under the **MIT license**. See [LICENSE](../LICENSE) for details.

## 📧 Contact

- 📧 **Email**: [kadechola@gmail.com](mailto:kadechola@gmail.com)
- 💼 **LinkedIn**: [linkedin.com/in/kadechola](https://www.linkedin.com/in/kadechola/)
- 💻 **Malt**: [malt.fr/profile/adecholaemilekkouande](https://www.malt.fr/profile/adecholaemilekkouande)
