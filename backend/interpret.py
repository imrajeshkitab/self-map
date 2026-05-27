"""
interpret.py
Q&A engine — answers life questions by reading the live Prashna chart.

Pipeline:
    1. Gemini classifies the question into a Vedic life-domain.
    2. Deterministic map: domain → houses + natural karakas + chara karaka role.
    3. Gather evidence from the chart for each relevant factor.
    4. Score the evidence to produce a verdict.
    5. Gemini synthesizes a 4-6 sentence Vedic reading.

The structured chart is always the source of truth.
LLM only does (a) intent classification and (b) prose synthesis.
"""

from __future__ import annotations
import json
import os
import re
from typing import Any
from dotenv import load_dotenv
import google.generativeai as genai

import house_mapper

load_dotenv()
# Latest stable Gemini, verified to handle the polarity-flipping cases
# correctly (gemini-3.1-pro-preview tripped on the "avoid" negation test;
# 3.5-flash passed). Same model used for both polarity classification
# and narrative synthesis.
GEMINI_MODEL = "gemini-3.5-flash"
# Legacy alias kept so older sites don't break; same model.
GEMINI_LEGACY_MODEL = GEMINI_MODEL
_configured = False


def _configure_gemini() -> bool:
    global _configured
    if _configured:
        return True
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return False
    genai.configure(api_key=key)
    _configured = True
    return True


# ---------------------------------------------------------------------------
# 1. Question → Domain mapping (deterministic + LLM fallback)
# ---------------------------------------------------------------------------

DOMAIN_MAP: dict[str, dict] = {
    "career":       {"houses": [10, 6, 1],  "naturals": ["Sun", "Saturn"],     "chara": "Amatya",  "label": "Career & profession"},
    "marriage":     {"houses": [7, 2, 11],  "naturals": ["Venus", "Jupiter"],  "chara": "Dara",    "label": "Marriage & partnership"},
    "wealth":       {"houses": [2, 11, 5],  "naturals": ["Jupiter", "Venus"],  "chara": "Amatya",  "label": "Wealth & finances"},
    "education":    {"houses": [4, 5, 2],   "naturals": ["Mercury", "Jupiter"],"chara": "Putra",   "label": "Education & learning"},
    "health":       {"houses": [1, 6, 8],   "naturals": ["Sun", "Mars"],       "chara": "Atma",    "label": "Health & vitality"},
    "children":     {"houses": [5, 9],      "naturals": ["Jupiter"],           "chara": "Putra",   "label": "Children"},
    "travel":       {"houses": [3, 9, 12],  "naturals": ["Rahu", "Moon"],      "chara": "Amatya",  "label": "Travel"},
    "spirituality": {"houses": [9, 12, 8],  "naturals": ["Jupiter", "Ketu"],   "chara": "Atma",    "label": "Spirituality"},
    "relationships":{"houses": [7, 11, 3],  "naturals": ["Venus", "Mercury"],  "chara": "Dara",    "label": "Relationships"},
    "property":     {"houses": [4],         "naturals": ["Mars", "Moon"],      "chara": "Matri",   "label": "Property & home"},
    "siblings":     {"houses": [3, 11],     "naturals": ["Mars", "Mercury"],   "chara": "Bhratri", "label": "Siblings"},
    "parents":      {"houses": [4, 9],      "naturals": ["Moon", "Sun"],       "chara": "Matri",   "label": "Parents"},
    "enemies":      {"houses": [6, 8],      "naturals": ["Mars", "Saturn"],    "chara": "Gnati",   "label": "Enemies & obstacles"},
    "general":      {"houses": [1],         "naturals": ["Sun", "Moon"],       "chara": "Atma",    "label": "General life direction"},
}

# For each domain, what does each house *mean for this question*?
# Used to help the LLM interpret DBA lord placements specifically
# (e.g. "Mercury PD in your 7th — contracts — directly relevant to a job offer"
#  instead of generic "Mercury says communication matters").
# If a house isn't listed for a domain, GENERIC_HOUSE_MEANING is used.
GENERIC_HOUSE_MEANING = {
    1:  "you yourself — body, identity",
    2:  "earnings, family, speech",
    3:  "courage, siblings, short journeys",
    4:  "home, mother, comfort, roots",
    5:  "creativity, intelligence, romance, children",
    6:  "daily effort, obstacles, health, debts",
    7:  "partner, contracts, the other person",
    8:  "secrets, transformation, sudden events",
    9:  "dharma, luck, father, long journeys",
    10: "career, status, public role",
    11: "gains, network, hopes fulfilled",
    12: "loss, foreign lands, spirituality, expenses",
}

HOUSE_MEANING_FOR_DOMAIN: dict[str, dict[int, str]] = {
    "career": {
        1:  "you yourself — the seat of the question",
        6:  "the daily grind — effort and competition for this role",
        7:  "contracts and agreements — directly relevant to a job offer",
        10: "career and status — the primary house for this question",
        11: "gains and professional network — career-adjacent",
    },
    "marriage": {
        2:  "family lineage and what you bring to the union",
        5:  "romance and emotional attraction",
        7:  "partner and marriage — the primary house here",
        8:  "shared resources, intimacy, hidden aspects of the union",
        11: "social network — friends who shape the match",
    },
    "wealth": {
        2:  "earnings and accumulated wealth — primary house",
        5:  "investments, speculation, sudden gains",
        9:  "fortune and blessings that bring wealth",
        11: "income from many sources — primary support",
    },
    "health": {
        1:  "the body itself — primary house for health",
        6:  "illness and recovery — the disease house",
        8:  "chronic conditions, surgery, sudden events",
        12: "hospitalization, sleep, isolation",
    },
    "education": {
        2:  "memory and retention",
        4:  "schooling and the early learning environment",
        5:  "intelligence and creative learning — primary",
        9:  "higher education, philosophy, mentors",
    },
    "children": {
        5:  "children and creativity — the primary house",
        9:  "blessings of progeny",
        2:  "family expansion",
    },
    "travel": {
        3:  "short journeys",
        9:  "long journeys and pilgrimage",
        12: "foreign lands and overseas settlement",
    },
    "relationships": {
        3:  "the immediate circle — friends, courage to connect",
        7:  "the partner — primary house",
        11: "social network and shared joy",
    },
    "spirituality": {
        9:  "dharma and the path of wisdom — primary",
        12: "moksha, retreat, surrender",
        8:  "transformation, deep inner work",
    },
    "property": {
        4:  "the home itself — primary house",
        2:  "the value of what you own",
    },
    "siblings": {
        3:  "siblings and courage — primary house",
        11: "elder siblings and gains through them",
    },
    "parents": {
        4:  "mother",
        9:  "father",
    },
    "enemies": {
        6:  "open enemies, lawsuits, debts — primary house",
        8:  "hidden enemies, betrayal",
    },
    "general": {
        1:  "you yourself — the seat of the question",
    },
}


def _house_meaning(domain: str, house: int) -> str:
    """Return what `house` means for `domain` — domain-specific if defined, else generic."""
    domain_map = HOUSE_MEANING_FOR_DOMAIN.get(domain, {})
    return domain_map.get(house) or GENERIC_HOUSE_MEANING.get(house, f"{house}th house themes")


