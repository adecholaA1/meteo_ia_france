import { useMemo } from "react"
import { useStaticData } from "@/hooks/useStaticData"
import type { VariableName } from "@/types/forecast"

export type Horizon = "h6" | "h12" | "h18" | "h24"

export interface MaeRow {
  variable: VariableName
  arome: number | null
  graphcast: number | null
  ratio: number | null    // GraphCast / AROME ; null si non comparable
  winner: "arome" | "graphcast" | null
}

interface MaeMetric {
  latest: number
  avg_7d: number
  rmse_latest: number
  bias_latest: number | null
}

interface ComparisonsBlock {
  graphcast_vs_era5?: Record<string, MaeMetric>
  arome_vs_era5?: Record<string, MaeMetric>
  graphcast_vs_arome?: Record<string, MaeMetric>
}

interface HorizonBlock {
  horizon: number
  latest_date: string
  comparisons: ComparisonsBlock
}

const VARIABLE_ORDER: VariableName[] = [
  "t2m_celsius",
  "wind_speed_10m_ms",
  "wind_direction_10m_deg",
  "msl_hpa",
  "tp_6h_mm",
  "toa_wm2",
]

/**
 * Lit mae_comparison du JSON statique pour l'horizon donné
 * Retourne 1 ligne par variable avec : MAE AROME, MAE GraphCast, ratio, gagnant
 */
export function useMaeData(horizon: Horizon = "h24"): MaeRow[] {
  const { data } = useStaticData()

  return useMemo(() => {
    if (!data || !("mae_comparison" in data)) return []

    const maeComparison = (data as unknown as { mae_comparison: Record<string, HorizonBlock> }).mae_comparison
    const block = maeComparison?.[horizon]
    if (!block?.comparisons) return []

    const arome = block.comparisons.arome_vs_era5 ?? {}
    const graphcast = block.comparisons.graphcast_vs_era5 ?? {}

    return VARIABLE_ORDER.map((variable): MaeRow => {
      const aromeMae = arome[variable]?.avg_7d ?? null
      const graphcastMae = graphcast[variable]?.avg_7d ?? null

      // Cas TOA : pas de comparaison pertinente (calculé pas prédit)
      if (variable === "toa_wm2") {
        return { variable, arome: null, graphcast: null, ratio: null, winner: null }
      }

      // Si une des deux valeurs est manquante ou nulle
      if (aromeMae === null || graphcastMae === null) {
        return { variable, arome: aromeMae, graphcast: graphcastMae, ratio: null, winner: null }
      }

      // Ratio = GraphCast / AROME ; >1 signifie AROME meilleur
      const ratio = aromeMae > 0 ? graphcastMae / aromeMae : null
      const winner: "arome" | "graphcast" | null =
        ratio === null ? null : ratio > 1 ? "arome" : "graphcast"

      return { variable, arome: aromeMae, graphcast: graphcastMae, ratio, winner }
    })
  }, [data, horizon])
}
