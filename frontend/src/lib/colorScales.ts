import type { SourceName, VariableName } from "@/types/forecast"

// ═══════════════════════════════════════════════════════════════════════
//  Couleurs des 3 sources de données
//  Utilisées partout : courbes, header central, footer, légendes
// ═══════════════════════════════════════════════════════════════════════
export const SOURCE_COLORS: Record<SourceName, string> = {
  era5: "#1E73E8",       // Bleu franc (vérité terrain)
  arome: "#1D9E75",      // Vert (Météo-France)
  graphcast: "#F08C3D",  // Orange franc (Google DeepMind)
}

export const SOURCE_LABELS: Record<SourceName, string> = {
  era5: "ERA5",
  arome: "AROME",
  graphcast: "GraphCast",
}

interface VariableMetadata {
  emoji: string
  unit: string
  decimals: number
  heatmapMin: number
  heatmapMax: number
  heatmapGradient: string[]
  // Si true, l'axe Y des graphiques commence à 0 (pour les variables
  // dont une valeur 0 a un sens physique fort : rayonnement, précipitations).
  // Si false ou absent, l'axe Y se cale automatiquement sur le min/max
  // des données (utile pour pression, température, vent qui ont des
  // gammes éloignées de 0).
  yAxisStartsAtZero?: boolean
}

export const VARIABLE_METADATA: Record<VariableName, VariableMetadata> = {
  t2m_celsius: {
    emoji: "🌡️",
    unit: "°C",
    decimals: 1,
    heatmapMin: -10,
    heatmapMax: 30,
    heatmapGradient: ["#185FA5", "#1D9E75", "#EF9F27", "#A32D2D"],
  },
  wind_speed_10m_ms: {
    emoji: "🌬️",
    unit: "m/s",
    decimals: 1,
    heatmapMin: 0,
    heatmapMax: 25,
    heatmapGradient: ["#E6F1FB", "#85B7EB", "#185FA5", "#0C447C"],
    yAxisStartsAtZero: true,
  },
  wind_direction_10m_deg: {
    emoji: "🧭",
    unit: "°",
    decimals: 0,
    heatmapMin: 0,
    heatmapMax: 360,
    heatmapGradient: ["#7F77DD", "#1D9E75", "#EF9F27", "#7F77DD"],
  },
  msl_hpa: {
    emoji: "☁️",
    unit: "hPa",
    decimals: 1,
    heatmapMin: 980,
    heatmapMax: 1040,
    heatmapGradient: ["#185FA5", "#85B7EB", "#F0997B", "#A32D2D"],
  },
  tp_6h_mm: {
    emoji: "🌧️",
    unit: "mm",
    decimals: 2,
    heatmapMin: 0,
    heatmapMax: 20,
    heatmapGradient: ["#FAFAFA", "#85B7EB", "#185FA5", "#0C447C"],
    yAxisStartsAtZero: true,
  },
  toa_wm2: {
    emoji: "☀️",
    unit: "W/m²",
    decimals: 0,
    heatmapMin: 0,
    heatmapMax: 1400,
    heatmapGradient: ["#0C447C", "#5F5E5A", "#FAC775", "#EF9F27"],
    yAxisStartsAtZero: true,
  },
}

export function getHeatmapColor(
  variable: VariableName,
  value: number | null
): string {
  if (value === null || isNaN(value)) {
    return "#888780"
  }

  const meta = VARIABLE_METADATA[variable]
  const { heatmapMin, heatmapMax, heatmapGradient } = meta

  const t = Math.max(0, Math.min(1, (value - heatmapMin) / (heatmapMax - heatmapMin)))

  const segmentCount = heatmapGradient.length - 1
  const segmentIndex = Math.min(Math.floor(t * segmentCount), segmentCount - 1)
  const localT = (t * segmentCount) - segmentIndex

  return interpolateHexColor(
    heatmapGradient[segmentIndex],
    heatmapGradient[segmentIndex + 1],
    localT
  )
}

function interpolateHexColor(hex1: string, hex2: string, t: number): string {
  const r1 = parseInt(hex1.slice(1, 3), 16)
  const g1 = parseInt(hex1.slice(3, 5), 16)
  const b1 = parseInt(hex1.slice(5, 7), 16)
  const r2 = parseInt(hex2.slice(1, 3), 16)
  const g2 = parseInt(hex2.slice(3, 5), 16)
  const b2 = parseInt(hex2.slice(5, 7), 16)

  const r = Math.round(r1 + (r2 - r1) * t)
  const g = Math.round(g1 + (g2 - g1) * t)
  const b = Math.round(b1 + (b2 - b1) * t)

  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`
}
