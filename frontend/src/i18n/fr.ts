// ═══════════════════════════════════════════════════════════════════════
//  Traductions françaises — Météo IA France
//  Version : A v9 + centralText dans le header
// ═══════════════════════════════════════════════════════════════════════

export const fr = {
  header: {
    title: "Météo IA France",
    subtitle: "Tableau de bord de comparaison des modèles de prévision météo",
    centralText: {
      headline: "Comparaison de prévisions à 24h",
      sources: {
        era5: "ERA5",
        era5Suffix: "(vérité)",
        arome: "AROME",
        aromeSuffix: "(Météo-France)",
        graphcast: "GraphCast",
        graphcastSuffix: "(DeepMind)",
      },
    },
    clock: {},
    theme: {
      label: "Thème",
      light: "Clair",
      dark: "Sombre",
      system: "Système",
    },
    language: {
      fr: "FR",
      en: "EN",
    },
  },

  controls: {
    syncBanner:
      "Filtres synchronisés · 🔍 zoom disponible sur tous les blocs · 1 changement = tout se met à jour partout",
    date: "Date",
    time: "Heure",
    mapSource: "Source carte",
    mapVariable: "Variable carte",
    globalRange: "⚡ Période globale",
    timeRanges: {
      "1d": "24 heures",
      "7d": "7 jours",
      "14d": "14 jours",
    },
  },

  variables: {
    t2m_celsius: "🌡️ Température 2m",
    wind_speed_10m_ms: "🌬️ Vitesse vent",
    wind_direction_10m_deg: "🧭 Direction vent",
    msl_hpa: "☁️ Pression",
    tp_6h_mm: "🌧️ Précipitations",
    toa_wm2: "☀️ Rayonnement TOA — Calculée non prédite",
  },

  map: {
    title: "🗺️ Carte de France",
    selectedPoint: "Point sélectionné",
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
    ratioBetter: "× plus précis",
    summaryWin: "🏆 AROME bat GraphCast sur 5/5 variables comparables",
  },

  zoom: {
    title: "Vue agrandie",
    close: "Fermer",
    comingSoon: "🚧 Vue détail à venir",
  },

  states: {
    loading: "Chargement des données…",
    error: "Erreur de chargement",
    noData: "Pas de données disponibles",
  },

  footer: {
    sources: {
      era5:
        "Données de l'ECMWF (vérité terrain), latence J-6, générées le J à 5h00 UTC{offset}.",
      graphcast:
        "Modèle IA de Google DeepMind avec les données GFS NOMADS (NOAA), générées le J à 3h30 UTC{offset}.",
      arome:
        "Modèle physique régional de Météo-France via data.gouv.fr, générées le J à 4h00 UTC{offset}.",
      mae:
        "Recalculé le J à 6h00 UTC{offset} sur les 2 925 points de la grille France 0,25°.",
    },
    copyright:
      "© 2026 — Météo IA France · Données : ECMWF Copernicus · NOAA · Météo-France",
    version: "v1.0",
    sourceCode: "Code source",
  },

  a11y: {
    languageSwitcher: "Changer de langue",
    themeSwitcher: "Changer de thème",
    timeRangeSelect: "Sélectionner une période",
    zoomButton: "Agrandir ce bloc",
  },
  maeTable: {
    title: "📊 MAE (Mean Absolute Error) — Vérité terrain ERA5",
    subtitle: "moyenne 7 derniers jours",
    horizons: {
      h6: "02 h UTC+2",
      h12: "08 h UTC+2",
      h18: "14 h UTC+2",
      h24: "20 h UTC+2",
    },
    toaShort: "☀️ TOA radiation",
    columns: {
      variable: "Variable",
      arome: "AROME",
      graphcast: "GraphCast",
      ratio: "Ratio",
      winner: "Gagnant",
    },
    legend: {
      aromeBetter: "AROME meilleur",
      graphcastBetter: "GraphCast meilleur",
      formula: "Ratio = MAE GraphCast / MAE AROME",
    },
    notComparable: "non comparé",
    noData: "Aucune donnée MAE disponible",
  },
  franceMap: {
    title: "🗺️ Carte France",
    subtitle: "103 villes / 2 925 · grille 0,25° (Résolution 0,25° ≈ 25 km)",
    topCitiesLegend: "10 plus grandes villes",
    sources: {
      arome: "AROME",
      graphcast: "GraphCast",
    },
    legend: {
      sourceValue: "Valeur prédite",
      era5Value: "Vérité ERA5",
      truthLabel: "vérité",
      error: "Écart",
    },
    noData: "Aucune donnée disponible pour cette sélection",
    loading: "Chargement de la carte…",
  },
} as const

export type FrenchTranslations = typeof fr

/**
 * Type des traductions, dérivé de la structure FR mais avec les valeurs
 * assouplies en `string` génériques (au lieu de littéraux exacts).
 * Permet à `en.ts` d'implémenter la même structure avec ses propres textes anglais.
 */
export type Translations = DeepStringify<typeof fr>

// Helper récursif : remplace tous les literal types `string` par le type `string` générique
type DeepStringify<T> = T extends string
  ? string
  : T extends readonly (infer U)[]
  ? readonly DeepStringify<U>[]
  : T extends object
  ? { [K in keyof T]: DeepStringify<T[K]> }
  : T
