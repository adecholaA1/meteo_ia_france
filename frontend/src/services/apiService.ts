/**
 * 🟢 ÉTAPE 10 — Service API
 *
 * Encapsule TOUS les appels HTTP vers le backend Express (8 endpoints).
 * Chaque fonction est typée avec TypeScript pour une type-safety complète.
 *
 * Utilisation :
 *   import { apiService } from "@/services/apiService"
 *   const data = await apiService.getForecast("2026-04-27", 12)
 *
 * Le hook useForecastData() (à venir micro-étape 3) appellera ces fonctions
 * via TanStack Query pour bénéficier du cache, retry, dedup, etc.
 */

// ═══════════════════════════════════════════════════════════════════════════
// Configuration
// ═══════════════════════════════════════════════════════════════════════════

/**
 * URL de base du backend Express.
 * Lue depuis la variable d'environnement Vite VITE_API_URL.
 * Défaut : http://localhost:3001 (dev local).
 *
 * Pour modifier en prod, créer un fichier .env.production :
 *   VITE_API_URL=https://api.meteo-ia-france.fr
 */
const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:3001"

// ═══════════════════════════════════════════════════════════════════════════
// Types des réponses API (alignés avec backend/controllers/*)
// ═══════════════════════════════════════════════════════════════════════════

export type SourceName = "graphcast" | "arome" | "era5"

export type VariableName =
  | "t2m_celsius"
  | "wind_speed_10m_ms"
  | "wind_direction_10m_deg"
  | "msl_hpa"
  | "tp_6h_mm"
  | "toa_wm2"

export interface HealthResponse {
  status: "ok" | "error"
  message: string
  timestamp: string
  uptime_seconds: number
}

export interface StatusResponse {
  tables: {
    graphcast_predictions: { count: number; latest_run: string; latest_timestamp: string }
    arome_forecasts: { count: number; latest_run: string; latest_timestamp: string }
    era5_truth: { count: number; latest_timestamp: string }
    mae_metrics: { count: number; latest_evaluation_date: string }
  }
  cache: { keys: number; hits: number; misses: number; hitRate: string }
  server: { uptime_seconds: number; node_env: string }
}

export interface AvailableTime {
  date: string
  hour: number
}

export interface AvailableTimesResponse {
  source: SourceName
  count: number
  times: AvailableTime[]
}

export interface GridPoint {
  lat: number
  lon: number
}

export interface GridPointsResponse {
  count: number
  points: GridPoint[]
}

export interface TimeseriesPoint {
  timestamp: string
  graphcast: number | null
  arome: number | null
  era5: number | null
}

export interface TimeseriesResponse {
  point: { lat: number; lon: number }
  days: number
  variables: Record<VariableName, TimeseriesPoint[]>
}

export interface ForecastGridPoint {
  lat: number
  lon: number
  value: number
}

export interface ForecastResponse {
  date: string
  hour: number
  source: SourceName
  variable: VariableName
  count: number
  grid: ForecastGridPoint[]
}

export interface MaeStat {
  latest: number | null
  avg_7d: number | null
  rmse_latest: number | null
  bias_latest: number | null
}

export interface MaeComparisonResponse {
  horizon: number
  latest_date: string
  comparisons: {
    graphcast_vs_era5: Record<VariableName, MaeStat>
    arome_vs_era5: Record<VariableName, MaeStat>
  }
}

export interface MaeHistoryEntry {
  date: string
  graphcast_vs_era5: number | null
  arome_vs_era5: number | null
}

export interface MaeHistoryResponse {
  variable: VariableName
  horizon: number
  days: number
  history: MaeHistoryEntry[]
}

export interface HeatmapGridPoint {
  lat: number
  lon: number
  source_value: number
  era5_value: number
  error: number
}

export interface HeatmapResponse {
  source: SourceName
  comparison: string
  variable: VariableName
  timestamp: string
  count: number
  stats: { min: number; max: number; mean: number; abs_mean: number }
  grid: HeatmapGridPoint[]
}

// ═══════════════════════════════════════════════════════════════════════════
// Helper : fetch avec gestion d'erreur unifiée
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Wrapper autour de fetch() qui :
 * - Préfixe l'URL avec BASE_URL
 * - Gère les query params en objet
 * - Throw une erreur explicite si le status HTTP n'est pas 2xx
 * - Parse automatiquement le JSON
 */
