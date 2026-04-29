// ═══════════════════════════════════════════════════════════════════
// methodology.fr.ts — Textes longs FR de la page Méthodologie
// ═══════════════════════════════════════════════════════════════════
//
// 🆕 Refonte du typage (V1.0 ship) :
//   - Interface MethodologyTranslations explicite (au lieu de DeepStringify)
//   - methodologyFr typé directement avec cette interface (sans "as const")
//   - Permet à methodology.en.ts d'utiliser le MÊME type sans conflit
//   - Ainsi MethodologyPage.tsx peut switcher entre FR/EN sans erreur
// ═══════════════════════════════════════════════════════════════════

// ───────────────────────────────────────────────────────────────────
// 📐 INTERFACE — Source de vérité unique pour les traductions
// ───────────────────────────────────────────────────────────────────

export interface GlossaryEntry {
  term: string
  definition: string
}

export interface VariableItem {
  emoji: string
  name: string
  code: string
  description: string
  range: string
}

export interface MetaItem {
  label: string
  value: string
  highlight?: boolean
}

export interface SourceCard {
  name: string
  tag: string
  provider: string
  description: string
  meta: readonly MetaItem[]
}

export interface ComparisonRow {
  criterion: string
  era5: string
  arome: string
  graphcast: string
  era5Color?: "good" | "warn" | "bad"
  aromeColor?: "good" | "warn" | "bad"
  graphcastColor?: "good" | "warn" | "bad"
}

export interface LimitationItem {
  title: string
  description: string
}

export interface RoadmapItem {
  name: string
  description: string
}

export interface ArchitectureCard {
  title: string
  color: string
  items: readonly MetaItem[]
}

export interface MethodologyTranslations {
  pageTitle: string
  pageSubtitle: string
  backToDashboard: string

  about: {
    heading: string
    paragraph: string
  }

  glossary: {
    heading: string
    entries: readonly GlossaryEntry[]
  }

  variables: {
    heading: string
    items: readonly VariableItem[]
  }

  sources: {
    heading: string
    era5: SourceCard
    arome: SourceCard
    graphcast: SourceCard
  }

  comparison: {
    heading: string
    headers: {
      criterion: string
      era5: string
      era5Sub: string
      arome: string
      aromeSub: string
      graphcast: string
      graphcastSub: string
    }
    rows: readonly ComparisonRow[]
    legend: string
  }

  limitations: {
    heading: string
    items: readonly LimitationItem[]
  }

  roadmap: {
    heading: string
    items: readonly RoadmapItem[]
  }

  architecture: {
    heading: string
    intro: string
    cards: readonly ArchitectureCard[]
  }
}

// ───────────────────────────────────────────────────────────────────
// 🇫🇷 VALEURS — Traductions françaises
// ───────────────────────────────────────────────────────────────────

