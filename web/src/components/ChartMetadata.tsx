import type { Chart } from "@/lib/types";

export function ChartMetadata({ chart }: { chart: Chart }) {
  const when = new Date(chart.datetime_utc);
  const rows: [string, React.ReactNode][] = [
    ["Cast at", when.toLocaleString()],
    ["Location", chart.location.place],
    ["Lagna", `${chart.lagna.sign} ${chart.lagna.degree.toFixed(1)}°`],
    ["Lagna lord", `${chart.lagna.lord} (${chart.lagna.lord_state})`],
    ["Mahadasha", `${chart.dasha.current_mahadasha} · ${chart.dasha.remaining_years} yrs`],
    ["Ayanamsa", chart.ayanamsa],
    ["House system", chart.house_system],
  ];

  return (
    <div className="glass p-4">
      <h3 className="text-sm text-[var(--accent-gold)]">Chart Metadata</h3>
      <dl className="mt-2 text-sm">
        {rows.map(([label, value], i) => (
          <div
            key={label}
            className={`flex justify-between gap-3 py-1.5 ${
              i < rows.length - 1 ? "border-b border-white/[0.04]" : ""
            }`}
          >
            <dt className="text-[var(--text-muted)]">{label}</dt>
            <dd className="text-right text-[var(--text-main)]">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