async function apiFetch<T>(
  path: string,
  params?: Record<string, string | number | undefined>
): Promise<T> {
  // Construction de l'URL avec query params
  const url = new URL(`${BASE_URL}${path}`)
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, String(value))
      }
    })
  }

  const response = await fetch(url.toString())

  if (!response.ok) {
    // Tenter de lire le message d'erreur du backend (format { error, message, statusCode })
    let errorMessage = `HTTP ${response.status} on ${path}`
    try {
      const errorBody = await response.json()
      if (errorBody?.message) errorMessage = errorBody.message
    } catch {
      // si le body n'est pas du JSON, on garde le message générique
    }
    throw new Error(errorMessage)
  }

  return response.json() as Promise<T>
}

// ═══════════════════════════════════════════════════════════════════════════
// Service API : 8 endpoints + helpers
// ═══════════════════════════════════════════════════════════════════════════

export const apiService = {
  /**
   * 1️⃣ Healthcheck — vérifie que l'API et la DB sont opérationnelles.
   * Utilisé en démo pour montrer qu'on est connecté au backend.
   */
  getHealth: () => apiFetch<HealthResponse>("/api/health"),

  /**
   * 2️⃣ Status — compteurs des 4 tables + stats cache + uptime.
   * Utile pour la page de monitoring (à venir).
   */
  getStatus: () => apiFetch<StatusResponse>("/api/status"),

  /**
   * 3️⃣ Available times — liste des couples (date, heure) disponibles pour une source.
   * Utilisé au chargement initial pour peupler les sélecteurs date/heure.
   */
  getAvailableTimes: (source: SourceName = "graphcast") =>
    apiFetch<AvailableTimesResponse>("/api/forecast/available-times", { source }),

  /**
   * 4️⃣ Grid points — 2925 points GPS uniques de la grille France.
   * À appeler UNE FOIS au chargement pour dessiner les markers Leaflet.
   */
  getGridPoints: () => apiFetch<GridPointsResponse>("/api/forecast/grid-points"),

  /**
   * 5️⃣ Timeseries — 7 jours de séries temporelles pour 1 point GPS, 6 variables, 3 sources.
   * Endpoint principal pour les ChartCards.
   */
  getTimeseries: (lat: number, lon: number, days: number = 7) =>
    apiFetch<TimeseriesResponse>("/api/forecast/timeseries", { lat, lon, days }),

  /**
   * 6️⃣ Forecast à instant T — grille complète (2925 points) pour 1 source, 1 variable.
   * Utilisé par la carte France pour afficher la heatmap.
   *
   * ⚠️ L'heure doit être paddée à 2 chiffres (ex: "06" pas "6").
   */
  getForecast: (
    date: string,
    hour: number,
    source: SourceName = "graphcast",
    variable: VariableName = "t2m_celsius"
  ) => {
    const hourPadded = String(hour).padStart(2, "0")
    return apiFetch<ForecastResponse>(`/api/forecast/${date}/${hourPadded}`, {
      source,
      variable,
    })
  },

  /**
   * 7️⃣ MAE comparison — tableau MAE latest + moyenne 7j pour 6 variables × 2 comparaisons.
   * Endpoint principal pour le MaeTableCard.
   */
  getMaeComparison: (horizon: number = 24) =>
    apiFetch<MaeComparisonResponse>("/api/mae/comparison", { horizon }),

  /**
   * 8️⃣ MAE history — évolution quotidienne du MAE pour 1 variable.
   * Format pivoté optimisé pour Recharts.
   */
  getMaeHistory: (
    variable: VariableName = "t2m_celsius",
    horizon: number = 24,
    days: number = 30
  ) =>
    apiFetch<MaeHistoryResponse>("/api/mae/history", { variable, horizon, days }),

  /**
   * 9️⃣ Heatmap d'écart — grille (source - era5) pour 1 instant T, 1 variable.
   * Utilisé pour la heatmap d'erreur spatiale.
   */
  getHeatmapError: (
    source: Exclude<SourceName, "era5">,
    date: string,
    hour: number,
    variable: VariableName = "t2m_celsius"
  ) => {
    const hourPadded = String(hour).padStart(2, "0")
    return apiFetch<HeatmapResponse>("/api/heatmap/error", {
      source,
      date,
      hour: hourPadded,
      variable,
    })
  },
}