export const methodologyFr: MethodologyTranslations = {
  pageTitle: "Méthodologie",
  pageSubtitle: "Météo IA France · Tableau de bord de comparaison de modèles de prévision",
  backToDashboard: "← Retour au tableau de bord",

  // ───── Section 1 : À propos ─────
  about: {
    heading: "1 · À propos du projet",
    paragraph:
      "Météo IA France compare quotidiennement deux approches de prévision météorologique sur la France métropolitaine : le modèle physique régional AROME de Météo-France, et le modèle d'intelligence artificielle GraphCast Operational de Google DeepMind. La référence terrain (vérité observée) est fournie par la réanalyse ERA5 de l'ECMWF.",
  },

  // ───── Section 2 : Glossaire ─────
  glossary: {
    heading: "2 · Glossaire",
    entries: [
      { term: "ECMWF", definition: "European Centre for Medium-Range Weather Forecasts. Centre européen basé à Reading (UK)." },
      { term: "ERA5", definition: "5e génération de la réanalyse atmosphérique de l'ECMWF, considérée comme vérité terrain." },
      { term: "CDS", definition: "Climate Data Store. Plateforme d'accès aux données ERA5 (gratuit après inscription)." },
      { term: "NOAA", definition: "National Oceanic and Atmospheric Administration. Agence météorologique américaine." },
      { term: "GFS", definition: "Global Forecast System. Modèle global de la NOAA, résolution 0.25°, runs toutes les 6h." },
      { term: "NOMADS", definition: "NOAA Operational Model Archive and Distribution System. Serveur d'accès aux données GFS." },
      { term: "AROME", definition: "Applications de la Recherche à l'Opérationnel à Méso-Échelle. Modèle régional de Météo-France." },
      { term: "ARPEGE", definition: "Action de Recherche Petite Échelle Grande Échelle. Modèle global de Météo-France." },
      { term: "GRIB2", definition: "GRIdded Binary version 2. Format binaire standard OMM pour les données météo." },
      { term: "NetCDF", definition: "Network Common Data Form. Format scientifique pour données multidimensionnelles." },
      { term: "MAE", definition: "Mean Absolute Error. Moyenne des écarts absolus entre prédictions et vérité ERA5." },
      { term: "RMSE", definition: "Root Mean Square Error. Racine carrée de la moyenne des écarts au carré." },
      { term: "Bias", definition: "Erreur systématique moyenne (positive = surestimation, négative = sous-estimation)." },
      { term: "Run", definition: "Une exécution complète d'un modèle à un instant T (ex: run 18z = run de 18h UTC)." },
      { term: "Horizon", definition: "Délai entre le run et l'échéance prédite (ex: horizon 24h = prévision pour J+1)." },
      { term: "Zero-shot", definition: "Modèle utilisé sur de nouvelles données sans réentraînement (sans fine-tuning)." },
    ],
  },

  // ───── Section 3 : Variables ─────
  variables: {
    heading: "3 · Les 6 variables météorologiques",
    items: [
      { emoji: "🌡️", name: "Température 2m", code: "t2m_celsius · °C", description: "Température de l'air à 2 mètres au-dessus du sol.", range: "Plage France : -15 °C à +40 °C · Variable la plus stable" },
      { emoji: "🌬️", name: "Vitesse du vent 10m", code: "wind_speed_10m_ms · m/s", description: "Norme du vecteur vent horizontal à 10 mètres.", range: "Plage France : 0 à 30 m/s · Critique pour l'éolien" },
      { emoji: "🧭", name: "Direction du vent 10m", code: "wind_direction_10m_deg · °", description: "Angle du vent en degrés (0° = nord, 90° = est).", range: "Plage : 0 à 360° · Variable cyclique (MAE recalculé)" },
      { emoji: "☁️", name: "Pression au niveau mer", code: "msl_hpa · hPa", description: "Pression atmosphérique ramenée au niveau de la mer.", range: "Plage France : 980 à 1040 hPa · Indicateur dépressions" },
      { emoji: "🌧️", name: "Précipitations 6h", code: "tp_6h_mm · mm", description: "Cumul de précipitations sur 6 heures glissantes.", range: "Plage : 0 à 50 mm · Variable la plus difficile à prédire" },
      { emoji: "☀️", name: "Rayonnement TOA", code: "toa_wm2 · W/m²", description: "Rayonnement solaire au sommet de l'atmosphère (calculé astronomiquement).", range: "Plage : 0 à 1400 W/m² · Référence de cycle solaire" },
    ],
  },

  // ───── Section 4 : Sources ─────
  sources: {
    heading: "4 · Sources de données",
    era5: {
      name: "ERA5",
      tag: "Vérité terrain",
      provider: "ECMWF Copernicus",
      description: "Réanalyse de 5e génération de l'ECMWF. Combine observations satellites, stations sol et modèles physiques pour produire la « vérité » météorologique passée.",
      meta: [
        { label: "Résolution", value: "0.25° ≈ 25 km" },
        { label: "Pas temps", value: "1h" },
        { label: "Latence", value: "J-6" },
        { label: "Accès", value: "CDS API gratuit" },
      ],
    },
    arome: {
      name: "AROME",
      tag: "Modèle physique régional",
      provider: "Météo-France",
      description: "Modèle non-hydrostatique haute résolution couvrant la France métropolitaine.",
      meta: [
        { label: "Résolution", value: "0.025° ≈ 2.5 km ★", highlight: true },
        { label: "Runs/jour", value: "8 (toutes les 3h)" },
        { label: "Horizon", value: "jusqu'à 51h" },
        { label: "Accès", value: "data.gouv.fr" },
      ],
    },
    graphcast: {
      name: "GraphCast Operational",
      tag: "Modèle IA",
      provider: "Google DeepMind + GFS NOAA",
      description: "Réseau de neurones graphes pré-entraîné sur ERA5 puis fine-tuné pour utilisation avec GFS. Notre version utilise GFS NOMADS comme conditions initiales (zero-shot car non re-fine-tuné sur la France).",
      meta: [
        { label: "Résolution", value: "0.25° ≈ 25 km" },
        { label: "Pas temps", value: "6h" },
        { label: "Horizon", value: "jusqu'à 10 jours" },
        { label: "Inférence", value: "~1-8 min CPU" },
      ],
    },
  },

  // ───── Section 5 : Tableau comparatif ─────
  comparison: {
    heading: "5 · Tableau comparatif",
    headers: {
      criterion: "Critère",
      era5: "ERA5",
      era5Sub: "Vérité terrain",
      arome: "AROME",
      aromeSub: "Modèle physique",
      graphcast: "GraphCast Op.",
      graphcastSub: "Modèle IA",
    },
    rows: [
      { criterion: "Type", era5: "Réanalyse passée", arome: "Modèle physique régional", graphcast: "Réseau de neurones graphes" },
      { criterion: "Éditeur", era5: "ECMWF (Europe)", arome: "Météo-France", graphcast: "Google DeepMind" },
      { criterion: "Source physique", era5: "Observations + assimilation", arome: "Conditions initiales ARPEGE", graphcast: "Données GFS (NOAA)" },
      { criterion: "Résolution native", era5: "0.25° (≈ 25 km)", arome: "0.025° (≈ 2.5 km) ★", graphcast: "0.25° (≈ 25 km)", aromeColor: "good" },
      { criterion: "Résolution utilisée", era5: "0.25°", arome: "0.25° (sous-échantillonnée)", graphcast: "0.25°", aromeColor: "warn" },
      { criterion: "Pas de temps natif", era5: "1h", arome: "1h", graphcast: "6h", aromeColor: "good" },
      { criterion: "Pas de temps utilisé", era5: "6h", arome: "6h (sous-échantillonné)", graphcast: "6h", aromeColor: "warn" },
      { criterion: "Runs nominaux/jour", era5: "—", arome: "8 (toutes les 3h)", graphcast: "4 (toutes les 6h)", aromeColor: "good" },
      { criterion: "Runs utilisés ici", era5: "—", arome: "1 (run 18z UTC)", graphcast: "1 (run 18z UTC)", aromeColor: "warn", graphcastColor: "warn" },
      { criterion: "Horizon prédit", era5: "—", arome: "jusqu'à 51h (J+2)", graphcast: "jusqu'à 10 jours" },
      { criterion: "Latence des données", era5: "J-6 (5 à 6 jours)", arome: "~4 h", graphcast: "~4 h", era5Color: "warn", aromeColor: "good", graphcastColor: "good" },
      { criterion: "Entraînement", era5: "—", arome: "Équations physiques", graphcast: "Pré-entraîné ERA5, zero-shot sur GFS", graphcastColor: "warn" },
      { criterion: "Format données", era5: "NetCDF (CDS API)", arome: "GRIB2 (data.gouv.fr)", graphcast: "GRIB2 → NetCDF" },
      { criterion: "Coût d'accès", era5: "Gratuit (CDS API)", arome: "Gratuit (data.gouv.fr)", graphcast: "Gratuit (NOMADS + open weights)", era5Color: "good", aromeColor: "good", graphcastColor: "good" },
    ],
    legend: "Légende : vert = avantage · orange = limitation actuelle · gris = neutre",
  },

  // ───── Section 6 : Limitations ─────
  limitations: {
    heading: "6 · Limitations actuelles (v1.0)",
    items: [
      { title: "Un seul run par jour", description: "au lieu de 4-8 nominaux. Conséquence : prévisions faites avec 24h de retard d'information." },
      { title: "Pas de mise à jour intra-journalière", description: "— les prévisions ne sont jamais rafraîchies en cours de journée par de nouveaux runs." },
      { title: "AROME sous-échantillonné", description: "de 0.025° à 0.25° pour aligner la grille avec ERA5/GraphCast (perte 90% résolution spatiale)." },
      { title: "GraphCast en zero-shot", description: "sur GFS, sans fine-tuning sur les données françaises." },
      { title: "Pas de temps de 6h", description: "imposé par GraphCast Operational, alors qu'AROME nominal fait du 1h." },
    ],
  },

  // ───── Section 7 : Roadmap ─────
  roadmap: {
    heading: "7 · Roadmap v2.0",
    items: [
      { name: "Pangu-Weather (Huawei)", description: "architecture hiérarchique 1h/3h/6h/24h" },
      { name: "ClimaX (Microsoft)", description: "foundation model fine-tunable sur données régionales France" },
      { name: "AROME résolution native 0.025°", description: "retrouver la haute résolution régionale" },
      { name: "Multi-runs quotidiens", description: "4 à 8 runs/jour avec rafraîchissement des prévisions" },
      { name: "Pas de temps horaire", description: "capter cycles diurnes et fronts météo rapides" },
    ],
  },

  // ───── Section 8 : Architecture ─────
  architecture: {
    heading: "8 · Architecture technique",
    intro: "Stack complète end-to-end, de l'ingestion des données jusqu'à l'affichage navigateur.",
    cards: [
      {
        title: "Pipelines de données (Python)",
        color: "#1D9E75",
        items: [
          { label: "Langage", value: "Python 3.11 (env conda meteo_ia)" },
          { label: "Manipulation", value: "xarray, pandas, numpy, scipy" },
          { label: "Téléchargement", value: "cdsapi (ERA5), httpx (NOMADS), requests (data.gouv.fr)" },
          { label: "Parsing GRIB2", value: "eccodes, cfgrib" },
          { label: "Inférence IA", value: "JAX + GraphCast (open weights DeepMind)" },
          { label: "Pipelines", value: "4 modules : arome, era5, graphcast_gfs, mae" },
          { label: "Orchestration", value: "Cron quotidien (UTC) avec retry 3× pause 30 min" },
        ],
      },
      {
        title: "Base de données",
        color: "#1E73E8",
        items: [
          { label: "SGBD", value: "PostgreSQL 15 (Docker, port 5433)" },
          { label: "Tables", value: "graphcast_predictions, arome_forecasts, era5_truth, mae_metrics" },
          { label: "Volume", value: "~2 M lignes (1 mois × 6 variables × 2925 points × 4 horizons)" },
          { label: "Ingestion", value: "UPSERT idempotent via COPY + table de staging" },
          { label: "Indexation", value: "Index composites (timestamp, lat, lon) pour requêtes rapides" },
        ],
      },
      {
        title: "Backend API (Node.js)",
        color: "#F08C3D",
        items: [
          { label: "Runtime", value: "Node.js 20 + Express 4" },
          { label: "Endpoints", value: "8 routes REST (timeseries, mae, heatmap, grid, status, health)" },
          { label: "Cache", value: "node-cache TTL 600s (réduit charge DB)" },
          { label: "Sécurité", value: "CORS configuré, helmet, rate-limiter" },
          { label: "Port", value: "3001 (dev) · derrière Nginx (prod)" },
        ],
      },
      {
        title: "Frontend (React)",
        color: "#7F77DD",
        items: [
          { label: "Framework", value: "React 19 + TypeScript 5" },
          { label: "Build", value: "Vite 8 (HMR rapide, build optimisé)" },
          { label: "Styling", value: "Tailwind CSS v4 + shadcn/ui (Radix preset Nova)" },
          { label: "Routing", value: "react-router-dom v7 (routes /fr, /en, /methodologie)" },
          { label: "Charts", value: "Recharts (courbes), Leaflet (carte France)" },
          { label: "Mode", value: "Light + Dark (palette OKLCH style Claude)" },
        ],
      },
      {
        title: "Déploiement & DevOps",
        color: "#A0A0A8",
        items: [
          { label: "Hébergement", value: "VPS OVH (production) · localhost (développement)" },
          { label: "Conteneurs", value: "Docker Compose (PostgreSQL, services backend)" },
          { label: "Reverse proxy", value: "Nginx (HTTPS, compression, cache statique)" },
          { label: "Process manager", value: "PM2 (auto-restart Node.js + monitoring)" },
          { label: "CI/CD", value: "GitHub Actions (lint, tests, build, deploy)" },
          { label: "Monitoring", value: "Logs centralisés + alertes pipeline (v2.0)" },
        ],
      },
    ],
  },
}
