"use client";

import { useCallback, useEffect, useState } from "react";
import { ask } from "@/lib/api";
import type { AskResponse } from "@/lib/types";
import { MomentControls, defaultMoment, emptyMoment, toIsoWhen, type MomentValue } from "@/components/MomentControls";
import { HowItWorks } from "@/components/HowItWorks";
import { AskResultView } from "@/components/AskResultView";
import { AskGuidelines } from "@/components/AskGuidelines";
import { useSessionState } from "@/lib/useSessionState";

const EXAMPLES = [
  "Will my career grow this year?",
  "Is this the right time to marry?",
  "Should I take this new job?",
  "Should I avoid this business partnership?",
];

export default function AskPage() {
  const [question, setQuestion] = useSessionState("ask-question", "");
  // Start with stable empty date/time so SSR HTML matches the first client
  // render — populate the actual "now" only after mount (or restore from session).
  const [moment, setMoment, momentHydrated] = useSessionState<MomentValue>("ask-moment", emptyMoment);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useSessionState<AskResponse | null>("ask-data", null);
  const [error, setError] = useState<string | null>(null);

  // Populate the real "now" on the client — but only if the session didn't
  // already have a stored moment (i.e. date/time are still empty after hydration).
  useEffect(() => {
    if (!momentHydrated) return;
    if (!moment.date || !moment.time) setMoment(defaultMoment());
    // eslint-disable-next-line react-hooks/exhaustive-deps -- run once after hydration
  }, [momentHydrated]);

  // Keep the local-clock display in the meta line live-updating once a minute.
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setTick((v) => v + 1), 60_000);
    return () => clearInterval(t);
  }, []);

  const submit = useCallback(async (qOverride?: string) => {
    const q = (qOverride ?? question).trim();
    if (!q) return;
    setError(null);
    setLoading(true);
    setData(null);
    try {
      const res = await ask({
        q,
        lat: moment.lat,
        lon: moment.lon,
        place: moment.place,
        when: toIsoWhen(moment) ?? undefined,
      });
      setData(res);
      // Smooth scroll to result on next tick
      requestAnimationFrame(() => {
        document
          .getElementById("ask-result")
          ?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong. Is the API running?");
    } finally {
      setLoading(false);
    }
  }, [question, moment]);

  const askAgain = () => {
    setData(null);
    setQuestion("");
    setMoment(defaultMoment());
  };

  return (
    <>
      <header className="mb-6 text-center">
        <div className="flex items-center justify-center gap-2">
          <h1 className="text-4xl text-[var(--accent-gold)]">Ask the Moment</h1>
          <AskGuidelines />
        </div>
        <p className="mt-1 text-sm text-[var(--text-muted)]">
          Prashna — your question, answered from the sky at this instant
        </p>
      </header>

      {/* Question input */}
      <section className="glass mb-4 flex flex-col gap-3 p-5">
        <textarea
          rows={2}
          placeholder="Ask anything about your life — career, marriage, health, money, family… Press Enter to submit."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          className="w-full resize-y rounded-lg border border-[var(--border-glass)] bg-[rgba(10,11,22,0.7)] p-3 leading-relaxed text-[var(--text-main)] focus:border-[var(--accent-purple)] focus:outline-none focus:ring-2 focus:ring-[rgba(139,92,246,0.2)]"
        />
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => {
                  setQuestion(ex);
                  submit(ex);
                }}
                className="rounded-full border border-[var(--border-glass)] bg-[rgba(15,17,35,0.7)] px-3 py-1 text-xs text-[var(--text-muted)] transition hover:border-[rgba(139,92,246,0.4)] hover:text-[var(--text-main)]"
              >
                {ex}
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={() => submit()}
            disabled={loading || !question.trim()}
            className="whitespace-nowrap rounded-lg border border-[rgba(212,175,55,0.4)] bg-gradient-to-br from-[rgba(139,92,246,0.4)] to-[rgba(212,175,55,0.25)] px-5 py-2 text-sm font-medium tracking-wide text-white shadow-sm transition hover:shadow-[0_4px_18px_rgba(139,92,246,0.3)] disabled:cursor-not-allowed disabled:opacity-60"
          >
            Ask the Sky →
          </button>
        </div>
      </section>

      {/* Moment controls */}
      <MomentControls value={moment} onChange={setMoment} />

      {/* Live moment summary */}
      <div className="mb-3 flex flex-wrap items-center justify-center gap-2 text-sm text-[var(--text-muted)]">
        <span>Asking at:</span>
        <span>📍 <span className="font-medium text-[var(--accent-gold)]">{moment.place}</span></span>
        <span>·</span>
        <span>🕒 <span className="font-medium text-[var(--accent-gold)]">{formatMomentLabel(moment, tick)}</span></span>
      </div>

      <div className="mb-6">
        <HowItWorks data={data} />
      </div>

      {/* Loading */}
      {loading && (
        <section className="my-6 flex flex-col items-center gap-3 text-[var(--text-muted)]">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--border-glass)] border-t-[var(--accent-purple)]" />
          <p>Casting the chart and reading the sky…</p>
        </section>
      )}

      {error && (
        <section className="my-6 rounded-lg border border-[rgba(248,113,113,0.35)] bg-[rgba(248,113,113,0.08)] p-4 text-sm text-[#f87171]">
          {error}
        </section>
      )}

      {/* Result */}
      {data && <AskResultView data={data} onAskAgain={askAgain} />}
    </>
  );
}

function formatMomentLabel(m: MomentValue, _tick: number): string {
  if (!m.date || !m.time) return "now";
  try {
    return new Date(`${m.date}T${m.time}:00`).toLocaleString();
  } catch {
    return `${m.date} ${m.time}`;
  }
}
