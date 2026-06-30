"use client";

import { useCallback, useEffect, useState } from "react";
import { emotionDaily, type EmotionResponse } from "@/lib/emotion";
import { EmotionVector } from "@/components/EmotionVector";
import { EmotionTrace } from "@/components/EmotionTrace";

// Sensible default birth + a couple of presets so the page is usable instantly.
const PRESETS = [
  { label: "Sample · Hyderabad", dob: "1995-08-20", tob: "14:30", lat: 17.4399, lon: 78.3489, place: "Hyderabad" },
  { label: "Sample · Delhi", dob: "1988-03-12", tob: "06:45", lat: 28.6139, lon: 77.209, place: "Delhi" },
];

export default function DailyThemeV2Page() {
  const [dob, setDob] = useState("1995-08-20");
  const [tob, setTob] = useState("14:30");
  const [lat, setLat] = useState("17.4399");
  const [lon, setLon] = useState("78.3489");
  const [place, setPlace] = useState("Hyderabad");
  // "as of" — the moment we read the theme for. Empty = now.
  const [onDate, setOnDate] = useState("");
  const [onTime, setOnTime] = useState("");

  const [data, setData] = useState<EmotionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async () => {
    if (!dob) return;
    setLoading(true);
    setError(null);
    try {
      const on =
        onDate && onTime
          ? `${onDate}T${onTime}:00`
          : onDate
            ? `${onDate}T12:00:00`
            : undefined;
      const res = await emotionDaily({
        dob,
        tob: tob || "12:00",
        lat: Number(lat),
        lon: Number(lon),
        place,
        on,
      });
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong. Is the API running?");
    } finally {
      setLoading(false);
    }
  }, [dob, tob, lat, lon, place, onDate, onTime]);

  // Compute once on first load so the page isn't empty.
  useEffect(() => {
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- run once on mount
  }, []);

  return (
    <>
      <header className="mb-6 text-center">
        <h1 className="text-4xl text-[var(--accent-gold)]">Daily Theme v2</h1>
        <p className="mt-1 text-sm text-[var(--text-muted)]">
          Your emotional weather today — natal Moon × current Dasha × transit Moon, with every
          calculation shown.
        </p>
      </header>

      {/* Inputs */}
      <section className="glass mb-5 flex flex-col gap-4 p-5">
        <div className="flex flex-wrap gap-2">
          {PRESETS.map((p) => (
            <button
              key={p.label}
              type="button"
              onClick={() => {
                setDob(p.dob); setTob(p.tob); setLat(String(p.lat));
                setLon(String(p.lon)); setPlace(p.place);
              }}
              className="rounded-full border border-[var(--border-glass)] bg-[rgba(15,17,35,0.7)] px-3 py-1 text-xs text-[var(--text-muted)] transition hover:border-[rgba(139,92,246,0.4)] hover:text-[var(--text-main)]"
            >
              {p.label}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <Field label="Date of birth">
            <input type="date" value={dob} onChange={(e) => setDob(e.target.value)} className={inputCls} />
          </Field>
          <Field label="Time of birth">
            <input type="time" value={tob} onChange={(e) => setTob(e.target.value)} className={inputCls} />
          </Field>
          <Field label="Birth place">
            <input value={place} onChange={(e) => setPlace(e.target.value)} className={inputCls} placeholder="City" />
          </Field>
          <Field label="Latitude">
            <input value={lat} onChange={(e) => setLat(e.target.value)} className={inputCls} />
          </Field>
          <Field label="Longitude">
            <input value={lon} onChange={(e) => setLon(e.target.value)} className={inputCls} />
          </Field>
        </div>

        <div className="border-t border-[var(--border-glass)] pt-3">
          <div className="mb-2 text-xs uppercase tracking-widest text-[var(--text-muted)]">
            Read theme for — leave blank for now
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <Field label="On date">
              <input type="date" value={onDate} onChange={(e) => setOnDate(e.target.value)} className={inputCls} />
            </Field>
            <Field label="On time">
              <input type="time" value={onTime} onChange={(e) => setOnTime(e.target.value)} className={inputCls} />
            </Field>
            <div className="flex items-end">
              <button
                type="button"
                onClick={run}
                disabled={loading || !dob}
                className="w-full rounded-lg border border-[rgba(212,175,55,0.4)] bg-gradient-to-br from-[rgba(139,92,246,0.4)] to-[rgba(212,175,55,0.25)] px-4 py-2 text-sm font-medium text-white transition hover:shadow-[0_4px_18px_rgba(139,92,246,0.3)] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "Computing…" : "Compute theme →"}
              </button>
            </div>
          </div>
        </div>
      </section>

      {error && (
        <section className="my-6 rounded-lg border border-[rgba(248,113,113,0.35)] bg-[rgba(248,113,113,0.08)] p-4 text-sm text-[#f87171]">
          {error}
        </section>
      )}

      {data && (
        <section className="flex flex-col gap-5">
          {/* Chart-state summary */}
          <div className="glass p-4 text-xs">
            <div className="mb-2 text-[0.65rem] uppercase tracking-widest text-[var(--text-muted)]">
              Computed from
            </div>
            <div className="grid grid-cols-1 gap-1 sm:grid-cols-3">
              <KV k="Natal Moon" v={data.inputs.natal_moon} />
              <KV k="Current DBA" v={data.inputs.dba} />
              <KV k="Transit Moon" v={data.inputs.transit_moon} />
            </div>
            <div className="mt-2 text-[0.65rem] text-[var(--text-muted)]">
              as of {new Date(data.inputs.as_of).toLocaleString()}
              {data.chandra_ashtama && (
                <span className="ml-2 rounded-full border border-[rgba(245,169,127,0.4)] px-2 py-[1px] text-[#f5a97f]">
                  Chandra Ashtama
                </span>
              )}
            </div>
          </div>

          {/* Emotional vector */}
          <div>
            <h2 className="display mb-1 text-lg text-[var(--accent-gold)]">Emotional vector</h2>
            <p className="mb-3 text-xs text-[var(--text-muted)]">
              Ten dimensions, 0–100. Gold = a dominant theme for the day.
            </p>
            <div className="glass p-4">
              <EmotionVector scores={data.scores} dominant={data.dominant_themes} />
            </div>
          </div>

          {/* Narrative */}
          <div className="glass border-l-[3px] border-[var(--accent-purple)] p-4">
            <div className="mb-2 inline-block text-xs font-semibold uppercase tracking-widest text-[var(--accent-purple)]">
              Today&apos;s reading
            </div>
            <p className="text-sm leading-relaxed text-[var(--text-main)]">{data.narrative}</p>
          </div>

          {/* Full transparency trace */}
          <div>
            <h2 className="display mb-1 text-lg text-[var(--accent-gold)]">How this was calculated</h2>
            <p className="mb-3 text-xs text-[var(--text-muted)]">
              Every step, in order. Click any step to see the rule it applied and the exact numbers it produced.
            </p>
            <EmotionTrace trace={data.trace} />
          </div>

          <p className="text-center text-[0.65rem] italic text-[var(--text-muted)]">
            {data._model_note}
          </p>
        </section>
      )}
    </>
  );
}

const inputCls =
  "w-full rounded-lg border border-[var(--border-glass)] bg-[rgba(10,11,22,0.7)] p-2 text-sm text-[var(--text-main)] focus:border-[var(--accent-purple)] focus:outline-none";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[0.65rem] uppercase tracking-widest text-[var(--text-muted)]">{label}</span>
      {children}
    </label>
  );
}

function KV({ k, v }: { k: string; v: string }) {
  return (
    <div>
      <span className="text-[var(--text-muted)]">{k}: </span>
      <span className="text-[var(--text-main)]">{v}</span>
    </div>
  );
}
