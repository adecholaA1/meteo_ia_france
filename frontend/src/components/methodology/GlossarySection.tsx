import type { MethodologyTranslations } from "@/i18n/methodology.fr"

interface Props {
  data: MethodologyTranslations["glossary"]
}

export function GlossarySection({ data }: Props) {
  return (
    <section className="mb-7">
      <h2 className="text-base font-medium mb-3">{data.heading}</h2>
      <div className="bg-card border border-border rounded-lg p-4 md:p-5">
        <div className="grid grid-cols-[120px_1fr] md:grid-cols-[130px_1fr] gap-y-2 gap-x-4 text-[13px] leading-[1.6]">
          {data.entries.map((entry) => (
            <div key={entry.term} className="contents">
              <div className="font-medium text-foreground">{entry.term}</div>
              <div className="text-muted-foreground">{entry.definition}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
