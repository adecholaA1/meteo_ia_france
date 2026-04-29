import type { MethodologyTranslations } from "@/i18n/methodology.fr"

interface Props {
  data: MethodologyTranslations["limitations"]
}

export function LimitationsSection({ data }: Props) {
  return (
    <section className="mb-7">
      <h2 className="text-base font-medium mb-3">{data.heading}</h2>
      <div className="bg-card border border-border rounded-lg p-4 md:p-5">
        <div className="grid grid-cols-[24px_1fr] gap-y-2.5 gap-x-3 text-[13px] leading-[1.6]">
          {data.items.map((item, idx) => (
            <div key={idx} className="contents">
              <div className="text-[#EF9F27] font-medium">{idx + 1}.</div>
              <div>
                <span className="text-foreground font-medium">{item.title}</span>
                <span className="text-muted-foreground"> {item.description}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
