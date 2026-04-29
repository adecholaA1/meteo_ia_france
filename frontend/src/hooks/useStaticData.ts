// ═══════════════════════════════════════════════════════════════════════
//  Hook useStaticData (étape 10 — version hybride)
//  -----------------------------------------------------------------------
//  Selon le contexte DataSourceContext (variable env VITE_USE_API ou
//  toggle UI), ce hook charge les données :
//    🟢 depuis l'API Express runtime (http://localhost:3001/api/...)
//    💾 depuis le JSON statique pré-généré (/data/sample_forecast.json)
//
//  Les composants consomment ce hook SANS savoir quel mode est actif.
//  L'API publique ({ data, loading, error }) reste identique à avant.
// ═══════════════════════════════════════════════════════════════════════

import { useEffect, useState } from "react"
import { useDataSource } from "@/contexts/DataSourceContext"
import type {
  TimeseriesResponse,
  MaeComparisonResponse,
  GridPoint,
  ForecastGridResponse,
  VariableName,
  ForecastHorizon,
} from "@/types/forecast"

// Structure du JSON statique (mirror du script generate_static_data.mjs)
interface StaticDataSnapshot {
  generated_at: string
  paris: { lat: number; lon: number }
  status: {
    tables: Record<string, { count: number; latest_timestamp?: string }>
  }
  available_times_graphcast: { count: number; times: Array<{ date: string; hour: string }> }
  available_times_arome: { count: number; times: Array<{ date: string; hour: string }> }
  grid_points: { count: number; points: GridPoint[] }
  timeseries_paris: TimeseriesResponse
  mae_comparison: {
    h6: MaeComparisonResponse
    h12: MaeComparisonResponse
    h18: MaeComparisonResponse
    h24: MaeComparisonResponse
  }
  mae_history: Record<VariableName, unknown>
  heatmap_graphcast: unknown
  heatmap_arome: unknown
  forecast_grid_graphcast_t2m: ForecastGridResponse
}

interface UseStaticDataReturn {
  data: StaticDataSnapshot | null
  loading: boolean
  error: string | null
}

// URL de base du backend Express (configurable via .env)
const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:3001"

// Coordonnées Paris (alignées sur la grille 0.25° — le point réel le plus proche)
// Paris = 48.85°N / 2.35°E → grille la plus proche : 49°N / 2.5°E
const PARIS_GRID = { lat: 49, lon: 2.5 }

// Caches séparés pour chaque mode (API et statique)
let cachedStatic: StaticDataSnapshot | null = null
let cachedApi: StaticDataSnapshot | null = null

/**
 * Hook qui charge les données au premier appel et les met en cache.
 * Bascule entre mode API runtime et mode JSON statique selon le contexte.
 */
export function useStaticData(): UseStaticDataReturn {
  const { useApi } = useDataSource()
  const cached = useApi ? cachedApi : cachedStatic
  const [data, setData] = useState<StaticDataSnapshot | null>(cached)
  const [loading, setLoading] = useState(!cached)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Si déjà en cache pour ce mode, on ne refetch pas
    const currentCache = useApi ? cachedApi : cachedStatic
    if (currentCache) {
      setData(currentCache)
      setLoading(false)
      setError(null)
      return
    }

    let cancelled = false
    setLoading(true)
    setError(null)

    if (useApi) {
      // ─────────────────────────────────────────────────────────
      // 🟢 MODE API RUNTIME : on agrège plusieurs endpoints Express
      //    pour reconstruire la même structure que le JSON statique.
      // ─────────────────────────────────────────────────────────
      loadFromApi()
        .then((snapshot) => {
          if (cancelled) return
          cachedApi = snapshot
          setData(snapshot)
          setLoading(false)
        })
        .catch((err: Error) => {
          if (cancelled) return
          console.error("[useStaticData/API] Erreur :", err)
          setError(err.message)
          setLoading(false)
        })
    } else {
      // ─────────────────────────────────────────────────────────
      // 💾 MODE JSON STATIQUE (comportement d'origine)
      // ─────────────────────────────────────────────────────────
      // V1.0 : fichiers JSON pas inclus dans le build Docker
      //   → fallback automatique vers le mode API si fetch échoue
      // V1.1 : régénérer JSON via npm run build:data + inclure dans Docker
      fetch("/data/sample_forecast.json")
        .then((response) => {
          if (!response.ok) {
            throw new Error(`HTTP ${response.status} ${response.statusText}`)
          }
          // Vérifier que le content-type est bien JSON
          // (sinon nginx renvoie un HTML d'erreur 404 qui plante .json())
          const contentType = response.headers.get("content-type") || ""
          if (!contentType.includes("application/json")) {
            throw new Error(`Expected JSON, got ${contentType}`)
          }
          return response.json()
        })
        .then((json: StaticDataSnapshot) => {
          if (cancelled) return
          cachedStatic = json
          setData(json)
          setLoading(false)
        })
        .catch((err: Error) => {
          if (cancelled) return
          console.warn(
            "[useStaticData/STATIC] JSON statique indisponible " +
              "(probablement non inclus dans ce build), bascule en mode API :",
            err.message
          )
          // Fallback automatique : on utilise l'API
          loadFromApi()
            .then((snapshot) => {
              if (cancelled) return
              cachedStatic = snapshot
              cachedApi = snapshot
              setData(snapshot)
              setLoading(false)
            })
            .catch((apiErr: Error) => {
              if (cancelled) return
              console.error("[useStaticData/STATIC→API] Erreur :", apiErr)
              setError(apiErr.message)
              setLoading(false)
            })
        })
    }

    return () => {
      cancelled = true
    }
  }, [useApi])

  return { data, loading, error }
}

