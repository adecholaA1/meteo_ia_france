import { useMemo } from "react"
import { FRANCE_CITIES, type FrenchCity } from "@/lib/franceCities"
import { useHeatmapData, type HeatmapPoint } from "@/hooks/useHeatmapData"
import type { SourceName, VariableName } from "@/types/forecast"

export interface CityHeatmapPoint extends FrenchCity {
  source_value: number
  era5_value: number
  error: number
}

/**
 * Pour chaque ville française, trouve le point de la grille 0,25° le plus proche
 * et retourne sa valeur. Permet d'afficher 100 marqueurs au lieu de 2 925.
 */
export function useCityHeatmap(
  variable: VariableName,
  source: SourceName,
  timestamp: string | null
) {
  const { loading, error, grid, availableTimestamps } = useHeatmapData(variable, source, timestamp)

  const cityPoints = useMemo<CityHeatmapPoint[]>(() => {
    if (!grid?.grid || grid.grid.length === 0) return []

    return FRANCE_CITIES.map((city) => {
      // Trouver le point grille le plus proche (Haversine simplifiée = euclidienne sur lat/lon)
      let nearest: HeatmapPoint | null = null
      let minDist = Infinity
      for (const p of grid.grid) {
        const dLat = p.lat - city.lat
        const dLon = p.lon - city.lon
        const dist = dLat * dLat + dLon * dLon
        if (dist < minDist) {
          minDist = dist
          nearest = p
        }
      }
      if (!nearest) {
        return { ...city, source_value: NaN, era5_value: NaN, error: NaN }
      }
      return {
        ...city,
        source_value: nearest.source_value,
        era5_value: nearest.era5_value,
        error: nearest.error,
      }
    }).filter((p) => !isNaN(p.source_value))
  }, [grid])

  return { loading, error, cityPoints, availableTimestamps }
}
