"""
house_mapper.py
================
Token-driven question → candidate houses mapping.

Implements May 19 Durga MOM action item #4 — "Wire the word-to-house
dictionary into /ask". Replaces the old rigid 14-domain LLM classifier
(which forced the question into one of {career, marriage, …} and
hallucinated downstream) with a deterministic dictionary lookup that
narrows the candidate house set BEFORE the LLM is asked anything.

Pipeline used by `interpret.py`:

  1. tokenize(question)        — lowercase, strip punctuation, drop stopwords
  2. match_tokens(tokens)      — look each up in house_dictionary.json
  3. score_candidates(matches) — confidence-weighted aggregation per house
  4. (LLM step in interpret.py — picks 1-3 from the narrowed set)
  5. natural_karakas_for_houses(selected) — union from HOUSE_KARAKAS table

The deterministic stages (1-3) produce a `trace` that's perfect for the
upcoming audit log (May 19 MOM #3).
"""

from __future__ import annotations
import json
import os
import pickle
import re
from typing import Optional

# ---------------------------------------------------------------------------
# Dictionary loaded once at import time
# ---------------------------------------------------------------------------

DICT_PATH       = os.path.join(os.path.dirname(__file__), "house_dictionary.json")
EMB_INDEX_PATH  = os.path.join(os.path.dirname(__file__), "dict_embeddings.pkl")

try:
    with open(DICT_PATH, encoding="utf-8") as _f:
        DICTIONARY: dict = json.load(_f)
except FileNotFoundError:
    DICTIONARY = {}


# ---------------------------------------------------------------------------
# Semantic-match index — lazy-loaded sentence-transformer embeddings of every
# dictionary word. Used as a fallback when exact / stem / override all miss.
# ---------------------------------------------------------------------------
#
# Threshold: we only accept a semantic match if cosine similarity ≥ this.
# Tuned at 0.70 — high enough to reject the loud lexical-overlap false
# positives (time↔timework 0.69, grow↔growth 0.68, watch↔watchword 0.59)
# while still admitting genuine synonyms / verb↔noun forms:
#   marry↔marriage 0.85 · married↔married_man 0.89 · invest↔investing 0.91
# When a token falls below threshold it's surfaced as unmatched in the
# audit trace — better to honestly say "we don't know" than to invent a
# wrong mapping that misleads the reading.
SEMANTIC_THRESHOLD = 0.70

_SEM_INDEX: dict | None = None       # {model_name, words, embeddings (np.ndarray)}
_SEM_MODEL = None                    # SentenceTransformer instance (lazy)


def _load_sem_index() -> dict | None:
    """Lazy-load the dictionary embedding index. Returns None if unavailable."""
    global _SEM_INDEX
    if _SEM_INDEX is not None:
        return _SEM_INDEX
    if not os.path.exists(EMB_INDEX_PATH):
        return None
    try:
        with open(EMB_INDEX_PATH, "rb") as f:
            _SEM_INDEX = pickle.load(f)
        return _SEM_INDEX
    except Exception:
        return None


def _get_sem_model():
    """Lazy-load the SentenceTransformer model (heavy — ~100MB RAM)."""
    global _SEM_MODEL
    if _SEM_MODEL is not None:
        return _SEM_MODEL
    idx = _load_sem_index()
    if idx is None:
        return None
    try:
        from sentence_transformers import SentenceTransformer
        _SEM_MODEL = SentenceTransformer(idx["model_name"])
        return _SEM_MODEL
    except Exception:
        return None


def semantic_match(token: str) -> tuple[str, float] | None:
    """Return (closest dictionary word, similarity) above threshold, or None.

    Uses cosine similarity (= dot product since embeddings are L2-normalised).
    """
    idx = _load_sem_index()
    model = _get_sem_model()
    if idx is None or model is None:
        return None
    import numpy as np
    query_vec = model.encode([token], normalize_embeddings=True)[0]
    sims = idx["embeddings"] @ query_vec       # cosine, since both normed
    best_i = int(np.argmax(sims))
    best_sim = float(sims[best_i])
    if best_sim < SEMANTIC_THRESHOLD:
        return None
    return idx["words"][best_i], best_sim


# ---------------------------------------------------------------------------
# Stopwords — pronouns, articles, prepositions, copulas, basic modals.
# We deliberately do NOT stopword common verbs (go, marry, work, etc.) —
# they're in the dictionary for a reason. The LLM picks which matches matter.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Manual primary-house overrides for tokens whose dictionary primary is wrong.
#
# The dictionary's primary_house is "first seed wins" — fine for most terms,
# but WordNet's synonym graph drags some words into the wrong house. e.g.
# "career" got dragged into H6 (because "work"→H6 was processed before
# "career"→H10 in the seed order). Manual overrides re-anchor these.
#
# This table is intentionally small and reviewable — Durga can audit it.
# Anything not in here uses the dictionary's primary_house as-is.
# ---------------------------------------------------------------------------

