import { Header } from "@/components/layout/Header"
import { Footer } from "@/components/layout/Footer"
import { ChartCard } from "@/components/charts/ChartCard"
import { MaeTableCard } from "@/components/charts/MaeTableCard"
import { FranceMap } from "@/components/map/FranceMap"
import { ZoomDialog } from "@/components/zoom/ZoomDialog"
import { useT } from "@/i18n"
import { TimeFilterProvider } from "@/contexts/TimeFilterContext"
import { ZoomProvider } from "@/contexts/ZoomContext"
import {
  SelectedCityProvider,
  useSelectedCity,
} from "@/contexts/SelectedCityContext"
import { useStaticData } from "@/hooks/useStaticData"

/**
 * Composant interne qui consomme le SelectedCityContext.
 * Doit être enfant du <SelectedCityProvider> pour pouvoir appeler useSelectedCity().
 */
function DashboardContent() {
  const { t } = useT()
  const { loading, error } = useStaticData()
  const { selectedCity, chartsBandRef } = useSelectedCity()

  return (
    <>
      <div className="min-h-screen bg-background p-4 space-y-3">
        <Header />
        {loading && (
          <div className="rounded-md border border-border bg-card p-12 text-center text-muted-foreground">
            <p className="text-sm">⏳ {t.states.loading}</p>
          </div>
        )}
        {error && (
          <div className="rounded-md border border-destructive/30 bg-destructive/10 p-8 text-center text-destructive">
            <p className="font-medium text-sm">❌ {t.states.error}</p>
            <p className="text-xs mt-2 font-mono">{error}</p>
          </div>
        )}
        {!loading && !error && (
          <>
            {/* ═══════════════════════════════════════════════════════════ */}
            {/* BANDE 1 : Carte France (2/3) + Tableau MAE (1/3)           */}
            {/* min-h augmenté pour que carte + MAE soient bien visibles   */}
            {/* items-stretch pour que MAE s'aligne sur la hauteur carte   */}
            {/* ═══════════════════════════════════════════════════════════ */}
            <div className="grid grid-cols-3 gap-3 items-stretch min-h-[480px]">
              {/* Carte 2/3 — Leaflet avec heatmap 2925 points */}
              <div className="col-span-2 h-full">
                <FranceMap />
              </div>
              {/* MAE 1/3 — h-full pour s'étirer à la hauteur de la carte */}
              <div className="col-span-1 h-full">
                <MaeTableCard />
              </div>
            </div>
            {/* ═══════════════════════════════════════════════════════════ */}
            {/* BANDE 2 : 6 ChartCards (3 colonnes × 2 lignes)            */}
            {/* 🆕 PHASE B.3 — ref attachée pour le scroll auto            */}
            {/* 🆕 PHASE B.3 — cityName={selectedCity.name} dynamique      */}
            {/* ═══════════════════════════════════════════════════════════ */}
            <div ref={chartsBandRef} className="grid grid-cols-3 gap-3 scroll-mt-4">
              <ChartCard variable="t2m_celsius" cityName={selectedCity.name} />
              <ChartCard variable="wind_speed_10m_ms" cityName={selectedCity.name} />
              <ChartCard variable="wind_direction_10m_deg" cityName={selectedCity.name} />
              <ChartCard variable="msl_hpa" cityName={selectedCity.name} />
              <ChartCard variable="tp_6h_mm" cityName={selectedCity.name} />
              <ChartCard variable="toa_wm2" cityName={selectedCity.name} />
            </div>
          </>
        )}
        <Footer />
      </div>
      <ZoomDialog />
    </>
  )
}

export function Dashboard() {
  return (
    <TimeFilterProvider defaultRange="7d">
      <ZoomProvider>
        <SelectedCityProvider>
          <DashboardContent />
        </SelectedCityProvider>
      </ZoomProvider>
    </TimeFilterProvider>
  )
}
