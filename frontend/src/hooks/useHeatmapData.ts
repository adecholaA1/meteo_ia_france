// ═══════════════════════════════════════════════════════════════════════
//  Hook useHeatmapData (étape 10 — version hybride)
//  -----------------------------------------------------------------------
//  Charge les heatmaps :
//    🟢 Mode API runtime : 1 fetch par timestamp via /api/heatmap/error
//    💾 Mode JSON statique : fichier /data/heatmaps/{variable}.json
//
//  L'API publique reste identique à avant
//  ({ loading, error, grid, availableTimestamps }).
// ═══════════════════════════════════════════════════════════════════════

import { useEffect, useState } from "react"
import { useDataSource } from "@/contexts/DataSourceContext"
import type { SourceName, VariableName } from "@/types/forecast"

export interface HeatmapPoint {
  lat: number
  lon: number
  source_value: number
  era5_value: number
  error: number
}

export interface HeatmapGrid {
  source: string
  comparison: string
  variable: string
  timestamp: string
  count: number
  stats: { min: number; max: number; mean: number; abs_mean: number }
  grid: HeatmapPoint[]
}

export interface HeatmapVariableFile {
  variable: VariableName
  generated_at: string
  arome: { timestamps: string[]; grids: Record<string, HeatmapGrid> }
  graphcast: { timestamps: string[]; grids: Record<string, HeatmapGrid> }
}

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:3001"

// Caches séparés pour chaque mode
const cacheStatic = new Map<VariableName, HeatmapVariableFile>()
const cacheApi = new Map<string, HeatmapGrid>() // clé : `${variable}|${source}|${timestamp}`
const cacheApiTimestamps = new Map<string, string[]>() // clé : `${variable}|${source}`

/**
 * Lazy-loading des heatmaps : charge le fichier JSON ou appelle l'API
 * selon le contexte DataSourceContext, et met en cache.
 */
export function useHeatmapData(
  variable: VariableName,
  source: SourceName,
  timestamp: string | null
) {
  const { useApi } = useDataSource()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [grid, setGrid] = useState<HeatmapGrid | null>(null)
  const [availableTimestamps, setAvailableTimestamps] = useState<string[]>([])

  // ERA5 n'est pas une source pour la carte (c'est la vérité, déjà incluse dans chaque point)
  const sourceForFile: "arome" | "graphcast" =
    source === "graphcast" ? "graphcast" : "arome"

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      setError(null)

      try {
        if (useApi) {
          // ─────────────────────────────────────────────────────
          // 🟢 MODE API RUNTIME
          // ─────────────────────────────────────────────────────
          // 1. Récupérer les timestamps où la comparaison est possible.
          //    On utilise source=era5 car ERA5 a une latence J-6 et c'est
          //    la source qui limite la disponibilité des comparaisons.
          //    Les timestamps AROME et GraphCast plus récents existent
          //    mais n'ont pas encore d'ERA5 correspondant pour comparer.
          const tsCacheKey = `${variable}|${sourceForFile}`
          let timestamps = cacheApiTimestamps.get(tsCacheKey)
          if (!timestamps) {
            const availResponse = await fetch(
              `${API_BASE_URL}/api/forecast/available-times?source=era5`
            )
            if (!availResponse.ok)
              throw new Error(`HTTP ${availResponse.status} (available-times)`)
            const availData = (await availResponse.json()) as {
              times: Array<{ date: string; hour: string }>
            }
            // Construction de l'ISO Z directement depuis date+hour de l'API (UTC).
            // Pas via new Date() qui appliquerait un décalage timezone local.
            timestamps = availData.times.map(
              (t) => `${t.date}T${t.hour.padStart(2, "0")}:00:00.000Z`
            )
            cacheApiTimestamps.set(tsCacheKey, timestamps)
          }
          if (cancelled) return
          setAvailableTimestamps(timestamps)

          // 2. Récupérer la grid pour le timestamp courant
          const ts = timestamp || timestamps[0]
          if (!ts) {
            setGrid(null)
            return
          }

          const gridCacheKey = `${variable}|${sourceForFile}|${ts}`
          if (cacheApi.has(gridCacheKey)) {
            setGrid(cacheApi.get(gridCacheKey) ?? null)
            return
          }

          // Extraction de date+hour depuis l'ISO en manipulant la string
          // directement (pas new Date(), pour éviter tout décalage timezone).
          // Format ISO Z attendu : "2026-04-19T18:00:00.000Z"
          //   → date = "2026-04-19"
          //   → hour = "18"
          const isoMatch = ts.match(/^(\d{4}-\d{2}-\d{2})T(\d{2}):/)
          if (!isoMatch) {
            throw new Error(`Format timestamp invalide : ${ts}`)
          }
          const date = isoMatch[1]
          const hour = isoMatch[2]

          const heatmapResponse = await fetch(
            `${API_BASE_URL}/api/heatmap/error?source=${sourceForFile}&date=${date}&hour=${hour}&variable=${variable}`
          )
          if (!heatmapResponse.ok)
            throw new Error(`HTTP ${heatmapResponse.status} (heatmap)`)
          const heatmapGrid = (await heatmapResponse.json()) as HeatmapGrid
          if (cancelled) return
          cacheApi.set(gridCacheKey, heatmapGrid)
          setGrid(heatmapGrid)
        } else {
          // ─────────────────────────────────────────────────────
          // 💾 MODE JSON STATIQUE (comportement d'origine)
          // ─────────────────────────────────────────────────────
          let file = cacheStatic.get(variable)
          if (!file) {
            const response = await fetch(`/data/heatmaps/${variable}.json`)
            if (!response.ok) throw new Error(`HTTP ${response.status}`)
            file = (await response.json()) as HeatmapVariableFile
            if (cancelled) return
            cacheStatic.set(variable, file)
          }

          const sourceData = file[sourceForFile]
          setAvailableTimestamps(sourceData.timestamps)
          const ts = timestamp || sourceData.timestamps[0]
          setGrid(ts && sourceData.grids[ts] ? sourceData.grids[ts] : null)
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [variable, sourceForFile, timestamp, useApi])

  return { loading, error, grid, availableTimestamps }
}
