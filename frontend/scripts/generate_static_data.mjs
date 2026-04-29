// ═══════════════════════════════════════════════════════════════════════
//  Script de génération du JSON statique pour le frontend
//  Appelle l'API backend (port 3001) et écrit :
//
//  1. public/data/sample_forecast.json — données générales (header, MAE, courbes)
//  2. public/data/heatmaps/<variable>.json — 1 fichier par variable météo
//     contenant tous les timestamps disponibles pour AROME et GraphCast
//
//  Usage : node scripts/generate_static_data.mjs
// ═══════════════════════════════════════════════════════════════════════

import { writeFileSync, mkdirSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

const __dirname = dirname(fileURLToPath(import.meta.url))
const OUTPUT_DIR = join(__dirname, "..", "public", "data")
const HEATMAP_DIR = join(OUTPUT_DIR, "heatmaps")
const API_BASE = "http://localhost:3001/api"

// Point GPS de référence pour les courbes : Paris
const PARIS_LAT = 48.75
const PARIS_LON = 2.5

// Variables exposées au frontend
const VARIABLES = [
  "t2m_celsius",
  "wind_speed_10m_ms",
  "wind_direction_10m_deg",
  "msl_hpa",
  "tp_6h_mm",
  "toa_wm2",
]

// Nombre de derniers timestamps à inclure dans les heatmaps (pour limiter la taille)
const HEATMAP_LAST_N_TIMESTAMPS = 4

console.log("🌦️  Génération du JSON statique pour Météo IA France")
console.log("═══════════════════════════════════════════════════════════")

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

async function fetchJson(url) {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText} sur ${url}`)
  }
  const data = await response.json()
  await sleep(120)  // pause anti rate-limit (express-rate-limit côté backend)
  return data
}

async function fetchJsonSilent(url) {
  // Variante sans log (pour les appels en boucle nombreux)
  try {
    const response = await fetch(url)
    if (!response.ok) {
      await sleep(120)
      return null
    }
    const data = await response.json()
    await sleep(120)  // pause anti rate-limit
    return data
  } catch {
    return null
  }
}

async function main() {
  const snapshot = {
    generated_at: new Date().toISOString(),
    paris: { lat: PARIS_LAT, lon: PARIS_LON },
  }

  // 1. Status DB
  console.log("\n📊 Status DB")
  console.log(`  📡 GET ${API_BASE}/status`)
  snapshot.status = await fetchJson(`${API_BASE}/status`)

  // 2. Available times
  console.log("\n📅 Available times")
  console.log(`  📡 GET available-times graphcast`)
  snapshot.available_times_graphcast = await fetchJson(
    `${API_BASE}/forecast/available-times?source=graphcast`
  )
  console.log(`  📡 GET available-times arome`)
  snapshot.available_times_arome = await fetchJson(
    `${API_BASE}/forecast/available-times?source=arome`
  )
  console.log(`  📡 GET available-times era5 (vérité, latence ~5j)`)
  snapshot.available_times_era5 = await fetchJson(
    `${API_BASE}/forecast/available-times?source=era5`
  )

  // 3. Grille des 2925 points GPS
  console.log("\n🗺️  Grid points")
  console.log(`  📡 GET grid-points`)
  snapshot.grid_points = await fetchJson(`${API_BASE}/forecast/grid-points`)

  // 4. Timeseries 14 jours sur Paris
  console.log("\n📈 Timeseries Paris (14 jours)")
  console.log(`  📡 GET timeseries`)
  snapshot.timeseries_paris = await fetchJson(
    `${API_BASE}/forecast/timeseries?lat=${PARIS_LAT}&lon=${PARIS_LON}&days=14`
  )

  // 5. MAE comparison sur les 4 horizons
  console.log("\n📊 MAE comparison")
  snapshot.mae_comparison = {}
  for (const horizon of [6, 12, 18, 24]) {
    console.log(`  📡 GET mae/comparison h${horizon}`)
    snapshot.mae_comparison[`h${horizon}`] = await fetchJson(
      `${API_BASE}/mae/comparison?horizon=${horizon}`
    )
  }

  // 6. MAE history sur 14 jours pour chaque variable
  console.log("\n📈 MAE history (14 jours, par variable)")
  snapshot.mae_history = {}
  for (const variable of VARIABLES) {
    console.log(`  📡 GET mae/history ${variable}`)
    snapshot.mae_history[variable] = await fetchJson(
      `${API_BASE}/mae/history?variable=${variable}&days=14`
    )
  }

  // 7. Heatmap d'écart spatial — date la plus récente disponible (pour compat)
  console.log("\n🔥 Heatmap snapshot (date la plus récente)")
  const latestDate = snapshot.mae_comparison.h24?.evaluation_date || "2026-04-19"
  console.log(`     Date utilisée : ${latestDate} 12h UTC`)

  snapshot.heatmap_graphcast = await fetchJson(
    `${API_BASE}/heatmap/error?source=graphcast&date=${latestDate}&hour=12&variable=t2m_celsius`
  )
  snapshot.heatmap_arome = await fetchJson(
    `${API_BASE}/heatmap/error?source=arome&date=${latestDate}&hour=12&variable=t2m_celsius`
  )

  // 8. Forecast grid (carte de France à un instant T) — pour la heatmap principale
  console.log("\n🗺️  Forecast grid (carte de France)")
  snapshot.forecast_grid_graphcast_t2m = await fetchJson(
    `${API_BASE}/forecast/${latestDate}/12?source=graphcast&variable=t2m_celsius`
  )

  // Écriture du fichier principal
  mkdirSync(OUTPUT_DIR, { recursive: true })
  const outputPath = join(OUTPUT_DIR, "sample_forecast.json")
  writeFileSync(outputPath, JSON.stringify(snapshot, null, 2), "utf8")
  const sizeKb = (JSON.stringify(snapshot).length / 1024).toFixed(1)
  console.log(`\n✅ ${outputPath} (${sizeKb} KB)`)

  // ═══════════════════════════════════════════════════════════════════════
  // 9. NOUVEAU : Heatmaps par variable (6 fichiers séparés)
  //    Pour chaque variable, on récupère les N derniers timestamps disponibles
  //    pour AROME et GraphCast, et on stocke tout dans un fichier dédié.
  // ═══════════════════════════════════════════════════════════════════════
  console.log("\n🗺️  Génération des 6 heatmaps par variable")
  console.log(`     ${HEATMAP_LAST_N_TIMESTAMPS} derniers timestamps × 2 sources × 6 variables = ${HEATMAP_LAST_N_TIMESTAMPS * 2 * 6} appels API`)
  mkdirSync(HEATMAP_DIR, { recursive: true })

  // Helper pour extraire les N derniers timestamps uniques
  // Format attendu : { times: [ {date: "2026-04-26", hour: "18", horizons: [24]}, ... ] }
  // Trié du plus récent au plus ancien (donc on prend les N premiers).
  const getLastTimestamps = (response, n) => {
    if (!response?.times || !Array.isArray(response.times)) return []
    return response.times
      .slice(0, n)  // les N premiers = les plus récents (déjà triés DESC)
      .map((item) => ({
        date: item.date,
        hour: parseInt(item.hour, 10),
        // ISO timestamp utile comme clé unique dans les heatmap grids
        iso: `${item.date}T${item.hour.padStart(2, "0")}:00:00Z`,
      }))
  }

  // ERA5 a une latence ~5 jours : on PART d'ERA5 (intersection garantie avec AROME/GraphCast)
  // qui ont eux toutes les dates récentes mais sans vérité comparable.
  const era5Times = getLastTimestamps(snapshot.available_times_era5, HEATMAP_LAST_N_TIMESTAMPS)
  const aromeTimes = era5Times    // mêmes timestamps : on a ERA5 → AROME existe forcément aussi
  const graphcastTimes = era5Times

  console.log(`     Timestamps ERA5 (vérité) : ${era5Times.length}`)
  if (era5Times.length > 0) {
    console.log(`        Plus récent : ${era5Times[0].iso}`)
    console.log(`        Plus ancien : ${era5Times[era5Times.length - 1].iso}`)
  }

  for (const variable of VARIABLES) {
    const heatmapData = {
      variable,
      generated_at: new Date().toISOString(),
      arome: { timestamps: [], grids: {} },
      graphcast: { timestamps: [], grids: {} },
    }

    // AROME
    for (const t of aromeTimes) {
      const grid = await fetchJsonSilent(
        `${API_BASE}/heatmap/error?source=arome&date=${t.date}&hour=${String(t.hour).padStart(2, "0")}&variable=${variable}`
      )
      if (grid && Array.isArray(grid.grid)) {
        heatmapData.arome.timestamps.push(t.iso)
        heatmapData.arome.grids[t.iso] = grid
      }
    }

    // GraphCast
    for (const t of graphcastTimes) {
      const grid = await fetchJsonSilent(
        `${API_BASE}/heatmap/error?source=graphcast&date=${t.date}&hour=${String(t.hour).padStart(2, "0")}&variable=${variable}`
      )
      if (grid && Array.isArray(grid.grid)) {
        heatmapData.graphcast.timestamps.push(t.iso)
        heatmapData.graphcast.grids[t.iso] = grid
      }
    }

    const filePath = join(HEATMAP_DIR, `${variable}.json`)
    writeFileSync(filePath, JSON.stringify(heatmapData), "utf8")
    const fileSizeKb = (JSON.stringify(heatmapData).length / 1024).toFixed(1)
    console.log(
      `   ✅ ${variable}.json — ${fileSizeKb} KB (${heatmapData.arome.timestamps.length} ts AROME + ${heatmapData.graphcast.timestamps.length} ts GraphCast)`
    )
  }

  console.log("\n═══════════════════════════════════════════════════════════")
  console.log(`✅ Génération terminée`)
  console.log(`   Date du snapshot : ${snapshot.generated_at}`)
  console.log("═══════════════════════════════════════════════════════════")
}

main().catch((err) => {
  console.error("\n❌ Erreur lors de la génération :")
  console.error(err)
  process.exit(1)
})