PRIMARY_OVERRIDES: dict[str, int] = {
    # Career — primary house is H10, not H6
    "career":      10,
    "promotion":   10,
    "profession":  10,
    "occupation":  10,
    "authority":   10,
    "status":      10,
    # Relationships / marriage → H7
    "marriage":    7,
    "wedding":     7,
    "spouse":      7,
    "husband":     7,
    "wife":        7,
    "partner":     7,
    "contract":    7,
    # Children / play / entertainment → H5
    "child":       5,
    "children":    5,
    "baby":        5,
    "movie":       5,
    "film":        5,
    "cinema":      5,
    "game":        5,
    "play":        5,
    "tennis":      5,
    "sport":       5,
    "romance":     5,
    # Money / wealth → H2 (accumulated) vs H11 (gains)
    "money":       2,
    "wealth":      2,
    "income":      11,
    "salary":      11,
    "profit":      11,
    # Family
    "father":      9,
    "mother":      4,
    "sibling":     3,
    "brother":     3,
    "sister":      3,
    # Home / property → H4
    "home":        4,
    "house":       4,   # the dwelling sense, not the astrological house
    "property":    4,
    "vehicle":     4,
    # Health → H1 / H6
    "health":      1,
    "illness":     6,
    "disease":     6,
    # Spirituality / dharma → H9 / H12
    "spirituality":9,
    "guru":        9,
    "dharma":      9,
    "meditation":  12,
    "moksha":      12,
    # Travel / foreign → H9 / H12
    "travel":      9,
    "abroad":      12,
    "foreign":     12,
    # Death / transformation → H8
    "death":       8,
    "inheritance": 8,
}


STOPWORDS = frozenset([
    # articles
    "the", "a", "an",
    # pronouns / determiners
    "i", "you", "we", "they", "it", "this", "that", "these", "those",
    "my", "your", "our", "their", "his", "her", "its",
    "me", "him", "us", "them", "myself", "yourself",
    # prepositions
    "to", "of", "in", "on", "at", "with", "for", "from", "by", "about",
    "into", "onto", "upon", "out", "off", "up", "down", "through",
    # conjunctions / connectives
    "and", "or", "but", "so", "if", "because", "when", "while",
    "although", "though", "since", "than", "as", "yet",
    # copulas + modals
    "be", "am", "is", "are", "was", "were", "been", "being",
    "can", "could", "will", "would", "shall", "should", "may", "might", "must",
    # interrogatives
    "what", "where", "why", "how", "who", "which",
    # misc filler
    "not", "no", "yes", "any", "some", "all", "now", "then", "here", "there",
    "very", "just", "only", "ever", "never", "still", "too",
])


# ---------------------------------------------------------------------------
# House labels (used to assemble a "domain label" for display once houses
# are picked — no longer derived from a 14-domain enum)
# ---------------------------------------------------------------------------

HOUSE_LABELS: dict[int, str] = {
    1:  "Self / Body",
    2:  "Wealth / Family / Speech",
    3:  "Siblings / Courage / Communication",
    4:  "Home / Mother / Property",
    5:  "Children / Creativity / Play / Romance",
    6:  "Work / Health / Debts / Enemies",
    7:  "Partner / Marriage / Contracts",
    8:  "Mystery / Transformation / Longevity",
    9:  "Father / Dharma / Luck / Higher learning",
    10: "Career / Status / Authority",
    11: "Gains / Friends / Hopes",
    12: "Loss / Foreign / Isolation / Moksha",
}


# ---------------------------------------------------------------------------
# Per-house natural karakas (significator planets).
# Replaces the old DOMAIN_MAP["naturals"] lookup. Encodes classical
# Parashari conventions + Durga's May 12 MOM corrections:
#   - Career → Saturn (hard work), NOT Sun
#   - Self-improvement → Mars (action / energy) → routed via H5
#   - Strategy / Thinking → Mercury
#   - Blessings / Abundance → Jupiter
# ---------------------------------------------------------------------------

HOUSE_KARAKAS: dict[int, list[str]] = {
    1:  ["Sun"],                              # self, body, vitality
    2:  ["Jupiter", "Venus"],                 # wealth, family, speech
    3:  ["Mars", "Mercury"],                  # courage, siblings, communication
    4:  ["Moon", "Mars"],                     # mother, home, property
    5:  ["Jupiter", "Venus", "Mars"],         # children, creativity, romance, self-improvement
    6:  ["Mars", "Saturn"],                   # enemies, illness, daily work
    7:  ["Venus", "Mercury"],                 # partner, contracts
    8:  ["Saturn"],                           # longevity, occult, sudden events
    9:  ["Jupiter", "Sun"],                   # dharma, father, luck
    10: ["Saturn", "Mercury", "Sun"],         # career — Saturn primary per Durga
    11: ["Jupiter"],                          # gains
    12: ["Saturn", "Ketu"],                   # loss, moksha, foreign
}


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------

