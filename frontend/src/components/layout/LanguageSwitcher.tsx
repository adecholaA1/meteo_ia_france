// ═══════════════════════════════════════════════════════════════════════
//  Composant LanguageSwitcher
//  Affiche 2 boutons "FR" et "EN" dans le header
//  Clic sur FR → navigue vers /fr | Clic sur EN → navigue vers /en
//  Le bouton actif (correspondant à la langue courante) est mis en avant
// ═══════════════════════════════════════════════════════════════════════

import { useNavigate } from "react-router-dom"
import { useT, type Locale } from "@/i18n"

export function LanguageSwitcher() {
  const navigate = useNavigate()
  const { locale, t } = useT()

  const switchTo = (newLocale: Locale) => {
    if (newLocale === locale) return  // déjà sur la bonne langue
    navigate(`/${newLocale}`)
  }

  return (
    <div
      className="flex items-center gap-1 rounded-md border border-slate-200 bg-white p-0.5"
      role="group"
      aria-label={t.a11y.languageSwitcher}
    >
      <button
        onClick={() => switchTo("fr")}
        className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
          locale === "fr"
            ? "bg-slate-900 text-white"
            : "text-slate-600 hover:bg-slate-100"
        }`}
        aria-pressed={locale === "fr"}
      >
        FR
      </button>
      <button
        onClick={() => switchTo("en")}
        className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
          locale === "en"
            ? "bg-slate-900 text-white"
            : "text-slate-600 hover:bg-slate-100"
        }`}
        aria-pressed={locale === "en"}
      >
        EN
      </button>
    </div>
  )
}
