"use client";

/**
 * AuditTable
 * ===========
 * Client component — renders the filterable list of audit entries.
 *
 * Filters live in URL search params (source, verdict, since) so they're
 * bookmarkable and survive refresh. The parent server component already
 * read those params and fetched the filtered list; this component just
 * provides the inputs that drive navigation.
 *
 * No internal state — the URL is the source of truth.
 */

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import type { AuditEntry } from "@/lib/api";
import { cn } from "@/lib/utils";

type Filters = {
  source?: string;
  verdict?: string;
  since?: string;
};

// Known source buckets — kept in sync with backend/interpret.py decide_houses
const SOURCE_OPTIONS = [
  { value: "", label: "(any source)" },
  { value: "dictionary", label: "dictionary — single candidate" },
  { value: "dictionary+llm", label: "dictionary + LLM pick" },
  { value: "dictionary+top_score", label: "dictionary + top-score fallback" },
];

// Verdict labels mirror interpret.make_verdict
const VERDICT_OPTIONS = [
  { value: "", label: "(any verdict)" },
  { value: "strongly favorable", label: "strongly favorable" },
  { value: "favorable", label: "favorable" },
  { value: "mixed", label: "mixed" },
  { value: "challenging", label: "challenging" },
  { value: "strongly challenging", label: "strongly challenging" },
];

const SINCE_OPTIONS = [
  { value: "", label: "all-time" },
  { value: "24h", label: "last 24 hours" },
  { value: "7d", label: "last 7 days" },
  { value: "30d", label: "last 30 days" },
];

