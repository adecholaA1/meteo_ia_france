import { useState } from "react"
import { ZoomIn } from "lucide-react"

import { useT } from "@/i18n"
import { SOURCE_COLORS, VARIABLE_METADATA } from "@/lib/colorScales"
import { formatNumber } from "@/lib/numberFormat"
import { useZoom } from "@/contexts/ZoomContext"
import { useMaeData, type Horizon } from "@/hooks/useMaeData"

import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

interface MaeTableCardProps {
  isZoomed?: boolean
}

export function MaeTableCard({ isZoomed = false }: MaeTableCardProps) {
  const { t, locale } = useT()
  const { openZoom } = useZoom()
  const [horizon, setHorizon] = useState<Horizon>("h24")
  const rows = useMaeData(horizon)

  const hasData = rows.length > 0 && rows.some((r) => r.arome !== null || r.graphcast !== null)

  return (
    <div className="rounded-md border border-border bg-card p-3 flex flex-col h-full">
      {/* Header — titre + filtre + zoom */}
      <div className="flex items-start justify-between mb-2 gap-2 flex-shrink-0">
        <div className="min-w-0 flex-1">
          <div className="text-[12.5px] font-medium text-foreground leading-tight">
            {t.maeTable.title}
          </div>
          <div className="text-[12px] text-muted-foreground mt-0.5">
            {t.maeTable.subtitle}
          </div>
        </div>

        <div className="flex items-center gap-1 flex-shrink-0">
          <Select
            value={horizon}
            onValueChange={(v) => setHorizon(v as Horizon)}
          >
            <SelectTrigger className="h-6 text-[12px] px-1.5 gap-1 w-auto">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="h6">{t.maeTable.horizons.h6}</SelectItem>
              <SelectItem value="h12">{t.maeTable.horizons.h12}</SelectItem>
              <SelectItem value="h18">{t.maeTable.horizons.h18}</SelectItem>
              <SelectItem value="h24">{t.maeTable.horizons.h24}</SelectItem>
            </SelectContent>
          </Select>

          {!isZoomed && (
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => openZoom("mae_table")}
            >
              <ZoomIn className="h-3 w-3" />
            </Button>
          )}
        </div>
      </div>

      {/* Tableau — flex-1 pour s'étirer en hauteur */}
      {!hasData ? (
        <div className="flex-1 flex items-center justify-center text-xs text-muted-foreground">
          {t.states.noData}
        </div>
      ) : (
        <div className="flex-1 overflow-hidden rounded-sm border border-border">
          <table className="w-full text-[12.5px] border-collapse h-full">
            <thead>
              <tr className="bg-muted/40 border-b border-border">
                <th className="text-left px-2 py-1.5 font-medium text-muted-foreground text-[11.5px]">
                  {t.maeTable.columns.variable}
                </th>
                <th
                  className="text-right px-2 py-1.5 font-medium text-[11.5px]"
                  style={{ color: SOURCE_COLORS.arome }}
                >
                  {t.maeTable.columns.arome}
                </th>
                <th
                  className="text-right px-2 py-1.5 font-medium text-[11.5px]"
                  style={{ color: SOURCE_COLORS.graphcast }}
                >
                  {t.maeTable.columns.graphcast}
                </th>
                <th className="text-right px-2 py-1.5 font-medium text-muted-foreground text-[11.5px]">
                  {t.maeTable.columns.ratio}
                </th>
              </tr>
            </thead>
            <tbody className="tabular-nums">
              {rows.map((row) => {
                const meta = VARIABLE_METADATA[row.variable]
                const isToa = row.variable === "toa_wm2"
                // Pour TOA, libellé court ; sinon le label habituel des variables
                const variableLabel = isToa ? t.maeTable.toaShort : t.variables[row.variable]

                const aromeColor =
                  row.winner === "arome"
                    ? "text-emerald-400 font-medium"
                    : "text-foreground"
                const graphcastColor =
                  row.winner === "graphcast"
                    ? "text-orange-400 font-medium"
                    : "text-foreground"
                const ratioColor =
                  row.ratio === null
                    ? "text-muted-foreground"
                    : row.winner === "arome"
                      ? "text-emerald-400 font-medium"
                      : "text-orange-400 font-medium"

                return (
                  <tr
                    key={row.variable}
                    className={
                      "border-b border-border/40 last:border-b-0 " +
                      (isToa ? "italic text-muted-foreground" : "")
                    }
                  >
                    <td className="px-2 py-1.5 truncate">{variableLabel}</td>
                    <td className={`px-2 py-1.5 text-right ${isToa ? "text-muted-foreground" : aromeColor}`}>
                      {row.arome !== null
                        ? formatNumber(row.arome, locale, meta.decimals)
                        : "—"}
                    </td>
                    <td className={`px-2 py-1.5 text-right ${isToa ? "text-muted-foreground" : graphcastColor}`}>
                      {row.graphcast !== null
                        ? formatNumber(row.graphcast, locale, meta.decimals)
                        : "—"}
                    </td>
                    <td className={`px-2 py-1.5 text-right ${ratioColor}`}>
                      {row.ratio !== null ? `×${row.ratio.toFixed(1)}` : "—"}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
