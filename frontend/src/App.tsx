// ═══════════════════════════════════════════════════════════════════════
//  Point d'entrée de l'application Météo IA France
//  - Routes /fr et /en (react-router-dom)
//  - Routes /fr/methodologie et /en/methodology (page Méthodologie)
//  - ThemeProvider global
// ═══════════════════════════════════════════════════════════════════════

import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import { ThemeProvider } from "@/contexts/ThemeContext"
import { Dashboard } from "@/routes/Dashboard"
import { MethodologyPage } from "@/routes/MethodologyPage"

function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/fr" replace />} />
          <Route path="/fr" element={<Dashboard />} />
          <Route path="/en" element={<Dashboard />} />
          <Route path="/fr/methodologie" element={<MethodologyPage />} />
          <Route path="/en/methodology" element={<MethodologyPage />} />
          <Route path="*" element={<Navigate to="/fr" replace />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  )
}

export default App
