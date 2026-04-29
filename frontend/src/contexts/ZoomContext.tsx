// ═══════════════════════════════════════════════════════════════════════
//  Context React pour le mode zoom
//  Gère l'état "quel élément est actuellement affiché en grand au centre"
// ═══════════════════════════════════════════════════════════════════════

import { createContext, useContext, useState, type ReactNode } from "react"
import type { VariableName } from "@/types/forecast"

// Identifiant de l'élément zoomé : null si rien n'est zoomé
export type ZoomTarget =
  | null
  | "map"
  | "mae_table"
  | { type: "chart"; variable: VariableName }

interface ZoomContextValue {
  zoomTarget: ZoomTarget
  openZoom: (target: Exclude<ZoomTarget, null>) => void
  closeZoom: () => void
}

const ZoomContext = createContext<ZoomContextValue | undefined>(undefined)

export function ZoomProvider({ children }: { children: ReactNode }) {
  const [zoomTarget, setZoomTarget] = useState<ZoomTarget>(null)

  const openZoom = (target: Exclude<ZoomTarget, null>) => {
    setZoomTarget(target)
  }

  const closeZoom = () => {
    setZoomTarget(null)
  }

  return (
    <ZoomContext.Provider value={{ zoomTarget, openZoom, closeZoom }}>
      {children}
    </ZoomContext.Provider>
  )
}

export function useZoom() {
  const context = useContext(ZoomContext)
  if (!context) {
    throw new Error("useZoom must be used inside a ZoomProvider")
  }
  return context
}
