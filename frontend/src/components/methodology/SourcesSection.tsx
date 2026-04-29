import type { MethodologyTranslations } from "@/i18n/methodology.fr"

interface Props {
  data: MethodologyTranslations["sources"]
}

const SOURCE_COLORS = {
  era5: "#1E73E8",
  arome: "#1D9E75",
  graphcast: "#F08C3D",
} as const

export function SourcesSection({ data }: Props) {
  const sources = [
    { ...data.era5, key: "era5" as const },
    { ...data.arome, key: "arome" as const },
    { ...data.graphcast, key: "graphcast" as const },
  ]

  return (
    <section className="mb-7">
      <h2 className="text-base font-medium mb-3">{data.heading}</h2>
      <div className="space-y-3">
        {sources.map((source) => (
          <div
            key={source.key}
            className="bg-card border border-border rounded-lg p-4"
            style={{ borderLeft: `3px solid ${SOURCE_COLORS[source.key]}` }}
          >
            <div className="flex justify-between items-baseline mb-2">
              <div>
                <span
                  className="text-[15px] font-medium"
                  style={{ color: SOURCE_COLORS[source.key] }}
                >
                  {source.name}
                </span>
                <span className="ml-2 text-xs text-muted-foreground">
                  {source.tag}
                </span>
              </div>
              <span className="text-[11px] text-muted-foreground/70">
                {source.provider}
              </span>
            </div>
            <p className="text-[13px] leading-[1.6] text-muted-foreground mb-2">
              {source.description}
            </p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-3 text-xs">
              {source.meta.map((m) => (
                <div key={m.label}>
                  <div className="text-muted-foreground/70">{m.label}</div>
                  <div
                    className={
                      "highlight" in m && m.highlight
                        ? "text-[#5DCAA5] font-medium"
                        : "text-foreground"
                    }
                  >
                    {m.value}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
