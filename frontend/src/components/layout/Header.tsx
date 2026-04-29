// ═══════════════════════════════════════════════════════════════════════
//  Header de l'application
//  Horloge live (tick 10s) avec UTC dynamique selon DST.
// ═══════════════════════════════════════════════════════════════════════

import { useEffect, useState } from "react"
import { Clock } from "lucide-react"

import { useT } from "@/i18n"
import { LanguageSwitcher } from "./LanguageSwitcher"
import { ModeToggle } from "./ModeToggle"
import { DataSourceToggle } from "./DataSourceToggle"
import { getParisUtcOffset } from "@/lib/timezone"
import { SOURCE_COLORS } from "@/lib/colorScales"

export function Header() {
  const { t } = useT()
  const [now, setNow] = useState(new Date())

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 10_000)
    return () => clearInterval(id)
  }, [])

  const time = new Intl.DateTimeFormat("fr-FR", {
    timeZone: "Europe/Paris",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(now)

  const offset = getParisUtcOffset(now)
  const utcLabel = `UTC${offset >= 0 ? "+" : ""}${offset}`

  const central = t.header.centralText

  return (
    <header className="grid grid-cols-[1fr_auto_1fr] items-center gap-4 rounded-md border border-border bg-card px-5 py-4">
      <div className="flex items-center gap-3">
        <span className="text-2xl">🌦️</span>
        <div>
          <h1 className="text-base font-medium text-foreground">
            {t.header.title}
          </h1>
          <p className="text-sm text-muted-foreground">
            {t.header.subtitle}
          </p>
        </div>
      </div>

      <div className="text-center">
        <div className="text-base font-semibold text-foreground">
          {central.headline}
        </div>
        <div className="mt-1 text-sm text-muted-foreground">
          <span style={{ color: SOURCE_COLORS.era5 }} className="font-medium">
            {central.sources.era5}
          </span>
          <span className="mx-1">{central.sources.era5Suffix}</span>
          <span className="mx-1.5 text-muted-foreground/60">—</span>
          <span style={{ color: SOURCE_COLORS.arome }} className="font-medium">
            {central.sources.arome}
          </span>
          <span className="mx-1">{central.sources.aromeSuffix}</span>
          <span className="mx-1.5 text-muted-foreground/60">—</span>
          <span style={{ color: SOURCE_COLORS.graphcast }} className="font-medium">
            {central.sources.graphcast}
          </span>
          <span className="mx-1">{central.sources.graphcastSuffix}</span>
        </div>
      </div>

      <div className="flex items-center justify-end gap-3">
        <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <Clock className="h-3.5 w-3.5" />
          <span className="font-medium tabular-nums text-foreground">
            {time}
          </span>
          <span>·</span>
          <span>{utcLabel}</span>
        </span>

        <DataSourceToggle />

        <ModeToggle />

        <LanguageSwitcher />
      </div>
    </header>
  )
}
