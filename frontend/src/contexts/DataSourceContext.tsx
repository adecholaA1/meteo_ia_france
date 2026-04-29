/**
 * 🟢 ÉTAPE 10 — DataSourceContext
 *
 * Contexte React qui gère la bascule entre :
 *   🟢 Mode API runtime (TanStack Query → backend Express)
 *   💾 Mode JSON statique (imports build-time)
 *
 * Bascule contrôlée par :
 *   1. Variable env `VITE_USE_API` au build (valeur par défaut)
 *   2. Toggle UI live (override à la volée, état local React)
 *
 * Le contexte expose :
 *   - useApi: boolean (true = mode API, false = mode statique)
 *   - toggleDataSource: () => void
 */

import { createContext, useContext, useState, type ReactNode } from "react"

// Lecture de la variable env Vite — true par défaut si non définie
// Pour passer en mode statique par défaut : VITE_USE_API=false dans .env
const ENV_USE_API = import.meta.env.VITE_USE_API !== "false"

interface DataSourceContextValue {
  useApi: boolean
  toggleDataSource: () => void
  setUseApi: (value: boolean) => void
}

const DataSourceContext = createContext<DataSourceContextValue | null>(null)

export function DataSourceProvider({ children }: { children: ReactNode }) {
  const [useApi, setUseApi] = useState<boolean>(ENV_USE_API)

  const toggleDataSource = () => setUseApi((prev) => !prev)

  return (
    <DataSourceContext.Provider value={{ useApi, toggleDataSource, setUseApi }}>
      {children}
    </DataSourceContext.Provider>
  )
}

/**
 * Hook pour accéder au mode de données courant.
 * Utilisable dans n'importe quel composant enfant du DataSourceProvider.
 */
export function useDataSource() {
  const context = useContext(DataSourceContext)
  if (!context) {
    throw new Error("useDataSource doit être utilisé dans un <DataSourceProvider>")
  }
  return context
}
