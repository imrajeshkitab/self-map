import type { Chart, PlanetName } from "@/lib/types";
import { ordinal } from "@/lib/utils";

const ORDER: PlanetName[] = [
  "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu",
];

const STATE_LABEL = {
  exalted:     { tag: "Exalted",     symbol: "⭐" },
  debilitated: { tag: "Debilitated", symbol: "⚠️" },
  own:         { tag: "Own Sign",    symbol: "🏠" },
  neutral:     { tag: "Neutral",     symbol: "✦"  },
} as const;

const REL_LABEL = {
  friend:  { tag: "Friend's sign",  cls: "bg-[rgba(134,239,172,0.12)] text-[#86efac]" },
  enemy:   { tag: "Enemy's sign",   cls: "bg-[rgba(248,113,113,0.12)] text-[#f87171]" },
  neutral: { tag: "Neutral sign",   cls: "bg-white/5 text-[var(--text-muted)]"        },
  own:     { tag: "Own sign",       cls: "bg-[rgba(212,175,55,0.12)] text-[var(--accent-gold)]" },
} as const;

export function CosmicWeather({ chart }: { chart: Chart }) {
  const sorted = ORDER
    .map((n) => chart.planets.find((p) => p.name === n))
    .filter(Boolean) as NonNullable<ReturnType<typeof chart.planets.find>>[];

  return (
    <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
      {sorted.map((p) => {
        const st = STATE_LABEL[p.state];
        const rel = REL_LABEL[p.relation] ?? REL_LABEL.neutral;
        return (
          <div key={p.name} className="glass flex items-start justify-between gap-3 p-3 text-sm">
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-medium text-[var(--text-main)]">{p.name}</span>
                {p.retrograde && (
                  <span className="rounded-full bg-[rgba(248,113,113,0.12)] px-1.5 py-[1px] text-[0.6rem] font-bold tracking-widest text-[#f87171]">
                    RETRO
                  </span>
                )}
                {p.combust && (
                  <span className="rounded-full bg-[rgba(212,175,55,0.12)] px-1.5 py-[1px] text-[0.6rem] font-bold tracking-widest text-[var(--accent-gold)]">
                    COMBUST
                  </span>
                )}
              </div>
              <div className="mt-1 text-xs text-[var(--text-muted)]">
                in <strong className="text-[var(--text-main)]">{p.sign}</strong> · {ordinal(p.house)} house · {p.degree.toFixed(1)}°
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-[var(--text-muted)]">
                <span>
                  {p.nakshatra} (pada {p.pada})
                </span>
                <span>·</span>
                <span>{p.avastha}</span>
                <span>·</span>
                <span className={`rounded-full px-2 py-[1px] text-[0.65rem] tracking-wide ${rel.cls}`}>
                  {rel.tag}
                </span>
              </div>
            </div>
            <span
              className="whitespace-nowrap rounded-md bg-white/5 px-2 py-1 text-xs"
              title={st.tag}
            >
              {st.symbol} {st.tag}
            </span>
          </div>
        );
      })}
    </div>
  );
}
