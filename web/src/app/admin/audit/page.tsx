/**
 * /admin/audit
 * =============
 * Server component — fetches /audit/recent, /audit/summary, and
 * /audit/unmatched-tokens in parallel, then hands the results to the
 * client-side filter UI for the recent-entries table.
 *
 * No auth gate yet (localhost trust model). Add a token check before this
 * faces real users — see the Phase 3 todo in docs/INTERPRETATION.md.
 */

import { auditRecent, auditSummary, auditUnmatchedTokens } from "@/lib/api";
import type {
  AuditEntry,
  AuditSummary,
  UnmatchedToken,
} from "@/lib/api";
import { AuditTable } from "@/components/AuditTable";
import { LogoutButton } from "@/components/LogoutButton";

export const dynamic = "force-dynamic";

type SearchParams = Promise<{
  source?: string;
  verdict?: string;
  since?: string;
  limit?: string;
}>;

export default async function AuditPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const params = await searchParams;
  const limit = Math.min(500, Math.max(1, Number(params.limit) || 100));

  // Fetch all three in parallel. allSettled so one slow / failing endpoint
  // doesn't blank the whole page.
  const [recentR, summaryR, unmatchedR] = await Promise.allSettled([
    auditRecent({ limit, source: params.source, verdict: params.verdict, since: params.since }),
    auditSummary(params.since),
    auditUnmatchedTokens(20, params.since),
  ]);

  const recent =
    recentR.status === "fulfilled" ? recentR.value.items : ([] as AuditEntry[]);
  const summary: AuditSummary | null =
    summaryR.status === "fulfilled" ? summaryR.value : null;
  const unmatched: UnmatchedToken[] =
    unmatchedR.status === "fulfilled" ? unmatchedR.value.tokens : [];

  const fetchErrors = [recentR, summaryR, unmatchedR]
    .filter((r) => r.status === "rejected")
    .map((r) =>
      r.status === "rejected"
        ? r.reason instanceof Error
          ? r.reason.message
          : String(r.reason)
        : "",
    );

  return (
    <>
      <header className="relative mb-6 text-center">
        <div className="absolute right-0 top-0">
          <LogoutButton />
        </div>
        <h1 className="text-4xl text-[var(--accent-gold)]">Audit Log</h1>
        <p className="mt-1 text-sm text-[var(--text-muted)]">
          Every <code>/ask</code> request, its mapping trace, and the verdict
          it produced — for post-mortem and dictionary tuning
        </p>
      </header>

      {fetchErrors.length > 0 && (
        <section className="mb-6 rounded-lg border border-[rgba(248,113,113,0.35)] bg-[rgba(248,113,113,0.08)] p-4 text-sm text-[#f87171]">
          Couldn&apos;t load some audit data — is the backend running?
          <ul className="ml-4 mt-2 list-disc text-xs opacity-90">
            {fetchErrors.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </section>
      )}

      {/* Stats cards */}
      {summary && <SummaryStats summary={summary} />}

      {/* Top unmatched tokens — the actionable dictionary-expansion feed */}
      {unmatched.length > 0 && <UnmatchedTokensPanel tokens={unmatched} />}

      {/* Recent entries with filters */}
      <section>
        <h2 className="display mb-3 text-xl text-[var(--accent-gold)]">
          Recent /ask requests
          <span className="ml-2 text-sm font-normal text-[var(--text-muted)]">
            · {recent.length} of {summary?.total ?? "?"}
          </span>
        </h2>
        <AuditTable entries={recent} appliedFilters={params} />
      </section>
    </>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SummaryStats({ summary }: { summary: AuditSummary }) {
  const hiccupPct = (summary.llm_hiccup_rate * 100).toFixed(0);
  const fallbackPct = (summary.fallback_rate * 100).toFixed(0);
  const llmPickPct = (summary.llm_pick_rate * 100).toFixed(0);
  const singlePct = (summary.single_candidate_rate * 100).toFixed(0);

  return (
    <section className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
      <StatCard label="Total /ask" value={summary.total.toLocaleString()} />
      <StatCard
        label="Avg latency"
        value={summary.avg_request_ms !== null ? `${summary.avg_request_ms} ms` : "—"}
      />
      <StatCard
        label="LLM hiccups"
        value={`${hiccupPct}%`}
        sub={`${summary.by_source["dictionary+top_score"] ?? 0} entries used the deterministic fallback`}
        accent={summary.llm_hiccup_rate > 0.1 ? "warn" : "neutral"}
      />
      <StatCard
        label="Domain fallback"
        value={`${fallbackPct}%`}
        sub="dictionary returned zero matches → legacy 14-domain classifier"
        accent={summary.fallback_rate > 0.1 ? "warn" : "neutral"}
      />

      <StatCard label="Single-candidate" value={`${singlePct}%`} sub="no LLM call needed" />
      <StatCard label="LLM-picked" value={`${llmPickPct}%`} sub="LLM disambiguated from a narrowed set" />
      <SourceBreakdown summary={summary} />
      <VerdictBreakdown summary={summary} />
    </section>
  );
}

function StatCard({
  label,
  value,
  sub,
  accent = "neutral",
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: "neutral" | "warn";
}) {
  return (
    <div className="glass p-4">
      <div className="text-[0.65rem] uppercase tracking-widest text-[var(--text-muted)]">
        {label}
      </div>
      <div
        className={
          "display mt-1 text-2xl " +
          (accent === "warn" ? "text-[#f87171]" : "text-[var(--accent-gold)]")
        }
      >
        {value}
      </div>
      {sub && <div className="mt-1 text-[0.7rem] leading-relaxed text-[var(--text-muted)]">{sub}</div>}
    </div>
  );
}

function SourceBreakdown({ summary }: { summary: AuditSummary }) {
  const entries = Object.entries(summary.by_source).sort((a, b) => b[1] - a[1]);
  return (
    <div className="glass col-span-2 p-4">
      <div className="text-[0.65rem] uppercase tracking-widest text-[var(--text-muted)]">
        By source
      </div>
      <ul className="mt-2 flex flex-col gap-1.5 text-xs">
        {entries.map(([src, n]) => {
          const pct = summary.total > 0 ? (n / summary.total) * 100 : 0;
          return (
            <li key={src} className="flex items-center gap-2">
              <span className="w-44 truncate text-[var(--text-muted)]" title={src}>
                {src}
              </span>
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/5">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-[rgba(139,92,246,0.6)] to-[rgba(212,175,55,0.6)]"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="w-12 text-right font-mono text-[var(--text-main)]">
                {n}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function VerdictBreakdown({ summary }: { summary: AuditSummary }) {
  const order = [
    "strongly favorable",
    "favorable",
    "mixed",
    "challenging",
    "strongly challenging",
  ];
  const entries = order
    .map((label) => [label, summary.by_verdict[label] ?? 0] as const)
    .filter(([, n]) => n > 0);
  return (
    <div className="glass col-span-2 p-4">
      <div className="text-[0.65rem] uppercase tracking-widest text-[var(--text-muted)]">
        By verdict
      </div>
      <ul className="mt-2 flex flex-col gap-1.5 text-xs">
        {entries.length === 0 && (
          <li className="text-[var(--text-muted)]">no verdicts yet</li>
        )}
        {entries.map(([label, n]) => {
          const pct = summary.total > 0 ? (n / summary.total) * 100 : 0;
          const color = verdictColor(label);
          return (
            <li key={label} className="flex items-center gap-2">
              <span className="w-44 truncate capitalize" style={{ color }}>
                {label}
              </span>
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/5">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${pct}%`, background: color, opacity: 0.55 }}
                />
              </div>
              <span className="w-12 text-right font-mono text-[var(--text-main)]">
                {n}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function UnmatchedTokensPanel({ tokens }: { tokens: UnmatchedToken[] }) {
  return (
    <section className="mb-6 glass p-5">
      <div className="mb-2 flex items-center gap-2">
        <h2 className="display text-lg text-[var(--accent-gold)]">
          Top unmatched tokens
        </h2>
        <span className="text-[0.65rem] uppercase tracking-widest text-[var(--text-muted)]">
          dictionary-expansion candidates
        </span>
      </div>
      <p className="mb-3 text-xs text-[var(--text-muted)]">
        Words that fell through the exact / stem / override / semantic
        cascade and ended up &ldquo;unmatched&rdquo;. The frequent ones are
        prime candidates for adding to <code>house_seeds.py</code> or to
        the <code>PRIMARY_OVERRIDES</code> table.
      </p>
      <ul className="grid grid-cols-1 gap-2 md:grid-cols-2">
        {tokens.map((t) => (
          <li
            key={t.token}
            className="rounded-md border border-[var(--border-glass)] bg-[rgba(15,17,35,0.55)] p-2.5 text-xs"
          >
            <div className="flex items-center justify-between">
              <code className="rounded bg-white/5 px-1.5 py-0.5 text-[var(--accent-gold)]">
                {t.token}
              </code>
              <span className="font-mono text-[var(--text-muted)]">×{t.count}</span>
            </div>
            {t.examples.length > 0 && (
              <ul className="mt-1.5 flex flex-col gap-0.5 text-[0.7rem] text-[var(--text-muted)]">
                {t.examples.map((ex) => (
                  <li key={ex.id} className="truncate" title={ex.question}>
                    · <span className="text-[var(--text-main)]">{ex.question}</span>
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

function verdictColor(label: string): string {
  if (label === "strongly favorable" || label === "favorable") return "#86efac";
  if (label === "challenging" || label === "strongly challenging") return "#f87171";
  return "#d4af37";
}