# Fallback keyword classifier when LLM is unavailable.
_KEYWORDS = {
    "career":       ["career", "job", "work", "promotion", "business", "profession", "office"],
    "marriage":     ["marriage", "married", "wedding", "spouse", "wife", "husband"],
    "wealth":       ["money", "wealth", "rich", "income", "earnings", "salary", "finance"],
    "education":    ["study", "exam", "college", "education", "degree", "learn"],
    "health":       ["health", "sick", "disease", "anxious", "depression", "body"],
    "children":     ["child", "children", "baby", "pregnancy", "kids"],
    "travel":       ["travel", "trip", "journey", "abroad", "foreign"],
    "spirituality": ["spiritual", "moksha", "god", "meditation", "guru", "dharma"],
    "relationships":["relationship", "love", "girlfriend", "boyfriend", "partner", "dating"],
    "property":     ["house", "property", "land", "home", "real estate", "vehicle"],
    "siblings":     ["sibling", "brother", "sister"],
    "parents":      ["father", "mother", "parent", "dad", "mom"],
    "enemies":      ["enemy", "enemies", "lawsuit", "court", "litigation", "debt"],
}


def classify_question(question: str) -> dict:
    """Return {'domain': str, 'source': 'llm'|'keyword'|'fallback', 'reason': str}."""
    # First, LLM (best at picking up paraphrase).
    if _configure_gemini():
        try:
            prompt = (
                "You are a Vedic astrology question classifier. "
                "Map the user's question to EXACTLY ONE of these life-domains:\n"
                + ", ".join(DOMAIN_MAP.keys()) + ".\n\n"
                f'Question: "{question}"\n\n'
                "Return only the domain key as a single lowercase word. No punctuation, no explanation."
            )
            model = genai.GenerativeModel(GEMINI_MODEL)
            resp = model.generate_content(prompt)
            text = (resp.text or "").strip().lower()
            text = text.split()[0] if text else ""
            text = text.strip(".,!?\"'`")
            if text in DOMAIN_MAP:
                return {"domain": text, "source": "llm"}
        except Exception:
            pass

    # Fallback: keyword match.
    q = question.lower()
    for domain, kws in _KEYWORDS.items():
        if any(k in q for k in kws):
            return {"domain": domain, "source": "keyword"}
    return {"domain": "general", "source": "fallback"}


# ---------------------------------------------------------------------------
# 1b. Word-to-house mapping (May 19 Durga MOM — action item #4)
# ---------------------------------------------------------------------------
#
# Replaces the rigid 14-domain classifier above with a dictionary-driven
# narrowing of candidate houses, followed by an LLM disambiguation step
# constrained to that narrowed set.
#
# Order of operations:
#   1. house_mapper.map_question(q) → token-driven candidates
#   2. If 0 candidates    → fall back to classify_question + DOMAIN_MAP
#      If 1 candidate     → accept it directly, skip the LLM
#      If 2+ candidates   → ask the LLM to pick top 1-3
#
# Output shape (the "intent" object downstream code consumes):
#   {
#     "selected_houses":  [5],
#     "natural_karakas":  ["Jupiter", "Venus", "Mars"],
#     "label":            "Children / Creativity / Play / Romance",
#     "source":           "dictionary" | "dictionary+llm" | "domain_map_fallback",
#     "mapping":          <house_mapper.map_question trace>,
#     "llm_reasoning":    str | None,
#     "domain":           str   # legacy field, present for downstream
#                              # HOUSE_MEANING_FOR_DOMAIN lookup. "general"
#                              # when dictionary-driven (no 14-domain key).
#   }
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Polarity classification — the new LLM step (May-meeting follow-up).
# ---------------------------------------------------------------------------
#
# Replaces _llm_pick_houses. Where the old version asked "pick 1-3 houses",
# the new version asks "given the user's actual intent, classify each
# candidate house as favourable (strength = helpful to user's preferred
# outcome) or unfavourable (strength = obstacle to it)".
#
# Why this matters: bag-of-words misses negation, escape verbs, and tense.
# "Will I lose my job?" and "Will my career grow?" hit the SAME tokens but
# need OPPOSITE polarity on H10. The LLM is the only layer that can read
# the full sentence and decide.
#
# Hallucination control:
#   1. JSON schema enforcement via response_schema — the model literally
#      cannot return malformed output.
#   2. Temperature 0 — deterministic for a given prompt.
#   3. Candidate set is constrained to (dictionary candidates ∪ structural
#      dusthana); LLM is *permitted* to add up to 2 outside houses with
#      explicit reasoning, surfaced as `llm_added_houses` in the trace.
#   4. Examples in the prompt explicitly walk through the "avoid" polarity
#      flip — this was the case where the older gemini-3.1-pro-preview
#      tripped during our model selection probe.


def _structural_opposition(primary_house: int) -> dict[int, str]:
    """For any primary house, return the classical dusthana relationships:
       6th-from-primary  → obstacles / disputes about the matter
       8th-from-primary  → sudden disruption / endings of the matter
       12th-from-primary → loss / dissolution of the matter
    Returns {house_num: relationship_label}. House numbers wrap 1..12.
    """
    rotate = lambda p, offset: ((p - 1 + offset - 1) % 12) + 1
    return {
        rotate(primary_house, 6):  f"6th-from-H{primary_house} (obstacles/disputes)",
        rotate(primary_house, 8):  f"8th-from-H{primary_house} (sudden disruption)",
        rotate(primary_house, 12): f"12th-from-H{primary_house} (loss/dissolution)",
    }


# JSON schema the LLM is constrained to produce.
# Gemini's response_schema is a SUBSET of JSON Schema — it does NOT accept
# minItems / maxItems / minimum / maximum on items. We enforce those
# constraints in Python after parsing (see sanitization in _llm_classify_houses).
_POLARITY_SCHEMA = {
    "type": "object",
    "properties": {
        "user_intent": {
            "type": "string",
            "enum": ["achieve", "avoid", "predict", "decide", "timing", "quality"],
            "description": (
                "What the user actually wants: "
                "'achieve' (e.g. will career grow), "
                "'avoid' (e.g. should I avoid this marriage), "
                "'predict' (e.g. will it rain — no clear preference), "
                "'decide' (e.g. should I take this job — wants advice), "
                "'timing' (e.g. when will I marry), "
                "'quality' (e.g. how will the trip go — character not yes/no)."
            ),
        },
        "intent_summary": {
            "type": "string",
            "description": "One sentence in plain language describing what the user wants. Should cite specific words from their question.",
        },
        "negation_detected": {
            "type": "boolean",
            "description": "Did the question contain a polarity-flipping phrase ('avoid', 'not', 'never', 'lose', 'escape', 'leave', 'quit')?",
        },
        "favourable_houses": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "Up to 3 houses (1-12) whose STRENGTH supports the user's preferred outcome. First house is the primary. At least 1 required.",
        },
        "unfavourable_houses": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "Up to 3 houses (1-12) whose STRENGTH would obstruct the user's preferred outcome. May be empty.",
        },
        "llm_added_houses": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "Up to 2 houses (1-12) you added that were NOT in the candidate set. Each must be justified in `reasoning`. May be empty.",
        },
        "reasoning": {
            "type": "string",
            "description": (
                "2-3 sentences justifying your picks. MUST cite specific words "
                "from the user's question. MUST explain any house you added "
                "outside the candidate set. Do not write generic statements."
            ),
        },
    },
    "required": [
        "user_intent", "intent_summary", "negation_detected",
        "favourable_houses", "unfavourable_houses", "reasoning",
    ],
}


