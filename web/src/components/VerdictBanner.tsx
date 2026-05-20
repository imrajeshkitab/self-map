import type { Verdict } from "@/lib/types";

const VERDICT_STYLES: Record<string, { bg: string; border: string; text: string }> = {
  "strongly favorable": {
    bg: "linear-gradient(135deg, rgba(134,239,172,0.12), rgba(212,175,55,0.08))",
    border: "rgba(134,239,172,0.35)",
    text: "#86efac",
  },
  favorable: {
    bg: "linear-gradient(135deg, rgba(134,239,172,0.12), rgba(212,175,55,0.08))",
    border: "rgba(134,239,172,0.35)",
    text: "#86efac",
  },
  mixed: {
    bg: "linear-gradient(135deg, rgba(212,175,55,0.12), rgba(139,92,246,0.06))",
    border: "rgba(212,175,55,0.35)",
    text: "#d4af37",
  },
  challenging: {
    bg: "linear-gradient(135deg, rgba(248,113,113,0.12), rgba(139,92,246,0.06))",
    border: "rgba(248,113,113,0.35)",
    text: "#f87171",
  },
  "strongly challenging": {
    bg: "linear-gradient(135deg, rgba(248,113,113,0.12), rgba(139,92,246,0.06))",
    border: "rgba(248,113,113,0.35)",
    text: "#f87171",
  },
};

export function VerdictBanner({
  question,
  intentLabel,
  verdict,
}: {
  question: string;
  intentLabel: string;
  verdict: Verdict;
}) {
  const s = VERDICT_STYLES[verdict.label] ?? VERDICT_STYLES.mixed;
  return (
    <div
      className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border p-5"
      style={{ background: s.bg, borderColor: s.border }}
    >
      <div className="min-w-[250px] flex-[1_1_60%] text-[0.95rem] leading-snug text-[var(--text-main)]">
        <span className="text-[var(--text-muted)]">You asked about </span>
        <strong className="font-medium text-[var(--accent-gold)]">{intentLabel}</strong>
        :<br />
        &ldquo;{question}&rdquo;
      </div>
      <div className="text-right">
        <div className="display text-2xl capitalize" style={{ color: s.text }}>
          {verdict.label}
        </div>
        <div className="mt-1 text-xs uppercase tracking-widest text-[var(--text-muted)]">
          Score {verdict.score} · {verdict.confidence} confidence
        </div>
      </div>
    </div>
  );
}
