// ═══════════════════════════════════════════════════════════════════════
//  Composant ModeToggle
//  Bouton icône (☾ / ☀) qui ouvre un dropdown avec 3 options :
//  Clair / Sombre / Système
// ═══════════════════════════════════════════════════════════════════════

import { Sun, Moon, Monitor } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

import { useTheme } from "@/contexts/ThemeContext"
import { useT } from "@/i18n"

export function ModeToggle() {
  const { theme, setTheme } = useTheme()
  const { t } = useT()

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="icon"
          className="h-7 w-7"
          aria-label={t.a11y.themeSwitcher}
        >
          {/* Soleil visible en light, masqué en dark */}
          <Sun className="h-3.5 w-3.5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          {/* Lune visible en dark, masquée en light */}
          <Moon className="absolute h-3.5 w-3.5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          <span className="sr-only">{t.a11y.themeSwitcher}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-[8rem]">
        <DropdownMenuItem
          onClick={() => setTheme("light")}
          className={theme === "light" ? "bg-accent" : ""}
        >
          <Sun className="mr-2 h-3.5 w-3.5" />
          <span>{t.header.theme.light}</span>
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => setTheme("dark")}
          className={theme === "dark" ? "bg-accent" : ""}
        >
          <Moon className="mr-2 h-3.5 w-3.5" />
          <span>{t.header.theme.dark}</span>
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => setTheme("system")}
          className={theme === "system" ? "bg-accent" : ""}
        >
          <Monitor className="mr-2 h-3.5 w-3.5" />
          <span>{t.header.theme.system}</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
