import { useMemo, useState } from "react"
import { MapContainer, TileLayer, CircleMarker, Marker, Tooltip as LeafletTooltip } from "react-leaflet"
import L from "leaflet"
import { ZoomIn } from "lucide-react"

import { useT } from "@/i18n"
import {
  SOURCE_COLORS,
  VARIABLE_METADATA,
  getHeatmapColor,
} from "@/lib/colorScales"
import { formatNumber } from "@/lib/numberFormat"
import { formatTooltipDate } from "@/lib/timezone"
import { useZoom } from "@/contexts/ZoomContext"
import { useSelectedCity } from "@/contexts/SelectedCityContext"
import { useCityHeatmap } from "@/hooks/useCityHeatmap"
import type { SourceName, VariableName } from "@/types/forecast"
import type { FrenchCity } from "@/lib/franceCities"

import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

interface FranceMapProps {
  isZoomed?: boolean
}


// Top 10 villes les plus peuplées de France métropolitaine
// (label permanent affiché en plus du tooltip au survol)
const TOP_10_CITIES = new Set([
  "Paris", "Marseille", "Lyon", "Toulouse", "Nice",
  "Nantes", "Strasbourg", "Montpellier", "Bordeaux", "Lille",
])


// Icône 📍 pour signaler les 10 plus grandes villes
const PIN_ICON = L.divIcon({
  className: "city-pin-icon",
  html: '<div style="font-size: 18px; line-height: 1; transform: translateY(-9px);">📍</div>',
  iconSize: [20, 20],
  iconAnchor: [10, 18],
})

// Toutes les variables disponibles dans la carte
const MAP_VARIABLES: VariableName[] = [
  "t2m_celsius",
  "wind_speed_10m_ms",
  "wind_direction_10m_deg",
  "msl_hpa",
  "tp_6h_mm",
  "toa_wm2",
]

