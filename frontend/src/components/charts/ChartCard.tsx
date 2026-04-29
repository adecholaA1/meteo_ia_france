import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { ZoomIn } from "lucide-react"

import { useT } from "@/i18n"
import { SOURCE_COLORS, VARIABLE_METADATA } from "@/lib/colorScales"
import { formatAxisDate, formatTooltipDate } from "@/lib/timezone"
import { formatNumber } from "@/lib/numberFormat"
import { useTimeFilter } from "@/contexts/TimeFilterContext"
import { useZoom } from "@/contexts/ZoomContext"
import { useChartData } from "@/hooks/useChartData"
import type { TimeRange, VariableName } from "@/types/forecast"

import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

interface ChartCardProps {
  variable: VariableName
  isZoomed?: boolean
  cityName?: string
}

interface TooltipPayloadEntry {
  dataKey: string
  value: number | null
}

interface CustomTooltipProps {
  active?: boolean
  payload?: TooltipPayloadEntry[]
  label?: string
  unit: string
  decimals: number
  locale: "fr" | "en"
  variable?: VariableName
}

/**
 * Convertit un angle en degrés en abréviation cardinale 8 secteurs.
 * 0° = N, 45° = NE, 90° = E, 135° = SE, 180° = S, 225° = SO/SW, 270° = O/W, 315° = NO/NW
 * Chaque secteur fait 45° (ex: N = 337.5° à 22.5°).
 */
function getCardinal8(deg: number | null, locale: "fr" | "en"): string | null {
  if (deg === null || deg === undefined) return null
  const sectorsFr = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
  const sectorsEn = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
  const sectors = locale === "fr" ? sectorsFr : sectorsEn
  const idx = Math.round(deg / 45) % 8
  return sectors[idx]
}

function CustomTooltip({ active, payload, label, unit, decimals, locale, variable }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0 || !label) return null

  const era5 = payload.find((p) => p.dataKey === "era5")?.value
  const arome = payload.find((p) => p.dataKey === "arome")?.value
  const graphcast = payload.find((p) => p.dataKey === "graphcast")?.value

  // Pour wind_direction, on ajoute l'abréviation cardinale après la valeur
  const isWindDir = variable === "wind_direction_10m_deg"
  const formatValue = (v: number | null | undefined) => {
    const num = formatNumber(v ?? null, locale, decimals)
    if (isWindDir && v !== null && v !== undefined) {
      const card = getCardinal8(v, locale)
      return card ? `${num}° ${card}` : `${num} ${unit}`
    }
    return `${num} ${unit}`
  }

  return (
    <div className="rounded-md border border-border bg-popover px-3 py-2 shadow-md text-xs">
      <div className="font-medium text-foreground mb-1.5">
        {formatTooltipDate(label, locale)}
      </div>
      <div className="space-y-0.5">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-1.5">
            <span className="inline-block w-2 h-2 rounded-sm" style={{ backgroundColor: SOURCE_COLORS.era5 }} />
            <span className="text-muted-foreground">ERA5</span>
          </div>
          <span className="font-medium text-foreground tabular-nums">
            {formatValue(era5)}
          </span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-1.5">
            <span className="inline-block w-2 h-2 rounded-sm" style={{ backgroundColor: SOURCE_COLORS.arome }} />
            <span className="text-muted-foreground">AROME</span>
          </div>
          <span className="font-medium text-foreground tabular-nums">
            {formatValue(arome)}
          </span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-1.5">
            <span className="inline-block w-2 h-2 rounded-sm" style={{ backgroundColor: SOURCE_COLORS.graphcast }} />
            <span className="text-muted-foreground">GraphCast</span>
          </div>
          <span className="font-medium text-foreground tabular-nums">
            {formatValue(graphcast)}
          </span>
        </div>
      </div>
    </div>
  )
}