def _llm_classify_houses(
    question: str, trace: dict
) -> dict | None:
    """Ask Gemini to classify candidate houses as favourable or unfavourable
    for the user's preferred outcome.

    Returns the parsed schema-conformant dict, or None on configuration
    failure (caller falls back to top-N-by-score with empty unfavourable list).
    Network/API errors also return None — graceful degradation.
    """
    candidates = trace["candidates"]
    if not candidates or not _configure_gemini():
        return None

    # Top candidate's primary becomes the anchor for structural opposition.
    primary = candidates[0]["house"]
    opposition = _structural_opposition(primary)

    # Build a deduplicated candidate union (dictionary + structural opposition).
    house_labels = house_mapper.HOUSE_LABELS
    candidate_lines: list[str] = []
    for c in candidates[:6]:
        toks = ", ".join(c["supporting_tokens"])
        candidate_lines.append(
            f"  H{c['house']:>2}  (dictionary match: \"{toks}\")  — {house_labels.get(c['house'], '?')}"
        )
    opposition_lines: list[str] = []
    for h, label in opposition.items():
        # Only add to the prompt if not already a dictionary candidate (avoid duplication)
        if h not in {c["house"] for c in candidates[:6]}:
            opposition_lines.append(
                f"  H{h:>2}  ({label})  — {house_labels.get(h, '?')}"
            )

    prompt = f"""You are a Prashna (horary Vedic astrology) house classifier.

USER QUESTION: "{question}"

# DICTIONARY-DERIVED CANDIDATES (matched via word→house mapping):
{chr(10).join(candidate_lines)}

# STRUCTURAL OPPOSITION (auto-derived from primary candidate H{primary}):
{chr(10).join(opposition_lines) if opposition_lines else "  (none — primary's dusthana houses are already in the dictionary candidates)"}

# YOUR TASK
1. Identify what the user ACTUALLY wants. Cite specific words from their question.
2. Classify each relevant house as FAVOURABLE or UNFAVOURABLE relative to that preferred outcome.

# CRITICAL POLARITY RULES
- "Will my career grow?"     → user wants growth.   H10 strong = ✅ favourable.
- "Will I lose my job?"      → user fears loss.     H10 strong = ✅ favourable (job is safe);  H8/H12 strong = ❌ unfavourable.
- "Should I avoid X?"        → user wants to avoid X. House of X strong = ❌ unfavourable (X is robust, hard to avoid).
- "Should I quit my job?"    → user is considering leaving. H10 strong = ❌ unfavourable (job is solid, hard to leave); H8 strong = ✅ favourable (easy transition).
- "Will my marriage last?"   → user wants it to last. H7/H2 strong = ✅ favourable; H8/H12 strong = ❌ unfavourable.

# WORD-LEVEL POLARITY TRIGGERS (set negation_detected=true if any appear)
"avoid", "not", "never", "without", "lose", "escape", "leave", "quit",
"end", "break", "cancel", "skip", "refuse", "reject"

# RULES ON HOUSE SELECTION
- favourable_houses: 1-3 houses. The FIRST is the primary house.
- unfavourable_houses: 0-3 houses. Empty list is allowed for pure prediction
  questions where no obstacle factors are obvious from the question.
- Prefer houses from the candidate union above. You MAY add up to 2 houses
  outside this set IF they are astrologically critical AND not in the union
  — list them in llm_added_houses and justify in reasoning.
- A house may appear in EITHER favourable_houses OR unfavourable_houses,
  never both.

Be precise and conservative. If unsure, return fewer houses with higher confidence."""

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        resp = model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": _POLARITY_SCHEMA,
                "temperature": 0,
            },
        )
        text = (resp.text or "").strip()
        if not text:
            return None
        data = json.loads(text)

        # Sanitize numeric house IDs + enforce non-overlap between fav/unfav.
        fav = [int(h) for h in (data.get("favourable_houses") or []) if 1 <= int(h) <= 12][:3]
        unfav = [int(h) for h in (data.get("unfavourable_houses") or []) if 1 <= int(h) <= 12][:3]
        # Drop any unfavourable that's also in favourable (favourable wins)
        unfav = [h for h in unfav if h not in fav]
        added = [int(h) for h in (data.get("llm_added_houses") or []) if 1 <= int(h) <= 12][:2]

        # Track which favourable houses came from where (for trace transparency)
        candidate_set = {c["house"] for c in candidates}
        opposition_set = set(opposition.keys())

        return {
            "user_intent":         data.get("user_intent") or "predict",
            "intent_summary":      data.get("intent_summary") or "",
            "negation_detected":   bool(data.get("negation_detected", False)),
            "favourable_houses":   fav,
            "unfavourable_houses": unfav,
            "llm_added_houses":    added,
            "candidate_set":       sorted(candidate_set),
            "opposition_set":      sorted(opposition_set),
            "reasoning":           data.get("reasoning") or "",
        }
    except Exception as e:
        # Don't crash on Gemini hiccup; caller will gracefully fall back.
        print(f"[interpret] _llm_classify_houses failed: {e}", file=__import__("sys").stderr)
        return None


def _domain_map_fallback(question: str) -> dict:
    """Used only when the dictionary returns ZERO candidate houses.
    Falls back to the old 14-domain classifier so the system still produces
    a reading instead of erroring out.
    """
    intent_raw = classify_question(question)
    domain = intent_raw["domain"]
    spec = DOMAIN_MAP[domain]
    return {
        "selected_houses":  list(spec["houses"]),
        "natural_karakas":  list(spec["naturals"]),
        "label":            spec["label"],
        "source":           f"domain_map_fallback({intent_raw['source']})",
        "mapping":          None,
        "llm_reasoning":    None,
        "domain":           domain,
    }


