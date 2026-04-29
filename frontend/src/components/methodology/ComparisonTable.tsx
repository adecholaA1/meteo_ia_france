import type { MethodologyTranslations } from "@/i18n/methodology.fr"

interface Props {
  data: MethodologyTranslations["comparison"]
}

const COLOR_MAP: Record<string, string> = {
  good: "text-[#5DCAA5]",
  warn: "text-[#EF9F27]",
}

function cellClass(color?: string) {
  if (!color) return "text-muted-foreground"
  return COLOR_MAP[color] || "text-muted-foreground"
}

export function ComparisonTable({ data }: Props) {
  return (
    <section className="mb-7">
      <h2 className="text-base font-medium mb-3">{data.heading}</h2>
      <div className="bg-card border border-border rounded-lg overflow-x-auto">
        <table className="w-full text-[12.5px] border-collapse min-w-[640px]">
          <thead>
            <tr className="bg-muted/40 border-b border-border">
              <th className="text-left px-3.5 py-3 font-medium text-muted-foreground w-[180px]">
                {data.headers.criterion}
              </th>
              <th
                className="text-left px-3.5 py-3 font-medium"
                style={{ borderLeft: "3px solid #1E73E8" }}
              >
                <span className="text-[#1E73E8]">{data.headers.era5}</span>
                <span className="block text-[11px] font-normal text-muted-foreground/70 mt-0.5">
                  {data.headers.era5Sub}
                </span>
              </th>
              <th
                className="text-left px-3.5 py-3 font-medium"
                style={{ borderLeft: "3px solid #1D9E75" }}
              >
                <span className="text-[#1D9E75]">{data.headers.arome}</span>
                <span className="block text-[11px] font-normal text-muted-foreground/70 mt-0.5">
                  {data.headers.aromeSub}
                </span>
              </th>
              <th
                className="text-left px-3.5 py-3 font-medium"
                style={{ borderLeft: "3px solid #F08C3D" }}
              >
                <span className="text-[#F08C3D]">{data.headers.graphcast}</span>
                <span className="block text-[11px] font-normal text-muted-foreground/70 mt-0.5">
                  {data.headers.graphcastSub}
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row, idx) => (
              <tr key={idx} className="border-b border-border/40 last:border-0">
                <td className="px-3.5 py-2 text-muted-foreground">{row.criterion}</td>
                <td className={`px-3.5 py-2 ${cellClass((row as any).era5Color)}`}>
                  {row.era5}
                </td>
                <td
                  className={`px-3.5 py-2 ${cellClass((row as any).aromeColor)} ${
                    (row as any).aromeColor === "good" ? "font-medium" : ""
                  }`}
                >
                  {row.arome}
                </td>
                <td className={`px-3.5 py-2 ${cellClass((row as any).graphcastColor)}`}>
                  {row.graphcast}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[11px] text-muted-foreground/70 mt-2 italic">
        {data.legend}
      </p>
    </section>
  )
}
