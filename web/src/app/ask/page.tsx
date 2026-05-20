"use client";

import { useCallback, useEffect, useState } from "react";
import { ask } from "@/lib/api";
import type { AskResponse } from "@/lib/types";
import { MomentControls, defaultMoment, emptyMoment, toIsoWhen, type MomentValue } from "@/components/MomentControls";
import { HowItWorks } from "@/components/HowItWorks";
import { VerdictBanner } from "@/components/VerdictBanner";
import { MarkdownReading } from "@/components/MarkdownReading";
import { EvidenceList } from "@/components/EvidenceList";
import { PrashnaChart } from "@/components/PrashnaChart";
import { ChartMetadata } from "@/components/ChartMetadata";
import { DbaPanel } from "@/components/DbaPanel";
import { CosmicWeather } from "@/components/CosmicWeather";

const EXAMPLES = [
  "Will my career grow this year?",
  "Is this the right time to marry?",
  "Should I take this new job?",
  "What is my path right now?",
];

export default function AskPage() {
  const [question, setQuestion] = useState("");
  // Start with stable empty date/time so SSR HTML matches the first client
  // render — populate the actual "now" only after mount.
  const [moment, setMoment] = useState<MomentValue>(() => emptyMoment());
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Populate the real "now" on the client. Empty deps → runs once after mount.
  useEffect(() => {
    setMoment(defaultMoment());
  }, []);

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
        <h1 className="text-4xl text-[var(--accent-gold)]">Ask the Moment</h1>
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
        <HowItWorks />
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
      {data && (
        <section id="ask-result" className="flex flex-col gap-5">
          <VerdictBanner question={data.question} intentLabel={data.intent.label} verdict={data.verdict} />
          <MarkdownReading markdown={data.answer} source={data.answer_source} />

          <div>
            <h2 className="display text-lg text-[var(--accent-gold)]">What the chart shows</h2>
            <p className="mb-3 text-xs text-[var(--text-muted)]">Click each factor to see the reasoning.</p>
            <EvidenceList items={data.evidence.evidence} />
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-[420px_minmax(0,1fr)]">
            <div>
              <h2 className="display mb-1 text-lg text-[var(--accent-gold)]">Prashna Chart</h2>
              <p className="mb-3 text-xs text-[var(--text-muted)]">Cast at the moment of your question.</p>
              <PrashnaChart chart={data.chart} />
            </div>
            <ChartMetadata chart={data.chart} />
          </div>

          {/* Moment context */}
          <div className="my-4 flex items-center justify-center gap-4 text-[var(--accent-gold)]">
            <span className="h-px max-w-[200px] flex-1 bg-gradient-to-r from-transparent via-[rgba(212,175,55,0.35)] to-transparent" />
            <span className="display whitespace-nowrap text-xs uppercase tracking-[0.2em] opacity-85">
              Moment Context
            </span>
            <span className="h-px max-w-[200px] flex-1 bg-gradient-to-r from-transparent via-[rgba(212,175,55,0.35)] to-transparent" />
          </div>
          <p className="-mt-3 mb-2 text-center text-xs text-[var(--text-muted)]">
            The fuller picture of the sky at the moment you asked.
          </p>

          {data.chart.pulse && (
            <div className="glass border-l-[3px] border-[var(--accent-gold)] p-4">
              <div className="mb-2 inline-block text-xs font-semibold uppercase tracking-widest text-[var(--accent-gold)]">
                Cosmic Pulse
                <span className="ml-2 inline-block rounded-full bg-[rgba(212,175,55,0.15)] px-2 py-[1px] text-[0.65rem]">
                  {data.chart.pulse.source === "gemini" ? "AI" : "Template"}
                </span>
              </div>
              <p className="text-sm leading-relaxed">{data.chart.pulse.summary}</p>
            </div>
          )}

          <div>
            <h3 className="display text-base text-[var(--accent-gold)]">
              Cosmic Weather <span className="ml-2 text-xs font-normal text-[var(--text-muted)]">· every planet&apos;s state</span>
            </h3>
            <p className="mb-3 text-xs text-[var(--text-muted)]" />
            <CosmicWeather chart={data.chart} />
          </div>

          <DbaPanel dasha={data.chart.dasha} />

          <button
            type="button"
            onClick={askAgain}
            className="mx-auto mt-2 block rounded-lg border border-[rgba(212,175,55,0.4)] bg-gradient-to-br from-[rgba(139,92,246,0.4)] to-[rgba(212,175,55,0.25)] px-5 py-2 text-sm font-medium text-white transition hover:shadow-[0_4px_18px_rgba(139,92,246,0.3)]"
          >
            Ask another question
          </button>
        </section>
      )}
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