def decide_houses(question: str) -> dict:
    """Pick the houses relevant to a question via the dictionary → LLM polarity
    classifier pipeline, with a graceful fallback to the old domain classifier.

    Output shape (new fields marked ★ for the polarity-aware revision):
      {
        "selected_houses":       [int, …],   # legacy alias = favourable_houses
        "favourable_houses":     [int, …],   ★ houses whose strength helps user's outcome
        "unfavourable_houses":   [int, …],   ★ houses whose strength obstructs it
        "llm_added_houses":      [int, …],   ★ houses LLM added outside candidates
        "natural_karakas":       [str, …],
        "label":                 str,
        "source":                "dictionary" | "dictionary+llm" | "domain_map_fallback(*)",
        "mapping":               <trace dict>,
        "llm_reasoning":         str | None,
        "user_intent":           str | None, ★ "achieve" | "avoid" | "predict" | "decide" | "timing" | "quality"
        "intent_summary":        str | None, ★ one-sentence plain-English description
        "negation_detected":     bool | None,★ explicit flip-the-polarity phrase present
        "domain":                str,        # legacy hint for HOUSE_MEANING_FOR_DOMAIN
      }
    """
    trace = house_mapper.map_question(question)
    candidates = trace["candidates"]

    if not candidates:
        # Zero matches — fall back to the old 14-domain classifier. We don't
        # run the polarity classifier here because the fallback already
        # produces a fixed houses list; nothing to classify.
        fb = _domain_map_fallback(question)
        # Decorate with empty polarity fields so downstream code doesn't NPE.
        fb.update({
            "favourable_houses":   list(fb["selected_houses"]),
            "unfavourable_houses": [],
            "llm_added_houses":    [],
            "unfavourable_natural_karakas": [],
            "user_intent":         None,
            "intent_summary":      None,
            "negation_detected":   None,
        })
        return fb

    if len(candidates) == 1:
        # Single candidate → no LLM call needed for picking, but we still
        # benefit from polarity classification (e.g. "Should I avoid X?"
        # with a single dictionary hit on X still needs a polarity flip).
        # So we DO run the classifier here — its output may flip the lane.
        classification = _llm_classify_houses(question, trace)
        if classification:
            return _build_intent(trace, classification, source="dictionary+llm")
        # Classifier unavailable → accept candidate as favourable, no opposition.
        h = candidates[0]["house"]
        return {
            "selected_houses":     [h],
            "favourable_houses":   [h],
            "unfavourable_houses": [],
            "llm_added_houses":    [],
            "natural_karakas":     house_mapper.natural_karakas_for_houses([h]),
            "unfavourable_natural_karakas": [],
            "label":               house_mapper.label_for_houses([h]),
            "source":              "dictionary",
            "mapping":             trace,
            "llm_reasoning":       None,
            "user_intent":         None,
            "intent_summary":      None,
            "negation_detected":   None,
            "domain":              "general",
        }

    # 2+ candidates → LLM classifies polarity
    classification = _llm_classify_houses(question, trace)
    if classification:
        return _build_intent(trace, classification, source="dictionary+llm")

    # LLM unavailable / errored → top-N-by-score fallback, all marked favourable.
    top_by_score = [c["house"] for c in candidates[:3]]
    return {
        "selected_houses":     top_by_score,
        "favourable_houses":   top_by_score,
        "unfavourable_houses": [],
        "llm_added_houses":    [],
        "natural_karakas":     house_mapper.natural_karakas_for_houses(top_by_score),
        "unfavourable_natural_karakas": [],
        "label":               house_mapper.label_for_houses(top_by_score),
        "source":              "dictionary+top_score",
        "mapping":             trace,
        "llm_reasoning":       None,
        "user_intent":         None,
        "intent_summary":      None,
        "negation_detected":   None,
        "domain":              "general",
    }


def _build_intent(trace: dict, classification: dict, source: str) -> dict:
    """Assemble the intent dict from a successful polarity classification.
    `selected_houses` is kept as an alias for `favourable_houses` so all
    existing downstream code keeps working without reading the polarity
    fields it doesn't yet understand.

    Natural karakas are computed for BOTH lanes: the favourable karakas
    (planets that, when strong, help the user) and the unfavourable karakas
    (planets that, when strong, reinforce the obstacle and therefore
    obstruct the user's preferred outcome). The unfavourable karakas are
    scored in the unfavourable lane by gather_evidence.
    """
    fav = classification["favourable_houses"]
    unfav = classification["unfavourable_houses"]
    fav_karakas = house_mapper.natural_karakas_for_houses(fav)
    # Karakas of unfavourable houses, with any planet that's ALSO a favourable
    # karaka removed — when a planet plays both roles, the favourable lane
    # claims it (avoids double-counting in opposite directions).
    raw_unfav_karakas = house_mapper.natural_karakas_for_houses(unfav)
    unfav_karakas = [k for k in raw_unfav_karakas if k not in fav_karakas]
    return {
        "selected_houses":     fav,
        "favourable_houses":   fav,
        "unfavourable_houses": unfav,
        "llm_added_houses":    classification["llm_added_houses"],
        "natural_karakas":     fav_karakas,
        "unfavourable_natural_karakas": unfav_karakas,
        "label":               house_mapper.label_for_houses(fav),
        "source":              source,
        "mapping":             trace,
        "llm_reasoning":       classification["reasoning"],
        "user_intent":         classification["user_intent"],
        "intent_summary":      classification["intent_summary"],
        "negation_detected":   classification["negation_detected"],
        "domain":              "general",
    }


# ---------------------------------------------------------------------------
# 2. Evidence gathering from the chart (deterministic)
# ---------------------------------------------------------------------------

STATE_SCORE = {"exalted": 2.0, "own": 1.0, "debilitated": -2.0, "neutral": 0.0}
RELATION_SCORE = {"own": 1.0, "friend": 0.5, "neutral": 0.0, "enemy": -0.5}


def _planet(chart: dict, name: str) -> dict | None:
    for p in chart["planets"]:
        if p["name"] == name:
            return p
    return None


def _house(chart: dict, num: int) -> dict:
    return chart["houses"][num - 1]


def _karaka_planet(chart: dict, karaka: str) -> dict | None:
    for k in chart.get("chara_karakas", []):
        if k["karaka"] == karaka:
            return _planet(chart, k["planet"])
    return None


def _score_planet(p: dict) -> tuple[float, list[str]]:
    """Return (score, notes) for a planet's current condition."""
    score = STATE_SCORE.get(p["state"], 0.0)
    notes = []
    if p["state"] == "exalted":         notes.append("exalted (peak strength)")
    elif p["state"] == "own":           notes.append("in own sign (comfortable)")
    elif p["state"] == "debilitated":   notes.append("debilitated (struggling)")
    rel = p.get("relation", "neutral")
    if rel == "friend":   notes.append("in friend's sign")
    elif rel == "enemy":  notes.append("in enemy's sign")
    score += RELATION_SCORE.get(rel, 0.0)
    if p.get("combust"):
        score -= 1.0
        notes.append("combust (burnt by Sun)")
    if p.get("retrograde"):
        notes.append("retrograde")
    return score, notes


# Dampening factor applied to all unfavourable-lane contributions.
# Classical Parashari treats the primary house lord as the central signal;
# opposition factors are qualifying weather, not equal-weight inputs. We
# dampen by 0.7 so a strong opposition lord can shade the verdict without
# fully cancelling a strong primary lord. See Durga meeting decision log.
UNFAVOURABLE_DAMPENING = 0.7


