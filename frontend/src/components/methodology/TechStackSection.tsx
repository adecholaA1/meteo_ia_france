import type { MethodologyTranslations } from "@/i18n/methodology.fr"

interface Props {
  data: MethodologyTranslations["architecture"]
}

export function TechStackSection({ data }: Props) {
  return (
    <section className="mb-7">
      <h2 className="text-base font-medium mb-3">{data.heading}</h2>
      <p className="text-[13px] text-muted-foreground mb-4">{data.intro}</p>
      <div className="space-y-3">
        {data.cards.map((card) => (
          <div
            key={card.title}
            className="bg-card border border-border rounded-lg p-4 md:p-5"
            style={{ borderLeft: `3px solid ${card.color}` }}
          >
            <div
              className="text-[13px] font-medium mb-2.5"
              style={{ color: card.color }}
            >
              {card.title}
            </div>
            <div className="grid grid-cols-[110px_1fr] md:grid-cols-[130px_1fr] gap-y-1.5 gap-x-4 text-[12.5px] leading-[1.6]">
              {card.items.map((item) => (
                <div key={item.label} className="contents">
                  <div className="text-muted-foreground/70">{item.label}</div>
                  <div className="text-muted-foreground">{item.value}</div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
