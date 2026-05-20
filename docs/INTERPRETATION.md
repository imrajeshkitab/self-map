# How Prashna Interpretations Are Made

This doc answers the question: **"When the user asks something and gets an answer back, what actually fed into that answer?"**

---

## TL;DR

A Prashna reading combines **6 context sources**, runs through **5 deterministic stages**, and uses the LLM in **only 2 places** — to classify the question, and to write the final prose.

The chart is always the source of truth. The LLM is constrained to use only the structured facts derived from it — it cannot invent placements, planets, or aspects.

---

## The 6 Context Sources

### 1. User Input
What the user provides directly:
- **Question text** (required) — e.g. "Should I take this new job?"
- **Moment** — defaults to "now"; overridable via the date/time picker
- **Location** — defaults to Gachibowli, Hyderabad; overridable via the place dropdown or geolocation

### 2. Swiss Ephemeris (external library)
The astronomy engine. Given a datetime + lat/lon, it returns precise planetary longitudes.
- Library: `swisseph` (pyswisseph)
- Configured for the **Lahiri ayanamsa** (Vedic sidereal zodiac)
- Produces: longitude + speed for Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu (Mean Node), Ketu (computed as Rahu + 180°)
- Speed sign tells us retrograde state
- Used in: `prashna.py → compute_chart()`

### 3. Static Vedic Reference Tables (`prashna.py`)
Hardcoded constants that encode classical Parashari rules:

| Table | What it encodes |
|-------|-----------------|
| `SIGN_LORDS` | Which planet rules each of the 12 signs |
| `PLANET_DATA` | Exaltation, debilitation, and domicile signs for each of 9 planets |
| `NATURAL_KARAKAS` | Houses each planet naturally signifies |
| `NAKSHATRAS` | The 27 lunar mansions, each spanning 13°20' |
| `NAK_LORDS` | Vimshottari lord cycle (Ketu, Venus, Sun, …) |
| `DASHA_YEARS` | 120-year proportional cycle (Ketu 7, Venus 20, …, Mercury 17) |
| `FRIENDSHIPS` | Permanent (Naisargika) planetary relationships |
| `COMBUST_ORBS` | Parashara's degree thresholds for combustion by the Sun |
| `BALADI_ODD/EVEN` | Five Baladi avastha bands by degree-in-sign |

### 4. Domain Knowledge (`interpret.py`)
The bridge between a free-text question and the chart. Hardcoded:

- **`DOMAIN_MAP`** — for each life-domain (career, marriage, wealth, health, …), declares:
  - which **houses** are primary for that question
  - which **natural significator planets** to consult
  - which **chara karaka role** applies *(Jaimini, slated for removal per Durga MOM)*
- **`_KEYWORDS`** — a fallback keyword classifier used only when the LLM is unavailable

### 5. Scoring Rules (`interpret.py`)
The math that turns chart conditions into a numeric verdict:

| Rule | Value |
|------|-------|
| Exalted | +2.0 |
| Own sign | +1.0 |
| Friend's sign | +0.5 |
| Neutral | 0.0 |
| Enemy's sign | −0.5 |
| Debilitated | −2.0 |
| Combust (burnt by Sun) | −1.0 |

**Weights per evidence layer:**

| Factor | Weight |
|--------|--------|
| Primary house lord | × 1.5 |
| Natural karakas | × 1.0 |
| Chara karaka | × 0.8 |
| Mahadasha lord | × 0.6 + 0.5 if in core house |
| Antardasha lord | × 0.5 + 0.4 if in core house |
| Pratyantar lord | × 0.4 + 0.3 if in core house |
| Supporting houses | × 0.5 |
| Lagna lord | × 0.3 |

**Verdict thresholds** (from total score):
- `≥ 3.0` → strongly favorable
- `≥ 1.0` → favorable
- `> −1.0` → mixed
- `> −3.0` → challenging
- otherwise → strongly challenging

### 6. Google Gemini LLM (`gemini-2.0-flash`)
Used in **exactly 2 stages** and nowhere else:

- **Question classification** — maps free text → one of ~14 domain keys. Falls back to keyword matching if the API is unavailable.
- **Narrative synthesis** — given the structured facts, writes the 4–6 sentence reading. The prompt forbids inventing placements. Falls back to a template if the API is unavailable.

