"""
dasha_table.py
===============
The Dasa Tenure Table — canonical reference for the 9 Vimshottari Mahadasha
lords, each with their fixed tenure (years) and Parashari signification metadata.

Implements May 19 Durga MOM action item #2:
  "Stores the fixed duration of each planetary Dasa.
   Use case: identify users completing a Dasa cycle and prepare them for the next one."

The numeric `years` field is the authoritative classical value (BPHS / Phaladeepika).
Total of all 9 = 120 years (the Vimshottari cycle).

The `themes`, `nature`, `tone`, `transition_advice` fields are Parashari-aligned
significations distilled from common modern textbooks (Light on Life, Phaladeepika).
They guide the LLM when narrating "where the user is in their dasha journey" —
not part of the math, just colour for the reading.
"""

from __future__ import annotations
from typing import Literal

PlanetName = Literal[
    "Sun", "Moon", "Mars", "Mercury", "Jupiter",
    "Venus", "Saturn", "Rahu", "Ketu",
]

Tone = Literal["favorable", "mixed", "challenging"]


# ---------------------------------------------------------------------------
# The table
# ---------------------------------------------------------------------------

DASHA_TENURE: dict[PlanetName, dict] = {
    # ------------------------------------------------------------------
    "Ketu": {
        "years":          7,
        "nature":         "spiritual, dissolving, sudden",
        "tone":           "mixed",
        "themes":         ["spirituality", "moksha", "detachment", "research",
                           "occult", "sudden change", "loss", "isolation"],
        "life_areas":     [8, 12],   # houses Ketu naturally activates
        "best_for":       "introspection, letting go, spiritual practice, research",
        "challenges":     "anxiety, isolation, sudden upheavals, confusion",
        "transition_advice":
            "As Ketu MD ends, expect a sense of clearing — what no longer "
            "serves drops away. The incoming Venus dasha tends to restore "
            "warmth, beauty, and relational life.",
    },
    # ------------------------------------------------------------------
    "Venus": {
        "years":          20,
        "nature":         "harmonious, sensual, relational",
        "tone":           "favorable",
        "themes":         ["love", "marriage", "art", "beauty", "luxury",
                           "comfort", "vehicles", "music", "diplomacy"],
        "life_areas":     [7, 4, 2],
        "best_for":       "relationships, creative work, financial stability, marriage",
        "challenges":     "indulgence, over-attachment, hesitation in conflict",
        "transition_advice":
            "Venus dasha's twenty-year arc is often the most relationally "
            "rich period in a life. As it closes, Sun MD takes over — "
            "the focus shifts toward authority, self-expression, and visibility.",
    },
    # ------------------------------------------------------------------
    "Sun": {
        "years":          6,
        "nature":         "authoritative, illuminating, ego-defining",
        "tone":           "mixed",
        "themes":         ["self", "authority", "government", "father",
                           "leadership", "fame", "vitality"],
        "life_areas":     [1, 9, 10],
        "best_for":       "stepping into authority, public roles, achievement, visibility",
        "challenges":     "ego clashes, conflict with father or bosses, burnout",
        "transition_advice":
            "Six years pass quickly. Sun MD often coincides with reputation "
            "shifts. Moon dasha follows — the next decade softens, "
            "becoming more emotional and home-focused.",
    },
    # ------------------------------------------------------------------
    "Moon": {
        "years":          10,
        "nature":         "fluctuating, emotional, public",
        "tone":           "mixed",
        "themes":         ["mind", "emotions", "mother", "home", "public",
                           "popularity", "intuition", "water"],
        "life_areas":     [4, 2],
        "best_for":       "emotional growth, family life, public connection, intuition",
        "challenges":     "mood swings, dependency, indecisiveness",
        "transition_advice":
            "Moon dasha's emotional weather changes often. As it ends, "
            "Mars MD brings sharper focus and direct action — sometimes "
            "felt as a relief after years of internal flux.",
    },
    # ------------------------------------------------------------------
    "Mars": {
        "years":          7,
        "nature":         "energetic, assertive, combative",
        "tone":           "mixed",
        "themes":         ["action", "energy", "courage", "siblings",
                           "property", "land", "competition", "conflict"],
        "life_areas":     [3, 6, 1],
        "best_for":       "decisive action, real estate moves, competitive ventures",
        "challenges":     "conflict, accidents, impatience, anger",
        "transition_advice":
            "Mars MD is short but intense. Rahu's 18-year MD follows — "
            "a long arc of ambition, foreign influences, and unconventional paths.",
    },
    # ------------------------------------------------------------------
    "Rahu": {
        "years":          18,
        "nature":         "ambitious, illusory, foreign, technological",
        "tone":           "mixed",
        "themes":         ["ambition", "foreign", "technology", "sudden gains",
                           "illusion", "obsession", "outside-the-box", "career leaps"],
        "life_areas":     [11, 6, 10],
        "best_for":       "career leaps, foreign moves, technology, ambitious projects",
        "challenges":     "obsession, scandal, deception, sudden falls, anxiety",
        "transition_advice":
            "Rahu's eighteen years are often the most transformative — "
            "career, identity, and ambitions shift. Jupiter MD follows "
            "and brings wisdom, slowing, and integration of those gains.",
    },
    # ------------------------------------------------------------------
    "Jupiter": {
        "years":          16,
        "nature":         "expansive, wise, blessing",
        "tone":           "favorable",
        "themes":         ["wisdom", "expansion", "children", "dharma",
                           "teachers", "philosophy", "blessings", "wealth"],
        "life_areas":     [2, 5, 9, 11],
        "best_for":       "higher learning, having children, spiritual growth, dharma",
        "challenges":     "over-extension, complacency, weight gain",
        "transition_advice":
            "Jupiter's sixteen years are widely seen as one of the most "
            "fortunate periods. As it ends, Saturn MD's nineteen-year "
            "discipline begins — structure replaces grace.",
    },
    # ------------------------------------------------------------------
    "Saturn": {
        "years":          19,
        "nature":         "disciplined, restrictive, structural, slow",
        "tone":           "challenging",
        "themes":         ["discipline", "hard work", "longevity", "structure",
                           "delays", "responsibility", "renunciation"],
        "life_areas":     [6, 8, 10, 12],
        "best_for":       "long-term builds, mastery through effort, renunciation, service",
        "challenges":     "delays, health issues, loneliness, depression",
        "transition_advice":
            "Saturn MD is the longest and often the heaviest period. "
            "Whatever survives Saturn becomes durable. Mercury MD follows "
            "— faster, lighter, more communicative.",
    },
    # ------------------------------------------------------------------
    "Mercury": {
        "years":          17,
        "nature":         "communicative, intellectual, agile",
        "tone":           "favorable",
        "themes":         ["communication", "learning", "business", "trade",
                           "writing", "intellect", "wit", "networks"],
        "life_areas":     [3, 5, 10],
        "best_for":       "writing, business, learning new skills, networking, trade",
        "challenges":     "scattered focus, nervousness, mental restlessness",
        "transition_advice":
            "Mercury's seventeen years favour communication and intellect. "
            "Ketu MD follows — a sudden inward turn after the Mercury "
            "extroversion, often felt as a course-correction.",
    },
}


