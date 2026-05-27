/**
 * /admin/audit/[id]
 * =================
 * Detail view for a single audit-log entry. Renders the *same* result panel
 * shown after an Ask the Moment submission, by re-casting the chart from the
 * stored question + when + place + lat/lon. Adds a small audit-metadata
 * banner up top so we know we're looking at a logged entry (and how the
 * original verdict compares).
 *
 * Why replay instead of rehydrate? The audit log only stores a slim
 * chart_summary + the answer markdown — not the full Chart, planets list,
 * or per-factor evidence. The replay is deterministic for everything except
 * the LLM-polarity classifier and the Gemini synthesis, which is good
 * enough to inspect what the user saw.
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ask, auditEntry, cacheAuditReplay, type AuditEntryDetail } from "@/lib/api";
import type { AskResponse } from "@/lib/types";
import { AskResultView } from "@/components/AskResultView";
import { HowItWorks } from "@/components/HowItWorks";

export default function AuditEntryPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const [id, setId] = useState<string | null>(null);
  const [entry, setEntry] = useState<AuditEntryDetail | null>(null);
  const [data, setData] = useState<AskResponse | null>(null);
  // "snapshot"      = exact original response (100% faithful).
  // "reconstructed" = replay (either freshly cast or a cached replay) — a
  //                   reconstruction that may differ from the original.
  const [fidelity, setFidelity] = useState<"snapshot" | "reconstructed" | null>(
    null,
  );
  const [phase, setPhase] = useState<"loading-entry" | "replaying" | "done" | "error">(
    "loading-entry",
  );
  const [error, setError] = useState<string | null>(null);

  // Resolve the route params promise once.
  useEffect(() => {
    params.then((p) => setId(p.id));
  }, [params]);

  // Step 1: fetch the audit row. If it carries a full response snapshot we
  // render it directly — faithful, instant, no regeneration. Only rows
  // logged before the snapshot migration fall through to replay.
  useEffect(() => {
    if (!id) return;
    const numericId = Number(id);
    if (!Number.isFinite(numericId)) {
      setError("Invalid entry id");
      setPhase("error");
      return;
    }
    let cancelled = false;
    auditEntry(numericId)
      .then((e) => {
        if (cancelled) return;
        setEntry(e);
        if (e.response_json) {
          // Have a stored snapshot — render instantly. It's either a genuine
          // original or a previously-cached replay; the source tag decides
          // how we label it.
          setData(e.response_json);
          setFidelity(
            e.response_source === "replay" ? "reconstructed" : "snapshot",
          );
          setPhase("done");
        } else {
          // Old row, no snapshot — must replay, then cache it for next time.
          setFidelity("reconstructed");
          setPhase("replaying");
        }
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : String(e));
        setPhase("error");
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  // Step 2 (fallback only): replay /ask with the stored params to rebuild the
  // chart for older rows that have no snapshot.
  useEffect(() => {
    if (phase !== "replaying" || !entry) return;
    let cancelled = false;
    ask({
      q: entry.question,
      lat: entry.lat ?? undefined,
      lon: entry.lon ?? undefined,
      place: entry.place ?? undefined,
      when: entry.chart_datetime ?? undefined,
    })
      .then((r) => {
        if (cancelled) return;
        setData(r);
        setPhase("done");
        // Back-fill the snapshot so the next open of this row is instant.
        // Fire-and-forget: a failed cache write must not affect the view.
        // Server tags it response_source='replay' and refuses to clobber an
        // existing original, so this is safe even on a race.
        cacheAuditReplay(entry.id, r).catch(() => {});
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : String(e));
        setPhase("error");
      });
    return () => {
      cancelled = true;
    };
  }, [phase, entry]);

  return (
    <>
      <header className="mb-4">
        <Link
          href="/admin/audit"
          className="text-xs text-[var(--text-muted)] transition-colors hover:text-[var(--accent-gold)]"
        >
          ← Back to audit log
        </Link>
      </header>

      {/* Header — mirrors the Ask the Moment page title, view-only. */}
      <header className="mb-6 text-center">
        <h1 className="text-4xl text-[var(--accent-gold)]">Ask the Moment</h1>
        <p className="mt-1 text-sm text-[var(--text-muted)]">
          {fidelity === "reconstructed"
            ? "Prashna — reconstructed from the logged moment (view-only)"
            : "Prashna — the saved reading from this logged moment (view-only)"}
        </p>
      </header>

      {entry && (
        <AuditBanner entry={entry} replayedData={data} fidelity={fidelity} />
      )}

      {phase === "loading-entry" && <Spinner label="Loading entry…" />}
      {phase === "replaying" && (
        <Spinner label="Re-casting the chart at the recorded moment…" />
      )}

      {phase === "error" && (
        <section className="my-6 rounded-lg border border-[rgba(248,113,113,0.35)] bg-[rgba(248,113,113,0.08)] p-4 text-sm text-[#f87171]">
          {error ?? "Something went wrong loading this entry."}
        </section>
      )}

      {phase === "done" && data && (
        <>
          {/* "How was this answered?" journey trace — same as Ask the Moment. */}
          <div className="mb-6">
            <HowItWorks data={data} />
          </div>
          <AskResultView data={data} />
        </>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Sub-components (module-scope per React best-practices)
// ---------------------------------------------------------------------------

function Spinner({ label }: { label: string }) {
  return (
    <section className="my-6 flex flex-col items-center gap-3 text-[var(--text-muted)]">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--border-glass)] border-t-[var(--accent-purple)]" />
      <p>{label}</p>
    </section>
  );
}

