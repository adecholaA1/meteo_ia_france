// ═══════════════════════════════════════════════════════════════════════
//  Context React pour les filtres temporels synchronisés
//  Le filtre global en haut + les filtres sur chaque graphique partagent
//  le même state. Un changement sur l'un propage à tous les autres.
// ═══════════════════════════════════════════════════════════════════════

import { createContext, useContext, useState, type ReactNode } from "react"
import type { TimeRange } from "@/types/forecast"

interface TimeFilterContextValue {
  timeRange: TimeRange
  setTimeRange: (range: TimeRange) => void
}

const TimeFilterContext = createContext<TimeFilterContextValue | undefined>(
  undefined
)

interface TimeFilterProviderProps {
  children: ReactNode
  defaultRange?: TimeRange
}

export function TimeFilterProvider({
  children,
  defaultRange = "7d",
}: TimeFilterProviderProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>(defaultRange)

  return (
    <TimeFilterContext.Provider value={{ timeRange, setTimeRange }}>
      {children}
    </TimeFilterContext.Provider>
  )
}

/**
 * Hook pour lire/modifier la période globale.
 * Tous les composants qui appellent ce hook sont synchronisés automatiquement.
 */
export function useTimeFilter() {
  const context = useContext(TimeFilterContext)
  if (!context) {
    throw new Error("useTimeFilter must be used inside a TimeFilterProvider")
  }
  return context
}
