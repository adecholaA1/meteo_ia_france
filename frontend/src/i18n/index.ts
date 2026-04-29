// ═══════════════════════════════════════════════════════════════════════
//  Point d'entrée du système i18n
//  Détecte la langue depuis l'URL (/fr ou /en) et expose un hook useT()
// ═══════════════════════════════════════════════════════════════════════

import { useLocation } from "react-router-dom"
import { fr } from "./fr"
import { en } from "./en"
import type { Translations } from "./fr"

export type Locale = "fr" | "en"

const TRANSLATIONS: Record<Locale, Translations> = {
  fr,
  en,
}

/**
 * Hook qui retourne les traductions correspondant à l'URL courante.
 * - URL contient /fr → retourne les traductions FR
 * - URL contient /en → retourne les traductions EN
 * - Sinon (défaut) → retourne FR
 *
 * Usage:
 *   const { t, locale } = useT()
 *   return <h1>{t.header.title}</h1>
 */
export function useT() {
  const location = useLocation()
  const locale: Locale = location.pathname.startsWith("/en") ? "en" : "fr"
  return {
    t: TRANSLATIONS[locale],
    locale,
  }
}

/**
 * Remplace les placeholders {key} dans une chaîne par les valeurs fournies.
 * Ex: interpolate("AROME beats {count}/{total}", { count: 5, total: 5 })
 *     → "AROME beats 5/5"
 */
export function interpolate(
  template: string,
  values: Record<string, string | number>
): string {
  return template.replace(/\{(\w+)\}/g, (_, key) =>
    values[key] !== undefined ? String(values[key]) : `{${key}}`
  )
}
