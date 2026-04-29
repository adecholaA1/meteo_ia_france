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
          <a href="https://github.com/adecholaA1/meteo_ia_france"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center text-foreground hover:opacity-70 transition-opacity"
            title={t.footer.sourceCode}
            aria-label={t.footer.sourceCode}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
            </svg>
          </a>
        </span>
      </div>
    </footer>
  )
}
