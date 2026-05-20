"use client";

import { useEffect, useRef, useState } from "react";

const DIAGRAM = `
flowchart TD
    Q["🌙 You ask a question<br/>at this exact moment"]:::start

    Q --> Chart["✨ The sky is cast<br/><i>Lagna · 9 planets · 12 houses</i>"]
    Q --> Theme["🎯 Your question's theme<br/><i>career · marriage · health · …</i>"]

    Chart --> Houses["🏛️ Which houses<br/>govern this theme?"]
    Theme --> Houses

    Houses --> Lords["👑 What are the<br/>house lords doing?"]
    Houses --> Karakas["⭐ How are the natural<br/>significator planets placed?"]

    Lords --> Timing["⏳ <b>Dasha · Bhukti · Antara</b><br/>Which planets are on duty?<br/><i>years · months · weeks</i>"]
    Karakas --> Timing

    Timing --> Lagna["🪔 Lagna lord<br/>How sincere is the question?"]

    Lagna --> Verdict{"⚖️ The chart weighs in<br/>Favorable · Mixed · Challenging"}

    Verdict --> Reading["📜 Your reading<br/>spoken in the chart's own voice"]:::endNode

    classDef start fill:#3b2a5c,stroke:#8b5cf6,stroke-width:2px,color:#fff
    classDef endNode fill:#5c4a1a,stroke:#d4af37,stroke-width:2px,color:#fff
`;

const LEGEND = [
  { term: "Lagna",                    desc: "the rising sign at the moment of your question — the 1st house" },
  { term: "Houses",                   desc: "12 life areas (self, wealth, partner, career, …) — every question maps to specific houses" },
  { term: "House Lords",              desc: "the planet that rules each house — its current strength tells the story" },
  { term: "Karakas",                  desc: "natural significators — e.g. Venus for marriage, Saturn for career, Jupiter for blessings" },
  { term: "Dasha · Bhukti · Antara",  desc: "three nested time-clocks naming which planets are \"on duty\" — across years, months, and weeks" },
];

export function HowItWorks() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  // Lazy-load mermaid only when the section is opened.
  useEffect(() => {
    if (!open || !ref.current) return;
    let cancelled = false;
    (async () => {
      const mermaid = (await import("mermaid")).default;
      if (cancelled) return;
      mermaid.initialize({
        startOnLoad: false,
        theme: "dark",
        themeVariables: {
          background: "transparent",
          primaryColor: "#1a1b2e",
          primaryTextColor: "#e8e6f0",
          primaryBorderColor: "#8b5cf6",
          lineColor: "#d4af37",
          secondaryColor: "#2a1f3d",
          tertiaryColor: "#0f1123",
          fontFamily: "Outfit, sans-serif",
          fontSize: "14px",
        },
        flowchart: { curve: "basis", padding: 20 },
      });
      const { svg } = await mermaid.render("how-it-works-graph", DIAGRAM);
      if (!cancelled && ref.current) ref.current.innerHTML = svg;
    })();
    return () => { cancelled = true; };
  }, [open]);

  return (
    <details
      className="rounded-xl border border-[rgba(139,92,246,0.2)] bg-gradient-to-br from-[rgba(139,92,246,0.05)] to-[rgba(212,175,55,0.03)] transition-shadow open:shadow-[0_4px_24px_rgba(139,92,246,0.08)]"
      onToggle={(e) => setOpen((e.currentTarget as HTMLDetailsElement).open)}
    >
      <summary className="display flex cursor-pointer items-center gap-2 px-5 py-3 text-sm tracking-wide text-[var(--accent-gold)] [&::-webkit-details-marker]:hidden">
        <span>✨</span>
        How is this answered? — the journey from your question to the reading
        <span className="ml-auto text-[var(--text-muted)] transition-transform [details[open]_&]:rotate-180">▾</span>
      </summary>
      <div className="border-t border-[rgba(139,92,246,0.12)] px-5 pb-5 pt-2">
        <p className="mx-auto my-4 max-w-2xl text-center text-sm italic text-[var(--text-muted)]">
          The instant you ask, the sky above you is read like an open book.
          Your question and the moment meet — and together they shape the answer.
        </p>
        <div
          ref={ref}
          className="flex justify-center overflow-x-auto rounded-lg bg-[rgba(10,11,22,0.4)] p-5"
        >
          {/* mermaid renders here */}
          <span className="text-[var(--text-muted)]">Loading diagram…</span>
        </div>
        <div className="mt-4 grid grid-cols-1 gap-2 md:grid-cols-2">
          {LEGEND.map((l) => (
            <div
              key={l.term}
              className="rounded-lg border border-l-[2px] border-[var(--border-glass)] border-l-[var(--accent-purple)] bg-[rgba(15,17,35,0.45)] p-2.5"
            >
              <div className="display text-xs tracking-wider text-[var(--accent-gold)]">{l.term}</div>
              <div className="mt-1 text-xs leading-relaxed text-[var(--text-muted)]">{l.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </details>
  );
}
