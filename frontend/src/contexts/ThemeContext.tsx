// ═══════════════════════════════════════════════════════════════════════
//  Context React pour la gestion du thème (light / dark / system)
//  - Charge le thème depuis localStorage au démarrage
//  - Surveille les changements de préférence système (matchMedia)
//  - Applique automatiquement la classe "dark" sur <html>
// ═══════════════════════════════════════════════════════════════════════

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react"
import {
  type Theme,
  getStoredTheme,
  setStoredTheme,
  resolveTheme,
  applyThemeToDom,
} from "@/lib/theme"

interface ThemeContextValue {
  theme: Theme
  resolvedTheme: "light" | "dark"
  setTheme: (theme: Theme) => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => getStoredTheme())
  const [resolvedTheme, setResolvedTheme] = useState<"light" | "dark">(() =>
    resolveTheme(getStoredTheme())
  )

  // Applique le thème au DOM à chaque changement
  useEffect(() => {
    const resolved = resolveTheme(theme)
    setResolvedTheme(resolved)
    applyThemeToDom(resolved)
  }, [theme])

  // Surveille les changements système (utile si theme === "system")
  useEffect(() => {
    if (theme !== "system") return

    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)")
    const handleChange = () => {
      const resolved = resolveTheme("system")
      setResolvedTheme(resolved)
      applyThemeToDom(resolved)
    }

    mediaQuery.addEventListener("change", handleChange)
    return () => mediaQuery.removeEventListener("change", handleChange)
  }, [theme])

  const setTheme = (newTheme: Theme) => {
    setStoredTheme(newTheme)
    setThemeState(newTheme)
  }

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext)
  if (!ctx) {
    throw new Error("useTheme doit être utilisé à l'intérieur de <ThemeProvider>")
  }
  return ctx
}
