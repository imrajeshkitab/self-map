import { PLANET_ABBR, SIGNS, SIGN_POS } from "@/lib/utils";
import type { Chart, Planet } from "@/lib/types";

/**
 * South-Indian style 4×4 chart grid. Each sign occupies a fixed cell;
 * the centre 2×2 holds a label.
 */
export function PrashnaChart({ chart, label = "PRASHNA" }: { chart: Chart; label?: string }) {
  const lagnaSign = chart.lagna.sign;
  const bySign: Record<string, Planet[]> = {};
  chart.planets.forEach((p) => {
    if (!bySign[p.sign]) bySign[p.sign] = [];
    bySign[p.sign].push(p);
  });

  return (
    <div className="chart-grid">
      {SIGNS.map((sign) => {
        const [row, col] = SIGN_POS[sign];
        const house = chart.houses.find((h) => h.sign === sign);
        const planets = bySign[sign] ?? [];
        return (
          <div
            key={sign}
            className={`chart-cell${sign === lagnaSign ? " has-lagna" : ""}`}
            style={{ gridRow: row, gridColumn: col }}
          >
            <div className="cell-house">H{house?.number}</div>
            <div className="cell-sign">{sign}</div>
            <div className="cell-planets">
              {planets.map((p) => {
                const tags: string[] = [];
                if (p.retrograde) tags.push("R");
                if (p.combust) tags.push("C");
                return (
                  <span
                    key={p.name}
                    className={`cell-planet ${p.state}`}
                    title={`${p.name} · ${p.state}`}
                  >
                    {PLANET_ABBR[p.name]}
                    {tags.length > 0 && <sup>{tags.join("")}</sup>}
                  </span>
                );
              })}
            </div>
          </div>
        );
      })}
      <div
        className="chart-cell center"
        style={{ gridRow: "2 / span 2", gridColumn: "2 / span 2" }}
      >
        {label}
      </div>
    </div>
  );
}
