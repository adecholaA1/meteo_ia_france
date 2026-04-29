import type { MethodologyTranslations } from "@/i18n/methodology.fr"

interface Props {
  data: MethodologyTranslations["variables"]
}

export function VariablesSection({ data }: Props) {
  return (
    <section className="mb-7">
      <h2 className="text-base font-medium mb-3">{data.heading}</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {data.items.map((item) => (
          <div
            key={item.code}
            className="bg-card border border-border rounded-lg p-3.5"
          >
            <div className="flex justify-between items-baseline mb-1.5">
              <span className="text-sm font-medium">
                {item.emoji} {item.name}
              </span>
              <span className="text-[11px] text-muted-foreground">
                {item.code}
              </span>
            </div>
            <p className="text-xs leading-[1.5] text-muted-foreground mb-1.5">
              {item.description}
            </p>
            <p className="text-[11px] text-muted-foreground/70">
              {item.range}
            </p>
          </div>
        ))}
      </div>
    </section>
  )
}
