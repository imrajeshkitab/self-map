"use client";

import { useState } from "react";
import type { DashaTenureResponse, DashaTenureEntry } from "@/lib/api";
import { cn } from "@/lib/utils";

type RefItem = Record<string, unknown>;
type RefList = { count: number; items: RefItem[] };

type TabKey = "bhavas" | "grahas" | "rashis" | "dasha";

const TABS: { key: TabKey; label: string; sub: string }[] = [
  { key: "bhavas", label: "Bhavas",        sub: "12 Houses" },
  { key: "grahas", label: "Grahas",        sub: "9 Planets" },
  { key: "rashis", label: "Rashis",        sub: "12 Signs" },
  { key: "dasha",  label: "Dasha-Tenure",  sub: "9 Periods · 120 yrs" },
];

export function BrowseTabs({
  houses, planets, zodiac, dasha,
}: {
  houses: RefList | null;
  planets: RefList | null;
  zodiac: RefList | null;
  dasha: DashaTenureResponse | null;
}) {
  const [active, setActive] = useState<TabKey>("bhavas");

  return (
    <>
      <div role="tablist" className="glass mb-6 flex flex-wrap gap-1 p-1 text-sm">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={active === t.key}
            onClick={() => setActive(t.key)}
            className={cn(
              "flex-1 min-w-[120px] rounded-md px-3 py-2 text-center transition",
              active === t.key
                ? "bg-gradient-to-br from-[rgba(139,92,246,0.35)] to-[rgba(212,175,55,0.18)] text-white shadow-[inset_0_0_0_1px_rgba(212,175,55,0.35)]"
                : "text-[var(--text-muted)] hover:bg-white/[0.04] hover:text-[var(--text-main)]"
            )}
          >
            <div className="display tracking-wider">{t.label}</div>
            <div className="mt-0.5 text-[0.7rem] opacity-70">{t.sub}</div>
          </button>
        ))}
      </div>

      {active === "bhavas" && houses && (
        <Section title="12 Houses (Bhavas)" count={houses.count}>
          {houses.items.map((h) => (
            <ItemCard
              key={String(h.house_number)}
              title={`${h.house_number}. ${h.english_name} (${h.sanskrit_name})`}
              accent={`Ruling sign: ${h.ruling_sign} · Ruling planet: ${h.ruling_planet}`}
              body={String(h.significance ?? "")}
              keywords={String(h.keywords ?? "")}
            />
          ))}
        </Section>
      )}

      {active === "grahas" && planets && (
        <Section title="9 Planets (Grahas)" count={planets.count}>
          {planets.items.map((p) => (
            <ItemCard
              key={String(p.english_name)}
              title={`${p.symbol ?? ""} ${p.english_name} (${p.sanskrit_name})`}
              accent={`Rules: ${p.rules_sign} · Exalted in ${p.exalted_in} · Debilitated in ${p.debilitated_in}`}
              body={String(p.significance ?? "")}
              keywords={String(p.keywords ?? "")}
            />
          ))}
        </Section>
      )}

      {active === "rashis" && zodiac && (
        <Section title="12 Zodiac Signs (Rashis)" count={zodiac.count}>
          {zodiac.items.map((z) => (
            <ItemCard
              key={String(z.sign_number)}
              title={`${z.sign_number}. ${z.english_name} (${z.sanskrit_name})`}
              accent={`Lord: ${z.ruling_planet} · ${z.element} · ${z.quality}`}
              body={String(z.significance ?? "")}
              keywords={String(z.keywords ?? "")}
            />
          ))}
        </Section>
      )}

      {active === "dasha" && dasha && <DashaTenureView data={dasha} />}

      {/* Loading / missing states */}
      {active === "bhavas" && !houses && <Empty />}
      {active === "grahas" && !planets && <Empty />}
      {active === "rashis" && !zodiac && <Empty />}
      {active === "dasha"  && !dasha   && <Empty />}
    </>
  );
}

function Empty() {
  return (
    <div className="glass p-6 text-center text-sm text-[var(--text-muted)]">
      Couldn&apos;t load this section. Is the backend running?
    </div>
  );
}

function Section({
  title, count, children,
}: { title: string; count: number; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="display mb-3 text-2xl text-[var(--accent-gold)]">
        {title} <span className="ml-2 text-sm font-normal text-[var(--text-muted)]">· {count} entries</span>
      </h2>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">{children}</div>
    </section>
  );
}

function ItemCard({
  title, accent, body, keywords,
}: { title: string; accent: string; body: string; keywords: string }) {
  return (
    <article className="glass p-4">
      <h3 className="display text-base text-[var(--accent-gold)]">{title}</h3>
      <p className="mt-1 text-xs text-[var(--text-muted)]">{accent}</p>
      {body && <p className="mt-2 text-sm leading-relaxed text-[var(--text-main)]">{body}</p>}
      {keywords && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {keywords.split(/[,;]\s*/).filter(Boolean).slice(0, 12).map((k) => (
            <span
              key={k}
              className="rounded-full border border-[var(--border-glass)] bg-[rgba(15,17,35,0.6)] px-2 py-[2px] text-[0.7rem] text-[var(--text-muted)]"
            >
              {k}
            </span>
          ))}
        </div>
      )}
    </article>
  );
}

// ---------- Dasha-Tenure view ----------

const TONE_STYLES: Record<DashaTenureEntry["tone"], { dot: string; chip: string }> = {
  favorable:   { dot: "bg-[#86efac]", chip: "bg-[rgba(134,239,172,0.12)] text-[#86efac]" },
  mixed:       { dot: "bg-[#d4af37]", chip: "bg-[rgba(212,175,55,0.12)] text-[var(--accent-gold)]" },
  challenging: { dot: "bg-[#f87171]", chip: "bg-[rgba(248,113,113,0.12)] text-[#f87171]" },
};