export function ChartCard({ variable, isZoomed = false, cityName }: ChartCardProps) {
  const { t, locale } = useT()
  const { timeRange, setTimeRange } = useTimeFilter()
  const { openZoom } = useZoom()

  const meta = VARIABLE_METADATA[variable]
  const variableLabel = t.variables[variable]
  const rawData = useChartData(variable, timeRange)

  // ─────────────────────────────────────────────────────────────────────
  // 🆕 Wind direction = bar chart (pas de cleanup nécessaire)
  // Les autres variables = line chart (comportement classique)
  //
  // Pourquoi bar chart pour wind_direction ?
  //   La direction du vent est CIRCULAIRE (0° = 360° = nord). Une courbe
  //   linéaire crée des zigzags artificiels au passage 0°/360° puisque
  //   Recharts trace une ligne droite entre 357° et 5°.
  //   Un bar chart évite ce problème : chaque barre est indépendante,
  //   pas d'interpolation entre points consécutifs.
  // ─────────────────────────────────────────────────────────────────────
  const isWindDirection = variable === "wind_direction_10m_deg"
  const chartData = rawData

  const hasData = chartData.length > 0

  const axisColor = "#888888"
  const gridColor = "#3a3a40"
  const chartHeight = isZoomed ? "h-full" : "h-[200px]"

  const yAxisWidth = (variable === "msl_hpa" || variable === "toa_wm2") ? 56 : 40

  return (
    <div className={`rounded-md ${isZoomed ? "h-full flex flex-col" : "border border-border bg-card p-3"}`}>
      {/* Header rendu UNIQUEMENT en mode normal (en mode zoom, il est dans le DialogHeader) */}
      {!isZoomed && (
        <div className="flex items-center justify-between mb-2 flex-shrink-0 gap-2">
          {/* Zone 1 (gauche) — Titre */}
          <span className="text-sm font-medium text-foreground">
            {variableLabel}
            <span className="ml-1.5 text-xs font-normal text-muted-foreground">
              ({meta.unit})
            </span>
          </span>

          {/* Zone 2 (centre) — Badge ville */}
          {cityName && (
            <div
              className="h-7 px-2 flex items-center gap-1 rounded-md border border-input bg-transparent text-xs text-foreground whitespace-nowrap"
              aria-label={`Données pour ${cityName}`}
            >
              <span style={{ fontSize: "11px", lineHeight: 1 }}>📍</span>
              <span>{cityName}</span>
            </div>
          )}

          {/* Zone 3 (droite) — Filtre temps + bouton zoom */}
          <div className="flex items-center gap-1.5">
            <Select
              value={timeRange}
              onValueChange={(v) => setTimeRange(v as TimeRange)}
            >
              <SelectTrigger
                className="h-7 text-xs px-2 gap-1"
                aria-label={t.a11y.timeRangeSelect}
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1d">{t.controls.timeRanges["1d"]}</SelectItem>
                <SelectItem value="7d">{t.controls.timeRanges["7d"]}</SelectItem>
                <SelectItem value="14d">{t.controls.timeRanges["14d"]}</SelectItem>
              </SelectContent>
            </Select>

            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => openZoom({ type: "chart", variable })}
              aria-label={t.a11y.zoomButton}
            >
              <ZoomIn className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      )}

      {/* Le graphique */}
      <div className={chartHeight + (isZoomed ? " flex-1 min-h-0" : "")}>
        {!hasData ? (
          <div className="h-full flex items-center justify-center text-xs text-muted-foreground">
            {t.states.noData}
          </div>
        ) : isWindDirection ? (
          // 🆕 BAR CHART pour wind_direction (3 barres fines groupées par timestamp)
          // + légende des 8 secteurs cardinaux en bas
          <div className="h-full flex flex-col">
            <div className="flex-1 min-h-0">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={chartData}
                  margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
                  barCategoryGap="30%"
                  barGap={1}
                >
                  <CartesianGrid
                    stroke={gridColor}
                    strokeDasharray="2 4"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="timestamp"
                    tickFormatter={(v) => formatAxisDate(v, locale)}
                    stroke={axisColor}
                    tick={{ fill: axisColor, fontSize: 10 }}
                    tickLine={false}
                    axisLine={false}
                    minTickGap={40}
                  />
                  <YAxis
                    stroke={axisColor}
                    tick={{ fill: axisColor, fontSize: 10, fontWeight: 500 }}
                    tickLine={false}
                    axisLine={false}
                    width={42}
                    domain={[0, 360]}
                    ticks={[0, 90, 180, 270, 360]}
                    tickFormatter={(v) => {
                      // Format Style 3 : "360°N", "270°O" (numéro + ° + lettre cardinale collés)
                      // Convention : 0/360=N, 90=E, 180=S, 270=O(FR)/W(EN)
                      const cardinals: Record<number, string> = {
                        0: "N",
                        90: "E",
                        180: "S",
                        270: locale === "fr" ? "O" : "W",
                        360: "N",
                      }
                      const cardinal = cardinals[v]
                      return cardinal ? `${v}°${cardinal}` : formatNumber(v, locale, 0)
                    }}
                  />
                  <Tooltip
                    content={
                      <CustomTooltip
                        unit={meta.unit}
                        decimals={meta.decimals}
                        locale={locale}
                        variable={variable}
                      />
                    }
                    cursor={{ fill: "rgba(136, 136, 136, 0.1)" }}
                  />
                  <Bar
                    dataKey="era5"
                    fill={SOURCE_COLORS.era5}
                    isAnimationActive={false}
                  />
                  <Bar
                    dataKey="arome"
                    fill={SOURCE_COLORS.arome}
                    isAnimationActive={false}
                  />
                  <Bar
                    dataKey="graphcast"
                    fill={SOURCE_COLORS.graphcast}
                    isAnimationActive={false}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
            {/* 🆕 Légende des 8 secteurs cardinaux (Style B) */}
            <div className="mt-1.5 px-2 py-1 text-[10px] leading-tight text-muted-foreground flex flex-wrap gap-x-2 gap-y-0.5">
              {[
                { abbr: "N", range: "337.5–22.5°" },
                { abbr: "NE", range: "22.5–67.5°" },
                { abbr: "E", range: "67.5–112.5°" },
                { abbr: "SE", range: "112.5–157.5°" },
                { abbr: "S", range: "157.5–202.5°" },
                { abbr: locale === "fr" ? "SO" : "SW", range: "202.5–247.5°" },
                { abbr: locale === "fr" ? "O" : "W", range: "247.5–292.5°" },
                { abbr: locale === "fr" ? "NO" : "NW", range: "292.5–337.5°" },
              ].map((s, i, arr) => (
                <span key={s.abbr} className="inline-flex items-baseline gap-1">
                  <span className="font-medium text-foreground">{s.abbr}</span>
                  <span>{s.range}</span>
                  {i < arr.length - 1 && <span className="text-border ml-1">·</span>}
                </span>
              ))}
            </div>
          </div>
        ) : (
          // LINE CHART pour les autres variables (comportement classique)
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
            >
              <CartesianGrid
                stroke={gridColor}
                strokeDasharray="2 4"
                vertical={false}
              />
              <XAxis
                dataKey="timestamp"
                tickFormatter={(v) => formatAxisDate(v, locale)}
                stroke={axisColor}
                tick={{ fill: axisColor, fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                minTickGap={40}
              />
              <YAxis
                stroke={axisColor}
                tick={{ fill: axisColor, fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                width={yAxisWidth}
                domain={
                  meta.yAxisStartsAtZero
                    ? [0, "auto"]
                    : ["dataMin - 1", "dataMax + 1"]
                }
                tickFormatter={(v) => formatNumber(v, locale, meta.decimals)}
                allowDecimals={meta.decimals > 0}
              />
              <Tooltip
                content={
                  <CustomTooltip
                    unit={meta.unit}
                    decimals={meta.decimals}
                    locale={locale}
                  />
                }
                cursor={{ stroke: axisColor, strokeWidth: 1, strokeDasharray: "3 3" }}
              />
              <Line
                type="monotone"
                dataKey="era5"
                stroke={SOURCE_COLORS.era5}
                strokeWidth={2}
                dot={false}
                connectNulls={false}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="arome"
                stroke={SOURCE_COLORS.arome}
                strokeWidth={1.8}
                dot={false}
                connectNulls={false}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="graphcast"
                stroke={SOURCE_COLORS.graphcast}
                strokeWidth={1.8}
                dot={false}
                connectNulls={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}
