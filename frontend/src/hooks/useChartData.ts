import { useMemo } from "react"
import { useTimeseriesData } from "./useTimeseriesData"
import type { TimeRange, VariableName } from "@/types/forecast"

const RANGE_TO_DAYS: Record<TimeRange, number> = {
  "1d": 1,
  "7d": 7,
  "14d": 14,
}

interface ChartDataPoint {
  timestamp: string
  era5: number | null
  arome: number | null
  graphcast: number | null
}

/**
 * Hook qui prépare les données d'une variable météo pour Recharts,
 * en filtrant sur la période choisie.
 *
 * 🆕 PHASE B.5 — utilise useTimeseriesData au lieu de useStaticData.timeseries_paris
 * → Les courbes deviennent dynamiques selon la ville sélectionnée (SelectedCityContext).
 */
export function useChartData(
  variable: VariableName,
  timeRange: TimeRange
): ChartDataPoint[] {
  const { data } = useTimeseriesData()

  return useMemo(() => {
    if (!data) return []

    const allPoints = data.variables[variable] ?? []
    if (allPoints.length === 0) return []

    const days = RANGE_TO_DAYS[timeRange]
    const latestTimestamp = new Date(allPoints[allPoints.length - 1].timestamp)
    const cutoff = new Date(latestTimestamp.getTime() - days * 24 * 60 * 60 * 1000)

    return allPoints
      .filter((p) => new Date(p.timestamp) >= cutoff)
      .map((p) => ({
        timestamp: p.timestamp,
        era5: p.era5,
        arome: p.arome,
        graphcast: p.graphcast,
      }))
  }, [data, variable, timeRange])
}
