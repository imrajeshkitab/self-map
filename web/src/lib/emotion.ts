// Client + types for the Daily Emotional Analysis Engine (/emotion/daily).
// Separate from the Prashna types — this is the emotional-vector model.

import { API_BASE } from "./api";

export type EmotionScores = Record<string, number>;

export type DominantTheme = { dimension: string; score: number };

export type TraceStep = {
  step: number;
  title: string;
  narration: string;
  // `data` is step-specific and freeform; rendered generically by the UI.
  data: Record<string, unknown>;
};

export type EmotionResponse = {
  inputs: {
    birth: string;
    as_of: string;
    place: string;
    lat: number;
    lon: number;
    natal_moon: string;
    dba: string;
    transit_moon: string;
  };
  scores: EmotionScores;
  dominant_themes: DominantTheme[];
  chandra_ashtama: boolean;
  narrative: string;
  trace: TraceStep[];
  _model_note: string;
};

export type EmotionParams = {
  dob: string; // YYYY-MM-DD
  tob?: string; // HH:MM
  lat?: number;
  lon?: number;
  place?: string;
  on?: string; // ISO datetime; defaults to now on the backend
};

export async function emotionDaily(params: EmotionParams): Promise<EmotionResponse> {
  const url = new URL(`${API_BASE}/emotion/daily`);
  url.searchParams.set("dob", params.dob);
  if (params.tob) url.searchParams.set("tob", params.tob);
  if (params.lat !== undefined) url.searchParams.set("lat", String(params.lat));
  if (params.lon !== undefined) url.searchParams.set("lon", String(params.lon));
  if (params.place) url.searchParams.set("place", params.place);
  if (params.on) url.searchParams.set("on", params.on);

  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) throw new Error(`/emotion/daily failed: ${res.status}`);
  return res.json();
}

// The 10 canonical dimensions, in display order.
export const DIMENSIONS = [
  "sensitivity", "stress", "confidence", "clarity", "motivation",
  "attachment", "patience", "impulsiveness", "social_engagement", "focus",
] as const;

export function dimensionLabel(d: string): string {
  return d
    .split("_")
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(" ");
}
