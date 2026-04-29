import { useT } from "@/i18n"
import { useZoom } from "@/contexts/ZoomContext"
import { useTimeFilter } from "@/contexts/TimeFilterContext"
import { useSelectedCity } from "@/contexts/SelectedCityContext"
import { VARIABLE_METADATA } from "@/lib/colorScales"
import { ChartCard } from "@/components/charts/ChartCard"
import { MaeTableCard } from "@/components/charts/MaeTableCard"
import { FranceMap } from "@/components/map/FranceMap"
import type { TimeRange } from "@/types/forecast"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

export function ZoomDialog() {
  const { t } = useT()
  const { zoomTarget, closeZoom } = useZoom()
  const { timeRange, setTimeRange } = useTimeFilter()
  const { selectedCity } = useSelectedCity()

  if (zoomTarget === null) return null

  const isChart = typeof zoomTarget === "object" && zoomTarget !== null && "variable" in zoomTarget
  const isMap = zoomTarget === "map"
  const isMae = zoomTarget === "mae_table"

  let zoomTitle: string = ""
  let zoomContent: React.ReactNode = null

  if (isMap) {
    zoomTitle = t.franceMap.title
    zoomContent = <FranceMap isZoomed />
  } else if (isMae) {
    zoomTitle = t.maeTable.title
    zoomContent = <MaeTableCard isZoomed />
  } else if (isChart) {
    // 🆕 PHASE B.4 — cityName dynamique via le context (plus de "Paris" en dur)
    const variableLabel = t.variables[zoomTarget.variable]
    const meta = VARIABLE_METADATA[zoomTarget.variable]
    zoomTitle = `${variableLabel} (${meta.unit})`
    zoomContent = (
      <ChartCard
        variable={zoomTarget.variable}
        isZoomed
        cityName={selectedCity.name}
      />
    )
  }

  return (
    <Dialog
      open={zoomTarget !== null}
      onOpenChange={(open) => {
        if (!open) closeZoom()
      }}
    >
      <DialogContent
        className="!max-w-[95vw] w-[95vw] h-[80vh] !p-0 flex flex-col gap-0 overflow-hidden"
      >
        <DialogHeader className="px-5 py-3 border-b border-border">
          {isChart ? (
            <div className="flex items-center justify-between gap-3 pr-8">
              <DialogTitle className="text-base font-medium whitespace-nowrap">
                {zoomTitle}
              </DialogTitle>

              {/* 🆕 PHASE B.4 — Badge ville dynamique (lit selectedCity du context) */}
              <div
                className="h-10 px-4 flex items-center justify-center gap-2 rounded-md border border-input bg-transparent text-base font-medium text-foreground whitespace-nowrap"
                aria-label={`Données pour ${selectedCity.name}`}
              >
                <span style={{ fontSize: "18px", lineHeight: 1 }}>📍</span>
                <span>{selectedCity.name}</span>
              </div>

              <Select
                value={timeRange}
                onValueChange={(v) => setTimeRange(v as TimeRange)}
              >
                <SelectTrigger
                  className="h-10 text-base px-4 gap-1"
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
            </div>
          ) : (
            <DialogTitle className="text-base font-medium">
              {zoomTitle}
            </DialogTitle>
          )}
        </DialogHeader>

        <div className="flex-1 min-h-0 p-4">
          {zoomContent}
        </div>
      </DialogContent>
    </Dialog>
  )
}
