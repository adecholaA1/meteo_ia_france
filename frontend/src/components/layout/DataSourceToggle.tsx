// ═══════════════════════════════════════════════════════════════════════
//  Composant DataSourceToggle (étape 10 — micro-étape 4B)
//  Bouton icône qui bascule en live entre :
//    🟢 Mode API runtime (Wifi)  → fetch http://localhost:3001/api/...
//    💾 Mode JSON statique (Database) → fetch /data/sample_forecast.json
//
//  Au clic, useDataSource().toggleDataSource() change le booléen useApi,
//  ce qui déclenche un re-render des hooks useStaticData / useHeatmapData
//  et un nouveau chargement des données dans le mode choisi.
// ═══════════════════════════════════════════════════════════════════════

import { Wifi, Database } from "lucide-react"

import { Button } from "@/components/ui/button"
import { useDataSource } from "@/contexts/DataSourceContext"

export function DataSourceToggle() {
  const { useApi, toggleDataSource } = useDataSource()

  const label = useApi ? "API live" : "JSON statique"
  const tooltip = useApi
    ? "Mode API runtime actif — cliquer pour passer en JSON statique"
    : "Mode JSON statique actif — cliquer pour passer en API runtime"

  return (
    <Button
      variant="outline"
      size="icon"
      className="h-7 w-7"
      onClick={toggleDataSource}
      aria-label={tooltip}
      title={tooltip}
    >
      {useApi ? (
        // Mode API : icône Wifi colorée en vert/bleu (signal "live")
        <Wifi className="h-3.5 w-3.5 text-emerald-500 dark:text-emerald-400" />
      ) : (
        // Mode statique : icône Database neutre
        <Database className="h-3.5 w-3.5 text-muted-foreground" />
      )}
      <span className="sr-only">{label}</span>
    </Button>
  )
}