// Brighter variant used inside the proportional ribbon, where each segment
// needs to read as a coloured fill, not a translucent chip on a dark page.
const RIBBON_TONE: Record<DashaTenureEntry["tone"], string> = {
  favorable:   "bg-[rgba(134,239,172,0.22)] text-[#86efac]",
  mixed:       "bg-[rgba(212,175,55,0.22)] text-[var(--accent-gold)]",
  challenging: "bg-[rgba(248,113,113,0.22)] text-[#f87171]",
};

// Three-letter abbreviation for narrow ribbon segments where the full name
// won't fit. Kept explicit so it's stable and reviewable, not derived.
const LORD_ABBR: Record<string, string> = {
  Ketu: "Ke", Venus: "Ve", Sun: "Su", Moon: "Mo", Mars: "Ma",
  Rahu: "Ra", Jupiter: "Ju", Saturn: "Sa", Mercury: "Me",
};

function DashaTenureView({ data }: { data: DashaTenureResponse }) {
  return (
    <section>
      <h2 className="display mb-1 text-2xl text-[var(--accent-gold)]">
        Vimshottari Dasa Tenure
        <span className="ml-2 text-sm font-normal text-[var(--text-muted)]">
          · {data.order.length} lords · {data.cycle_total_years}-year cycle
        </span>
      </h2>
      <p className="mb-4 text-sm italic text-[var(--text-muted)]">
        Each Mahadasha runs for a fixed tenure. The cycle always advances in this order — Ketu → Venus → Sun → Moon → Mars → Rahu → Jupiter → Saturn → Mercury — then repeats.
      </p>

      {/* Cycle ribbon — visual proportion of each lord's tenure */}
      <CycleRibbon data={data} />

      <div className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-2">
        {data.order.map((lord) => {
          const t = data.tenure[lord];
          const tone = TONE_STYLES[t.tone];
          return (
            <article key={lord} className="glass p-4">
              <header className="mb-2 flex items-start justify-between gap-2">
                <div>
                  <h3 className="display text-base text-[var(--accent-gold)]">{lord}</h3>
                  <p className="mt-0.5 text-xs italic text-[var(--text-muted)]">{t.nature}</p>
                </div>
                <div className="text-right">
                  <div className="display text-xl text-[var(--text-main)]">{t.years}</div>
                  <div className="text-[0.65rem] uppercase tracking-widest text-[var(--text-muted)]">years</div>
                </div>
              </header>

              <div className="mb-2 flex items-center gap-2 text-[0.7rem]">
                <span className={cn("inline-block h-1.5 w-1.5 rounded-full", tone.dot)} />
                <span className={cn("rounded-full px-2 py-[1px] uppercase tracking-widest", tone.chip)}>
                  {t.tone}
                </span>
                {t.life_areas.length > 0 && (
                  <span className="ml-1 text-[var(--text-muted)]">
                    activates H{t.life_areas.join(", H")}
                  </span>
                )}
              </div>

              <div className="mt-2 flex flex-wrap gap-1.5">
                {t.themes.slice(0, 8).map((th) => (
                  <span
                    key={th}
                    className="rounded-full border border-[var(--border-glass)] bg-[rgba(15,17,35,0.6)] px-2 py-[2px] text-[0.7rem] text-[var(--text-muted)]"
                  >
                    {th}
                  </span>
                ))}
              </div>

              <dl className="mt-3 space-y-1.5 text-xs leading-relaxed">
                <Detail label="Best for">{t.best_for}</Detail>
                <Detail label="Challenges">{t.challenges}</Detail>
                <Detail label="As it ends">{t.transition_advice}</Detail>
              </dl>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function Detail({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-2">
      <dt className="min-w-[5.5rem] text-[var(--text-muted)]">{label}:</dt>
      <dd className="flex-1 text-[var(--text-main)]">{children}</dd>
    </div>
  );
}

function CycleRibbon({ data }: { data: DashaTenureResponse }) {
  const total = data.cycle_total_years;

  // Pick the label that fits a given width. Below ~9% the full name overflows
  // — fall back to the canonical 2-letter abbreviation (Ke, Ve, Su, …).
  const labelFor = (lord: string, widthPct: number) =>
    widthPct >= 9 ? lord : LORD_ABBR[lord] ?? lord.slice(0, 2);

  return (
    <div className="glass overflow-hidden p-3">
      <div className="text-[0.65rem] uppercase tracking-widest text-[var(--text-muted)]">
        the 120-year cycle — proportional view
      </div>
      <div className="mt-2 flex h-10 w-full overflow-hidden rounded-md border border-[var(--border-glass)]">
        {data.order.map((lord) => {
          const t = data.tenure[lord];
          const widthPct = (t.years / total) * 100;
          return (
            <div
              key={lord}
              title={`${lord} — ${t.years} years (${t.tone})`}
              className={cn(
                "flex items-center justify-center border-r border-black/40 text-[0.7rem] font-medium last:border-r-0",
                RIBBON_TONE[t.tone]
              )}
              style={{ width: `${widthPct}%` }}
            >
              {labelFor(lord, widthPct)}
            </div>
          );
        })}
      </div>
      <div className="mt-1 flex w-full text-[0.55rem] text-[var(--text-muted)]">
        {data.order.map((lord) => (
          <div
            key={lord}
            className="text-center"
            style={{ width: `${(data.tenure[lord].years / total) * 100}%` }}
          >
            {data.tenure[lord].years}y
          </div>
        ))}
      </div>
    </div>
  );
}
