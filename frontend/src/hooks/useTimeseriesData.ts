// ═══════════════════════════════════════════════════════════════════════
//  Hook useTimeseriesData (Phase B.5 — carte interactive)
//  ----------------------------------------------------------------------
//  Charge les séries temporelles (6 variables sur 14 jours) pour la ville
//  actuellement sélectionnée. Optimisé pour les changements fréquents :
//
//    🚀 Cache automatique via TanStack Query :
//        clic Marseille → fetch (~14s) puis cache 5 min
//        clic Paris    → cache instantané (déjà chargé)
//        re-clic Marseille → cache instantané
//
//    🟢 Bascule automatique en mode API :
//        Si l'utilisateur est en mode statique et clique sur une ville,
//        on bascule automatiquement le toggle vers le mode API (DataSourceContext).
//        En mode statique uniquement Paris fonctionne (un seul fichier JSON pré-généré).
//
//    🎯 Snapping sur la grille 0.25° :
//        La DB ne contient que les points multiples de 0.25° (résolution ERA5/AROME/GraphCast).
//        Une ville à 46.171°N, 1.870°E doit être snappée à 46.25°N, 1.75°E pour avoir des données.
//
//  Utilisé par useChartData.ts (qui filtre ensuite sur la période 1d/7d/14d).
// ═══════════════════════════════════════════════════════════════════════

import { useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
import { useSelectedCity } from "@/contexts/SelectedCityContext"
import { useDataSource } from "@/contexts/DataSourceContext"
import { useStaticData } from "./useStaticData"
import type { TimeseriesResponse } from "@/types/forecast"

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:3001"

// Coordonnées Paris snappées sur la grille 0.25° (cohérent avec sample_forecast.json)
const PARIS_GRID = { lat: 49, lon: 2.5 }

// Pas de la grille (résolution ERA5/AROME/GraphCast après ré-échantillonnage)
const GRID_RESOLUTION = 0.25

/**
 * Snappe une coordonnée (lat ou lon) sur la grille 0.25° la plus proche.
 * Ex: 46.171 → 46.25, 1.870 → 1.75, 5.370 → 5.25, 4.720 → 4.75
 */
function snapToGrid(value: number): number {
  return Math.round(value / GRID_RESOLUTION) * GRID_RESOLUTION
}

// Réponse brute de l'API timeseries (avec point: { lat, lon })
interface ApiTimeseriesRaw {
  point: { lat: number; lon: number }
  days: number
  variables: TimeseriesResponse["variables"]
}

interface UseTimeseriesDataReturn {
  data: TimeseriesResponse | null
  loading: boolean
  error: string | null
}

/**
 * Hook qui charge les courbes pour la ville sélectionnée.
 * - Si la ville sélectionnée est Paris (par défaut) ET qu'on est en mode statique :
 *   utilise les données pré-chargées dans useStaticData (instantané, pas de fetch).
 * - Sinon (autre ville OU mode API) : fetch dynamique avec cache TanStack.
 *
 * 🆕 BUGFIX : les coords des villes sont snappées sur la grille 0.25° avant fetch
 * (sinon le backend cherche un point exact qui n'existe pas en DB → tableaux vides).
 */
export function useTimeseriesData(): UseTimeseriesDataReturn {
  const { selectedCity } = useSelectedCity()
  const { useApi, setUseApi } = useDataSource()
  const { data: staticData } = useStaticData()

  // Détection : sommes-nous sur Paris (= ville par défaut) ?
  const isParis = selectedCity.name === "Paris"

  // Si on n'est PAS sur Paris et qu'on est en mode statique, basculer auto vers mode API
  useEffect(() => {
    if (!isParis && !useApi) {
      console.log(
        `[useTimeseriesData] Bascule auto vers mode API pour ${selectedCity.name}`
      )
      setUseApi(true)
    }
  }, [isParis, useApi, selectedCity.name, setUseApi])

  // Coordonnées à utiliser pour le fetch
  // Pour Paris : on snappe sur la grille 0.25° (49, 2.5) — déjà configuré dans PARIS_GRID
  // Pour les autres : on snappe les coords réelles via snapToGrid()
  const fetchLat = isParis ? PARIS_GRID.lat : snapToGrid(selectedCity.lat)
  const fetchLon = isParis ? PARIS_GRID.lon : snapToGrid(selectedCity.lon)

  // Cas spécial : si Paris + mode statique + données déjà chargées dans useStaticData,
  // on utilise les données pré-chargées (pas besoin de fetcher).
  const useStaticTimeseries = isParis && !useApi && staticData !== null

  // TanStack Query : ne fetch QUE si on n'utilise pas la donnée statique
  const queryResult = useQuery<TimeseriesResponse, Error>({
    queryKey: ["timeseries", fetchLat, fetchLon, 14],
    queryFn: async () => {
      const url = `${API_BASE_URL}/api/forecast/timeseries?lat=${fetchLat}&lon=${fetchLon}&days=14`
      const response = await fetch(url)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status} sur ${url}`)
      }
      const raw: ApiTimeseriesRaw = await response.json()
      // Adaptation du shape API ({ point, days, variables }) vers le shape frontend
      return {
        lat: raw.point.lat,
        lon: raw.point.lon,
        days: raw.days,
        variables: raw.variables,
      }
    },
    enabled: !useStaticTimeseries, // ne pas fetch si on utilise la donnée statique
    staleTime: 5 * 60 * 1000, // cache 5 minutes
    gcTime: 10 * 60 * 1000, // garde en mémoire 10 minutes après le dernier usage
    retry: 1,
  })

  // Si on est sur Paris en mode statique, on retourne la donnée pré-chargée
  if (useStaticTimeseries && staticData) {
    return {
      data: staticData.timeseries_paris,
      loading: false,
      error: null,
    }
  }

  // Sinon on retourne le résultat de TanStack Query
  return {
    data: queryResult.data ?? null,
    loading: queryResult.isLoading,
    error: queryResult.error?.message ?? null,
  }
}
