// ═══════════════════════════════════════════════════════════════════════
//  Utilitaires de thème pour Météo IA France
//  Modes supportés : "light" | "dark" | "system"
//  Persistance : localStorage clé "meteo-ia-theme"
// ═══════════════════════════════════════════════════════════════════════

export type Theme = "light" | "dark" | "system"

const STORAGE_KEY = "meteo-ia-theme"

/**
 * Récupère le thème stocké dans localStorage, ou "system" par défaut.
 */
export function getStoredTheme(): Theme {
  if (typeof window === "undefined") return "system"
  const stored = window.localStorage.getItem(STORAGE_KEY)
  if (stored === "light" || stored === "dark" || stored === "system") {
    return stored
  }
  return "system"
}

/**
 * Sauvegarde le thème dans localStorage.
 */
export function setStoredTheme(theme: Theme): void {
  if (typeof window === "undefined") return
  window.localStorage.setItem(STORAGE_KEY, theme)
}

/**
 * Résout "system" en "light" ou "dark" selon les préférences OS.
 */
export function resolveTheme(theme: Theme): "light" | "dark" {
  if (theme !== "system") return theme
  if (typeof window === "undefined") return "light"
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light"
}

/**
 * Applique le thème résolu en ajoutant/enlevant la classe "dark"
 * sur l'élément <html>. Tailwind v4 + shadcn s'appuient dessus.
 */
export function applyThemeToDom(resolvedTheme: "light" | "dark"): void {
  if (typeof window === "undefined") return
  const root = window.document.documentElement
  if (resolvedTheme === "dark") {
    root.classList.add("dark")
  } else {
    root.classList.remove("dark")
  }
}
