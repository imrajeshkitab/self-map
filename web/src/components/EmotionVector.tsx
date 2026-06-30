"use client";

import { DIMENSIONS, dimensionLabel, type EmotionScores, type DominantTheme } from "@/lib/emotion";

/**
 * The 10-dimension emotional vector as labelled bars (0-100), centred on a
 * neutral 50 marker so it's clear which dimensions are elevated vs subdued.
 * Dominant themes are highlighted.
 */
export function EmotionVector({
  scores,
  dominant,
}: {
  scores: EmotionScores;
  dominant: DominantTheme[];
}) {
  const dominantSet = new Set(dominant.map((d) => d.dimension));

  return (
    <div className="flex flex-col gap-2">
      {DIMENSIONS.map((dim) => {
        const score = scores[dim] ?? 50;
        const isDominant = dominantSet.has(dim);
        // Color by how far from neutral (50) and direction.
        const dist = Math.abs(score - 50);
        const high = score >= 50;
        const color =
          dist < 8
            ? "var(--text-muted)"
            : high
              ? "#86efac"
              : "#f5a97f";
        return (
          <div key={dim} className="flex items-center gap-3 text-xs">
            <div className="w-32 shrink-0 text-right text-[var(--text-muted)]">
              {dimensionLabel(dim)}
            </div>
            {/* track */}
            <div className="relative h-5 flex-1 overflow-hidden rounded-md border border-[var(--border-glass)] bg-[rgba(10,11,22,0.5)]">
              {/* neutral 50 marker */}
              <div
                className="absolute top-0 h-full w-px bg-[var(--border-strong)]"
                style={{ left: "50%" }}
              />
              {/* bar grows from 50 toward the score */}
              <div
                className="absolute top-0 h-full"
                style={{
                  left: high ? "50%" : `${score}%`,
                  width: `${dist}%`,
                  backgroundColor: color,
                  opacity: isDominant ? 0.9 : 0.55,
                }}
              />
            </div>
            <div
              className={`w-8 shrink-0 text-right tabular-nums ${
                isDominant ? "font-semibold text-[var(--accent-gold)]" : "text-[var(--text-main)]"
              }`}
            >
              {score}
            </div>
          </div>
        );
      })}
      <div className="mt-1 flex items-center gap-4 text-[0.65rem] text-[var(--text-muted)]">
        <span>0</span>
        <span className="flex-1 text-center">↑ neutral 50 (midline)</span>
        <span>100</span>
      </div>
    </div>
  );
}
