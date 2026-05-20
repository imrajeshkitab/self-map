import type { Dasha } from "@/lib/types";

/**
 * 3-tier DBA display: Mahadasha → Antardasha → Pratyantar.
 * Each tier shows the lord, time remaining, and a progress bar.
 */
export function DbaPanel({ dasha }: { dasha: Dasha }) {
  const md = dasha.timeline.find((t) => t.current);
  const ad = dasha.antardasha_timeline.find((t) => t.current);
  const pd = dasha.pratyantar_timeline.find((t) => t.current);

  return (
    <div className="glass p-4">
      <h3 className="text-base text-[var(--accent-gold)]">Vimshottari DBA</h3>
      <p className="mt-1 text-xs italic text-[var(--text-muted)]">
        From Moon&apos;s nakshatra — {dasha.moon_nakshatra}. Three nested timing
        layers: Mahadasha (years) → Antardasha (months) → Pratyantar (days).
      </p>

      <div className="mt-3 flex flex-col gap-2">
        {md && (
          <Tier
            label="MD"
            lord={md.lord}
            total={md.years}
            remaining={dasha.remaining_years}
            unit="yrs"
          />
        )}
        {ad && dasha.antardasha_remaining_years != null && (
          <Tier
            label="AD"
            lord={ad.lord}
            total={ad.years}
            remaining={dasha.antardasha_remaining_years}
            unit="yrs"
          />
        )}
        {pd && dasha.pratyantar_remaining_days != null && (
          <Tier
            label="PD"
            lord={pd.lord}
            total={pd.years * 365.25}
            remaining={dasha.pratyantar_remaining_days}
            unit="days"
          />
        )}
      </div>
    </div>
  );
}

function Tier({
  label,
  lord,
  total,
  remaining,
  unit,
}: {
  label: "MD" | "AD" | "PD";
  lord: string;
  total: number;
  remaining: number;
  unit: "yrs" | "days";
}) {
  const elapsed = Math.max(0, total - remaining);
  const pct = total > 0 ? Math.max(2, Math.min(100, (elapsed / total) * 100)) : 0;
  return (
    <div className="rounded-lg border border-[var(--border-glass)] bg-[rgba(15,17,35,0.5)] p-3">
      <div className="mb-2 flex flex-wrap items-baseline gap-3">
        <span className="display text-xs uppercase tracking-widest text-[var(--accent-purple)]">{label}</span>
        <span className="font-medium text-[var(--accent-gold)]">{lord}</span>
        <span className="ml-auto text-xs text-[var(--text-muted)]">
          {Number(remaining).toFixed(unit === "days" ? 0 : 1)} {unit} left
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-white/5">
        <div
          className="h-full rounded-full"
          style={{
            width: `${pct}%`,
            background: "linear-gradient(to right, rgba(139,92,246,0.7), rgba(212,175,55,0.7))",
            transition: "width 0.3s ease",
          }}
        />
      </div>
    </div>
  );
}
