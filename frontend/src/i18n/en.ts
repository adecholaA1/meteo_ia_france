// ═══════════════════════════════════════════════════════════════════════
//  English translations — France AI Weather
//  Version : A v9 + centralText in header
// ═══════════════════════════════════════════════════════════════════════

import type { Translations } from "./fr"

export const en: Translations = {
  header: {
    title: "France AI Weather",
    subtitle: "Weather forecast model comparison dashboard",
    centralText: {
      headline: "24-Hour Forecast Comparison",
      sources: {
        era5: "ERA5",
        era5Suffix: "(truth)",
        arome: "AROME",
        aromeSuffix: "(Météo-France)",
        graphcast: "GraphCast",
        graphcastSuffix: "(DeepMind)",
      },
    },
    clock: {},
    theme: {
      label: "Theme",
      light: "Light",
      dark: "Dark",
      system: "System",
    },
    language: {
      fr: "FR",
      en: "EN",
    },
  },

  controls: {
    syncBanner:
      "Synchronized filters · 🔍 zoom available on all blocks · 1 change = everything updates everywhere",
    date: "Date",
    time: "Time",
    mapSource: "Map source",
    mapVariable: "Map variable",
    globalRange: "⚡ Global range",
    timeRanges: {
      "1d": "24 hours",
      "7d": "7 days",
      "14d": "14 days",
    },
  },

  variables: {
    t2m_celsius: "🌡️ Temperature 2m",
    wind_speed_10m_ms: "🌬️ Wind speed",
    wind_direction_10m_deg: "🧭 Wind direction",
    msl_hpa: "☁️ Pressure",
    tp_6h_mm: "🌧️ Precipitation",
    toa_wm2: "☀️ TOA radiation — Computed not forecast",
  },

  map: {
    title: "🗺️ Map of France",
    selectedPoint: "Selected point",
    legendMin: "min",
    legendMax: "max",
  },

  mae: {
    title: "📊 MAE (Mean Absolute Error)",
    horizon: "horizon",
    table: {
      variable: "Variable",
      arome: "AROME",
      graphcast: "GraphCast",
      ratio: "Ratio",
    },
    ratioBetter: "× more accurate",
    summaryWin: "🏆 AROME beats GraphCast on 5/5 comparable variables",
  },

  zoom: {
    title: "Expanded view",
    close: "Close",
    comingSoon: "🚧 Detailed view coming soon",
  },

  states: {
    loading: "Loading data…",
    error: "Loading error",
    noData: "No data available",
  },

  footer: {
    sources: {
      era5:
        "ECMWF data (ground truth), J-6 latency, generated on day J at 5 a.m. UTC{offset}.",
      graphcast:
        "Google DeepMind AI model with GFS NOMADS data (NOAA), generated on day J at 3:30 a.m. UTC{offset}.",
      arome:
        "Météo-France regional physical model via data.gouv.fr, generated on day J at 4 a.m. UTC{offset}.",
      mae:
        "Recomputed on day J at 6 a.m. UTC{offset} over the 2,925 points of the 0.25° France grid.",
    },
    copyright:
      "© 2026 — France AI Weather · Data: ECMWF Copernicus · NOAA · Météo-France",
    version: "v1.0",
    sourceCode: "Source code",
  },

  a11y: {
    languageSwitcher: "Change language",
    themeSwitcher: "Change theme",
    timeRangeSelect: "Select time range",
    zoomButton: "Zoom this block",
  },
  maeTable: {
    title: "📊 MAE (Mean Absolute Error) — ERA5 ground truth",
    subtitle: "7-day average",
    horizons: {
      h6: "2 a.m. UTC+2",
      h12: "8 a.m. UTC+2",
      h18: "2 p.m. UTC+2",
      h24: "8 p.m. UTC+2",
    },
    toaShort: "☀️ TOA radiation",
    columns: {
      variable: "Variable",
      arome: "AROME",
      graphcast: "GraphCast",
      ratio: "Ratio",
      winner: "Winner",
    },
    legend: {
      aromeBetter: "AROME better",
      graphcastBetter: "GraphCast better",
      formula: "Ratio = GraphCast MAE / AROME MAE",
    },
    notComparable: "not compared",
    noData: "No MAE data available",
  },
  franceMap: {
    title: "🗺️ France map",
    subtitle: "103 cities / 2,925 · 0.25° grid",
    topCitiesLegend: "10 largest cities",
    sources: {
      arome: "AROME",
      graphcast: "GraphCast",
    },
    legend: {
      sourceValue: "Predicted value",
      era5Value: "ERA5 truth",
      truthLabel: "truth",
      error: "Error",
    },
    noData: "No data available for this selection",
    loading: "Loading map…",
  },
}