/**
 * Helper : récupère le tableau MAE pour un horizon donné depuis le JSON.
 */
export function getMaeForHorizon(
  data: StaticDataSnapshot,
  horizon: ForecastHorizon
): MaeComparisonResponse {
  const key = `h${horizon}` as keyof typeof data.mae_comparison
  return data.mae_comparison[key]
}

// ═══════════════════════════════════════════════════════════════════════
// Implémentation interne — agrégation des endpoints API Express
// vers la structure StaticDataSnapshot.
// ═══════════════════════════════════════════════════════════════════════

// Réponse brute de l'API timeseries (avec point: { lat, lon })
interface ApiTimeseriesRaw {
  point: { lat: number; lon: number }
  days: number
  variables: TimeseriesResponse["variables"]
}

async function loadFromApi(): Promise<StaticDataSnapshot> {
  const paris = PARIS_GRID

  // Helper pour fetch + JSON + erreur claire
  const apiGet = async <T>(path: string): Promise<T> => {
    const response = await fetch(`${API_BASE_URL}${path}`)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status} sur ${path}`)
    }
    return response.json() as Promise<T>
  }

  // Fetch parallèle de tous les endpoints nécessaires
  const [
    statusRaw,
    availTimesGraphcast,
    availTimesArome,
    gridPoints,
    timeseriesRaw,
    maeH6,
    maeH12,
    maeH18,
    maeH24,
  ] = await Promise.all([
    apiGet<{
      tables: Record<string, { count: number; latest_timestamp?: string }>
    }>("/api/status"),
    apiGet<{ count: number; times: Array<{ date: string; hour: string }> }>(
      "/api/forecast/available-times?source=graphcast"
    ),
    apiGet<{ count: number; times: Array<{ date: string; hour: string }> }>(
      "/api/forecast/available-times?source=arome"
    ),
    apiGet<{ count: number; points: GridPoint[] }>(
      "/api/forecast/grid-points"
    ),
    apiGet<ApiTimeseriesRaw>(
      `/api/forecast/timeseries?lat=${paris.lat}&lon=${paris.lon}&days=7`
    ),
    apiGet<MaeComparisonResponse>("/api/mae/comparison?horizon=6"),
    apiGet<MaeComparisonResponse>("/api/mae/comparison?horizon=12"),
    apiGet<MaeComparisonResponse>("/api/mae/comparison?horizon=18"),
    apiGet<MaeComparisonResponse>("/api/mae/comparison?horizon=24"),
  ])

  // Adaptation du shape API ({ point, days, variables }) vers le shape frontend ({ lat, lon, days, variables })
  const timeseriesParis: TimeseriesResponse = {
    lat: timeseriesRaw.point.lat,
    lon: timeseriesRaw.point.lon,
    days: timeseriesRaw.days,
    variables: timeseriesRaw.variables,
  }

  // Agrégation finale dans la structure StaticDataSnapshot
  return {
    generated_at: new Date().toISOString(),
    paris,
    status: { tables: statusRaw.tables },
    available_times_graphcast: availTimesGraphcast,
    available_times_arome: availTimesArome,
    grid_points: gridPoints,
    timeseries_paris: timeseriesParis,
    mae_comparison: {
      h6: maeH6,
      h12: maeH12,
      h18: maeH18,
      h24: maeH24,
    },
    // Les heatmaps ne sont pas pré-chargées en mode API (utilisées par useHeatmapData séparément)
    mae_history: {} as Record<VariableName, unknown>,
    heatmap_graphcast: null,
    heatmap_arome: null,
    // forecast_grid_graphcast_t2m : pas pré-chargé, utilisé à la demande
    forecast_grid_graphcast_t2m: {
      date: "",
      hour: 0,
      source: "graphcast",
      variable: "t2m_celsius",
      points: [],
    },
  }
}
