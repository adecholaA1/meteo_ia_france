import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import 'leaflet/dist/leaflet.css'
import './index.css'
import App from './App.tsx'
import { DataSourceProvider } from '@/contexts/DataSourceContext'

// 🟢 ÉTAPE 10 — TanStack Query
// QueryClient : orchestre tout le cache des requêtes API.
// Une seule instance pour toute l'application.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,      // 5 min : données fraîches sans refetch
      gcTime: 30 * 60 * 1000,        // 30 min : garde en cache après inactivité
      retry: 2,                      // 2 retries automatiques si erreur réseau
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      refetchOnWindowFocus: false,   // pas de refetch au retour sur l'onglet
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <DataSourceProvider>
        <App />
      </DataSourceProvider>
    </QueryClientProvider>
  </StrictMode>
)