def gather_evidence(
    chart: dict,
    favourable_houses: list[int],
    unfavourable_houses: list[int] | None,
    natural_karakas: list[str],
    unfavourable_natural_karakas: list[str] | None = None,
    domain_key: str = "general",
) -> dict:
    """Build a polarity-aware evidence list from the chart.

    Two lanes:
      • Favourable lane — strong = good for user's preferred outcome.
        Contributions positive when factors are strong, negative when weak.
      • Unfavourable lane — strong = bad for user's preferred outcome.
        Contributions are SIGN-FLIPPED and DAMPENED (×0.7) so a strong
        opposition lord subtracts from the total without fully cancelling
        a strong primary lord.

    Per-item evidence entries are tagged with `lane: "favourable" | "unfavourable" | "context"`
    so the trace UI can render the two columns side by side.

    Args:
        chart:                          the full chart dict from prashna.compute_chart
        favourable_houses:              houses whose strength helps the user (primary first)
        unfavourable_houses:            houses whose strength obstructs the user (can be empty)
        natural_karakas:                planets to treat as natural significators on the FAVOURABLE side
        unfavourable_natural_karakas:   planets that are natural significators of the UNFAVOURABLE
                                        houses — scored in the unfavourable lane (sign-flipped,
                                        dampened). E.g. for "avoid marriage" with H7 unfavourable,
                                        Venus + Mercury go here. Defaults to empty list.
        domain_key:                     legacy hint for HOUSE_MEANING_FOR_DOMAIN phrasing

    Returns:
      {
        ..., "favourable_score", "unfavourable_score", "total_score",
        "favourable_houses", "unfavourable_houses",
        "primary_houses": <legacy alias for favourable_houses>,
        "evidence": [{factor, subject, detail, score, weight, lane}, …]
      }
    """
    if not favourable_houses:
        favourable_houses = [1]
    if unfavourable_houses is None:
        unfavourable_houses = []
    if not natural_karakas:
        natural_karakas = ["Sun", "Moon"]
    if unfavourable_natural_karakas is None:
        unfavourable_natural_karakas = []

    evidence: list[dict] = []
    fav_score = 0.0
    unfav_score = 0.0

    # ------------------------------------------------------------------
    # Favourable lane — house lord + supporting + karakas
    # ------------------------------------------------------------------
    # Primary favourable house and its lord ----
    primary_house_num = favourable_houses[0]
    primary_house = _house(chart, primary_house_num)
    lord = _planet(chart, primary_house["lord"])
    s, notes = _score_planet(lord)
    delta = s * 1.5
    fav_score += delta
    evidence.append({
        "factor": f"House {primary_house_num} — primary (favourable)",
        "subject": f"{primary_house['sign']} ({primary_house['sign_sanskrit']}), ruled by {primary_house['lord']}",
        "detail": (
            f"The {primary_house_num}th house sign is {primary_house['sign']}. "
            f"Its lord {primary_house['lord']} is in {lord['sign']} ({lord['nakshatra']} pada {lord['pada']}), "
            f"sitting in the {lord['house']}th house. "
            f"Condition: {', '.join(notes) if notes else 'neutral'}."
        ),
        "score": round(delta, 2),
        "weight": "primary",
        "lane": "favourable",
    })
    if primary_house["occupants"]:
        evidence.append({
            "factor": f"Planets sitting in House {primary_house_num}",
            "subject": ", ".join(primary_house["occupants"]),
            "detail": (
                f"{', '.join(primary_house['occupants'])} currently occupy the "
                f"{primary_house_num}th house — they actively shape this domain."
            ),
            "score": 0.0,
            "weight": "context",
            "lane": "context",
        })

    # Supporting favourable houses ----
    for hn in favourable_houses[1:]:
        h = _house(chart, hn)
        l = _planet(chart, h["lord"])
        s2, notes2 = _score_planet(l)
        delta = s2 * 0.5
        fav_score += delta
        evidence.append({
            "factor": f"House {hn} — supporting (favourable)",
            "subject": f"{h['sign']}, ruled by {h['lord']}",
            "detail": f"Lord {h['lord']} in {l['sign']} — {', '.join(notes2) if notes2 else 'neutral'}.",
            "score": round(delta, 2),
            "weight": "supporting",
            "lane": "favourable",
        })

    # Natural karakas (favourable lane) ----
    for nk in natural_karakas:
        p = _planet(chart, nk)
        if not p:
            continue
        s3, notes3 = _score_planet(p)
        delta = s3
        fav_score += delta
        evidence.append({
            "factor": f"Natural karaka: {nk}",
            "subject": f"{nk} in {p['sign']}, {p['house']}th house",
            "detail": (
                f"{nk} is the natural significator of this domain. "
                f"It sits in {p['sign']} ({p['nakshatra']} pada {p['pada']}), "
                f"{p['house']}th house, avastha: {p['avastha']}. "
                f"Condition: {', '.join(notes3) if notes3 else 'neutral'}."
            ),
            "score": round(delta, 2),
            "weight": "primary",
            "lane": "favourable",
        })

    # Natural karakas (unfavourable lane) ----
    # Strong karaka of an obstacle → strong obstacle → SUBTRACT.
    # Weak karaka of an obstacle → feeble obstacle → ADD.
    # Skip any planet already scored as a favourable karaka (avoid double-counting).
    _seen_fav_karakas = set(natural_karakas)
    for nk in unfavourable_natural_karakas:
        if nk in _seen_fav_karakas:
            continue
        p = _planet(chart, nk)
        if not p:
            continue
        s_uk, notes_uk = _score_planet(p)
        delta = -s_uk * 1.0 * UNFAVOURABLE_DAMPENING
        unfav_score += delta
        if s_uk > 0:
            verdict_hint = "obstacle's significator is strong — argues against the user's outcome"
        elif s_uk < 0:
            verdict_hint = "obstacle's significator is feeble — favours the user's outcome"
        else:
            verdict_hint = "obstacle's significator is neutral"
        evidence.append({
            "factor": f"Natural karaka: {nk} (unfavourable)",
            "subject": f"{nk} in {p['sign']}, {p['house']}th house",
            "detail": (
                f"{nk} is the natural significator of the OBSTACLE domain. "
                f"It sits in {p['sign']} ({p['nakshatra']} pada {p['pada']}), "
                f"{p['house']}th house, avastha: {p['avastha']}. "
                f"Condition: {', '.join(notes_uk) if notes_uk else 'neutral'}. "
                f"{verdict_hint.capitalize()} (dampened ×{UNFAVOURABLE_DAMPENING})."
            ),
            "score": round(delta, 2),
            "weight": "primary-negative",
            "lane": "unfavourable",
        })

    # ------------------------------------------------------------------
    # Unfavourable lane — opposition house lords (sign-flipped, dampened)
    # ------------------------------------------------------------------
    # Strong opposition lord → strong obstacle → SUBTRACT from total.
    # Weak opposition lord → feeble obstacle → ADD to total.
    # Hence: delta = -score × weight × dampening
    for idx, hn in enumerate(unfavourable_houses):
        h = _house(chart, hn)
        l = _planet(chart, h["lord"])
        s_u, notes_u = _score_planet(l)
        weight_label = "primary-negative" if idx == 0 else "supporting-negative"
        weight_mag = 1.5 if idx == 0 else 0.5
        delta = -s_u * weight_mag * UNFAVOURABLE_DAMPENING
        unfav_score += delta
        # Interpretation hint for the UI/narrative
        if s_u > 0:
            verdict_hint = "obstacle is strong — argues against the user's preferred outcome"
        elif s_u < 0:
            verdict_hint = "obstacle is feeble — favours the user's outcome"
        else:
            verdict_hint = "obstacle is neutral"
        evidence.append({
            "factor": f"House {hn} — {('primary' if idx == 0 else 'supporting')} (unfavourable)",
            "subject": f"{h['sign']}, ruled by {h['lord']}",
            "detail": (
                f"Opposition house: H{hn} ({h['sign']}). Lord {h['lord']} is in "
                f"{l['sign']} ({l['nakshatra']} pada {l['pada']}), {l['house']}th house. "
                f"Condition: {', '.join(notes_u) if notes_u else 'neutral'}. "
                f"{verdict_hint.capitalize()} (dampened ×{UNFAVOURABLE_DAMPENING})."
            ),
            "score": round(delta, 2),
            "weight": weight_label,
            "lane": "unfavourable",
        })

    # ------------------------------------------------------------------
    # DBA layers — route each lord to a lane based on its house placement
    # ------------------------------------------------------------------
    # Rule: a DBA lord sitting in an UNFAVOURABLE house amplifies that
    # obstacle's activation right now; it goes in the unfavourable lane
    # (sign-flipped + dampened). A lord in a FAVOURABLE house activates
    # the helpful domain; it goes in the favourable lane with the
    # standard core-house bonus. A lord in a NEUTRAL house contributes
    # a general timing signal to the favourable lane (no bonus).
    dasha = chart.get("dasha", {})

    dba_layers = [
        ("MD", dasha.get("current_mahadasha"), 0.6, 0.5,
         f"{dasha.get('remaining_years', '?')} years remaining",
         "long-term theme — the multi-year backdrop for this question"),
        ("AD", dasha.get("current_antardasha"), 0.5, 0.4,
         f"~{dasha.get('antardasha_remaining_days', '?')} days remaining",
         "current sub-period — coloring the MD theme right now"),
        ("PD", dasha.get("current_pratyantar"), 0.4, 0.3,
         f"~{dasha.get('pratyantar_remaining_days', '?')} days remaining",
         "immediate trigger — what's active this week"),
    ]

    for label, lord_name, weight, core_bonus, remaining, role in dba_layers:
        if not lord_name:
            continue
        lord = _planet(chart, lord_name)
        if not lord:
            continue
        s_layer, notes_layer = _score_planet(lord)
        lord_house = lord["house"]
        in_fav = lord_house in favourable_houses
        in_unfav = lord_house in unfavourable_houses

        if in_unfav:
            delta = -s_layer * weight * UNFAVOURABLE_DAMPENING
            unfav_score += delta
            relevance = f"sits in unfavourable H{lord_house} — timing amplifies the obstacle"
            lane = "unfavourable"
            ev_weight = "primary-negative" if label == "MD" else "supporting-negative"
        elif in_fav:
            delta = s_layer * weight + core_bonus
            fav_score += delta
            relevance = f"sits in favourable H{lord_house} — directly activates the domain"
            lane = "favourable"
            ev_weight = "primary" if label == "MD" else "supporting"
        else:
            delta = s_layer * weight
            fav_score += delta
            relevance = f"sits in H{lord_house} — colors the background context"
            lane = "favourable"
            ev_weight = "primary" if label == "MD" else "supporting"

        evidence.append({
            "factor": f"{label} — {lord_name} ({role.split(' — ')[0]})",
            "subject": f"{lord_name} {label} · {remaining}",
            "detail": (
                f"{role.capitalize()}. "
                f"{lord_name} sits in {lord['sign']}, {lord['house']}th house — {relevance}. "
                f"Condition: {', '.join(notes_layer) if notes_layer else 'neutral'}."
            ),
            "score": round(delta, 2),
            "weight": ev_weight,
            "lane": lane,
        })

    # ---- Timing window (context only, no scoring) ------------------------
    pd_timeline = dasha.get("pratyantar_timeline") or []
    current_pd_idx = next((i for i, t in enumerate(pd_timeline) if t.get("current")), None)
    if current_pd_idx is not None and current_pd_idx + 1 < len(pd_timeline):
        next_pd = pd_timeline[current_pd_idx + 1]
        evidence.append({
            "factor": "Timing window — next PD shift",
            "subject": f"{next_pd['lord']} pratyantar begins {next_pd['starts']}",
            "detail": (
                f"The current {dasha.get('current_pratyantar')} pratyantar runs until {pd_timeline[current_pd_idx]['ends']}. "
                f"After that, {next_pd['lord']} pratyantar takes over — that's often when "
                f"questions of this nature naturally resolve or shift direction."
            ),
            "score": 0.0,
            "weight": "context",
            "lane": "context",
        })

    # ---- Lagna lord (favourable lane, context weight) --------------------
    lagna_lord_name = chart["lagna"]["lord"]
    lagna_lord = _planet(chart, lagna_lord_name)
    s6, _notes6 = _score_planet(lagna_lord)
    delta = s6 * 0.3
    fav_score += delta
    evidence.append({
        "factor": "Lagna lord — strength of the question itself",
        "subject": f"{lagna_lord_name} (Lagna lord)",
        "detail": (
            f"The Lagna lord {lagna_lord_name} reflects the seriousness of the question. "
            f"It is {chart['lagna']['lord_state']} in {chart['lagna']['lord_sign']}. "
            f"{'A strong Lagna lord lends weight to the chart' if s6 > 0 else 'A weak Lagna lord softens the chart' if s6 < 0 else 'Lagna lord is steady'}."
        ),
        "score": round(delta, 2),
        "weight": "context",
        "lane": "favourable",
    })

    total_score = fav_score + unfav_score

    return {
        "domain":              domain_key,
        "label":               house_mapper.label_for_houses(favourable_houses),
        "favourable_houses":   favourable_houses,
        "unfavourable_houses": unfavourable_houses,
        "primary_houses":      favourable_houses,   # legacy alias for back-compat
        "natural_karakas":     natural_karakas,
        "unfavourable_natural_karakas": unfavourable_natural_karakas,
        "evidence":            evidence,
        "favourable_score":    round(fav_score, 2),
        "unfavourable_score":  round(unfav_score, 2),
        "total_score":         round(total_score, 2),
    }


