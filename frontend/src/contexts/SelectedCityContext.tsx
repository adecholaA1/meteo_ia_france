// ═══════════════════════════════════════════════════════════════════════
//  Context React pour la ville actuellement sélectionnée sur la carte
//  Permet à la carte (FranceMap) de "piloter" les ChartCards :
//  un clic sur un marker propage la ville à tous les graphiques.
//
//  - selectedCity : ville active (par défaut Paris)
//  - setSelectedCity : change la ville depuis n'importe quel composant
//  - chartsBandRef : ref vers la div contenant les 6 ChartCards
//                    permet à FranceMap de déclencher un scroll auto vers les charts
// ═══════════════════════════════════════════════════════════════════════

import {
  createContext,
  useContext,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from "react"
import type { FrenchCity } from "@/lib/franceCities"

interface SelectedCityContextValue {
  selectedCity: FrenchCity
  setSelectedCity: (city: FrenchCity) => void
  chartsBandRef: RefObject<HTMLDivElement | null>
}

const SelectedCityContext = createContext<SelectedCityContextValue | undefined>(
  undefined
)

// Ville par défaut : Paris (alignée sur l'entrée de FRANCE_CITIES ligne 22)
const DEFAULT_CITY: FrenchCity = { name: "Paris", lat: 48.857, lon: 2.352 }

interface SelectedCityProviderProps {
  children: ReactNode
  defaultCity?: FrenchCity
}

export function SelectedCityProvider({
  children,
  defaultCity = DEFAULT_CITY,
}: SelectedCityProviderProps) {
  const [selectedCity, setSelectedCity] = useState<FrenchCity>(defaultCity)
  const chartsBandRef = useRef<HTMLDivElement>(null)

  return (
    <SelectedCityContext.Provider
      value={{ selectedCity, setSelectedCity, chartsBandRef }}
    >
      {children}
    </SelectedCityContext.Provider>
  )
}

/**
 * Hook pour lire/modifier la ville sélectionnée et accéder à la ref de la bande des charts.
 * Tous les composants qui appellent ce hook sont synchronisés automatiquement.
 */
export function useSelectedCity() {
  const context = useContext(SelectedCityContext)
  if (!context) {
    throw new Error("useSelectedCity must be used inside a SelectedCityProvider")
  }
  return context
}
