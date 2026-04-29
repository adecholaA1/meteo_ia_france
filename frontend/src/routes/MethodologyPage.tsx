import { Link, useLocation } from "react-router-dom"
import { methodologyFr } from "@/i18n/methodology.fr"
import { methodologyEn } from "@/i18n/methodology.en"
import { AboutSection } from "@/components/methodology/AboutSection"
import { GlossarySection } from "@/components/methodology/GlossarySection"
import { VariablesSection } from "@/components/methodology/VariablesSection"
import { SourcesSection } from "@/components/methodology/SourcesSection"
import { ComparisonTable } from "@/components/methodology/ComparisonTable"
import { LimitationsSection } from "@/components/methodology/LimitationsSection"
import { RoadmapSection } from "@/components/methodology/RoadmapSection"
import { TechStackSection } from "@/components/methodology/TechStackSection"

export function MethodologyPage() {
  const location = useLocation()
  const isEn = location.pathname.startsWith("/en")
  const t = isEn ? methodologyEn : methodologyFr
  const dashboardPath = isEn ? "/en" : "/fr"

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="max-w-4xl mx-auto px-4 md:px-8 py-6 md:py-10">
        {/* Lien retour */}
        <Link
          to={dashboardPath}
          className="text-[13px] text-muted-foreground hover:text-foreground transition-colors inline-block mb-3"
        >
          {t.backToDashboard}
        </Link>

        {/* En-tête */}
        <header className="border-b border-border pb-4 mb-7">
          <div className="flex items-center gap-2.5 mb-1.5">
            <span className="text-2xl">🌦️</span>
            <h1 className="text-[22px] font-medium m-0">{t.pageTitle}</h1>
          </div>
          <p className="text-sm text-muted-foreground m-0">{t.pageSubtitle}</p>
        </header>

        {/* 8 sections */}
        <AboutSection data={t.about} />
        <GlossarySection data={t.glossary} />
        <VariablesSection data={t.variables} />
        <SourcesSection data={t.sources} />
        <ComparisonTable data={t.comparison} />
        <LimitationsSection data={t.limitations} />
        <RoadmapSection data={t.roadmap} />
        <TechStackSection data={t.architecture} />
      </div>
    </div>
  )
}
