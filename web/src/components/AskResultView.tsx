/**
 * AskResultView
 * =============
 * The full result panel from /ask — verdict, reading, evidence, chart,
 * cosmic weather, DBA panel. Extracted from app/ask/page.tsx so it can be
 * reused by /admin/audit/[id] (which replays the same /ask call and shows
 * the same view).
 *
 * Pure presentational — no state, no fetching. Hand it a full AskResponse
 * and an optional askAgain callback.
 */

import type { AskResponse } from "@/lib/types";
import { VerdictBanner } from "@/components/VerdictBanner";
import { MarkdownReading } from "@/components/MarkdownReading";
import { EvidenceList } from "@/components/EvidenceList";
import { PrashnaChart } from "@/components/PrashnaChart";
import { ChartMetadata } from "@/components/ChartMetadata";
import { DbaPanel } from "@/components/DbaPanel";
import { CosmicWeather } from "@/components/CosmicWeather";

export function AskResultView({
  data,
  onAskAgain,
  askAgainLabel = "Ask another question",
}: {
  data: AskResponse;
  onAskAgain?: () => void;
  askAgainLabel?: string;
}) {
  return (
    <section id="ask-result" className="flex flex-col gap-5">
      <VerdictBanner
        question={data.question}
        intentLabel={data.intent.label}
        verdict={data.verdict}
      />
      <MarkdownReading markdown={data.answer} source={data.answer_source} />

      <div>
        <h2 className="display text-lg text-[var(--accent-gold)]">
          What the chart shows
        </h2>
        <p className="mb-3 text-xs text-[var(--text-muted)]">
          Click each factor to see the reasoning.
        </p>
        <EvidenceList items={data.evidence.evidence} />
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-[420px_minmax(0,1fr)]">
        <div>
          <h2 className="display mb-1 text-lg text-[var(--accent-gold)]">
            Prashna Chart
          </h2>
          <p className="mb-3 text-xs text-[var(--text-muted)]">
            Cast at the moment of your question.
          </p>
          <PrashnaChart chart={data.chart} />
        </div>
        <ChartMetadata chart={data.chart} />
      </div>

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
          Cosmic Weather{" "}
          <span className="ml-2 text-xs font-normal text-[var(--text-muted)]">
            · every planet&apos;s state
          </span>
        </h3>
        <p className="mb-3 text-xs text-[var(--text-muted)]" />
        <CosmicWeather chart={data.chart} />
      </div>

      <DbaPanel dasha={data.chart.dasha} />

      {onAskAgain && (
        <button
          type="button"
          onClick={onAskAgain}
          className="mx-auto mt-2 block rounded-lg border border-[rgba(212,175,55,0.4)] bg-gradient-to-br from-[rgba(139,92,246,0.4)] to-[rgba(212,175,55,0.25)] px-5 py-2 text-sm font-medium text-white transition hover:shadow-[0_4px_18px_rgba(139,92,246,0.3)]"
        >
          {askAgainLabel}
        </button>
      )}
    </section>
  );
}
