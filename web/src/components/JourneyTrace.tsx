/**
 * JourneyTrace
 * ============
 * Renders the actual step-by-step pipeline trace for a submitted question.
 * Replaces the static conceptual mermaid with a live "this is what happened
 * for YOUR query" view — removing the black-box feel.
 *
 * Each stage shows three slots: Input · Logic · Output, plus a small note
 * for the path actually taken (e.g. "single candidate → no LLM needed").
 *
 * Data flow:
 *   AskResponse (from /ask) → this component → vertical stack of stage cards.
 *
 * Stage map (mirrors backend/interpret.py + house_mapper.py):
 *   ① Tokenize        — strip stopwords
 *   ② Dictionary look — match each token against house_dictionary.json
 *   ③ Score candidates — confidence-weighted aggregation
 *   ④ Pick houses     — branched: single / LLM / fallback
 *   ⑤ Chart computation (parallel to ①-④)
 *   ⑥ Evidence        — deterministic scoring per factor
 *   ⑦ Verdict         — threshold check
 *   ⑧ Synthesis       — Gemini writes the markdown reading
 */

import type { AskResponse, EvidenceItem, TokenMatch } from "@/lib/types";
import { cn } from "@/lib/utils";

type StageType = "det" | "llm";

/** Mirrors `house_mapper.SEMANTIC_THRESHOLD` — kept in sync by hand.
 *  Displayed in the trace UI so the user can see exactly what bar a
 *  semantic match had to clear. */
const SEM_THRESHOLD = 0.70;