def tokenize(question: str) -> list[str]:
    """Lowercase, strip punctuation, split on whitespace, drop stopwords.
    Returns only the surviving tokens. Use `tokenize_traced` if you also
    need to see which tokens were dropped (useful for trace/audit displays).
    """
    return tokenize_traced(question)[0]


def tokenize_traced(question: str) -> tuple[list[str], list[str]]:
    """Like tokenize(), but also returns the dropped tokens for trace UIs.

    Returns:
        (kept_tokens, dropped_tokens) — preserving original order.
        `dropped_tokens` includes both stopwords and tokens that were too
        short / empty after punctuation stripping.
    """
    clean = re.sub(r"[^\w\s'-]", " ", question.lower())
    raw = [t.strip("-' ") for t in clean.split()]
    kept: list[str] = []
    dropped: list[str] = []
    for t in raw:
        if not t:
            continue
        if t in STOPWORDS or len(t) <= 1:
            dropped.append(t)
        else:
            kept.append(t)
    return kept, dropped


def match_tokens(tokens: list[str]) -> tuple[list[dict], list[str]]:
    """Look each token up in the dictionary.

    Returns (matched, unmatched):
      matched   = [{"token", "primary_house", "houses", "ambiguous"}, ...]
      unmatched = tokens that had no dictionary hit
    """
    matched: list[dict] = []
    unmatched: list[str] = []

    for tok in tokens:
        # Resolution cascade — exact → plural → -ing → override-from-tok →
        # semantic. We track `resolved_token` (which dict key was finally
        # used) and `semantic` (the matched word + similarity, if that path
        # fired) so we can build a transparent trace.
        rec = DICTIONARY.get(tok)
        resolved_token = tok if rec is not None else None
        semantic: tuple[str, float] | None = None

        # 1. Plural collapse: "movies" → "movie"
        if rec is None and tok.endswith("s") and len(tok) > 3:
            stem = tok[:-1]
            rec = DICTIONARY.get(stem)
            if rec:
                resolved_token = stem

        # 2. -ing drop: "watching" → "watch" (or "watche")
        if rec is None and tok.endswith("ing") and len(tok) > 4:
            stem = tok[:-3]
            rec = DICTIONARY.get(stem) or DICTIONARY.get(stem + "e")
            if rec:
                resolved_token = stem if DICTIONARY.get(stem) else stem + "e"

        # 3. PRIMARY_OVERRIDES hit on the ORIGINAL token (the token might not
        #    be in the dictionary at all but is in the override table —
        #    e.g. "children").
        override_house = PRIMARY_OVERRIDES.get(tok)

        # 4. Semantic fallback — only if all string-based attempts failed.
        #    Embeds the token, finds the nearest dictionary word above
        #    SEMANTIC_THRESHOLD. Closes verb↔noun gaps that exact-match +
        #    stemming can't reach (e.g. "marry" → "marriage").
        if rec is None and override_house is None:
            semantic = semantic_match(tok)
            if semantic is None:
                unmatched.append(tok)
                continue
            sem_word, sem_sim = semantic
            rec = DICTIONARY.get(sem_word)
            if rec is None:
                # safety: shouldn't happen since semantic words come FROM the dict
                unmatched.append(tok)
                continue
            resolved_token = sem_word

        # 5. After all resolution paths, re-check overrides against the
        #    resolved dictionary key. This catches the case where the
        #    original token had no override but its resolved form does
        #    (e.g. "marry" → semantic → "marriage" → override H7).
        if override_house is None and resolved_token is not None:
            override_house = PRIMARY_OVERRIDES.get(resolved_token)

        # ── Build the match record ─────────────────────────────────────────
        # PRIMARY_OVERRIDES is authoritative — the whole purpose of the
        # table is to correct dictionary noise (e.g. "marriage" was tagged
        # ambiguous H2/H7 because the H2 "family" seed dragged it in via
        # WordNet; we pin it to H7 only). So override replaces the houses
        # list entirely rather than appending to the noisy dictionary one.
        if override_house is not None:
            record = {
                "token":          tok,
                "primary_house":  override_house,
                "houses":         [override_house],
                "ambiguous":      False,
                "override":       True,
                "semantic_match": None,
            }
        else:
            record = {
                "token":          tok,
                "primary_house":  rec["primary_house"],
                "houses":         rec["houses"],
                "ambiguous":      rec.get("ambiguous", len(rec["houses"]) > 1),
                "override":       False,
                "semantic_match": None,
            }

        # Attach semantic trace (if this match came via the semantic path).
        if semantic is not None:
            sem_word, sem_sim = semantic
            record["semantic_match"] = {
                "matched_word": sem_word,
                "similarity":   round(sem_sim, 3),
            }

        matched.append(record)

    return matched, unmatched


