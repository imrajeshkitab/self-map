// Thin client over the FastAPI backend. One function per route we use.
// `NEXT_PUBLIC_API_BASE_URL` is read at runtime in client components and at
// build/request time in server components — defaults to localhost:8000.

import type { Chart, AskResponse } from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type AskParams = {
  q: string;
  lat?: number;
  lon?: number;
  place?: string;
  /** ISO 8601 datetime; if omitted, backend uses "now" UTC. */
  when?: string;
};

export async function ask(params: AskParams): Promise<AskResponse> {
  const url = new URL(`${API_BASE}/ask`);
  url.searchParams.set("q", params.q);
  if (params.lat !== undefined) url.searchParams.set("lat", String(params.lat));
  if (params.lon !== undefined) url.searchParams.set("lon", String(params.lon));
  if (params.place) url.searchParams.set("place", params.place);
  if (params.when) url.searchParams.set("when", params.when);

  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) throw new Error(`/ask failed: ${res.status}`);
  return res.json();
}

export type TodayParams = {
  lat?: number;
  lon?: number;
  place?: string;
  when?: string;
  pulse?: boolean;
};

export async function today(params: TodayParams = {}): Promise<Chart> {
  const url = new URL(`${API_BASE}/today`);
  if (params.lat !== undefined) url.searchParams.set("lat", String(params.lat));
  if (params.lon !== undefined) url.searchParams.set("lon", String(params.lon));
  if (params.place) url.searchParams.set("place", params.place);
  if (params.when) url.searchParams.set("when", params.when);
  if (params.pulse !== undefined) url.searchParams.set("pulse", String(params.pulse));

  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) throw new Error(`/today failed: ${res.status}`);
  return res.json();
}

export type SearchResult = {
  query: string;
  mode: "trinity" | "ranked";
  trinity?: { house?: unknown; planet?: unknown; zodiac?: unknown };
  overflow?: unknown[];
  results?: unknown[];
  count?: number;
};

export async function search(
  q: string,
  opts: { topK?: number; mode?: "trinity" | "ranked"; minScore?: number } = {}
): Promise<SearchResult> {
  const url = new URL(`${API_BASE}/search`);
  url.searchParams.set("q", q);
  if (opts.topK) url.searchParams.set("top_k", String(opts.topK));
  if (opts.mode) url.searchParams.set("mode", opts.mode);
  if (opts.minScore !== undefined) url.searchParams.set("min_score", String(opts.minScore));

  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) throw new Error(`/search failed: ${res.status}`);
  return res.json();
}

export async function listHouses() {
  const res = await fetch(`${API_BASE}/houses`, { cache: "no-store" });
  if (!res.ok) throw new Error(`/houses failed: ${res.status}`);
  return res.json();
}

export async function listPlanets() {
  const res = await fetch(`${API_BASE}/planets`, { cache: "no-store" });
  if (!res.ok) throw new Error(`/planets failed: ${res.status}`);
  return res.json();
}

export async function listZodiac() {
  const res = await fetch(`${API_BASE}/zodiac`, { cache: "no-store" });
  if (!res.ok) throw new Error(`/zodiac failed: ${res.status}`);
  return res.json();
}

export type DashaTenureEntry = {
  years: number;
  nature: string;
  tone: "favorable" | "mixed" | "challenging";
  themes: string[];
  life_areas: number[];
  best_for: string;
  challenges: string;
  transition_advice: string;
};

export type DashaTenureResponse = {
  cycle_total_years: number;
  order: string[];
  tenure: Record<string, DashaTenureEntry>;
  years_only: Record<string, number>;
};

