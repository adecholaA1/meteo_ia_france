// ═══════════════════════════════════════════════════════════════════
// methodology.en.ts — Long-form EN texts for the Methodology page
// ═══════════════════════════════════════════════════════════════════

import type { MethodologyTranslations } from "./methodology.fr"

export const methodologyEn: MethodologyTranslations = {
  pageTitle: "Methodology",
  pageSubtitle: "France AI Weather · Forecast model comparison dashboard",
  backToDashboard: "← Back to dashboard",

  // ───── Section 1: About ─────
  about: {
    heading: "1 · About this project",
    paragraph:
      "France AI Weather compares two forecasting approaches over metropolitan France on a daily basis: the AROME regional physical model from Météo-France, and the GraphCast Operational AI model from Google DeepMind. Ground truth (observed reference) is provided by ECMWF's ERA5 reanalysis.",
  },

  // ───── Section 2: Glossary ─────
  glossary: {
    heading: "2 · Glossary",
    entries: [
      { term: "ECMWF", definition: "European Centre for Medium-Range Weather Forecasts. European center based in Reading (UK)." },
      { term: "ERA5", definition: "5th generation atmospheric reanalysis from ECMWF, used as ground truth." },
      { term: "CDS", definition: "Climate Data Store. ERA5 data access platform (free with registration)." },
      { term: "NOAA", definition: "National Oceanic and Atmospheric Administration. US weather agency." },
      { term: "GFS", definition: "Global Forecast System. NOAA's global model, 0.25° resolution, 6-hourly runs." },
      { term: "NOMADS", definition: "NOAA Operational Model Archive and Distribution System. GFS data access server." },
      { term: "AROME", definition: "Applications de la Recherche à l'Opérationnel à Méso-Échelle. Météo-France regional model." },
      { term: "ARPEGE", definition: "Action de Recherche Petite Échelle Grande Échelle. Météo-France global model." },
      { term: "GRIB2", definition: "GRIdded Binary version 2. WMO standard binary format for weather data." },
      { term: "NetCDF", definition: "Network Common Data Form. Scientific format for multidimensional data." },
      { term: "MAE", definition: "Mean Absolute Error. Average of absolute differences between predictions and ERA5 truth." },
      { term: "RMSE", definition: "Root Mean Square Error. Square root of the mean squared differences." },
      { term: "Bias", definition: "Mean systematic error (positive = overestimation, negative = underestimation)." },
      { term: "Run", definition: "A complete model execution at time T (e.g. 18z run = 18:00 UTC run)." },
      { term: "Horizon", definition: "Time delta between run and predicted timestamp (e.g. 24h horizon = D+1 forecast)." },
      { term: "Zero-shot", definition: "Model used on new data without specific re-training (without fine-tuning)." },
    ],
  },

  // ───── Section 3: Variables ─────
  variables: {
    heading: "3 · The 6 weather variables",
    items: [
      { emoji: "🌡️", name: "Temperature 2m", code: "t2m_celsius · °C", description: "Air temperature 2 meters above ground level.", range: "France range: -15 °C to +40 °C · Most stable variable" },
      { emoji: "🌬️", name: "Wind speed 10m", code: "wind_speed_10m_ms · m/s", description: "Magnitude of horizontal wind vector at 10 meters.", range: "France range: 0 to 30 m/s · Critical for wind energy" },
      { emoji: "🧭", name: "Wind direction 10m", code: "wind_direction_10m_deg · °", description: "Wind angle in degrees (0° = north, 90° = east).", range: "Range: 0 to 360° · Cyclic variable (recomputed MAE)" },
      { emoji: "☁️", name: "Mean sea-level pressure", code: "msl_hpa · hPa", description: "Atmospheric pressure reduced to mean sea level.", range: "France range: 980 to 1040 hPa · Depression indicator" },
      { emoji: "🌧️", name: "Precipitation 6h", code: "tp_6h_mm · mm", description: "6-hour rolling precipitation accumulation.", range: "Range: 0 to 50 mm · Hardest variable to predict" },
      { emoji: "☀️", name: "TOA radiation", code: "toa_wm2 · W/m²", description: "Solar radiation at top of atmosphere (computed astronomically).", range: "Range: 0 to 1400 W/m² · Solar cycle reference" },
    ],
  },

  // ───── Section 4: Sources ─────
  sources: {
    heading: "4 · Data sources",
    era5: {
      name: "ERA5",
      tag: "Ground truth",
      provider: "ECMWF Copernicus",
      description: "5th-generation reanalysis from ECMWF. Combines satellite observations, ground stations and physical models to produce past meteorological \"truth\".",
      meta: [
        { label: "Resolution", value: "0.25° ≈ 25 km" },
        { label: "Time step", value: "1h" },
        { label: "Latency", value: "D-6" },
        { label: "Access", value: "CDS API (free)" },
      ],
    },
    arome: {
      name: "AROME",
      tag: "Regional physical model",
      provider: "Météo-France",
      description: "High-resolution non-hydrostatic model covering metropolitan France.",
      meta: [
        { label: "Resolution", value: "0.025° ≈ 2.5 km ★", highlight: true },
        { label: "Runs/day", value: "8 (every 3h)" },
        { label: "Horizon", value: "up to 51h" },
        { label: "Access", value: "data.gouv.fr" },
      ],
    },
    graphcast: {
      name: "GraphCast Operational",
      tag: "AI model",
      provider: "Google DeepMind + GFS NOAA",
      description: "Graph neural network pre-trained on ERA5 then fine-tuned for use with GFS. Our version uses GFS NOMADS as initial conditions (zero-shot since not re-fine-tuned for France).",
      meta: [
        { label: "Resolution", value: "0.25° ≈ 25 km" },
        { label: "Time step", value: "6h" },
        { label: "Horizon", value: "up to 10 days" },
        { label: "Inference", value: "~1-8 min CPU" },
      ],
    },
  },

  // ───── Section 5: Comparison table ─────
  comparison: {
    heading: "5 · Comparison table",
    headers: {
      criterion: "Criterion",
      era5: "ERA5",
      era5Sub: "Ground truth",
      arome: "AROME",
      aromeSub: "Physical model",
      graphcast: "GraphCast Op.",
      graphcastSub: "AI model",
    },
    rows: [
      { criterion: "Type", era5: "Past reanalysis", arome: "Regional physical model", graphcast: "Graph neural network" },
      { criterion: "Publisher", era5: "ECMWF (Europe)", arome: "Météo-France", graphcast: "Google DeepMind" },
      { criterion: "Physical input", era5: "Observations + assimilation", arome: "ARPEGE initial conditions", graphcast: "GFS data (NOAA)" },
      { criterion: "Native resolution", era5: "0.25° (≈ 25 km)", arome: "0.025° (≈ 2.5 km) ★", graphcast: "0.25° (≈ 25 km)", aromeColor: "good" },
      { criterion: "Used resolution", era5: "0.25°", arome: "0.25° (downsampled)", graphcast: "0.25°", aromeColor: "warn" },
      { criterion: "Native time step", era5: "1h", arome: "1h", graphcast: "6h", aromeColor: "good" },
      { criterion: "Used time step", era5: "6h", arome: "6h (downsampled)", graphcast: "6h", aromeColor: "warn" },
      { criterion: "Nominal runs/day", era5: "—", arome: "8 (every 3h)", graphcast: "4 (every 6h)", aromeColor: "good" },
      { criterion: "Used runs/day", era5: "—", arome: "1 (18z UTC run)", graphcast: "1 (18z UTC run)", aromeColor: "warn", graphcastColor: "warn" },
      { criterion: "Predicted horizon", era5: "—", arome: "up to 51h (D+2)", graphcast: "up to 10 days" },
      { criterion: "Data latency", era5: "D-6 (5 to 6 days)", arome: "~4 h", graphcast: "~4 h", era5Color: "warn", aromeColor: "good", graphcastColor: "good" },
      { criterion: "Training", era5: "—", arome: "Physical equations", graphcast: "Pre-trained on ERA5, zero-shot on GFS", graphcastColor: "warn" },
      { criterion: "Data format", era5: "NetCDF (CDS API)", arome: "GRIB2 (data.gouv.fr)", graphcast: "GRIB2 → NetCDF" },
      { criterion: "Access cost", era5: "Free (CDS API)", arome: "Free (data.gouv.fr)", graphcast: "Free (NOMADS + open weights)", era5Color: "good", aromeColor: "good", graphcastColor: "good" },
    ],
    legend: "Legend: green = advantage · orange = current limitation · gray = neutral",
  },

  // ───── Section 6: Limitations ─────
  limitations: {
    heading: "6 · Current limitations (v1.0)",
    items: [
      { title: "One run per day", description: "instead of 4-8 nominal. Consequence: forecasts made with 24h information delay." },
      { title: "No intraday updates", description: "— forecasts are never refreshed during the day with new runs." },
      { title: "AROME downsampled", description: "from 0.025° to 0.25° to align grid with ERA5/GraphCast (90% spatial resolution loss)." },
      { title: "GraphCast in zero-shot", description: "on GFS, without fine-tuning on French data." },
      { title: "6h time step", description: "imposed by GraphCast Operational, while AROME natively supports 1h." },
    ],
  },

  // ───── Section 7: Roadmap ─────
  roadmap: {
    heading: "7 · Roadmap v2.0",
    items: [
      { name: "Pangu-Weather (Huawei)", description: "hierarchical 1h/3h/6h/24h architecture" },
      { name: "ClimaX (Microsoft)", description: "foundation model fine-tunable on French regional data" },
      { name: "AROME native 0.025° resolution", description: "regain regional high resolution" },
      { name: "Multiple daily runs", description: "4 to 8 runs/day with forecast refresh" },
      { name: "Hourly time step", description: "capture diurnal cycles and fast weather fronts" },
    ],
  },

  // ───── Section 8: Architecture ─────
  architecture: {
    heading: "8 · Technical architecture",
    intro: "Full end-to-end stack, from data ingestion to browser display.",
    cards: [
      {
        title: "Data pipelines (Python)",
        color: "#1D9E75",
        items: [
          { label: "Language", value: "Python 3.11 (conda env meteo_ia)" },
          { label: "Data handling", value: "xarray, pandas, numpy, scipy" },
          { label: "Download", value: "cdsapi (ERA5), httpx (NOMADS), requests (data.gouv.fr)" },
          { label: "GRIB2 parsing", value: "eccodes, cfgrib" },
          { label: "AI inference", value: "JAX + GraphCast (DeepMind open weights)" },
          { label: "Pipelines", value: "4 modules: arome, era5, graphcast_gfs, mae" },
          { label: "Orchestration", value: "Daily cron (UTC) with 3× retry, 30-min pause" },
        ],
      },
      {
        title: "Database",
        color: "#1E73E8",
        items: [
          { label: "DBMS", value: "PostgreSQL 15 (Docker, port 5433)" },
          { label: "Tables", value: "graphcast_predictions, arome_forecasts, era5_truth, mae_metrics" },
          { label: "Volume", value: "~2 M rows (1 month × 6 variables × 2925 points × 4 horizons)" },
          { label: "Ingestion", value: "Idempotent UPSERT via COPY + staging table" },
          { label: "Indexing", value: "Composite indexes (timestamp, lat, lon) for fast queries" },
        ],
      },
      {
        title: "Backend API (Node.js)",
        color: "#F08C3D",
        items: [
          { label: "Runtime", value: "Node.js 20 + Express 4" },
          { label: "Endpoints", value: "8 REST routes (timeseries, mae, heatmap, grid, status, health)" },
          { label: "Cache", value: "node-cache TTL 600s (reduces DB load)" },
          { label: "Security", value: "CORS configured, helmet, rate-limiter" },
          { label: "Port", value: "3001 (dev) · behind Nginx (prod)" },
        ],
      },
      {
        title: "Frontend (React)",
        color: "#7F77DD",
        items: [
          { label: "Framework", value: "React 19 + TypeScript 5" },
          { label: "Build", value: "Vite 8 (fast HMR, optimized build)" },
          { label: "Styling", value: "Tailwind CSS v4 + shadcn/ui (Radix Nova preset)" },
          { label: "Routing", value: "react-router-dom v7 (routes /fr, /en, /methodology)" },
          { label: "Charts", value: "Recharts (curves), Leaflet (France map)" },
          { label: "Theme", value: "Light + Dark (Claude-style OKLCH palette)" },
        ],
      },
      {
        title: "Deployment & DevOps",
        color: "#A0A0A8",
        items: [
          { label: "Hosting", value: "OVH VPS (production) · localhost (development)" },
          { label: "Containers", value: "Docker Compose (PostgreSQL, backend services)" },
          { label: "Reverse proxy", value: "Nginx (HTTPS, compression, static caching)" },
          { label: "Process manager", value: "PM2 (Node.js auto-restart + monitoring)" },
          { label: "CI/CD", value: "GitHub Actions (lint, tests, build, deploy)" },
          { label: "Monitoring", value: "Logs centralized + pipeline alerts (v2.0)" },
        ],
      },
    ],
  },
} as const

