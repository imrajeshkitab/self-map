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
GEMINI_MODEL = "gemini-2.0-flash"
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


def _llm_pick_houses(question: str, trace: dict) -> tuple[list[int], str | None]:
    """Ask Gemini to pick 1-3 houses from the dictionary's narrowed candidate set.
    Returns (selected_houses, reasoning). Falls back to top-N-by-score on failure.
    """
    candidates = trace["candidates"]
    top_by_score = [c["house"] for c in candidates[:6]]

    if not _configure_gemini():
        return top_by_score[:4], None

    # Build a compact, LLM-friendly table of candidates + house meanings
    house_labels = house_mapper.HOUSE_LABELS
    candidate_lines = []
    for c in candidates[:6]:    # show at most 6
        toks = ", ".join(c["supporting_tokens"])
        candidate_lines.append(
            f"  H{c['house']:>2}  score={c['score']}  "
            f"meaning={house_labels.get(c['house'], '?')}  "
            f"matched_tokens=[{toks}]"
        )
    candidates_table = "\n".join(candidate_lines)

    prompt = f"""You are mapping a Prashna (horary) question to the relevant Vedic houses.

The user asked: "{question}"

A deterministic dictionary lookup of the words in their question produced
these candidate houses, ranked by score:

{candidates_table}

Your task: pick the 1-3 houses most relevant to THIS specific question.

Rules:
  - Prefer FEWER houses with stronger signal over more houses with weak signal.
  - Only include a house if its match makes semantic sense for the question.
  - The first house in your list should be the PRIMARY house (most central).
  - Do NOT pick houses that aren't in the candidate list — the dictionary
    already narrowed the relevant set.
  - If two candidates are equally relevant, prefer the one with higher score.

Return ONLY a JSON object, no surrounding text:
{{"selected_houses": [5], "reasoning": "movie maps to the 5th house of entertainment"}}
"""

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        resp = model.generate_content(prompt)
        text = (resp.text or "").strip()
        # Strip code fences if Gemini wraps the JSON
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
            text = re.sub(r"\n?```\s*$", "", text)
        data = json.loads(text)
        picked = data.get("selected_houses") or []
        if not isinstance(picked, list):
            return top_by_score[:4], None
        # Sanitize: only houses that were actually in the candidate set
        valid_houses = {c["house"] for c in candidates}
        picked_valid = [int(h) for h in picked if isinstance(h, (int, str)) and int(h) in valid_houses]
        if not picked_valid:
            return top_by_score[:4], data.get("reasoning")
        return picked_valid[:3], data.get("reasoning")
    except Exception:
        return top_by_score[:4], None


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
    """Pick the houses relevant to a question via the dictionary → LLM pipeline,
    with a graceful fallback to the old domain classifier.

    See module-level comment for the output shape.
    """
    trace = house_mapper.map_question(question)
    candidates = trace["candidates"]

    if not candidates:
        return _domain_map_fallback(question)

    if len(candidates) == 1:
        houses = [candidates[0]["house"]]
        return {
            "selected_houses":  houses,
            "natural_karakas":  house_mapper.natural_karakas_for_houses(houses),
            "label":            house_mapper.label_for_houses(houses),
            "source":           "dictionary",
            "mapping":          trace,
            "llm_reasoning":    None,
            "domain":           "general",
        }

    # 2+ candidates → LLM picks
    picked, reasoning = _llm_pick_houses(question, trace)
    return {
        "selected_houses":  picked,
        "natural_karakas":  house_mapper.natural_karakas_for_houses(picked),
        "label":            house_mapper.label_for_houses(picked),
        "source":           "dictionary+llm" if reasoning else "dictionary+top_score",
        "mapping":          trace,
        "llm_reasoning":    reasoning,
        "domain":           "general",
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


def gather_evidence(
    chart: dict,
    houses: list[int],
    natural_karakas: list[str],
    domain_key: str = "general",
) -> dict:
    """Build a structured list of evidence facts from the chart.

    Args:
        chart:            the full chart dict (from prashna.compute_chart)
        houses:           houses selected for this question (primary first)
        natural_karakas:  planets to treat as natural significators
        domain_key:       legacy hint used only by HOUSE_MEANING_FOR_DOMAIN
                          for richer per-house phrasing. "general" → use
                          generic English meanings. Stays in place for the
                          synthesize() prompt; not used in scoring math.
    """
    # Guard: callers should always pass at least one house, but be safe.
    if not houses:
        houses = [1]
    if not natural_karakas:
        natural_karakas = ["Sun", "Moon"]

    evidence: list[dict] = []
    total_score = 0.0

    # ---- Primary house and its lord -------------------------------------
    primary_house_num = houses[0]
    primary_house = _house(chart, primary_house_num)
    lord = _planet(chart, primary_house["lord"])
    s, notes = _score_planet(lord)
    total_score += s * 1.5  # weight house lord heavily
    evidence.append({
        "factor": f"House {primary_house_num} — primary house for this question",
        "subject": f"{primary_house['sign']} ({primary_house['sign_sanskrit']}), ruled by {primary_house['lord']}",
        "detail": (
            f"The {primary_house_num}th house sign is {primary_house['sign']}. "
            f"Its lord {primary_house['lord']} is in {lord['sign']} ({lord['nakshatra']} pada {lord['pada']}), "
            f"sitting in the {lord['house']}th house. "
            f"Condition: {', '.join(notes) if notes else 'neutral'}."
        ),
        "score": round(s * 1.5, 2),
        "weight": "primary",
    })
    if primary_house["occupants"]:
        evidence.append({
            "factor": f"Planets sitting in House {primary_house_num}",
            "subject": ", ".join(primary_house["occupants"]),
            "detail": f"{', '.join(primary_house['occupants'])} currently occupy the {primary_house_num}th house — they actively shape this domain.",
            "score": 0.0,
            "weight": "context",
        })

    # ---- Supporting houses (lighter weight) -----------------------------
    for hn in houses[1:]:
        h = _house(chart, hn)
        l = _planet(chart, h["lord"])
        s2, notes2 = _score_planet(l)
        total_score += s2 * 0.5
        evidence.append({
            "factor": f"House {hn} — supporting",
            "subject": f"{h['sign']}, ruled by {h['lord']}",
            "detail": f"Lord {h['lord']} in {l['sign']} — {', '.join(notes2) if notes2 else 'neutral'}.",
            "score": round(s2 * 0.5, 2),
            "weight": "supporting",
        })

    # ---- Natural karakas -------------------------------------------------
    for nk in natural_karakas:
        p = _planet(chart, nk)
        if not p:
            continue
        s3, notes3 = _score_planet(p)
        total_score += s3
        evidence.append({
            "factor": f"Natural karaka: {nk}",
            "subject": f"{nk} in {p['sign']}, {p['house']}th house",
            "detail": (
                f"{nk} is the natural significator of this domain. "
                f"It sits in {p['sign']} ({p['nakshatra']} pada {p['pada']}), "
                f"{p['house']}th house, avastha: {p['avastha']}. "
                f"Condition: {', '.join(notes3) if notes3 else 'neutral'}."
            ),
            "score": round(s3, 2),
            "weight": "primary",
        })

    # NOTE: The old "Chara Karaka (Jaimini)" evidence block was removed per
    # the May 12 Durga MOM action item: "Remove all Jaimini-based logic
    # (Chara Karakas) — the system is built on Parashari astrology."
    # The chart still carries chara_karakas (for backward-compatible API
    # output) but they no longer participate in scoring or the reading.

    # ---- DBA: Mahadasha → Antardasha → Pratyantar ------------------------
    # Three nested timing layers. MD sets the multi-year backdrop;
    # AD is the active sub-period coloring it; PD is the immediate trigger.
    # Each layer is scored, with weight decreasing as scope narrows but bonus
    # increasing if that lord directly touches a core house for this question.
    dasha = chart.get("dasha", {})

    dba_layers = [
        # (label, lord_name, scope_weight, core_bonus, remaining_text, role_text)
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
        in_primary = lord["house"] in houses
        layer_score = s_layer * weight + (core_bonus if in_primary else 0.0)
        total_score += layer_score
        relevance = "directly activates this domain" if in_primary else "colors the background context"
        evidence.append({
            "factor": f"{label} — {lord_name} ({role.split(' — ')[0]})",
            "subject": f"{lord_name} {label} · {remaining}",
            "detail": (
                f"{role.capitalize()}. "
                f"{lord_name} sits in {lord['sign']}, {lord['house']}th house — {relevance}. "
                f"Condition: {', '.join(notes_layer) if notes_layer else 'neutral'}."
            ),
            "score": round(layer_score, 2),
            "weight": "primary" if label == "MD" else "supporting",
        })

    # ---- Timing window: when the next PD lord shifts ---------------------
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
        })

    # ---- Lagna lord — sincerity of the question -------------------------
    lagna_lord_name = chart["lagna"]["lord"]
    lagna_lord = _planet(chart, lagna_lord_name)
    s6, _notes6 = _score_planet(lagna_lord)
    evidence.append({
        "factor": "Lagna lord — strength of the question itself",
        "subject": f"{lagna_lord_name} (Lagna lord)",
        "detail": (
            f"The Lagna lord {lagna_lord_name} reflects the seriousness of the question. "
            f"It is {chart['lagna']['lord_state']} in {chart['lagna']['lord_sign']}. "
            f"{'A strong Lagna lord lends weight to the chart' if s6 > 0 else 'A weak Lagna lord softens the chart' if s6 < 0 else 'Lagna lord is steady'}."
        ),
        "score": round(s6 * 0.3, 2),
        "weight": "context",
    })
    total_score += s6 * 0.3

    return {
        "domain":           domain_key,
        "label":            house_mapper.label_for_houses(houses),
        "primary_houses":   houses,
        "natural_karakas":  natural_karakas,
        "evidence":         evidence,
        "total_score":      round(total_score, 2),
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
    core_houses = intent.get("selected_houses") or evidence.get("primary_houses") or [1]
    natural_karakas = intent.get("natural_karakas") or evidence.get("natural_karakas") or []

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

    facts = {
        "question": question,
        "domain": intent["label"],
        "primary_houses": core_houses,
        "primary_house_meanings": {h: _house_meaning(domain_key, h) for h in core_houses},
        "natural_karakas": natural_karakas,
        "lagna": chart["lagna"],
        "primary_house_lord": primary_house_lord,
        "dba": dba_stack,
        "top_positive": [_slim(e) for e in top_positive],
        "top_negative": [_slim(e) for e in top_negative],
        "caveats": caveats,
        "verdict": verdict,
        "next_pd_shift": next_pd_shift,
    }

    prompt = f"""You are a Vedic astrologer giving a Prashna (horary) reading.

Tone: like a thoughtful friend who reads charts. Direct, grounded, specific to THIS chart.
Avoid cosmic vagueness ("the universe", "energies aligning"). No promises ("you will").
Prefer phrasings like "the chart suggests", "right now", "this period favors".

The user asked: "{question}"

Below are the structured facts from the chart cast at the moment of their question.
Use ONLY these facts. Do not invent placements, planets, or aspects.

FACTS (JSON):
{json.dumps(facts, indent=2, default=str)}

Write the reading as MARKDOWN with exactly these 6 sections, in order,
each starting with a level-2 header (##). Use the exact headers below:

## 🎯 The theme
2–3 sentences. Name the primary houses governing this question in plain English
(use `primary_house_meanings` to phrase them naturally). Name the natural karakas
and what they mean here (e.g. "Saturn — hard work").

## ✨ The moment
2–3 sentences. Name the Lagna and where the Lagna lord sits.
Say what that implies about how sincere/serious the question is.

## 🏛️ The houses governing your question
2–4 sentences. Walk through the primary house lord's current condition —
where it sits (use `lord_sits_in_house_meaning`), what state it's in, why
that helps or hurts. If a top_positive or top_negative comes from a supporting
house, mention it briefly.

## ⏳ Who's on duty — the three timing lords
3–5 sentences. For EACH of the three DBA lords (MD, AD, PD):
  1. Name the lord AND the house it sits in.
  2. Use the lord's `house_meaning` (already chart-specific) to say what that
     house represents for THIS question.
  3. Add the lord's state (own/exalted/combust/etc.) as a MODIFIER, not the
     main point.
Then connect the three — how do the long-term, mid-term, and immediate
energies stack up together for THIS question?

CRITICAL: do NOT describe the planets' generic nature (e.g. "Saturn says step
carefully"). Describe their PLACEMENTS for THIS question. A reading that
would apply to any question has failed this section.

## ⚖️ The verdict
2–3 sentences. State the verdict label in the first sentence ("the chart leans
favorable" / "the chart is mixed" / etc). Then name the TOP positive contributor
AND exactly ONE caveat from the `caveats` list. If `caveats` is empty, omit the
caveat sentence.

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

    Pipeline (May 19 Durga MOM #4 architecture):
      1. decide_houses(question)  — dictionary → narrowed candidates → LLM picks
      2. gather_evidence(chart, houses, karakas)  — deterministic scoring
      3. make_verdict(score)                       — fixed thresholds
      4. synthesize(...)                           — Gemini writes the reading

    The `intent` block carries both the human-readable label AND the full
    mapping trace, ready to be persisted by the audit log (MOM #3).
    """
    intent = decide_houses(question)
    evidence = gather_evidence(
        chart,
        houses=intent["selected_houses"],
        natural_karakas=intent["natural_karakas"],
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
