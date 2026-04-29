// ═══════════════════════════════════════════════════════════════════════
//  Formatage des nombres selon la locale (FR / EN)
//  - FR : "1 016,25" (espace insécable, virgule décimale)
//  - EN : "1,016.25" (virgule de milliers, point décimal)
// ═══════════════════════════════════════════════════════════════════════

import type { Locale } from "./timezone"

/**
 * Formate un nombre selon la locale, avec un nombre de décimales contrôlé.
 * Renvoie un fallback (par défaut "—") si la valeur est null/NaN.
 */
export function formatNumber(
  value: number | null | undefined,
  locale: Locale = "fr",
  decimals: number = 2,
  fallback: string = "—"
): string {
  if (value === null || value === undefined || isNaN(value)) {
    return fallback
  }

  return new Intl.NumberFormat(locale === "fr" ? "fr-FR" : "en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

/**
 * Formate une valeur numérique avec son unité.
 * Exemple : 12.45 → "12,45 °C" (FR) ou "12.45 °C" (EN)
 */
export function formatValueWithUnit(
  value: number | null | undefined,
  unit: string,
  locale: Locale = "fr",
  decimals: number = 2,
  fallback: string = "—"
): string {
  if (value === null || value === undefined || isNaN(value)) {
    return fallback
  }
  return `${formatNumber(value, locale, decimals)} ${unit}`
}

/**
 * Formate une coordonnée GPS (latitude ou longitude).
 * Exemple : 48.75 → "48,75°N" (FR) ou "48.75°N" (EN)
 */
export function formatCoordinate(
  value: number,
  type: "lat" | "lon",
  locale: Locale = "fr"
): string {
  const direction = type === "lat" ? (value >= 0 ? "N" : "S") : value >= 0 ? "E" : "W"
  const absValue = Math.abs(value)
  return `${formatNumber(absValue, locale, 2)}°${direction}`
}

/**
 * Formate un entier avec séparateur de milliers selon la locale.
 * Exemple : 2925 → "2 925" (FR) ou "2,925" (EN)
 */
export function formatInteger(value: number, locale: Locale = "fr"): string {
  return new Intl.NumberFormat(locale === "fr" ? "fr-FR" : "en-US", {
    maximumFractionDigits: 0,
  }).format(value)
}

// ═══════════════════════════════════════════════════════════════════════
//  ALIAS pour rétrocompatibilité avec l'ancien nom utilisé partout
// ═══════════════════════════════════════════════════════════════════════
export const formatNumberFr = (
  value: number | null | undefined,
  decimals: number = 2,
  fallback: string = "—"
) => formatNumber(value, "fr", decimals, fallback)
