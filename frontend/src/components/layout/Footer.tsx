import { Link, useLocation } from "react-router-dom"
import { useT } from "@/i18n"
import { applyOffsetPlaceholder } from "@/lib/timezone"
export function Footer() {
  const { t } = useT()
  const location = useLocation()
  const isEn = location.pathname.startsWith("/en")
  const methodologyPath = isEn ? "/en/methodology" : "/fr/methodologie"
  const methodologyLabel = isEn ? "Methodology" : "Méthodologie"
  const era5Text = applyOffsetPlaceholder(t.footer.sources.era5)
  const graphcastText = applyOffsetPlaceholder(t.footer.sources.graphcast)
  const aromeText = applyOffsetPlaceholder(t.footer.sources.arome)
  const maeText = applyOffsetPlaceholder(t.footer.sources.mae)
  return (
    <footer className="rounded-md border border-border bg-card px-5 py-4">
      <div className="space-y-1 text-sm leading-relaxed">
        <div className="flex gap-3">
          <span className="min-w-[88px] font-medium text-emerald-600 dark:text-emerald-400">ERA5</span>
          <span className="text-muted-foreground">{era5Text}</span>
        </div>
        <div className="flex gap-3">
          <span className="min-w-[88px] font-medium text-orange-500 dark:text-orange-400">GraphCast</span>
          <span className="text-muted-foreground">{graphcastText}</span>
        </div>
        <div className="flex gap-3">
          <span className="min-w-[88px] font-medium text-blue-500 dark:text-blue-400">AROME</span>
          <span className="text-muted-foreground">{aromeText}</span>
        </div>
        <div className="flex gap-3">
          <span className="min-w-[88px] font-medium text-muted-foreground">MAE</span>
          <span className="text-muted-foreground">{maeText}</span>
        </div>
      </div>
      <div className="mt-3 border-t border-border pt-3"></div>
      {/* Layout 3 colonnes : copyright à gauche, KAEK au centre (lien LinkedIn), liens (V1.0 · Méthodologie · Code source) à droite */}
      {/* grid-cols-[1fr_auto_1fr] : colonnes latérales flexibles (1fr) + centre auto (taille de KAEK) */}
      {/* → KAEK reste centré et le copyright a assez de place pour ne pas wrap */}
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-4 text-xs text-muted-foreground">
        {/* Colonne gauche : copyright */}
        <span className="justify-self-start">{t.footer.copyright}</span>

        {/* Colonne centre : KAEK cliquable vers LinkedIn (sans emoji, comme demandé) */}
        <a
          href="https://www.linkedin.com/in/kadechola/"
          target="_blank"
          rel="noopener noreferrer"
          className="justify-self-center text-blue-500 hover:underline"
          aria-label="LinkedIn de Adechola Emile Kouande"
        >
          KAEK
        </a>

        {/* Colonne droite : version, méthodologie, code source */}
        <span className="flex items-center gap-2 justify-self-end">
          <span>{t.footer.version}</span>
          <span>·</span>
          <Link to={methodologyPath} className="text-blue-500 hover:underline">{methodologyLabel}</Link>
          <span>·</span>
          <a href="https://github.com/kouande/meteo_ia_france" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">{t.footer.sourceCode}</a>
        </span>
      </div>
    </footer>
  )
}