export function AuditTable({
  entries,
  appliedFilters,
}: {
  entries: AuditEntry[];
  appliedFilters: Filters;
}) {
  const router = useRouter();
  const sp = useSearchParams();

  // Build a new URL with one filter changed, preserving the rest.
  const setFilter = useCallback(
    (key: keyof Filters, value: string) => {
      const params = new URLSearchParams(sp.toString());
      if (value) {
        if (key === "since") {
          // Translate relative "24h" / "7d" / "30d" into an ISO datetime
          // (anchored client-side so the URL is portable).
          params.set("since", relativeToIso(value));
        } else {
          params.set(key, value);
        }
      } else {
        params.delete(key);
      }
      router.push(`/admin/audit?${params.toString()}`);
    },
    [router, sp],
  );

  // Detect which "since" relative bucket the current ISO param came from,
  // so the dropdown shows the right selection when the page reloads.
  const sinceBucket = guessSinceBucket(appliedFilters.since);

  return (
    <>
      <div className="glass mb-3 flex flex-wrap items-end gap-3 p-3 text-sm">
        <FilterSelect
          label="Source"
          options={SOURCE_OPTIONS}
          value={appliedFilters.source ?? ""}
          onChange={(v) => setFilter("source", v)}
        />
        <FilterSelect
          label="Verdict"
          options={VERDICT_OPTIONS}
          value={appliedFilters.verdict ?? ""}
          onChange={(v) => setFilter("verdict", v)}
        />
        <FilterSelect
          label="Range"
          options={SINCE_OPTIONS}
          value={sinceBucket}
          onChange={(v) => setFilter("since", v)}
        />
        {(appliedFilters.source || appliedFilters.verdict || appliedFilters.since) && (
          <button
            type="button"
            onClick={() => router.push("/admin/audit")}
            className="ml-auto rounded-md border border-[var(--border-glass)] bg-[rgba(15,17,35,0.7)] px-3 py-1 text-xs text-[var(--text-muted)] hover:border-[rgba(139,92,246,0.4)] hover:text-[var(--text-main)]"
          >
            Clear filters
          </button>
        )}
      </div>

      {entries.length === 0 ? (
        <div className="glass p-6 text-center text-sm text-[var(--text-muted)]">
          No matching audit entries.
        </div>
      ) : (
        <div className="glass overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-[0.65rem] uppercase tracking-widest text-[var(--text-muted)]">
              <tr className="border-b border-[var(--border-glass)]">
                <th className="px-3 py-2 text-left">When</th>
                <th className="px-3 py-2 text-left">Question</th>
                <th className="px-3 py-2 text-left">Source</th>
                <th className="px-3 py-2 text-left">Houses</th>
                <th className="px-3 py-2 text-right">Score</th>
                <th className="px-3 py-2 text-left">Verdict</th>
                <th className="px-3 py-2 text-right">ms</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <Row key={e.id} entry={e} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function Row({ entry }: { entry: AuditEntry }) {
  const verdictColor = verdictTextColor(entry.verdict_label);
  return (
    <tr className="border-b border-white/[0.03] last:border-b-0 hover:bg-white/[0.02]">
      <td className="px-3 py-2 align-top text-[0.7rem] text-[var(--text-muted)]">
        <RelativeTime iso={entry.created_at} />
      </td>
      <td className="max-w-md px-3 py-2 align-top">
        <Link
          href={`/admin/audit/${entry.id}`}
          className="block truncate text-[var(--text-main)] hover:text-[var(--accent-gold)]"
          title={entry.question}
        >
          {entry.question}
        </Link>
      </td>
      <td className="px-3 py-2 align-top">
        <SourcePill source={entry.source} />
      </td>
      <td className="px-3 py-2 align-top text-xs font-mono">
        {entry.selected_houses
          ? entry.selected_houses
              .split(",")
              .map((h) => `H${h}`)
              .join(", ")
          : "—"}
      </td>
      <td className="px-3 py-2 text-right align-top font-mono text-xs">
        {entry.total_score !== null ? entry.total_score.toFixed(2) : "—"}
      </td>
      <td className={cn("px-3 py-2 align-top text-xs capitalize", verdictColor)}>
        {entry.verdict_label ?? "—"}
      </td>
      <td className="px-3 py-2 text-right align-top font-mono text-[0.7rem] text-[var(--text-muted)]">
        {entry.request_ms ?? "—"}
      </td>
    </tr>
  );
}

/**
 * Renders a relative "X ago" string client-side, with the absolute ISO
 * date as the fallback during SSR and the initial pre-mount client render.
 *
 * This is the canonical fix from react.dev's hydration error guide: any
 * value derived from `Date.now()` MUST be computed in an effect, not in
 * render — otherwise SSR and CSR diverge across a second boundary and
 * React throws a hydration mismatch (which can leave event handlers
 * unattached in the recovered subtree).
 *
 * After mount, refreshes every 30s so the table doesn't go stale on a
 * left-open tab.
 */
function RelativeTime({ iso }: { iso: string }) {
  // Pre-mount fallback: deterministic absolute date (stable across SSR/CSR).
  const [text, setText] = useState<string>(() => isoDate(iso));

  useEffect(() => {
    const update = () => setText(formatRelative(iso));
    update();
    const id = window.setInterval(update, 30_000);
    return () => window.clearInterval(id);
  }, [iso]);

  return <span title={iso}>{text}</span>;
}

function isoDate(iso: string): string {
  // Slice instead of toLocaleString — locale-free, so server and client
  // produce the exact same characters during the pre-mount render pass.
  return iso.slice(0, 10);
}

function FilterSelect({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1 text-[var(--text-muted)]">
      <span className="text-[0.65rem] uppercase tracking-widest">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-[var(--border-glass)] bg-[rgba(10,11,22,0.7)] px-2 py-1 text-[var(--text-main)] focus:border-[var(--accent-purple)] focus:outline-none"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function SourcePill({ source }: { source: string | null }) {
  if (!source) {
    return <span className="text-[var(--text-muted)]">—</span>;
  }
  const styles = sourcePillStyle(source);
  return (
    <span
      className={cn(
        "whitespace-nowrap rounded-full border px-2 py-[1px] text-[0.65rem] uppercase tracking-wider",
        styles,
      )}
      title={source}
    >
      {sourceShortLabel(source)}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function relativeToIso(bucket: string): string {
  const ms =
    bucket === "24h" ? 24 * 60 * 60 * 1000 :
    bucket === "7d"  ? 7  * 24 * 60 * 60 * 1000 :
    bucket === "30d" ? 30 * 24 * 60 * 60 * 1000 :
    0;
  return new Date(Date.now() - ms).toISOString();
}

function guessSinceBucket(iso: string | undefined): string {
  if (!iso) return "";
  const ageMs = Date.now() - new Date(iso).getTime();
  // Allow some wobble around exact thresholds because the page might
  // have been left open for a while.
  if (ageMs < 25 * 60 * 60 * 1000) return "24h";
  if (ageMs < 8  * 24 * 60 * 60 * 1000) return "7d";
  if (ageMs < 31 * 24 * 60 * 60 * 1000) return "30d";
  return "";
}

function formatRelative(iso: string): string {
  const then = new Date(iso).getTime();
  const diffMs = Date.now() - then;
  const s = Math.floor(diffMs / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 7) return `${d}d ago`;
  return new Date(iso).toLocaleDateString();
}

function sourceShortLabel(source: string): string {
  if (source === "dictionary") return "single";
  if (source === "dictionary+llm") return "LLM pick";
  if (source === "dictionary+top_score") return "top-score";
  if (source.startsWith("domain_map_fallback")) return "fallback";
  return source;
}

function sourcePillStyle(source: string): string {
  if (source === "dictionary")
    return "bg-[rgba(134,239,172,0.12)] text-[#86efac] border-[rgba(134,239,172,0.35)]";
  if (source === "dictionary+llm")
    return "bg-[rgba(212,175,55,0.15)] text-[var(--accent-gold)] border-[rgba(212,175,55,0.35)]";
  if (source === "dictionary+top_score")
    return "bg-[rgba(91,141,239,0.15)] text-[#93b8f8] border-[rgba(91,141,239,0.35)]";
  if (source.startsWith("domain_map_fallback"))
    return "bg-[rgba(248,113,113,0.12)] text-[#f87171] border-[rgba(248,113,113,0.35)]";
  return "bg-white/5 text-[var(--text-muted)] border-[var(--border-glass)]";
}

function verdictTextColor(label: string | null): string {
  if (!label) return "text-[var(--text-muted)]";
  if (label === "favorable" || label === "strongly favorable") return "text-[#86efac]";
  if (label === "challenging" || label === "strongly challenging") return "text-[#f87171]";
  return "text-[var(--accent-gold)]";
}