The LLM never sees the raw question alone — for synthesis, it always receives the deterministic chart facts, evidence list, verdict, and DBA stack as JSON. It is a *prose writer*, not an *astrologer*.

---

## The 5-Stage Pipeline

Every `/ask` request flows through these stages, in order:

### Stage 1 — Chart Computation (`prashna.py`)
**Deterministic.** Swiss Ephemeris + static tables → a full chart object:
- Lagna (sign, degree, lord, nakshatra)
- 9 planet placements (sign, house, degree, nakshatra, state, retrograde, combust, relation, avastha)
- 12 whole-sign houses with their lords and occupants
- DBA: current MD / AD / PD lords with remaining time, plus timelines for all three levels
- Chara karakas (Jaimini, to be removed)

### Stage 2 — Question Classification (`interpret.py → classify_question`)
**LLM + fallback.** Question text → domain key.
Tries Gemini first; falls back to keyword matching; final fallback is `"general"`.

### Stage 3 — Evidence Gathering (`interpret.py → gather_evidence`)
**Deterministic.** Domain → list of weighted evidence factors:

1. **Primary house** + its lord's condition
2. **Planets occupying** the primary house (context only)
3. **Supporting houses** + their lords (lighter weight)
4. **Natural karakas** for the domain
5. **Chara karaka** (Jaimini role)
6. **MD lord** — long-term theme
7. **AD lord** — current sub-period coloring
8. **PD lord** — immediate trigger
9. **Timing window** — when the next PD shift happens (context only)
10. **Lagna lord** — sincerity of the question itself

Each factor produces a `(score, detail)` pair. Scores sum to a `total_score`.

### Stage 4 — Verdict (`interpret.py → make_verdict`)
**Deterministic.** `total_score` → label + confidence using fixed thresholds.

### Stage 5 — Narrative Synthesis (`interpret.py → synthesize`)
**LLM + fallback.** Gemini receives a structured JSON of `{question, domain, lagna, dba, verdict, evidence}` and writes a colloquial 4–6 sentence reading. The prompt:
- Forbids inventing facts
- Requires naming the MD/AD/PD lords once
- Requires a time-aware closing observation
- Forbids cosmic vagueness ("the universe", "energies aligning")
- Falls back to a template if the API is unavailable

---

## Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│  USER INPUT                                                          │
│  • question text:  "Should I take this new job?"                     │
│  • datetime:        defaults to now                                  │
│  • location:        defaults to Gachibowli                           │
└─────────────────────────────┬────────────────────────────────────────┘
                              │
            ┌─────────────────┴──────────────────┐
            │                                    │
            ▼                                    ▼
