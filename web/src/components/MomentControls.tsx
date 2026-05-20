"use client";

import { useCallback, useEffect, useState } from "react";
import { PRESET_PLACES } from "@/lib/utils";

export type MomentValue = {
  date: string;       // YYYY-MM-DD
  time: string;       // HH:mm
  lat: number;
  lon: number;
  place: string;      // human label for display + API
};

/**
 * Stable placeholder used as the SSR/hydration initial state. Date/time are
 * left blank so the server-rendered HTML matches the first client render.
 * Pages should call `defaultMoment()` from inside a `useEffect` to populate
 * the actual "now" once mounted on the client.
 */
export function emptyMoment(): MomentValue {
  return {
    date: "",
    time: "",
    lat: PRESET_PLACES[0].lat,
    lon: PRESET_PLACES[0].lon,
    place: PRESET_PLACES[0].name,
  };
}

/**
 * Returns the current local date + time. Non-deterministic — only call this
 * on the client (inside an effect or event handler), never in useState's
 * initializer, otherwise SSR hydration will mismatch.
 */
export function defaultMoment(): MomentValue {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return {
    date: `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`,
    time: `${pad(now.getHours())}:${pad(now.getMinutes())}`,
    lat: PRESET_PLACES[0].lat,
    lon: PRESET_PLACES[0].lon,
    place: PRESET_PLACES[0].name,
  };
}

/**
 * Convert (date, time) in the user's local timezone to an ISO 8601 string
 * the FastAPI backend understands. Returns null if either field is empty.
 */
export function toIsoWhen(v: MomentValue): string | null {
  if (!v.date || !v.time) return null;
  return new Date(`${v.date}T${v.time}:00`).toISOString();
}

export function MomentControls({
  value,
  onChange,
}: {
  value: MomentValue;
  onChange: (v: MomentValue) => void;
}) {
  // "__custom__" sentinel matches the old vanilla UI behaviour for custom lat/lon entry.
  const [isCustom, setIsCustom] = useState(false);

  // If the value's place doesn't match any preset, treat it as custom.
  useEffect(() => {
    if (!PRESET_PLACES.find((p) => p.name === value.place)) setIsCustom(true);
  }, [value.place]);

  const setNow = useCallback(() => {
    const fresh = defaultMoment();
    onChange({ ...value, date: fresh.date, time: fresh.time });
  }, [onChange, value]);

  const useGeo = useCallback(() => {
    if (!navigator.geolocation) {
      alert("Geolocation not supported in this browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setIsCustom(true);
        onChange({
          ...value,
          lat: Number(pos.coords.latitude.toFixed(4)),
          lon: Number(pos.coords.longitude.toFixed(4)),
          place: "Custom location",
        });
      },
      () => alert("Could not get location."),
      { timeout: 5000 }
    );
  }, [onChange, value]);

  return (
    <section className="glass mb-4 flex flex-wrap items-end gap-x-6 gap-y-3 p-4 text-sm">
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-[var(--text-muted)]">
          📅 Date
          <input
            type="date"
            value={value.date}
            onChange={(e) => onChange({ ...value, date: e.target.value })}
            className="rounded-md border border-[var(--border-glass)] bg-[rgba(10,11,22,0.7)] px-2 py-1 text-[var(--text-main)] focus:border-[var(--accent-purple)] focus:outline-none"
          />
        </label>
        <label className="flex flex-col gap-1 text-[var(--text-muted)]">
          🕒 Time
          <input
            type="time"
            step={60}
            value={value.time}
            onChange={(e) => onChange({ ...value, time: e.target.value })}
            className="rounded-md border border-[var(--border-glass)] bg-[rgba(10,11,22,0.7)] px-2 py-1 text-[var(--text-main)] focus:border-[var(--accent-purple)] focus:outline-none"
          />
        </label>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-[var(--text-muted)]">
          📍 Place
          <select
            value={isCustom ? "__custom__" : value.place}
            onChange={(e) => {
              if (e.target.value === "__custom__") {
                setIsCustom(true);
                onChange({ ...value, place: "Custom location" });
              } else {
                const p = PRESET_PLACES.find((p) => p.name === e.target.value);
                if (!p) return;
                setIsCustom(false);
                onChange({ ...value, lat: p.lat, lon: p.lon, place: p.name });
              }
            }}
            className="rounded-md border border-[var(--border-glass)] bg-[rgba(10,11,22,0.7)] px-2 py-1 text-[var(--text-main)] focus:border-[var(--accent-purple)] focus:outline-none"
          >
            {PRESET_PLACES.map((p) => (
              <option key={p.name} value={p.name}>{p.name}</option>
            ))}
            <option value="__custom__">Custom lat/lon…</option>
          </select>
        </label>

        {isCustom && (
          <div className="flex gap-2">
            <input
              type="number"
              step="0.0001"
              placeholder="Lat"
              value={value.lat}
              onChange={(e) => onChange({ ...value, lat: parseFloat(e.target.value) })}
              className="w-24 rounded-md border border-[var(--border-glass)] bg-[rgba(10,11,22,0.7)] px-2 py-1 text-[var(--text-main)] focus:border-[var(--accent-purple)] focus:outline-none"
            />
            <input
              type="number"
              step="0.0001"
              placeholder="Lon"
              value={value.lon}
              onChange={(e) => onChange({ ...value, lon: parseFloat(e.target.value) })}
              className="w-24 rounded-md border border-[var(--border-glass)] bg-[rgba(10,11,22,0.7)] px-2 py-1 text-[var(--text-main)] focus:border-[var(--accent-purple)] focus:outline-none"
            />
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={setNow}
          title="Set to current moment"
          className="rounded-md border border-[var(--border-glass)] bg-[rgba(15,17,35,0.7)] px-3 py-1 text-[var(--text-muted)] transition hover:border-[var(--accent-purple)] hover:text-[var(--text-main)]"
        >
          ⟳ Now
        </button>
        <button
          type="button"
          onClick={useGeo}
          title="Use my browser location"
          className="rounded-md border border-[var(--border-glass)] bg-[rgba(15,17,35,0.7)] px-3 py-1 text-[var(--text-muted)] transition hover:border-[var(--accent-purple)] hover:text-[var(--text-main)]"
        >
          📍 My location
        </button>
      </div>
    </section>
  );
}