# ---------------------------------------------------------------------------
# 3. Verdict (deterministic)
# ---------------------------------------------------------------------------

def make_verdict(total_score: float) -> dict:
    if total_score >= 3.0:
        label, confidence = "strongly favorable", "high"
    elif total_score >= 1.0:
        label, confidence = "favorable", "medium"
    elif total_score > -1.0:
        label, confidence = "mixed", "medium"
    elif total_score > -3.0:
        label, confidence = "challenging", "medium"
    else:
        label, confidence = "strongly challenging", "high"
    return {"label": label, "score": round(total_score, 2), "confidence": confidence}


# ---------------------------------------------------------------------------
# 4. Narrative synthesis (Gemini, with template fallback)
# ---------------------------------------------------------------------------

def _template_narrative(question: str, intent: dict, verdict: dict, evidence: list[dict]) -> str:
    primary = [e for e in evidence if e["weight"] == "primary"]
    bullets = "\n".join(f"• {e['factor']}: {e['subject']}" for e in primary[:4])
    return (
        f"You asked: \"{question}\"\n"
        f"This is a question about {intent['label']}.\n\n"
        f"Reading: {verdict['label']} (score {verdict['score']}, confidence {verdict['confidence']}).\n\n"
        f"Key factors:\n{bullets}"
    )


