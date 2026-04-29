import type { MethodologyTranslations } from "@/i18n/methodology.fr"

interface Props {
  data: MethodologyTranslations["about"]
}

export function AboutSection({ data }: Props) {
  return (
    <section className="mb-7">
      <h2 className="text-base font-medium mb-3">{data.heading}</h2>
      <p className="text-[13px] leading-[1.7] text-muted-foreground">
        {data.paragraph}
      </p>
    </section>
  )
}