def score_candidates(matched: list[dict]) -> dict[int, dict]:
    """Aggregate token hits into per-house scores.

    Each unambiguous match contributes a full 1.0 to its house.
    Each ambiguous match splits 1.0 evenly across its candidate houses.
    Bonus: tokens that hit a house's PRIMARY classification get a small extra
    weight (0.25) because the primary is more semantically committed.

    Returns: { house_number: {"score": float, "supporting_tokens": [str, ...]} }
    """
    candidates: dict[int, dict] = {}
    for m in matched:
        n = len(m["houses"])
        base_weight = 1.0 / n
        for h in m["houses"]:
            primary_bonus = 0.25 if h == m["primary_house"] else 0.0
            if h not in candidates:
                candidates[h] = {"score": 0.0, "supporting_tokens": []}
            candidates[h]["score"] += base_weight + primary_bonus
            if m["token"] not in candidates[h]["supporting_tokens"]:
                candidates[h]["supporting_tokens"].append(m["token"])
    for h in candidates:
        candidates[h]["score"] = round(candidates[h]["score"], 3)
    return candidates


def natural_karakas_for_houses(houses: list[int]) -> list[str]:
    """Union of natural significators across the selected houses, preserving
    rough priority (planets earlier in each house's karaka list win)."""
    seen: list[str] = []
    for h in houses:
        for k in HOUSE_KARAKAS.get(h, []):
            if k not in seen:
                seen.append(k)
    return seen


def label_for_houses(houses: list[int]) -> str:
    """Human-readable composite label for the picked houses.
    e.g. [5] → 'Children / Creativity / Play / Romance'
         [7, 5] → 'Partner / Marriage / Contracts + Children / Creativity / Play / Romance'
    """
    if not houses:
        return "General life direction"
    return " + ".join(HOUSE_LABELS.get(h, f"House {h}") for h in houses)


# ---------------------------------------------------------------------------
# High-level entry point used by interpret.py
# ---------------------------------------------------------------------------

def map_question(question: str) -> dict:
    """Pure-deterministic pass: question text → candidate houses with trace.

    The returned `trace` is the foundation of the audit log (MOM #3):
    every step the system took to narrow from 12 houses to N candidates.
    It also feeds the on-the-fly "journey" trace shown in the UI so users
    can see how their question became a verdict.
    """
    tokens, dropped = tokenize_traced(question)
    matched, unmatched = match_tokens(tokens)
    candidates_dict = score_candidates(matched)

    ranked = sorted(candidates_dict.items(), key=lambda kv: -kv[1]["score"])
    candidates = [
        {"house": h, "score": v["score"], "supporting_tokens": v["supporting_tokens"]}
        for h, v in ranked
    ]

    return {
        "tokens":            tokens,
        "tokens_dropped":    dropped,
        "tokens_matched":    matched,
        "tokens_unmatched":  unmatched,
        "candidates":        candidates,
        "primary_candidate": candidates[0]["house"] if candidates else None,
        "match_count":       len(matched),
    }


# ---------------------------------------------------------------------------
# CLI sanity check
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    samples = [
        "Should I watch the movie that I have been postponing tonight?",
        "Should I go to tennis today?",
        "Will my career grow this year?",
        "Should I marry my partner?",
        "Is this the right time to take this new job?",
        "Will I have children soon?",
        "Should I invest in this risky startup?",
    ]
    for q in samples:
        t = map_question(q)
        print(f"\nQ: {q}")
        print(f"  tokens kept ({len(t['tokens'])}): {t['tokens']}")
        print(f"  matched: " + ", ".join(
            f"{m['token']}→H{m['primary_house']}" + ("*" if m["ambiguous"] else "")
            for m in t["tokens_matched"]
        ))
        print(f"  candidates: " + ", ".join(
            f"H{c['house']}({c['score']})" for c in t["candidates"][:5]
        ))
        karakas = natural_karakas_for_houses(
            [c["house"] for c in t["candidates"][:2]]
        )
        print(f"  primary candidate: H{t['primary_candidate']}  "
              f"label: {label_for_houses([t['primary_candidate']] if t['primary_candidate'] else [])}")
        print(f"  natural karakas: {karakas}")