export function JourneyTrace({ data }: { data: AskResponse }) {
  const question = data.question;
  const mapping = data.intent.mapping ?? null;
  const intent = data.intent;
  const chart = data.chart;
  const evidence = data.evidence;
  const verdict = data.verdict;

  // --- derive small displays ----------------------------------------------
  const verdictColor = verdictTextColor(verdict.label);
  const topPositive = [...evidence.evidence]
    .filter((e) => typeof e.score === "number" && e.score > 0)
    .sort((a, b) => b.score - a.score)[0];
  const topNegative = [...evidence.evidence]
    .filter((e) => typeof e.score === "number" && e.score < 0)
    .sort((a, b) => a.score - b.score)[0];

  return (
    <div className="flex flex-col gap-3">
      <p className="text-xs italic text-[var(--text-muted)] text-center">
        This is exactly what the system did with your question — every step,
        every input and output. No black box.
      </p>

      {/* ① Tokenize */}
      <Stage
        n={1}
        title="Tokenize"
        type="det"
        skipped={!mapping}
        skipReason={!mapping ? "No mapping trace (fell back to legacy classifier)." : undefined}
      >
        <KV label="Input">
          <code className="text-[var(--text-main)]">&ldquo;{question}&rdquo;</code>
        </KV>
        <KV label="Logic">
          lowercase · strip punctuation · drop stopwords (articles, pronouns,
          copulas, modals) and 1-letter tokens
        </KV>
        <KV label="Output (kept)">
          <ChipRow tokens={mapping?.tokens ?? []} variant="kept" />
        </KV>
        {mapping?.tokens_dropped && mapping.tokens_dropped.length > 0 && (
          <KV label="Dropped">
            <ChipRow tokens={mapping.tokens_dropped} variant="dropped" />
          </KV>
        )}
      </Stage>

      <Arrow />

      {/* ② Dictionary lookup */}
      <Stage
        n={2}
        title="Dictionary lookup"
        type="det"
        skipped={!mapping}
      >
        <KV label="Input">
          <ChipRow tokens={mapping?.tokens ?? []} variant="kept" />
        </KV>
        <KV label="Logic">
          <span className="block">
            1.&nbsp;exact match in <code>house_dictionary.json</code> (5,070
            entries)
          </span>
          <span className="block">2.&nbsp;light stemming — plural collapse, <code>-ing</code> drop</span>
          <span className="block">
            3.&nbsp;<code>PRIMARY_OVERRIDES</code> table re-anchors ~40 critical terms
          </span>
          <span className="block">
            4.&nbsp;<strong className="text-[var(--accent-gold)]">semantic fallback</strong>{" "}
            — embed the token (sentence-transformer, 384-dim) and find the
            closest dictionary word by cosine similarity (threshold {SEM_THRESHOLD})
          </span>
        </KV>
        <KV label="Output (matched)">
          {mapping && mapping.tokens_matched.length > 0 ? (
            <ul className="flex flex-col gap-1.5 text-xs">
              {mapping.tokens_matched.map((m) => (
                <li key={m.token} className="flex flex-wrap items-center gap-2">
                  <code className="rounded bg-white/5 px-1.5 py-0.5 text-[var(--accent-gold)]">
                    {m.token}
                  </code>
                  <span className="text-[var(--text-muted)]">→</span>
                  <span>
                    <strong className="text-[var(--text-main)]">H{m.primary_house}</strong>{" "}
                    {m.houses.length > 1 && (
                      <span className="text-[var(--text-muted)]">
                        (also{" "}
                        {m.houses
                          .filter((h) => h !== m.primary_house)
                          .map((h) => `H${h}`)
                          .join(", ")}
                        )
                      </span>
                    )}
                  </span>
                  {m.override && (
                    <span
                      className="rounded-full bg-[rgba(139,92,246,0.15)] px-1.5 text-[0.6rem] uppercase tracking-widest text-[var(--accent-purple)]"
                      title="PRIMARY_OVERRIDES table — manually re-anchored"
                    >
                      override
                    </span>
                  )}
                  {m.ambiguous && !m.override && (
                    <span className="rounded-full bg-[rgba(212,175,55,0.15)] px-1.5 text-[0.6rem] uppercase tracking-widest text-[var(--accent-gold)]">
                      ambiguous
                    </span>
                  )}
                  {m.semantic_match && (
                    <SemanticBadge
                      matched={m.semantic_match.matched_word}
                      similarity={m.semantic_match.similarity}
                    />
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <em className="text-[var(--text-muted)]">no matches</em>
          )}
        </KV>
        {mapping?.tokens_unmatched && mapping.tokens_unmatched.length > 0 && (
          <KV label="Unmatched">
            <ChipRow tokens={mapping.tokens_unmatched} variant="dropped" />
            <div className="mt-1 text-[0.65rem] italic text-[var(--text-muted)]">
              tokens with no exact, stemmed, override, or semantic match above threshold
            </div>
          </KV>
        )}
      </Stage>

      <Arrow />

      {/* ③ Score candidates */}
      <Stage
        n={3}
        title="Score candidates"
        type="det"
        skipped={!mapping || mapping.candidates.length === 0}
      >
        <KV label="Input">
          {mapping?.match_count ?? 0} token match{mapping?.match_count === 1 ? "" : "es"}
        </KV>
        <KV label="Logic">
          each matched token contributes <code>1.0 / n</code> to every house it
          touches (where <code>n</code> = number of candidate houses for that
          token); a token&apos;s primary house gets an extra{" "}
          <code>+0.25</code> bonus
        </KV>

        {/* NEW: per-token math breakdown so the calculation is fully visible. */}
        {mapping && mapping.tokens_matched.length > 0 && (
          <KV label="Per-token math">
            <ul className="flex flex-col gap-2 text-xs">
              {mapping.tokens_matched.map((m) => (
                <TokenMath key={m.token} match={m} />
              ))}
            </ul>
          </KV>
        )}

        <KV label="Output (ranked)">
          {mapping && mapping.candidates.length > 0 ? (
            <ul className="flex flex-col gap-1 text-xs">
              {mapping.candidates.slice(0, 5).map((c, i) => (
                <li key={c.house} className="flex flex-wrap items-center gap-2">
                  <span className="font-mono w-6 text-right text-[var(--text-muted)]">#{i + 1}</span>
                  <strong className="text-[var(--text-main)]">H{c.house}</strong>
                  <span className="text-[var(--accent-gold)]">score {c.score.toFixed(2)}</span>
                  <span className="text-[var(--text-muted)]">·</span>
                  <span className="text-[var(--text-muted)]">
                    from {c.supporting_tokens.map((t) => `"${t}"`).join(", ")}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <em className="text-[var(--text-muted)]">no candidates</em>
          )}
        </KV>
      </Stage>

      <Arrow />

      {/* ④ Pick houses — polarity-aware: shows favourable vs unfavourable */}
      <Stage n={4} title="Classify houses (polarity)" type={pickStageType(intent.source)}>
        <KV label="Path taken">
          <PathBadge source={intent.source} candidateCount={mapping?.candidates.length ?? 0} />
        </KV>
        <KV label="Logic">{pickStageLogic(intent.source)}</KV>

        {/* Intent classification — what the LLM thought the user wanted */}
        {intent.user_intent && (
          <KV label="User intent">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="rounded-full bg-[rgba(139,92,246,0.15)] px-2 py-[1px] text-[0.65rem] uppercase tracking-widest text-[var(--accent-purple)]">
                {intent.user_intent}
              </span>
              {intent.negation_detected && (
                <span
                  className="rounded-full bg-[rgba(248,113,113,0.15)] px-2 py-[1px] text-[0.65rem] uppercase tracking-widest text-[#f87171]"
                  title="A polarity-flipping word ('avoid', 'not', 'lose', 'escape'…) was detected — the LLM flipped the lane assignments accordingly"
                >
                  negation
                </span>
              )}
              {intent.intent_summary && (
                <span className="text-[var(--text-muted)] italic">
                  &ldquo;{intent.intent_summary}&rdquo;
                </span>
              )}
            </div>
          </KV>
        )}

        {intent.llm_reasoning && (
          <KV label="LLM reasoning">
            <em className="text-[var(--text-main)]">&ldquo;{intent.llm_reasoning}&rdquo;</em>
          </KV>
        )}

        {/* Two-column lane display — favourable left, unfavourable right */}
        <KV label="Output">
          <PolarityColumns
            favourable={intent.favourable_houses ?? intent.selected_houses}
            unfavourable={intent.unfavourable_houses ?? []}
            llmAdded={intent.llm_added_houses ?? []}
          />
        </KV>
        <KV label="Karakas">
          <ChipRow tokens={intent.natural_karakas} variant="planet" />
          <span className="ml-2 text-[0.65rem] text-[var(--text-muted)]">
            (derived from favourable houses only)
          </span>
        </KV>
        <KV label="Label">
          <span className="text-[var(--text-main)]">{intent.label}</span>
        </KV>
      </Stage>

      <Arrow />

      {/* ⑤ Chart computation (ran in parallel with ①-④) */}
      <Stage n={5} title="Chart computation (parallel)" type="det">
        <KV label="Input">
          <code>{new Date(chart.datetime_utc).toLocaleString()}</code>
          {" · "}
          <code>
            {chart.location.lat}, {chart.location.lon}
          </code>
        </KV>
        <KV label="Logic">
          Swiss Ephemeris (sidereal, Lahiri ayanamsa) computes planet
          longitudes; whole-sign houses assigned from the Lagna; Vimshottari
          DBA derived from the Moon&apos;s nakshatra
        </KV>
        <KV label="Output (snippet)">
          <div className="flex flex-col gap-1 text-xs">
            <div>
              <span className="text-[var(--text-muted)]">Lagna:</span>{" "}
              <strong className="text-[var(--accent-gold)]">{chart.lagna.sign}</strong>{" "}
              ({chart.lagna.degree.toFixed(1)}°)
            </div>
            <div>
              <span className="text-[var(--text-muted)]">DBA now:</span>{" "}
              <span className="text-[var(--text-main)]">
                {chart.dasha.current_mahadasha} MD
                {chart.dasha.current_antardasha && ` · ${chart.dasha.current_antardasha} AD`}
                {chart.dasha.current_pratyantar && ` · ${chart.dasha.current_pratyantar} PD`}
              </span>
            </div>
            <div className="text-[var(--text-muted)]">9 planets + 12 houses computed</div>
          </div>
        </KV>
      </Stage>

      <Arrow />

      {/* ⑥ Evidence gathering — dual lane (favourable + unfavourable) */}
      <Stage n={6} title="Evidence gathering (dual lane)" type="det">
        <KV label="Input">
          <div className="flex flex-col gap-1 text-xs">
            <div>
              <span className="text-[#86efac]">favourable:</span>{" "}
              {(intent.favourable_houses ?? intent.selected_houses).map((h) => `H${h}`).join(", ") || "(none)"}
            </div>
            {(intent.unfavourable_houses ?? []).length > 0 && (
              <div>
                <span className="text-[#f87171]">unfavourable:</span>{" "}
                {(intent.unfavourable_houses ?? []).map((h) => `H${h}`).join(", ")}
              </div>
            )}
            <div>
              <span className="text-[var(--text-muted)]">karakas:</span>{" "}
              {intent.natural_karakas.join(", ")}
            </div>
          </div>
        </KV>
        <KV label="Logic">
          Two lanes, same scoring math, opposite sign on the unfavourable side.
          <span className="block mt-1">
            <strong className="text-[#86efac]">Favourable lane</strong>: factor strong → adds positively
            (primary lord ×1.5, supporting ×0.5, karakas ×1.0, MD/AD/PD ×0.6/0.5/0.4).
          </span>
          <span className="block mt-1">
            <strong className="text-[#f87171]">Unfavourable lane</strong>: factor strong → subtracts
            (sign-flipped + dampened by <code>×0.7</code>, classical convention — opposition is qualifying
            weather, not equal weight to the primary signal).
          </span>
        </KV>
        <KV label="Output">
          <div className="flex flex-col gap-1 text-xs">
            <div>
              <span className="text-[var(--text-muted)]">factors:</span>{" "}
              <strong className="text-[var(--text-main)]">{evidence.evidence.length}</strong>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <span>
                <span className="text-[var(--text-muted)]">favourable_score:</span>{" "}
                <strong className="font-mono text-[#86efac]">
                  {(evidence.favourable_score ?? 0).toFixed(2)}
                </strong>
              </span>
              <span>
                <span className="text-[var(--text-muted)]">unfavourable_score:</span>{" "}
                <strong className={cn(
                  "font-mono",
                  (evidence.unfavourable_score ?? 0) < 0 ? "text-[#f87171]" : "text-[var(--text-muted)]",
                )}>
                  {(evidence.unfavourable_score ?? 0).toFixed(2)}
                </strong>
              </span>
              <span>
                <span className="text-[var(--text-muted)]">→ combined:</span>{" "}
                <strong className={cn("font-mono", verdictColor)}>
                  {evidence.total_score.toFixed(2)}
                </strong>
              </span>
            </div>
            {topPositive && (
              <div>
                <span className="text-[var(--text-muted)]">top positive:</span>{" "}
                <span className="text-[#86efac]">+{topPositive.score}</span>{" "}
                <span className="text-[var(--text-main)]">— {topPositive.factor}</span>
              </div>
            )}
            {topNegative && (
              <div>
                <span className="text-[var(--text-muted)]">top negative:</span>{" "}
                <span className="text-[#f87171]">{topNegative.score}</span>{" "}
                <span className="text-[var(--text-main)]">— {topNegative.factor}</span>
              </div>
            )}
          </div>
        </KV>

        {/* Calculation breakdown — lane-segregated factor table. */}
        <FactorBreakdown
          items={evidence.evidence}
          totalScore={evidence.total_score}
          favourableScore={evidence.favourable_score ?? null}
          unfavourableScore={evidence.unfavourable_score ?? null}
        />
      </Stage>

      <Arrow />

      {/* ⑦ Verdict */}
      <Stage n={7} title="Verdict" type="det">
        <KV label="Input">
          total_score ={" "}
          <code className="text-[var(--text-main)]">{evidence.total_score.toFixed(2)}</code>
        </KV>
        <KV label="Logic">
          thresholds: ≥3.0 strongly favorable · ≥1.0 favorable · &gt;−1.0
          mixed · &gt;−3.0 challenging · else strongly challenging
        </KV>
        <KV label="Output">
          <span className={cn("display text-base font-medium capitalize", verdictColor)}>
            {verdict.label}
          </span>
          <span className="ml-2 text-xs text-[var(--text-muted)]">
            ({verdict.confidence} confidence)
          </span>
        </KV>
      </Stage>

      <Arrow />

      {/* ⑧ Synthesis */}
      <Stage n={8} title="Synthesis" type="llm">
        <KV label="Input">
          structured facts JSON (chart · selected_houses · karakas · DBA stack ·
          evidence · verdict · caveats · next PD shift)
        </KV>
        <KV label="Logic">
          {data.answer_source === "gemini" ? (
            <>
              Gemini ({modelLabel()}) writes a 6-section markdown reading
              constrained to use only the provided facts. Cannot invent
              placements; must name MD/AD/PD lords; time-aware closing
            </>
          ) : (
            <>
              LLM unavailable — deterministic template wrote the reading
              from the evidence list
            </>
          )}
        </KV>
        <KV label="Output">
          <div className="flex flex-col gap-1 text-xs">
            <span className="text-[var(--text-muted)]">
              source:{" "}
              <span
                className={cn(
                  "rounded-full px-1.5 py-[1px] text-[0.65rem] uppercase tracking-widest",
                  data.answer_source === "gemini"
                    ? "bg-[rgba(212,175,55,0.15)] text-[var(--accent-gold)]"
                    : "bg-white/5 text-[var(--text-muted)]"
                )}
              >
                {data.answer_source}
              </span>
            </span>
            <span className="text-[var(--text-muted)]">
              ↓ rendered as &ldquo;The Reading&rdquo; below
            </span>
          </div>
        </KV>
      </Stage>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function Stage({
  n,
  title,
  type,
  skipped,
  skipReason,
  children,
}: {
  n: number;
  title: string;
  type: StageType;
  skipped?: boolean;
  skipReason?: string;
  children: React.ReactNode;
}) {
  const typeBadge =
    type === "det" ? (
      <span className="rounded-full bg-[rgba(91,141,239,0.15)] px-2 py-[1px] text-[0.6rem] font-medium uppercase tracking-widest text-[#5b8def]">
        deterministic
      </span>
    ) : (
      <span className="rounded-full bg-[rgba(212,175,55,0.15)] px-2 py-[1px] text-[0.6rem] font-medium uppercase tracking-widest text-[var(--accent-gold)]">
        LLM
      </span>
    );

  const numEnclosed = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨"][n - 1] ?? `(${n})`;

  return (
    <article
      className={cn(
        "rounded-lg border border-[var(--border-glass)] bg-[rgba(15,17,35,0.55)] p-3",
        skipped && "opacity-60"
      )}
    >
      <header className="mb-2 flex items-center gap-2 border-b border-white/[0.05] pb-2">
        <span className="display text-base text-[var(--accent-gold)]">{numEnclosed}</span>
        <span className="display text-sm tracking-wider text-[var(--text-main)]">{title}</span>
        <span className="ml-auto">{typeBadge}</span>
      </header>
      {skipped ? (
        <div className="text-xs italic text-[var(--text-muted)]">
          stage skipped — {skipReason ?? "no data"}
        </div>
      ) : (
        <div className="flex flex-col gap-1.5">{children}</div>
      )}
    </article>
  );
}

function KV({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1 text-xs sm:flex-row sm:items-start sm:gap-3">
      <dt className="min-w-[6.5rem] font-mono uppercase tracking-widest text-[0.65rem] text-[var(--text-muted)]">
        {label}
      </dt>
      <dd className="flex-1 leading-relaxed text-[var(--text-main)]">{children}</dd>
    </div>
  );
}

function ChipRow({
  tokens,
  variant,
}: {
  tokens: string[];
  variant: "kept" | "dropped" | "planet";
}) {
  if (!tokens || tokens.length === 0) {
    return <em className="text-[var(--text-muted)]">none</em>;
  }
  const cls =
    variant === "kept"
      ? "bg-[rgba(134,239,172,0.10)] text-[#86efac] border-[rgba(134,239,172,0.25)]"
      : variant === "dropped"
        ? "bg-white/[0.03] text-[var(--text-muted)] border-[var(--border-glass)] line-through opacity-70"
        : "bg-[rgba(139,92,246,0.15)] text-[var(--accent-purple)] border-[rgba(139,92,246,0.3)]";
  return (
    <span className="inline-flex flex-wrap gap-1">
      {tokens.map((t) => (
        <code key={t} className={cn("rounded-full border px-2 py-[1px] text-[0.7rem]", cls)}>
          {t}
        </code>
      ))}
    </span>
  );
}

function Arrow() {
  return (
    <div className="flex justify-center text-[var(--text-muted)]" aria-hidden>
      ↓
    </div>
  );
}

/**
 * Two-column display for the polarity-aware lane classification.
 * Favourable houses (strength helps user) on the left in green;
 * unfavourable houses (strength obstructs user) on the right in red.
 * LLM-added houses (outside the dictionary candidate set) are flagged.
 */
function PolarityColumns({
  favourable,
  unfavourable,
  llmAdded,
}: {
  favourable: number[];
  unfavourable: number[];
  llmAdded: number[];
}) {
  const isAdded = (h: number) => llmAdded.includes(h);
  return (
    <div className="grid grid-cols-1 gap-2 text-xs sm:grid-cols-2">
      <PolarityColumn
        title="Favourable (strength helps you)"
        tone="favourable"
        houses={favourable}
        isAdded={isAdded}
      />
      <PolarityColumn
        title="Unfavourable (strength obstructs you)"
        tone="unfavourable"
        houses={unfavourable}
        isAdded={isAdded}
      />
    </div>
  );
}

function PolarityColumn({
  title,
  tone,
  houses,
  isAdded,
}: {
  title: string;
  tone: "favourable" | "unfavourable";
  houses: number[];
  isAdded: (h: number) => boolean;
}) {
  const colorClasses =
    tone === "favourable"
      ? "border-[rgba(134,239,172,0.30)] bg-[rgba(134,239,172,0.04)]"
      : "border-[rgba(248,113,113,0.30)] bg-[rgba(248,113,113,0.04)]";
  const labelColor =
    tone === "favourable" ? "text-[#86efac]" : "text-[#f87171]";
  return (
    <div className={cn("rounded-md border p-2", colorClasses)}>
      <div className={cn("text-[0.6rem] uppercase tracking-widest", labelColor)}>
        {title}
      </div>
      {houses.length === 0 ? (
        <div className="mt-1 text-[var(--text-muted)] italic">none</div>
      ) : (
        <div className="mt-1 flex flex-wrap gap-1.5">
          {houses.map((h, i) => (
            <span
              key={h}
              className={cn(
                "inline-flex items-center gap-1 rounded-full border px-2 py-[1px]",
                tone === "favourable"
                  ? "border-[rgba(134,239,172,0.4)] bg-[rgba(134,239,172,0.12)] text-[#86efac]"
                  : "border-[rgba(248,113,113,0.4)] bg-[rgba(248,113,113,0.12)] text-[#f87171]",
              )}
            >
              <strong>H{h}</strong>
              {i === 0 && houses.length > 1 && tone === "favourable" && (
                <span className="text-[0.55rem] uppercase tracking-widest opacity-70">
                  primary
                </span>
              )}
              {isAdded(h) && (
                <span
                  className="text-[0.55rem] uppercase tracking-widest opacity-80"
                  title="LLM added this house — it was NOT in the dictionary candidate set"
                >
                  + llm-added
                </span>
              )}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function PathBadge({ source, candidateCount }: { source: string; candidateCount: number }) {
  if (source.startsWith("domain_map_fallback")) {
    return (
      <span className="rounded-full bg-[rgba(248,113,113,0.15)] px-2 py-[1px] text-[0.65rem] uppercase tracking-widest text-[#f87171]">
        fallback · 0 candidates
      </span>
    );
  }
  if (source === "dictionary") {
    return (
      <span className="rounded-full bg-[rgba(134,239,172,0.15)] px-2 py-[1px] text-[0.65rem] uppercase tracking-widest text-[#86efac]">
        single candidate · no LLM
      </span>
    );
  }
  if (source === "dictionary+llm") {
    return (
      <span className="rounded-full bg-[rgba(212,175,55,0.15)] px-2 py-[1px] text-[0.65rem] uppercase tracking-widest text-[var(--accent-gold)]">
        LLM pick · {candidateCount} candidates
      </span>
    );
  }
  if (source === "dictionary+top_score") {
    return (
      <span
        className="rounded-full bg-[rgba(91,141,239,0.15)] px-2 py-[1px] text-[0.65rem] uppercase tracking-widest text-[#93b8f8]"
        title="LLM didn't return a usable pick — the deterministic top-N-by-score fallback ran instead"
      >
        deterministic fallback · top-N by score
      </span>
    );
  }
  return (
    <span className="rounded-full bg-white/5 px-2 py-[1px] text-[0.65rem] uppercase tracking-widest text-[var(--text-muted)]">
      {source}
    </span>
  );
}

/**
 * Inline badge shown next to a matched token when the match came via the
 * semantic-embedding fallback (cosine similarity against the 5K-word
 * dictionary). Reveals exactly which dictionary word we matched against
 * and the similarity score — full transparency, no black box.
 */
function SemanticBadge({
  matched,
  similarity,
}: {
  matched: string;
  similarity: number;
}) {
  // Color the score by confidence band so the user can eyeball strength:
  //   ≥ 0.85  strong  (teal)
  //   ≥ 0.78  good    (sky)
  //   ≥ 0.70  passing (slate)
  const band =
    similarity >= 0.85
      ? "bg-[rgba(45,212,191,0.15)] text-[#5eead4] border-[rgba(45,212,191,0.35)]"
      : similarity >= 0.78
        ? "bg-[rgba(91,141,239,0.15)] text-[#93b8f8] border-[rgba(91,141,239,0.35)]"
        : "bg-white/[0.04] text-[var(--text-muted)] border-[var(--border-glass)]";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-[1px] text-[0.65rem]",
        band
      )}
      title={`semantic match · cosine similarity ${similarity}`}
    >
      <span className="uppercase tracking-widest">semantic</span>
      <span aria-hidden>→</span>
      <code className="font-mono">{matched}</code>
      <span className="font-mono opacity-80">{similarity.toFixed(2)}</span>
    </span>
  );
}

/**
 * Per-token math breakdown for stage ③. For each matched token, shows the
 * exact 1/n + 0.25 primary-bonus arithmetic so the user can audit how the
 * candidate scores were derived. No magic — just inline algebra.
 */
function TokenMath({ match }: { match: TokenMatch }) {
  const n = match.houses.length;
  const baseWeight = 1 / n;
  const ambiguousNote = match.ambiguous
    ? `ambiguous (${n} houses)`
    : "unambiguous (1 house)";
  return (
    <li>
      <div className="mb-1 flex flex-wrap items-center gap-2">
        <code className="rounded bg-white/5 px-1.5 py-0.5 text-[var(--accent-gold)]">
          {match.token}
        </code>
        <span className="text-[var(--text-muted)]">— {ambiguousNote}</span>
        {match.override && (
          <span
            className="rounded-full bg-[rgba(139,92,246,0.15)] px-1.5 text-[0.6rem] uppercase tracking-widest text-[var(--accent-purple)]"
            title="PRIMARY_OVERRIDES — single-house authoritative pin"
          >
            override
          </span>
        )}
        {match.semantic_match && (
          <span className="text-[0.65rem] text-[var(--text-muted)]">
            (via semantic →{" "}
            <code className="text-[var(--text-main)]">{match.semantic_match.matched_word}</code>{" "}
            sim {match.semantic_match.similarity})
          </span>
        )}
      </div>
      <ul className="ml-2 flex flex-col gap-0.5 text-[0.7rem] font-mono">
        {match.houses.map((h) => {
          const isPrimary = h === match.primary_house;
          const contribution = baseWeight + (isPrimary ? 0.25 : 0);
          return (
            <li key={h} className="text-[var(--text-muted)]">
              H{h}
              {isPrimary && (
                <span className="ml-1 text-[0.6rem] uppercase tracking-widest text-[var(--accent-gold)]">
                  primary
                </span>
              )}
              {" : "}
              1/{n} = <span className="text-[var(--text-main)]">{baseWeight.toFixed(2)}</span>
              {isPrimary && (
                <>
                  {" + 0.25 bonus = "}
                  <strong className="text-[var(--accent-gold)]">{contribution.toFixed(2)}</strong>
                </>
              )}
              {!isPrimary && (
                <>
                  {" + 0 = "}
                  <strong className="text-[var(--text-main)]">{contribution.toFixed(2)}</strong>
                </>
              )}
            </li>
          );
        })}
      </ul>
    </li>
  );
}

/**
 * Click-to-expand factor table for stage ⑥. Shows every evidence item with
 * its weight and score, then sums to the total_score at the bottom — so the
 * user can audit exactly how the verdict number was derived.
 *
 * Uses a native <details> for the expand/collapse so we don't need React state
 * (presentational stays presentational; the browser handles open/closed).
 */
function FactorBreakdown({
  items,
  totalScore,
  favourableScore,
  unfavourableScore,
}: {
  items: EvidenceItem[];
  totalScore: number;
  favourableScore: number | null;
  unfavourableScore: number | null;
}) {
  // Lane-segregate. Older audit-log rows from before the polarity migration
  // won't have `lane` — default to "favourable" so they still render.
  const favItems = items.filter((e) => (e.lane ?? "favourable") === "favourable");
  const unfavItems = items.filter((e) => e.lane === "unfavourable");
  const contextItems = items.filter((e) => e.lane === "context");

  const sortByImpact = (arr: EvidenceItem[]) =>
    [...arr].sort((a, b) => Math.abs(b.score) - Math.abs(a.score));

  return (
    <details className="mt-2 rounded-md border border-[var(--border-glass)] bg-[rgba(10,11,22,0.4)]">
      <summary className="cursor-pointer px-3 py-2 text-xs text-[var(--accent-gold)] [&::-webkit-details-marker]:hidden">
        📐 Calculation breakdown — how the total of{" "}
        <code className="font-mono">{totalScore.toFixed(2)}</code> was derived
        <span className="ml-auto inline-block text-[var(--text-muted)] transition-transform [details[open]_&]:rotate-180">
          ▾
        </span>
      </summary>
      <div className="border-t border-[var(--border-glass)] px-3 py-2">
        <FactorLaneTable
          title="Favourable lane"
          subtitle="strength of these factors helps your outcome"
          tone="favourable"
          items={sortByImpact(favItems)}
          laneTotal={favourableScore}
        />
        {unfavItems.length > 0 && (
          <FactorLaneTable
            title="Unfavourable lane"
            subtitle="strength of these factors opposes your outcome (sign-flipped + ×0.7 dampened)"
            tone="unfavourable"
            items={sortByImpact(unfavItems)}
            laneTotal={unfavourableScore}
          />
        )}
        {contextItems.length > 0 && (
          <FactorLaneTable
            title="Context (no scoring)"
            subtitle="informational; doesn't affect the total"
            tone="context"
            items={contextItems}
            laneTotal={null}
          />
        )}
        {/* Combined total */}
        <div className="mt-3 flex justify-between rounded-md border border-[var(--accent-gold)]/30 bg-white/[0.02] px-3 py-2 text-xs">
          <span className="text-[var(--accent-gold)]">
            Σ combined ({(favourableScore ?? 0).toFixed(2)} + ({(unfavourableScore ?? 0).toFixed(2)}))
          </span>
          <strong className="font-mono text-[var(--accent-gold)]">
            {totalScore.toFixed(2)}
          </strong>
        </div>
        <p className="mt-2 text-[0.65rem] italic text-[var(--text-muted)]">
          Factors sorted by absolute impact within each lane. The Verdict stage
          maps the combined total to the favourable / mixed / challenging label
          using fixed thresholds.
        </p>
      </div>
    </details>
  );
}

/**
 * One sub-table per lane (favourable / unfavourable / context). Same column
 * layout in all three so the eye can scan; tone-coded so the side is obvious.
 */
function FactorLaneTable({
  title,
  subtitle,
  tone,
  items,
  laneTotal,
}: {
  title: string;
  subtitle: string;
  tone: "favourable" | "unfavourable" | "context";
  items: EvidenceItem[];
  laneTotal: number | null;
}) {
  const accent =
    tone === "favourable" ? "text-[#86efac]" :
    tone === "unfavourable" ? "text-[#f87171]" :
    "text-[var(--text-muted)]";
  return (
    <div className="mt-2 first:mt-0">
      <div className="mb-1 flex items-baseline justify-between">
        <div>
          <span className={cn("text-[0.7rem] uppercase tracking-widest", accent)}>
            {title}
          </span>{" "}
          <span className="text-[0.6rem] italic text-[var(--text-muted)]">{subtitle}</span>
        </div>
        {laneTotal !== null && (
          <span className={cn("font-mono text-xs", accent)}>
            Σ {laneTotal >= 0 ? "+" : ""}{laneTotal.toFixed(2)}
          </span>
        )}
      </div>
      <table className="w-full text-[0.7rem] font-mono">
        <thead>
          <tr className="text-[var(--text-muted)]">
            <th className="pb-1 text-left">Factor</th>
            <th className="pb-1 text-left font-normal">Weight</th>
            <th className="pb-1 text-right font-normal">Score</th>
          </tr>
        </thead>
        <tbody>
          {items.map((e, i) => (
            <tr key={i} className="border-t border-white/[0.03]">
              <td className="py-1 pr-2 text-[var(--text-main)]">{e.factor}</td>
              <td className="py-1 pr-2 text-[0.65rem] uppercase tracking-widest text-[var(--text-muted)]">
                {e.weight}
              </td>
              <td
                className={cn(
                  "py-1 text-right",
                  e.score > 0 ? "text-[#86efac]" : e.score < 0 ? "text-[#f87171]" : "text-[var(--text-muted)]",
                )}
              >
                {e.score > 0 ? "+" : ""}
                {Number(e.score).toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function pickStageType(source: string): StageType {
  if (source === "dictionary") return "det";
  if (source.startsWith("dictionary+")) return "llm";
  return "llm";
}

function pickStageLogic(source: string): React.ReactNode {
  if (source === "dictionary") {
    return (
      <>
        Only one candidate house came out of stage ③ — accept it directly.
        No LLM call needed; the dictionary already gave us a confident answer.
      </>
    );
  }
  if (source === "dictionary+llm") {
    return (
      <>
        Multiple candidates were available. Gemini was asked to pick the 1–3
        most relevant houses <strong>from the candidate list only</strong> —
        it can&apos;t pick a house outside that list, which is exactly why
        we run the dictionary first.
      </>
    );
  }
  if (source === "dictionary+top_score") {
    return (
      <>
        Multiple candidates were available, but the LLM call didn&apos;t
        return a usable pick (timeout, malformed JSON, or houses outside the
        candidate list). This isn&apos;t an error — there&apos;s a
        deterministic fallback: take the <strong>top 2 candidates by score</strong>{" "}
        from stage ③. The reading still gets built normally from those
        houses.
      </>
    );
  }
  if (source.startsWith("domain_map_fallback")) {
    return (
      <>
        Zero dictionary matches for this question — fell back to the legacy
        14-domain classifier (Gemini maps the question to one of: career,
        marriage, wealth, …) and used that domain&apos;s default house list.
        The audit log captures these so we can extend the dictionary&apos;s
        coverage.
      </>
    );
  }
  return source;
}

function modelLabel(): string {
  return "gemini-2.0-flash";
}

function verdictTextColor(label: string): string {
  if (label.includes("strongly favorable") || label === "favorable") return "text-[#86efac]";
  if (label.includes("strongly challenging") || label === "challenging") return "text-[#f87171]";
  return "text-[var(--accent-gold)]";
}