function AuditBanner({
  entry,
  replayedData,
  fidelity,
}: {
  entry: AuditEntryDetail;
  replayedData: AskResponse | null;
  fidelity: "snapshot" | "reconstructed" | null;
}) {
  const created = entry.created_at
    ? new Date(entry.created_at).toLocaleString()
    : "—";
  const original = entry.verdict_label ?? "—";
  // Verdict drift only makes sense for reconstructions; a snapshot can't drift.
  const replayed = replayedData?.verdict.label ?? null;
  const drift =
    fidelity === "reconstructed" &&
    replayed &&
    original !== "—" &&
    replayed !== original
      ? `reconstructed verdict differs: ${replayed}`
      : null;

  return (
    <section className="glass mb-5 flex flex-wrap items-center gap-x-4 gap-y-1 p-3 text-xs text-[var(--text-muted)]">
      <span className="text-[var(--accent-gold)]">Entry #{entry.id}</span>
      {fidelity === "snapshot" && (
        <span
          className="rounded-full border border-[rgba(134,239,172,0.4)] bg-[rgba(134,239,172,0.12)] px-2 py-[1px] text-[0.6rem] uppercase tracking-widest text-[#86efac]"
          title="Rendered from the exact saved response — identical to what the user saw."
        >
          faithful snapshot
        </span>
      )}
      {fidelity === "reconstructed" && (
        <span
          className="rounded-full border border-[rgba(251,191,36,0.4)] bg-[rgba(251,191,36,0.12)] px-2 py-[1px] text-[0.6rem] uppercase tracking-widest text-[#fbbf24]"
          title="No original snapshot for this older row — reconstructed by re-running the pipeline. Cached after first open so repeat views are fast, but wording (and occasionally the verdict) may differ from the original."
        >
          reconstructed · may differ
        </span>
      )}
      <span>·</span>
      <span>logged {created}</span>
      {entry.request_ms != null && (
        <>
          <span>·</span>
          <span>{entry.request_ms} ms</span>
        </>
      )}
      <span>·</span>
      <span>
        original verdict:{" "}
        <strong className="text-[var(--text-main)]">{original}</strong>
        {entry.verdict_confidence && (
          <span className="ml-1 opacity-80">
            ({entry.verdict_confidence})
          </span>
        )}
      </span>
      {drift && (
        <>
          <span>·</span>
          <span className="text-[#fbbf24]">{drift}</span>
        </>
      )}
      {entry.error && (
        <>
          <span>·</span>
          <span className="text-[#f87171]">original errored: {entry.error}</span>
        </>
      )}
    </section>
  );
}
