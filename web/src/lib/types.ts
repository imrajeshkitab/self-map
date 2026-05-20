// TypeScript shape of the FastAPI responses.
// Mirrors the dataclasses produced by backend/prashna.py + backend/interpret.py.
// When the backend schema changes, update here.

export type PlanetName =
  | "Sun" | "Moon" | "Mars" | "Mercury" | "Jupiter"
  | "Venus" | "Saturn" | "Rahu" | "Ketu";

export type PlanetState = "exalted" | "own" | "debilitated" | "neutral";
export type Relation = "own" | "friend" | "neutral" | "enemy";

export type Planet = {
  name: PlanetName;
  sign: string;
  sign_sanskrit: string;
  degree: number;
  longitude: number;
  house: number;
  state: PlanetState;
  retrograde: boolean;
  combust: boolean;
  relation: Relation;
  sign_lord: PlanetName;
  nakshatra: string;
  nakshatra_lord: PlanetName;
  pada: number;
  avastha: string;
  domicile_signs: string[];
  exalted_in: string;
  debilitated_in: string;
  natural_karaka_houses: number[];
};

export type House = {
  number: number;
  sign: string;
  sign_sanskrit: string;
  lord: PlanetName;
  occupants: PlanetName[];
};

export type DashaTimelineEntry = {
  lord: PlanetName;
  starts: string;
  ends: string;
  years: number;
  current: boolean;
  remaining_years?: number;
  remaining_days?: number;
};

export type Dasha = {
  moon_nakshatra: string;
  current_mahadasha: PlanetName;
  remaining_years: number;
  current_antardasha: PlanetName | null;
  antardasha_remaining_years: number | null;
  antardasha_remaining_days: number | null;
  current_pratyantar: PlanetName | null;
  pratyantar_remaining_days: number | null;
  timeline: DashaTimelineEntry[];
  antardasha_timeline: DashaTimelineEntry[];
  pratyantar_timeline: DashaTimelineEntry[];
};

export type Lagna = {
  sign: string;
  sign_sanskrit: string;
  degree: number;
  lord: PlanetName;
  lord_state: PlanetState;
  lord_sign: string;
  lord_house: number;
  nakshatra: string;
  pada: number;
};

export type Karaka = { karaka: string; planet: PlanetName; degree: number };

export type Chart = {
  datetime_utc: string;
  location: { lat: number; lon: number; place: string };
  ayanamsa: string;
  house_system: string;
  lagna: Lagna;
  planets: Planet[];
  houses: House[];
  dasha: Dasha;
  /** Legacy Jaimini significators — still computed by prashna.py for chart
   *  back-compat, but no longer used in interpretation (per Durga May 12 MOM). */
  chara_karakas?: Karaka[];
  pulse?: { source: "gemini" | "template"; summary: string };
};

export type EvidenceItem = {
  factor: string;
  subject: string;
  detail: string;
  score: number;
  weight: "primary" | "supporting" | "context";
};

export type Verdict = {
  label: string;
  score: number;
  confidence: "high" | "medium" | "low";
};

// ---- House-mapper trace (May 19 Durga MOM #4) -----------------------------

export type TokenMatch = {
  token: string;
  primary_house: number;
  houses: number[];
  ambiguous: boolean;
  override?: boolean;
  /** Present when the token was matched via semantic similarity rather than
   *  a direct dictionary hit. Shows which dictionary word the embedding
   *  matched against, and the cosine similarity score [0, 1]. */
  semantic_match?: {
    matched_word: string;
    similarity: number;
  } | null;
};

export type HouseCandidate = {
  house: number;
  score: number;
  supporting_tokens: string[];
};

export type MappingTrace = {
  tokens: string[];
  /** Stopwords + tokens too short to be meaningful (e.g. articles, pronouns). */
  tokens_dropped?: string[];
  tokens_matched: TokenMatch[];
  tokens_unmatched: string[];
  candidates: HouseCandidate[];
  primary_candidate: number | null;
  match_count: number;
};

export type Intent = {
  /** Human-readable composite label, e.g. "Children / Creativity / Play / Romance". */
  label: string;
  /** Houses chosen for analysis. First entry is the primary house. */
  selected_houses: number[];
  /** Natural significator planets for the selected houses. */
  natural_karakas: PlanetName[];
  /**
   * How the houses were chosen:
   *   - "dictionary"            — single candidate, no LLM needed
   *   - "dictionary+llm"        — LLM picked from multiple candidates
   *   - "dictionary+top_score"  — LLM unavailable, defaulted to top-N
   *   - "domain_map_fallback(*)" — no dictionary match, fell back to old classifier
   */
  source: string;
  /** Reasoning from the LLM pick step (when applicable). */
  llm_reasoning?: string | null;
  /** Full deterministic trace — perfect for the future audit log (MOM #3). */
  mapping?: MappingTrace | null;
  /** Legacy hint; "general" in the dictionary-driven path. */
  domain: string;
};

export type AskResponse = {
  question: string;
  intent: Intent;
  evidence: {
    domain: string;
    label: string;
    primary_houses: number[];
    natural_karakas: PlanetName[];
    /** Removed in the dictionary-driven pipeline; kept optional for back-compat. */
    chara_karaka_role?: string;
    evidence: EvidenceItem[];
    total_score: number;
  };
  verdict: Verdict;
  answer: string;          // markdown — render via `marked`
  answer_source: "gemini" | "template";
  chart: Chart;
};