export function FranceMap({ isZoomed = false }: FranceMapProps) {
  const { t, locale } = useT()
  const { openZoom } = useZoom()

  // 🆕 PHASE B.6 — Récupération du setter de ville et de la ref pour le scroll
  const { setSelectedCity, chartsBandRef } = useSelectedCity()

  const [source, setSource] = useState<SourceName>("arome")
  const [variable, setVariable] = useState<VariableName>("t2m_celsius")
  const [timestamp, setTimestamp] = useState<string | null>(null)

  const { loading, error, cityPoints, availableTimestamps } = useCityHeatmap(
    variable,
    source,
    timestamp
  )

  const meta = VARIABLE_METADATA[variable]

  // Calcul de la couleur de chaque point ville selon le gradient
  const points = useMemo(() => {
    return cityPoints.map((p) => ({
      ...p,
      color: getHeatmapColor(variable, p.source_value),
    }))
  }, [cityPoints, variable])

  // 🆕 PHASE B.6 — Gestion du clic sur une ville (CircleMarker ou Pin)
  // 1. Met à jour le context (toutes les ChartCards refetchent automatiquement)
  // 2. Scrolle vers la bande des charts (Option B : début de bande)
  const handleCityClick = (city: FrenchCity) => {
    setSelectedCity(city)
    // setTimeout 100ms : laisse React mettre à jour le state avant de scroller
    setTimeout(() => {
      chartsBandRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      })
    }, 100)
  }

  return (
    <div className={`rounded-md ${isZoomed ? "" : "border border-border"} bg-card p-3 flex flex-col h-full`}>
      {/* Header — titre + 3 sélecteurs + zoom */}
      <div className="flex items-start justify-between mb-2 gap-2 flex-shrink-0">
        {!isZoomed && (
          <div className="min-w-0 flex-1">
            <div className="text-sm font-medium text-foreground leading-tight">
              {t.franceMap.title}
            </div>
            <div className="text-[12px] text-muted-foreground mt-0.5 flex items-center gap-3">
              <span>{t.franceMap.subtitle}</span>
              <span className="flex items-center gap-1">
                <span style={{ fontSize: "12px" }}>📍</span>
                <span>{t.franceMap.topCitiesLegend}</span>
              </span>
            </div>
          </div>
        )}
        {isZoomed && <div className="flex-1" />}

        <div className="flex items-center gap-1.5 flex-shrink-0 flex-wrap justify-end">
          {/* Sélecteur Source */}
          <Select value={source} onValueChange={(v) => setSource(v as SourceName)}>
            <SelectTrigger className="h-7 text-xs px-2 gap-1 w-auto">
              <SelectValue />
            </SelectTrigger>
            <SelectContent side="top" sideOffset={6} align="start" className="max-h-[260px] overflow-y-auto">
              <SelectItem value="arome">
                <span style={{ color: SOURCE_COLORS.arome }}>● </span>
                {t.franceMap.sources.arome}
              </SelectItem>
              <SelectItem value="graphcast">
                <span style={{ color: SOURCE_COLORS.graphcast }}>● </span>
                {t.franceMap.sources.graphcast}
              </SelectItem>
            </SelectContent>
          </Select>

          {/* Sélecteur Variable */}
          <Select value={variable} onValueChange={(v) => setVariable(v as VariableName)}>
            <SelectTrigger className="h-7 text-xs px-2 gap-1 w-auto">
              <SelectValue />
            </SelectTrigger>
            <SelectContent side="top" sideOffset={6} align="start" className="max-h-[260px] overflow-y-auto">
              {MAP_VARIABLES.map((v) => (
                <SelectItem key={v} value={v}>
                  {t.variables[v]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Sélecteur Timestamp */}
          {availableTimestamps.length > 0 && (
            <Select
              value={timestamp || availableTimestamps[0]}
              onValueChange={(v) => setTimestamp(v)}
            >
              <SelectTrigger className="h-7 text-xs px-2 gap-1 w-auto">
                <SelectValue />
              </SelectTrigger>
              <SelectContent side="top" sideOffset={6} align="start" className="max-h-[260px] overflow-y-auto">
                {availableTimestamps.map((ts) => (
                  <SelectItem key={ts} value={ts}>
                    {formatTooltipDate(ts, locale)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          {/* Bouton zoom */}
          {!isZoomed && (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => openZoom("map")}
            >
              <ZoomIn className="h-3.5 w-3.5" />
            </Button>
          )}
        </div>
      </div>

      {/* Carte — flex-1 pour prendre toute la hauteur */}
      <div className="flex-1 relative rounded overflow-hidden border border-border bg-muted/10">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/80 z-[1000]">
            <p className="text-xs text-muted-foreground">⏳ {t.franceMap.loading}</p>
          </div>
        )}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center z-[1000]">
            <p className="text-xs text-destructive">⚠️ {error}</p>
          </div>
        )}
        {!loading && !error && points.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center z-[1000]">
            <p className="text-xs text-muted-foreground">{t.franceMap.noData}</p>
          </div>
        )}

        <MapContainer
          center={[46.6, 2.5]}
          zoom={5.3}
          zoomSnap={0.1}
          zoomDelta={0.5}
          minZoom={4}
          maxZoom={9}
          style={{ width: "100%", height: "100%", background: "#0A1628" }}
          scrollWheelZoom={isZoomed}
          attributionControl={false}
        >
          {/* Fond de carte sobre */}
          <TileLayer
            url="https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://stadiamaps.com/" target="_blank">Stadia Maps</a> &copy; <a href="https://openmaptiles.org/" target="_blank">OpenMapTiles</a> &copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a>'
            maxZoom={20}
          />

          {/* 2 925 points colorés — 🆕 PHASE B.6 : eventHandlers click ajouté + cursor pointer */}
          {points.filter((p) => !TOP_10_CITIES.has(p.name)).map((p, idx) => (
            <CircleMarker
              key={`hover-${idx}`}
              center={[p.lat, p.lon]}
              radius={14}
              pathOptions={{
                color: "transparent",
                fillColor: "transparent",
                fillOpacity: 0,
                weight: 0,
                interactive: true,
                bubblingMouseEvents: false,
                className: "cursor-pointer",
              }}
              eventHandlers={{
                click: () => handleCityClick({ name: p.name, lat: p.lat, lon: p.lon }),
              }}
            >
              {/* Tooltip riche au survol — zone de capture invisible élargie */}
              <LeafletTooltip direction="top" offset={[0, -8]} opacity={1} sticky>
                <div style={{ fontSize: "12.5px", lineHeight: "1.5" }}>
                  <div style={{ fontWeight: 700, marginBottom: "4px", color: "#1a1a1a" }}>
                    {p.name} ({p.lat.toFixed(2)}°N · {p.lon.toFixed(2)}°E)
                  </div>
                  <div>
                    <span style={{ color: SOURCE_COLORS[source] }}>● </span>
                    {source === "arome" ? "AROME" : "GraphCast"} :{" "}
                    <strong>
                      {formatNumber(p.source_value, locale, meta.decimals)} {meta.unit}
                    </strong>
                  </div>
                  <div>
                    <span style={{ color: SOURCE_COLORS.era5 }}>● </span>
                    ERA5 ({t.franceMap.legend.truthLabel}) :{" "}
                    <strong>
                      {formatNumber(p.era5_value, locale, meta.decimals)} {meta.unit}
                    </strong>
                  </div>
                  <div style={{ marginTop: "2px", fontStyle: "italic", color: "#888" }}>
                    {t.franceMap.legend.error} :{" "}
                    {formatNumber(Math.abs(p.error), locale, meta.decimals)} {meta.unit}
                  </div>
                  {/* 🆕 PHASE B.6 — Indication clic */}
                  <div style={{ marginTop: "4px", fontSize: "11px", color: "#0066cc", fontWeight: 600 }}>
                    👆 {locale === "fr" ? "Cliquer pour voir les courbes" : "Click to see charts"}
                  </div>
                </div>
              </LeafletTooltip>
            </CircleMarker>
          ))}

          {/* Cercles VISUELS petits (non-interactive pour ne pas bloquer le hover) */}
          {points.filter((p) => !TOP_10_CITIES.has(p.name)).map((p, idx) => (
            <CircleMarker
              key={`visual-${idx}`}
              center={[p.lat, p.lon]}
              radius={1.5}
              pathOptions={{
                color: "#FFFFFF",
                fillColor: p.color,
                fillOpacity: 0.95,
                weight: 0.8,
                interactive: false,
              }}
            />
          ))}

          {/* Pins 📍 sur les 10 plus grandes villes — 🆕 PHASE B.6 : eventHandlers click ajouté */}
          {points
            .filter((p) => TOP_10_CITIES.has(p.name))
            .map((p, idx) => (
              <Marker
                key={`pin-${idx}`}
                position={[p.lat, p.lon]}
                icon={PIN_ICON}
                eventHandlers={{
                  click: () => handleCityClick({ name: p.name, lat: p.lat, lon: p.lon }),
                }}
              >
                <LeafletTooltip direction="top" offset={[0, -16]} opacity={1}>
                  <div style={{ fontSize: "12.5px", lineHeight: "1.5" }}>
                    <div style={{ fontWeight: 700, marginBottom: "4px", color: "#1a1a1a" }}>
                      {p.name} ({p.lat.toFixed(2)}°N · {p.lon.toFixed(2)}°E)
                    </div>
                    <div>
                      <span style={{ color: SOURCE_COLORS[source] }}>● </span>
                      {source === "arome" ? "AROME" : "GraphCast"} :{" "}
                      <strong>
                        {formatNumber(p.source_value, locale, meta.decimals)} {meta.unit}
                      </strong>
                    </div>
                    <div>
                      <span style={{ color: SOURCE_COLORS.era5 }}>● </span>
                      ERA5 ({t.franceMap.legend.truthLabel}) :{" "}
                      <strong>
                        {formatNumber(p.era5_value, locale, meta.decimals)} {meta.unit}
                      </strong>
                    </div>
                    <div style={{ marginTop: "2px", fontStyle: "italic", color: "#888" }}>
                      {t.franceMap.legend.error} :{" "}
                      {formatNumber(Math.abs(p.error), locale, meta.decimals)} {meta.unit}
                    </div>
                    {/* 🆕 PHASE B.6 — Indication clic */}
                    <div style={{ marginTop: "4px", fontSize: "11px", color: "#0066cc", fontWeight: 600 }}>
                      👆 {locale === "fr" ? "Cliquer pour voir les courbes" : "Click to see charts"}
                    </div>
                  </div>
                </LeafletTooltip>
              </Marker>
            ))}
        </MapContainer>

        {/* Légende couleur en bas à droite */}
</div>
    </div>
  )
}
