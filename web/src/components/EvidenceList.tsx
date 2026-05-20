"use client";

import { useState } from "react";
import type { EvidenceItem } from "@/lib/types";

export function EvidenceList({ items }: { items: EvidenceItem[] }) {
  return (
    <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
      {items.map((e, i) => (
        <Row key={i} item={e} />
      ))}
    </div>
  );
}

function Row({ item }: { item: EvidenceItem }) {
  const [open, setOpen] = useState(false);
  const score = item.score;
  const chipClass =
    score > 0 ? "bg-[rgba(134,239,172,0.15)] text-[#86efac]" :
    score < 0 ? "bg-[rgba(248,113,113,0.15)] text-[#f87171]" :
                "bg-white/5 text-[var(--text-muted)]";

  return (
    <button
      type="button"
      onClick={() => setOpen((v) => !v)}
      className="glass cursor-pointer p-3 text-left transition hover:-translate-y-[1px] hover:border-[rgba(139,92,246,0.4)]"
    >
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className="display text-sm text-[var(--accent-gold)]">
          {item.factor}
          <span className="ml-2 text-[0.6rem] uppercase tracking-widest text-[var(--text-muted)]">
            {item.weight === "primary" ? <span className="text-[var(--accent-purple)]">{item.weight}</span> : item.weight}
          </span>
        </span>
        <span className={`whitespace-nowrap rounded-full px-2 py-[2px] text-[0.65rem] font-bold tracking-widest ${chipClass}`}>
          {score > 0 ? "+" : ""}{score}
        </span>
      </div>
      <div className="text-sm text-[var(--text-main)]">{item.subject}</div>
      {open && (
        <div className="mt-2 text-xs leading-relaxed text-[var(--text-muted)]">
          {item.detail}
        </div>
      )}
    </button>
  );
}
