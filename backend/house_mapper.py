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
import re
from typing import Optional

# ---------------------------------------------------------------------------
# Dictionary loaded once at import time
# ---------------------------------------------------------------------------

DICT_PATH = os.path.join(os.path.dirname(__file__), "house_dictionary.json")

try:
    with open(DICT_PATH, encoding="utf-8") as _f:
        DICTIONARY: dict = json.load(_f)
except FileNotFoundError:
    DICTIONARY = {}


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
    """Lowercase, strip punctuation, split on whitespace, drop stopwords."""
    clean = re.sub(r"[^\w\s'-]", " ", question.lower())
    tokens = [t.strip("-' ") for t in clean.split()]
    return [t for t in tokens if t and t not in STOPWORDS and len(t) > 1]


def match_tokens(tokens: list[str]) -> tuple[list[dict], list[str]]:
    """Look each token up in the dictionary.

    Returns (matched, unmatched):
      matched   = [{"token", "primary_house", "houses", "ambiguous"}, ...]
      unmatched = tokens that had no dictionary hit
    """
    matched: list[dict] = []
    unmatched: list[str] = []

    for tok in tokens:
        rec = DICTIONARY.get(tok)
        resolved_token = tok
        # Light plural-collapse: "movies" → "movie" if the plural isn't present.
        if rec is None and tok.endswith("s") and len(tok) > 3:
            stem = tok[:-1]
            rec = DICTIONARY.get(stem)
            if rec:
                resolved_token = stem
        # Crude -ing → root drop ("watching" → "watch")
        if rec is None and tok.endswith("ing") and len(tok) > 4:
            stem = tok[:-3]
            rec = DICTIONARY.get(stem) or DICTIONARY.get(stem + "e")
            if rec:
                resolved_token = stem if DICTIONARY.get(stem) else stem + "e"

        # Check the override table — covers BOTH cases:
        #   (a) dictionary hit, but its primary_house is wrong → re-anchor
        #   (b) dictionary miss for a term we manually know about ("children")
        override_house = PRIMARY_OVERRIDES.get(tok) or PRIMARY_OVERRIDES.get(resolved_token)

        if rec is None and override_house is None:
            unmatched.append(tok)
            continue

        if override_house is not None:
            base_houses = list(rec["houses"]) if rec else []
            if override_house not in base_houses:
                base_houses.insert(0, override_house)
            matched.append({
                "token":         tok,
                "primary_house": override_house,
                "houses":        base_houses,
                "ambiguous":     len(base_houses) > 1,
                "override":      True,
            })
            continue

        # Plain dictionary hit, no override needed.
        matched.append({
            "token":         tok,
            "primary_house": rec["primary_house"],
            "houses":        rec["houses"],
            "ambiguous":     rec.get("ambiguous", len(rec["houses"]) > 1),
            "override":      False,
        })

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
    """
    tokens = tokenize(question)
    matched, unmatched = match_tokens(tokens)
    candidates_dict = score_candidates(matched)

    ranked = sorted(candidates_dict.items(), key=lambda kv: -kv[1]["score"])
    candidates = [
        {"house": h, "score": v["score"], "supporting_tokens": v["supporting_tokens"]}
        for h, v in ranked
    ]

    return {
        "tokens":            tokens,
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