export async function dashaTenure(): Promise<DashaTenureResponse> {
  const res = await fetch(`${API_BASE}/dasha/tenure`, { cache: "no-store" });
  if (!res.ok) throw new Error(`/dasha/tenure failed: ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Audit log (May 19 MOM #3)
// ---------------------------------------------------------------------------

export type AuditEntry = {
  id: number;
  created_at: string;
  request_ms: number | null;
  question: string;
  source: string | null;
  selected_houses: string | null;        // comma-separated
  natural_karakas: string | null;        // comma-separated
  intent_label: string | null;
  total_score: number | null;
  verdict_label: string | null;
  verdict_confidence: string | null;
  answer_source: "gemini" | "template" | null;
  // Polarity-aware columns (post-Neon migration). Older rows are null.
  favourable_houses?: string | null;     // comma-separated
  unfavourable_houses?: string | null;   // comma-separated
  llm_added_houses?: string | null;      // comma-separated
  user_intent?: string | null;           // achieve | avoid | predict | …
  intent_summary?: string | null;
  negation_detected?: boolean | null;
  favourable_score?: number | null;
  unfavourable_score?: number | null;
};

export type AuditSummary = {
  total: number;
  by_source: Record<string, number>;
  by_verdict: Record<string, number>;
  by_answer_source: Record<string, number>;
  fallback_rate: number;
  llm_hiccup_rate: number;
  single_candidate_rate: number;
  llm_pick_rate: number;
  avg_request_ms: number | null;
  error_count: number;
  since: string | null;
};

export type UnmatchedToken = {
  token: string;
  count: number;
  examples: { id: number; question: string }[];
};

export type AuditRecentParams = {
  limit?: number;
  source?: string;
  verdict?: string;
  since?: string;
};

export async function auditRecent(params: AuditRecentParams = {}): Promise<{
  count: number;
  filters: { source: string | null; verdict: string | null; since: string | null };
  items: AuditEntry[];
}> {
  const url = new URL(`${API_BASE}/audit/recent`);
  if (params.limit !== undefined) url.searchParams.set("limit", String(params.limit));
  if (params.source) url.searchParams.set("source", params.source);
  if (params.verdict) url.searchParams.set("verdict", params.verdict);
  if (params.since) url.searchParams.set("since", params.since);
  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) throw new Error(`/audit/recent failed: ${res.status}`);
  return res.json();
}

export async function auditSummary(since?: string): Promise<AuditSummary> {
  const url = new URL(`${API_BASE}/audit/summary`);
  if (since) url.searchParams.set("since", since);
  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) throw new Error(`/audit/summary failed: ${res.status}`);
  return res.json();
}

// Full detail for one entry — includes the JSONB mapping_trace and
// chart_summary so the detail page can show everything we logged.
export type AuditEntryDetail = AuditEntry & {
  lat: number | null;
  lon: number | null;
  place: string | null;
  chart_datetime: string | null;
  llm_reasoning: string | null;
  mapping_trace: unknown | null;  // JSONB — shape mirrors MappingTrace
  chart_summary: unknown | null;  // JSONB — slim chart snapshot
  answer_md: string | null;
  error: string | null;
  user_feedback?: string | null;
  /** Full faithful snapshot of exactly what the user saw (chart + intent +
   *  evidence + verdict + answer). Present for rows logged after the
   *  response_json migration; null for older rows (fall back to replay). */
  response_json?: AskResponse | null;
  /** Provenance of response_json:
   *   "original" — captured live at /ask time (100% faithful).
   *   "replay"   — back-filled later from a reconstruction (may differ).
   *   null       — pre-migration original snapshot (treat as "original"). */
  response_source?: "original" | "replay" | null;
};

/** Back-fill an old row's snapshot from a replay, so repeat-opens are fast.
 *  Tagged 'replay' server-side; never overwrites a genuine original. */
export async function cacheAuditReplay(
  id: number | string,
  response: AskResponse,
): Promise<{ id: number; cached: boolean }> {
  const res = await fetch(`${API_BASE}/audit/${id}/cache`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(response),
  });
  if (!res.ok) throw new Error(`/audit/${id}/cache failed: ${res.status}`);
  return res.json();
}

export async function auditEntry(id: number | string): Promise<AuditEntryDetail> {
  const res = await fetch(`${API_BASE}/audit/${id}`, { cache: "no-store" });
  if (res.status === 404) throw new Error(`audit entry ${id} not found`);
  if (!res.ok) throw new Error(`/audit/${id} failed: ${res.status}`);
  return res.json();
}

export async function auditUnmatchedTokens(
  limit = 20,
  since?: string,
): Promise<{ since: string | null; tokens: UnmatchedToken[] }> {
  const url = new URL(`${API_BASE}/audit/unmatched-tokens`);
  url.searchParams.set("limit", String(limit));
  if (since) url.searchParams.set("since", since);
  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) throw new Error(`/audit/unmatched-tokens failed: ${res.status}`);
  return res.json();
}
