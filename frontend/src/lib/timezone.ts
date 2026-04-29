// ═══════════════════════════════════════════════════════════════════════
//  Utilitaires Europe/Paris avec gestion DST automatique (UTC+1/UTC+2)
//  Tous les formats sont localisés selon la langue active (FR/EN).
// ═══════════════════════════════════════════════════════════════════════

const PARIS_TIMEZONE = "Europe/Paris"

export type Locale = "fr" | "en"

/**
 * Retourne le décalage UTC de Paris pour une date donnée.
 * Renvoie 1 (hiver, UTC+1) ou 2 (été, UTC+2).
 */
export function getParisUtcOffset(date: Date = new Date()): number {
  const utcHour = date.getUTCHours()

  const parisFormatter = new Intl.DateTimeFormat("en-US", {
    timeZone: PARIS_TIMEZONE,
    hour: "2-digit",
    hour12: false,
  })
  const parisHour = parseInt(parisFormatter.format(date), 10)

  let offset = parisHour - utcHour
  if (offset < -12) offset += 24
  if (offset > 12) offset -= 24

  return offset
}

/**
 * Retourne le suffixe UTC dynamique pour la date courante.
 * Exemples : "+1" en hiver, "+2" en été.
 */
export function getCurrentOffsetSuffix(): string {
  const offset = getParisUtcOffset(new Date())
  return offset >= 0 ? `+${offset}` : `${offset}`
}

/**
 * Indique si on est actuellement en heure d'été (UTC+2).
 */
export function isParisDST(date: Date = new Date()): boolean {
  return getParisUtcOffset(date) === 2
}

/**
 * Format heure courte HH:mm pour l'horloge du header.
 * Exemple : "14:32"
 */
export function formatHourMinute(date: Date): string {
  return new Intl.DateTimeFormat("fr-FR", {
    timeZone: PARIS_TIMEZONE,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date)
}

/**
 * Format date complète + heure + UTC pour les tooltips de courbes.
 * Exemples :
 *   FR : "21-04-2026 14:00 UTC+2"
 *   EN : "04-21-2026 2:00 p.m. UTC+2"
 */
export function formatTooltipDate(utcIsoString: string, locale: Locale = "fr"): string {
  const date = new Date(utcIsoString)
  const offset = getParisUtcOffset(date)
  const utcLabel = `UTC${offset >= 0 ? "+" : ""}${offset}`

  if (locale === "fr") {
    const datePart = new Intl.DateTimeFormat("fr-FR", {
      timeZone: PARIS_TIMEZONE,
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    }).format(date).replace(/\//g, "-")

    const timePart = new Intl.DateTimeFormat("fr-FR", {
      timeZone: PARIS_TIMEZONE,
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(date)

    return `${datePart} ${timePart} ${utcLabel}`
  }

  // EN
  const datePart = new Intl.DateTimeFormat("en-US", {
    timeZone: PARIS_TIMEZONE,
    month: "2-digit",
    day: "2-digit",
    year: "numeric",
  }).format(date).replace(/\//g, "-")

  const timePart = new Intl.DateTimeFormat("en-US", {
    timeZone: PARIS_TIMEZONE,
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).format(date).toLowerCase().replace("am", "a.m.").replace("pm", "p.m.")

  return `${datePart} ${timePart} ${utcLabel}`
}

/**
 * Format date courte sans heure pour l'axe X des graphiques.
 * Exemples : FR "19 avr." | EN "Apr 19"
 */
export function formatAxisDate(utcIsoString: string, locale: Locale = "fr"): string {
  const date = new Date(utcIsoString)

  if (locale === "fr") {
    return new Intl.DateTimeFormat("fr-FR", {
      timeZone: PARIS_TIMEZONE,
      day: "2-digit",
      month: "short",
    }).format(date)
  }

  // EN : "Apr 19"
  return new Intl.DateTimeFormat("en-US", {
    timeZone: PARIS_TIMEZONE,
    month: "short",
    day: "2-digit",
  }).format(date)
}

/**
 * Format date pour le sélecteur de date du ControlsBar.
 * Exemples : FR "25/04/2026" | EN "04/25/2026"
 */
export function formatDateSelector(utcIsoString: string, locale: Locale = "fr"): string {
  const date = new Date(utcIsoString)
  return new Intl.DateTimeFormat(locale === "fr" ? "fr-FR" : "en-US", {
    timeZone: PARIS_TIMEZONE,
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(date)
}

/**
 * Remplace le placeholder {offset} dans les chaînes du footer
 * par le décalage UTC courant ("+1" ou "+2").
 */
export function applyOffsetPlaceholder(template: string): string {
  return template.replace(/\{offset\}/g, getCurrentOffsetSuffix())
}