┌─────────────────────────────┐    ┌──────────────────────────────────┐
│  ① CHART COMPUTATION        │    │  ② QUESTION CLASSIFICATION       │
│     prashna.py              │    │     interpret.py                 │
│                             │    │                                  │
│  Sources:                   │    │  Sources:                        │
│   • Swiss Ephemeris         │    │   • Gemini LLM (primary)         │
│   • Static Vedic tables     │    │   • Keyword map (fallback)       │
│                             │    │                                  │
│  Produces (deterministic):  │    │  Produces:                       │
│   • Lagna                   │    │   • domain (career, marriage,    │
│   • 9 planets + state       │    │     wealth, health, …)           │
│   • 12 houses + occupants   │    │                                  │
│   • DBA: MD / AD / PD       │    │                                  │
│   • Aspects (coming next)   │    │                                  │
└─────────────┬───────────────┘    └─────────────┬────────────────────┘
              │                                  │
              │   chart (deterministic)          │   domain
              │                                  │
              └─────────────────┬────────────────┘
                                ▼
              ┌──────────────────────────────────────────┐
              │  ③ DOMAIN → HOUSES MAPPING               │
              │     interpret.py  DOMAIN_MAP             │
              │                                          │
              │   career  → houses [10, 6, 1]            │
              │             naturals [Sun, Saturn]       │
              │             chara role: Amatya           │
              └────────────────────┬─────────────────────┘
                                   ▼
              ┌──────────────────────────────────────────┐
              │  ④ EVIDENCE GATHERING (deterministic)    │
              │     interpret.py  gather_evidence()      │
              │                                          │
              │   For each factor, apply scoring rules:  │
              │    • Primary house + lord     × 1.5      │
              │    • Supporting houses        × 0.5      │
              │    • Natural karakas          × 1.0      │
              │    • Chara karaka             × 0.8      │
              │    • MD lord                  × 0.6      │
              │    • AD lord                  × 0.5      │
              │    • PD lord                  × 0.4      │
              │    • Timing window (next PD)  context    │
              │    • Lagna lord               × 0.3      │
              │                                          │
              │   Each evidence item:                    │
              │    { factor, subject, detail, score }    │
              │                                          │
              │   Sums → total_score                     │
              └────────────────────┬─────────────────────┘
                                   ▼
              ┌──────────────────────────────────────────┐
              │  ⑤ VERDICT (deterministic)               │
              │     interpret.py  make_verdict()         │
              │                                          │
              │   ≥ 3.0 → strongly favorable             │
              │   ≥ 1.0 → favorable                      │
              │   > −1.0→ mixed                          │
              │   > −3.0→ challenging                    │
              │   else  → strongly challenging           │
              └────────────────────┬─────────────────────┘
                                   ▼
              ┌──────────────────────────────────────────┐
              │  ⑥ NARRATIVE SYNTHESIS                   │
              │     interpret.py  synthesize()           │
              │                                          │
              │  Source: Gemini LLM (template fallback)  │
              │                                          │
              │  LLM input (JSON only):                  │
              │   { question, domain, lagna,             │
              │     dba: { md, ad, pd },                 │
              │     verdict, evidence }                  │
              │                                          │
              │  LLM constraints:                        │
              │   • No invented placements               │
              │   • Must name MD/AD/PD lords             │
              │   • Time-aware closing                   │
              │   • Colloquial, not mystical             │
              │                                          │
              │  → 4–6 sentence reading                  │
              └────────────────────┬─────────────────────┘
                                   ▼
              ┌──────────────────────────────────────────┐
              │  RESPONSE                                │
              │   { question, intent, evidence,          │
              │     verdict, answer, answer_source,      │
              │     chart (full DBA included) }          │
              └──────────────────────────────────────────┘
```

---

## Deterministic vs LLM — at a glance

| Stage | Type | Why |
|-------|------|-----|
| ① Chart computation | Deterministic | Pure astronomy + classical rules |
| ② Question classification | **LLM** (with fallback) | Free-text intent is fuzzy |
| ③ Domain → houses lookup | Deterministic | Hardcoded mapping |
| ④ Evidence gathering | Deterministic | Rule-based scoring |
| ⑤ Verdict | Deterministic | Fixed thresholds |
| ⑥ Narrative synthesis | **LLM** (with fallback) | Natural-language prose |

If both LLM calls fail, the system still produces a complete answer — keyword classification + template narrative — driven entirely by the chart and rules.

---

## How to Audit a Reading

For any answer in the UI:
1. **The verdict** comes from a single number: `total_score`. The math is in the **evidence list** — click each factor to see the score breakdown.
2. **The chart** that produced it is shown below the answer (Prashna chart + chart metadata).
3. **The DBA stack** is rendered as the 3-tier panel — those three lords are the ones the LLM was told about.
4. **The answer source** is tagged on the narrative card: `AI` (Gemini) or `Template` (deterministic fallback).

If a reading feels off, the first place to look is the **evidence list scores**. The LLM only describes what the scoring already decided — it cannot override the verdict.

---

## File Map

| File | Role |
|------|------|
| `prashna.py` | Chart computation. Pure astronomy + Vedic rules. No LLM. |
| `interpret.py` | Domain map, evidence scoring, verdict, LLM narrative. |
| `api.py` | FastAPI wrapper exposing `/ask`, `/today`, `/search`. |
| `frontend/ask.html` + `ask.js` + `ask.css` | The Prashna UI. |
| `frontend/today.html` + `today.js` | The "Today's Sky" non-question chart view. |

---

## Coming next (per May 12 Durga MOM)

- **Remove Jaimini Chara Karakas** — replace with Parashari-only logic
- **Fix natural karakas** — Career: Saturn (not Sun); add Self-Improvement domain (Mars)
- **3-step Prashna logic** — explicit genuineness check using Parashari aspects, then house analysis, then lord analysis
- **Compute aspects** — 7th for all planets, +4th/8th for Mars, +5th/9th for Jupiter, +3rd/10th for Saturn