def _detect_caveats(chart: dict, core_houses: list[int], dba_stack: dict, ev_items: list[dict]) -> list[str]:
    """Flag the chart-significant caveats so the LLM is guaranteed to mention them."""
    caveats: list[str] = []
    if not core_houses:
        core_houses = [1]

    # 1. DBA lord caveats
    for layer in ("md", "ad", "pd"):
        info = dba_stack.get(layer) or {}
        lord = info.get("lord")
        if not lord:
            continue
        if info.get("combust"):
            caveats.append(f"{lord} ({layer.upper()}) is combust by the Sun — its judgement is clouded right now")
        if info.get("state") == "debilitated":
            caveats.append(f"{lord} ({layer.upper()}) is debilitated — weak placement for timing")
        if info.get("relation") == "enemy":
            caveats.append(f"{lord} ({layer.upper()}) sits in an enemy's sign — uneasy host")
        if info.get("retrograde"):
            caveats.append(f"{lord} ({layer.upper()}) is retrograde — themes may revisit or reverse")

    # 2. Primary house lord caveats
    primary_h_num = core_houses[0]
    primary_h = chart["houses"][primary_h_num - 1]
    lord_planet = _planet(chart, primary_h["lord"])
    if lord_planet:
        if lord_planet.get("combust"):
            caveats.append(f"the {primary_h_num}th lord ({lord_planet['name']}) is combust — primary house weakened")
        if lord_planet.get("state") == "debilitated":
            caveats.append(f"the {primary_h_num}th lord ({lord_planet['name']}) is debilitated — primary house struggling")

    return caveats


