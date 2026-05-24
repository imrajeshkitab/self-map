"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { today } from "@/lib/api";
import type { Chart } from "@/lib/types";
import { MomentControls, defaultMoment, emptyMoment, toIsoWhen, type MomentValue } from "@/components/MomentControls";
import { PrashnaChart } from "@/components/PrashnaChart";
import { ChartMetadata } from "@/components/ChartMetadata";
import { DbaPanel } from "@/components/DbaPanel";
import { CosmicWeather } from "@/components/CosmicWeather";
import { useSessionState } from "@/lib/useSessionState";

export default function TodayPage() {
  // Stable empty date/time on first render — SSR HTML matches client hydration.
  // The real "now" is populated by the effect below (or restored from session).
  const [moment, setMoment, momentHydrated] = useSessionState<MomentValue>("today-moment", emptyMoment);
  const [chart, setChart, chartHydrated] = useSessionState<Chart | null>("today-chart", null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Track whether we should skip the first chart fetch (because chart was
  // restored from session and moment hasn't changed yet).
  const skipInitialFetch = useRef(true);

  useEffect(() => {
    if (!momentHydrated) return;
    if (!moment.date || !moment.time) setMoment(defaultMoment());
    // eslint-disable-next-line react-hooks/exhaustive-deps -- run once after hydration
  }, [momentHydrated]);

  const load = useCallback(async (m: MomentValue) => {
    setLoading(true);
    setError(null);
    try {
      const c = await today({
        lat: m.lat,
        lon: m.lon,
        place: m.place,
        when: toIsoWhen(m) ?? undefined,
        pulse: true,
      });
      setChart(c);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load chart. Is the API running?");
    } finally {
      setLoading(false);
    }
  }, [setChart]);

  // Fetch chart whenever moment changes. Skip the first trigger if we
  // already have a chart restored from session (avoids a redundant API call).
  useEffect(() => {
    if (!moment.date || !moment.time) return;
    if (skipInitialFetch.current) {
      skipInitialFetch.current = false;
      if (chart && chartHydrated) return; // already have session-restored chart
    }
    void load(moment);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- chart is intentionally excluded
  }, [moment, load]);

  return (
    <>
      <header className="mb-6 text-center">
        <h1 className="text-4xl text-[var(--accent-gold)]">Today&apos;s Sky</h1>
        <p className="mt-1 text-sm text-[var(--text-muted)]">
          A live Vedic snapshot — no birth data needed
        </p>
      </header>

      <MomentControls value={moment} onChange={setMoment} />

      {loading && (
        <section className="my-6 flex flex-col items-center gap-3 text-[var(--text-muted)]">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--border-glass)] border-t-[var(--accent-purple)]" />
          <p>Reading the sky…</p>
        </section>
      )}

      {error && (
        <section className="my-6 rounded-lg border border-[rgba(248,113,113,0.35)] bg-[rgba(248,113,113,0.08)] p-4 text-sm text-[#f87171]">
          {error}
        </section>
      )}

      {chart && (
        <section className="flex flex-col gap-5">
          {chart.pulse && (
            <div className="glass border-l-[3px] border-[var(--accent-gold)] p-4">
              <div className="mb-2 inline-block text-xs font-semibold uppercase tracking-widest text-[var(--accent-gold)]">
                Cosmic Pulse
                <span className="ml-2 inline-block rounded-full bg-[rgba(212,175,55,0.15)] px-2 py-[1px] text-[0.65rem]">
                  {chart.pulse.source === "gemini" ? "AI" : "Template"}
                </span>
              </div>
              <p className="text-sm leading-relaxed">{chart.pulse.summary}</p>
            </div>
          )}

          <div className="grid grid-cols-1 gap-6 md:grid-cols-[420px_minmax(0,1fr)]">
            <div>
              <h2 className="display mb-1 text-lg text-[var(--accent-gold)]">Live Chart</h2>
              <p className="mb-3 text-xs text-[var(--text-muted)]">South-Indian style — Lagna highlighted in gold.</p>
              <PrashnaChart chart={chart} label="NOW" />
            </div>
            <ChartMetadata chart={chart} />
          </div>

          <DbaPanel dasha={chart.dasha} />

          <div>
            <h3 className="display text-base text-[var(--accent-gold)]">
              Cosmic Weather <span className="ml-2 text-xs font-normal text-[var(--text-muted)]">· every planet&apos;s state</span>
            </h3>
            <div className="mt-3">
              <CosmicWeather chart={chart} />
            </div>
          </div>
        </section>
      )}
    </>
  );
}