# ---------------------------------------------------------------------------
# Derived constants
# ---------------------------------------------------------------------------

# The 9-lord cycle order used by Vimshottari (each successive MD follows this
# sequence — Ketu → Venus → Sun → Moon → Mars → Rahu → Jupiter → Saturn → Mercury → Ketu …).
VIMSHOTTARI_ORDER: list[PlanetName] = [
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury",
]

# Map of {planet: years} — convenience accessor used by the math layer.
DASHA_YEARS: dict[PlanetName, int] = {p: DASHA_TENURE[p]["years"] for p in VIMSHOTTARI_ORDER}

# Sanity check: the cycle must sum to 120 years.
assert sum(DASHA_YEARS.values()) == 120, f"DASHA_YEARS sum is {sum(DASHA_YEARS.values())} (must be 120)"


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def next_md_lord(current: PlanetName) -> PlanetName:
    """Return the lord that takes over after `current` Mahadasha ends."""
    i = VIMSHOTTARI_ORDER.index(current)
    return VIMSHOTTARI_ORDER[(i + 1) % 9]


def tenure_metadata(lord: PlanetName) -> dict:
    """Return the metadata block for a Mahadasha lord (themes, tone, advice)."""
    return DASHA_TENURE[lord]


if __name__ == "__main__":
    # Quick CLI sanity check.
    print(f"{'Lord':<10} {'Years':>5}  {'Tone':<13}  Themes")
    print("─" * 70)
    for p in VIMSHOTTARI_ORDER:
        t = DASHA_TENURE[p]
        themes = ", ".join(t["themes"][:3])
        print(f"{p:<10} {t['years']:>5}  {t['tone']:<13}  {themes}")
    print(f"\nTotal years: {sum(DASHA_YEARS.values())}  (must be 120 ✓)")
