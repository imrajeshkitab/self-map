"use client";

import { useState } from "react";
import { search } from "@/lib/api";

type Item = Record<string, unknown> & {
  category?: string;
  name?: string;
  english_name?: string;
  sanskrit_name?: string;
  significance?: string;
  score?: number;
};

type TrinitySlot = Item | null;

const QUICK = ["wealth", "relationships", "health", "spiritual growth", "career", "marriage"];

export function CosmicSearch() {
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [trinity, setTrinity] = useState<{ house: TrinitySlot; planet: TrinitySlot; zodiac: TrinitySlot } | null>(null);
  const [overflow, setOverflow] = useState<Item[]>([]);

  const run = async (query: string) => {
    const term = query.trim();
    if (!term) return;
    setQ(term);
    setLoading(true);
    setError(null);
    setTrinity(null);
    setOverflow([]);
    try {
      const res = await search(term, { mode: "trinity", topK: 5 });
      setTrinity((res.trinity as typeof trinity) ?? null);
      setOverflow((res.overflow as Item[]) ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed. Is the API running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="mx-auto mb-10 max-w-3xl">
      <div className="glass flex items-center gap-2 p-3">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run(q)}
          placeholder="Ask about career, marriage, spirituality…"
          className="flex-1 bg-transparent px-2 py-1 text-[var(--text-main)] outline-none placeholder:text-[var(--text-muted)]"
        />
        <button
          type="button"
          onClick={() => run(q)}
          className="rounded-md border border-[rgba(212,175,55,0.4)] bg-gradient-to-br from-[rgba(139,92,246,0.4)] to-[rgba(212,175,55,0.25)] px-3 py-1 text-sm text-white transition hover:shadow-[0_2px_12px_rgba(139,92,246,0.3)]"
          aria-label="Search"
        >
          Search
        </button>
      </div>

      <div className="mt-3 flex flex-wrap justify-center gap-2">
        {QUICK.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => run(p)}
            className="rounded-full border border-[var(--border-glass)] bg-[rgba(15,17,35,0.7)] px-3 py-1 text-xs text-[var(--text-muted)] transition hover:border-[rgba(139,92,246,0.4)] hover:text-[var(--text-main)]"
          >
            {p}
          </button>
        ))}
      </div>

      {loading && (
        <div className="mt-6 flex justify-center text-sm text-[var(--text-muted)]">
          <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-[var(--border-glass)] border-t-[var(--accent-purple)]" />
          Searching…
        </div>
      )}
      {error && (
        <div className="mt-6 rounded-lg border border-[rgba(248,113,113,0.35)] bg-[rgba(248,113,113,0.08)] p-3 text-sm text-[#f87171]">
          {error}
        </div>
      )}

      {trinity && (
        <div className="mt-6">
          <h3 className="display mb-2 text-sm uppercase tracking-widest text-[var(--accent-gold)]">
            Trinity — top match per category
          </h3>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <SlotCard label="House"  item={trinity.house} />
            <SlotCard label="Planet" item={trinity.planet} />
            <SlotCard label="Sign"   item={trinity.zodiac} />
          </div>
        </div>
      )}

      {overflow.length > 0 && (
        <div className="mt-6">
          <h3 className="display mb-2 text-sm uppercase tracking-widest text-[var(--accent-gold)]">
            More matches
          </h3>
          <ul className="flex flex-col gap-2">
            {overflow.slice(0, 5).map((it, i) => (
              <li
                key={i}
                className="glass flex items-baseline justify-between gap-3 px-3 py-2 text-sm"
              >
                <span>
                  <span className="text-[var(--text-muted)]">{it.category}:</span>{" "}
                  <span className="text-[var(--text-main)]">{(it.english_name as string) || (it.name as string)}</span>
                  {it.sanskrit_name ? (
                    <span className="ml-2 text-[var(--text-muted)]">({it.sanskrit_name as string})</span>
                  ) : null}
                </span>
                {typeof it.score === "number" && (
                  <span className="text-xs text-[var(--text-muted)]">{it.score.toFixed(2)}</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function SlotCard({ label, item }: { label: string; item: TrinitySlot }) {
  if (!item) {
    return (
      <div className="glass p-4 text-sm opacity-60">
        <div className="display text-xs uppercase tracking-widest text-[var(--text-muted)]">{label}</div>
        <div className="mt-2 text-[var(--text-muted)]">no strong match</div>
      </div>
    );
  }
  return (
    <div className="glass p-4 text-sm">
      <div className="display text-xs uppercase tracking-widest text-[var(--accent-purple)]">{label}</div>
      <div className="mt-1 text-base text-[var(--accent-gold)]">
        {(item.english_name as string) || (item.name as string)}
        {item.sanskrit_name ? (
          <span className="ml-2 text-xs font-normal text-[var(--text-muted)]">({item.sanskrit_name as string})</span>
        ) : null}
      </div>
      {item.significance ? (
        <p className="mt-2 line-clamp-4 text-xs leading-relaxed text-[var(--text-muted)]">
          {item.significance as string}
        </p>
      ) : null}
      {typeof item.score === "number" && (
        <div className="mt-2 text-[0.65rem] uppercase tracking-widest text-[var(--text-muted)]">
          score {item.score.toFixed(2)}
        </div>
      )}
    </div>
  );
}