def synthesize(question: str, chart: dict, intent: dict, evidence: dict, verdict: dict) -> dict:
    template = _template_narrative(question, intent, verdict, evidence["evidence"])
    if not _configure_gemini():
        return {"answer": template, "source": "template"}

    # Houses + karakas now come from the new dictionary-driven mapper (or the
    # DOMAIN_MAP fallback path). `domain_key` is kept only as a hint for the
    # HOUSE_MEANING_FOR_DOMAIN lookup — "general" produces the broadly-applicable
    # English meanings, which is the right default when we don't have a 14-domain
    # match anymore.
    domain_key = intent.get("domain", "general")
    core_houses = intent.get("favourable_houses") or intent.get("selected_houses") or evidence.get("primary_houses") or [1]
    unfavourable_houses = intent.get("unfavourable_houses") or evidence.get("unfavourable_houses") or []
    natural_karakas = intent.get("natural_karakas") or evidence.get("natural_karakas") or []
    unfavourable_natural_karakas = intent.get("unfavourable_natural_karakas") or []

    # ---- DBA stack with per-layer house_meaning (the chart-specific hint) ----
    d = chart.get("dasha", {}) or {}
    def _dba_layer(lord_name):
        if not lord_name:
            return None
        p = _planet(chart, lord_name)
        if not p:
            return None
        return {
            "lord": lord_name,
            "sign": p["sign"],
            "house": p["house"],
            "house_meaning": _house_meaning(domain_key, p["house"]),
            "in_core_houses": p["house"] in core_houses,
            "state": p["state"],
            "relation": p.get("relation"),
            "retrograde": p.get("retrograde"),
            "combust": p.get("combust"),
        }

    dba_stack = {
        "md": {**(_dba_layer(d.get("current_mahadasha")) or {}),
               "remaining_years": d.get("remaining_years")},
        "ad": {**(_dba_layer(d.get("current_antardasha")) or {}),
               "remaining_days": d.get("antardasha_remaining_days")},
        "pd": {**(_dba_layer(d.get("current_pratyantar")) or {}),
               "remaining_days": d.get("pratyantar_remaining_days")},
    }

    # ---- Primary house lord (separate, so the LLM has it at hand) ----
    primary_h_num = core_houses[0]
    primary_h = chart["houses"][primary_h_num - 1]
    primary_lord_p = _planet(chart, primary_h["lord"]) or {}
    primary_house_lord = {
        "house_number": primary_h_num,
        "house_meaning": _house_meaning(domain_key, primary_h_num),
        "lord_name": primary_h["lord"],
        "lord_sits_in_house": primary_lord_p.get("house"),
        "lord_sits_in_house_meaning": _house_meaning(domain_key, primary_lord_p.get("house") or 0),
        "lord_sign": primary_lord_p.get("sign"),
        "lord_state": primary_lord_p.get("state"),
        "lord_combust": primary_lord_p.get("combust"),
        "lord_retrograde": primary_lord_p.get("retrograde"),
    }

    # ---- Pre-grouped positive / negative contributors ----
    ev_items = evidence["evidence"]
    scored = [e for e in ev_items if isinstance(e.get("score"), (int, float)) and e["score"] != 0]
    top_positive = sorted([e for e in scored if e["score"] > 0], key=lambda e: -e["score"])[:3]
    top_negative = sorted([e for e in scored if e["score"] < 0], key=lambda e: e["score"])[:2]
    _slim = lambda e: {"factor": e["factor"], "subject": e["subject"], "score": e["score"]}

    # ---- Caveats (deterministic — guarantees they surface in the reading) ----
    caveats = _detect_caveats(chart, core_houses, dba_stack, ev_items)

    # ---- Next PD shift (for the timing-window section) ----
    pd_timeline = d.get("pratyantar_timeline") or []
    cur_pd_idx = next((i for i, t in enumerate(pd_timeline) if t.get("current")), None)
    next_pd_shift = None
    if cur_pd_idx is not None and cur_pd_idx + 1 < len(pd_timeline):
        next_pd_shift = {
            "lord": pd_timeline[cur_pd_idx + 1]["lord"],
            "date": pd_timeline[cur_pd_idx + 1]["starts"],
        }

    # ---- Polarity context (new in the polarity-aware revision) ----
    # If the LLM classifier surfaced an explicit user intent + a list of
    # houses that OPPOSE the desired outcome, we pass that through so the
    # narrative can name the tension instead of glossing over it.
    user_intent = intent.get("user_intent")
    intent_summary = intent.get("intent_summary")
    negation_detected = intent.get("negation_detected")
    fav_score = evidence.get("favourable_score")
    unfav_score = evidence.get("unfavourable_score")
    unfav_meanings = {h: _house_meaning(domain_key, h) for h in unfavourable_houses}

    # Tension flag: both lanes carry significant signal in opposing directions.
    # Threshold tuned empirically — when unfav magnitude is >40% of fav magnitude
    # AND fav is positive, the chart has real "yes, BUT" character.
    has_tension = (
        fav_score is not None
        and unfav_score is not None
        and abs(unfav_score) > 0.4 * abs(fav_score)
        and fav_score > 0
        and unfav_score < 0
    )

    facts = {
        "question": question,
        "domain": intent["label"],
        "user_intent": user_intent,
        "intent_summary": intent_summary,
        "negation_detected": negation_detected,
        "favourable_houses": core_houses,
        "favourable_house_meanings": {h: _house_meaning(domain_key, h) for h in core_houses},
        "unfavourable_houses": unfavourable_houses,
        "unfavourable_house_meanings": unfav_meanings,
        "natural_karakas": natural_karakas,
        "unfavourable_natural_karakas": unfavourable_natural_karakas,
        "lagna": chart["lagna"],
        "primary_house_lord": primary_house_lord,
        "dba": dba_stack,
        "top_positive": [_slim(e) for e in top_positive],
        "top_negative": [_slim(e) for e in top_negative],
        "caveats": caveats,
        "verdict": verdict,
        "scores": {
            "favourable": fav_score,
            "unfavourable": unfav_score,
            "total": evidence.get("total_score"),
        },
        "has_tension": has_tension,
        "next_pd_shift": next_pd_shift,
    }

    prompt = f"""You are a Vedic astrologer giving a Prashna (horary) reading.

Tone: like a thoughtful friend who reads charts. Direct, grounded, specific to THIS chart.
Avoid cosmic vagueness ("the universe", "energies aligning"). No promises ("you will").
Prefer phrasings like "the chart suggests", "right now", "this period favors".

The user asked: "{question}"

# IMPORTANT — UNDERSTAND THE POLARITY
We have already classified what the user wants (`intent_summary`) and which
houses are FAVOURABLE (their strength helps the user's preferred outcome)
versus UNFAVOURABLE (their strength obstructs it). Read these two arrays
carefully — they are the FRAME for everything that follows.

- If `negation_detected` is true OR `user_intent` is "avoid", the user is
  hoping AGAINST something. A strong favourable house lord means "yes, the
  thing you hope for is supported." A strong unfavourable house lord means
  the obstacle is real and active.
- If `has_tension` is true, the chart has genuine "yes, but" character —
  the favourable side is positive but the unfavourable side is also active.
  The reading MUST name this tension explicitly in the verdict section.

Below are the structured facts from the chart cast at the moment of their question.
Use ONLY these facts. Do not invent placements, planets, or aspects.

FACTS (JSON):
{json.dumps(facts, indent=2, default=str)}

Write the reading as MARKDOWN with exactly these 6 sections, in order,
each starting with a level-2 header (##). Use the exact headers below:

## 🎯 The theme
2–3 sentences. Start by naming what the user wants in plain English (cite
`intent_summary`). Name the favourable houses in plain English (use
`favourable_house_meanings`). If `unfavourable_houses` is non-empty, name them
too as the houses to watch for obstacles. Name the natural karakas.

## ✨ The moment
2–3 sentences. Name the Lagna and where the Lagna lord sits.
Say what that implies about how sincere/serious the question is.

## 🏛️ The houses governing your question
2–4 sentences. Walk through the primary FAVOURABLE house lord's current
condition (use `lord_sits_in_house_meaning`). Then, if `unfavourable_houses`
is non-empty, briefly note whether the obstacle lord(s) look strong or weak —
this is the "yes, but" texture.

## ⏳ Who's on duty — the three timing lords
3–5 sentences. For EACH of the three DBA lords (MD, AD, PD):
  1. Name the lord AND the house it sits in.
  2. Use the lord's `house_meaning` to say what that house represents
     for THIS question.
  3. Add the lord's state (own/exalted/combust/etc.) as a MODIFIER, not the
     main point.
Then connect the three — how do the long-term, mid-term, and immediate
energies stack up together for THIS question?

CRITICAL: do NOT describe the planets' generic nature (e.g. "Saturn says step
carefully"). Describe their PLACEMENTS for THIS question. A reading that
would apply to any question has failed this section.

## ⚖️ The verdict
2–4 sentences. State the verdict label in the first sentence ("the chart leans
favorable" / "the chart is mixed" / etc). Then:
  - Name the TOP positive contributor from `top_positive`.
  - If `has_tension` is true, OR `top_negative` has an item with magnitude
    ≥ 1.0, explicitly name what the OBSTACLE FACTOR is showing. Use phrasing
    like "but watch for…" or "with the caveat that…". Do NOT bury this.
  - If `caveats` is non-empty, mention exactly ONE caveat from that list.
  - If both sides are weak (low magnitudes), say the chart is muted and the
    timing window matters more than the static picture.

## 🪔 The timing window
1–2 sentences. State the days remaining in the current pratyantar (from `dba.pd`).
Name who takes over next and on what date (from `next_pd_shift`). Imply how the
question's timing might shift — without making a promise. If `next_pd_shift` is null,
just describe the current window.

Return ONLY the markdown. No surrounding text, no JSON wrapper, no code fence.
"""

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        resp = model.generate_content(prompt)
        text = (resp.text or "").strip()
        # Strip accidental ```markdown fences if Gemini adds one anyway
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("markdown"):
                text = text[len("markdown"):].lstrip("\n")
            text = text.rstrip("`").strip()
        if text:
            return {"answer": text, "source": "gemini"}
    except Exception as e:
        return {"answer": template, "source": "template", "error": str(e)}

    return {"answer": template, "source": "template"}


# ---------------------------------------------------------------------------
# 5. Public entry point
# ---------------------------------------------------------------------------

def answer(question: str, chart: dict) -> dict:
    """The public /ask entry point.

    Pipeline (polarity-aware revision):
      1. decide_houses(question)  — dictionary → narrowed candidates →
                                    Gemini classifies favourable + unfavourable
      2. gather_evidence(chart, fav, unfav, karakas)  — dual-lane scoring
      3. make_verdict(total_score)                    — fixed thresholds
      4. synthesize(...)                              — Gemini writes the reading
                                                        with explicit polarity hints

    The `intent` block carries both the human-readable label AND the full
    mapping trace, ready to be persisted by the audit log.
    """
    intent = decide_houses(question)
    evidence = gather_evidence(
        chart,
        favourable_houses=intent.get("favourable_houses") or intent["selected_houses"],
        unfavourable_houses=intent.get("unfavourable_houses") or [],
        natural_karakas=intent["natural_karakas"],
        unfavourable_natural_karakas=intent.get("unfavourable_natural_karakas", []),
        domain_key=intent.get("domain", "general"),
    )
    verdict = make_verdict(evidence["total_score"])
    synth = synthesize(question, chart, intent, evidence, verdict)
    return {
        "question": question,
        "intent": intent,
        "evidence": evidence,
        "verdict": verdict,
        "answer": synth["answer"],
        "answer_source": synth["source"],
    }
