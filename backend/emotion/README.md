# Daily Emotional Analysis Engine — `feat/emotional-engine`

Computes a person's **daily emotional vector** (10 dimensions, 0–100) from
their natal Moon, current Vimshottari DBA, and the transit Moon — exactly
per the 10-step specification. Output includes dominant themes, a narrative,
and a full step-by-step trace.

This is a **designed psychological model**, not a verse-cited transcription.
Every weight lives in `config/` so an astrologer (Durga) tunes interpretation
without touching code.

## The 10 steps → code

| Spec step | Where |
|---|---|
| 1 — Natal baseline (sign/nakshatra/house/aspects) | `engine.py` Step 1 + `config/sign,nakshatra,house_tables` |
| 2 — DBA climate (planet vectors, MD/AD/AD 50/30/20) | Step 2 + `config/planet_vectors`, `structure.dba_subweights` |
| 3 — Transit Moon sign & nakshatra | Step 3 + `config/sign,nakshatra`, `structure.transit_scale` |
| 4 — Moon house from natal Moon | Step 4 + `config/house_tables.transit_from_natal_moon` |
| 5 — Nakshatra-lord amplification | folded into Step 2 + `structure.nakshatra_lord_amplification` |
| 6 — Tara Bala | Step 6 + `config/tara_bala` |
| 7 — Chandra Ashtama | Step 7 + `structure.chandra_ashtama` |
| 8 — Moon ∩ natal DBA planets | folded into Step 2 + `structure.conjunction` |
| 9 — Final dimensions | Step 9 |
| 10 — Narrative rules | Step 10 + `config/narrative` |

## Math model (reconciles the spec's two formulas)

```
final[dim] = clamp( 50
                    + 0.30 · natal_delta[dim]
                    + 0.40 · dba_delta[dim]
                    + 0.30 · transit_delta[dim],  0, 100 )
```

One neutral 50 baseline; each layer's summed deltas weighted 30/40/30
(matches Step 9's "start at 50" while honouring the top-level weights).
Within DBA the three lords weight 50/30/20; Step-5 amplification and Step-8
conjunction are **multipliers** on a lord's contribution.

## Two design decisions (were ambiguous in the spec)

1. **Math model** — see above. The spec stated both a weighted blend and a
   "start at 50, add" accumulation; this reconciles them.
2. **Controlled vocabulary** — 10 canonical dimensions (sensitivity, stress,
   confidence, clarity, motivation, attachment, patience, impulsiveness,
   social_engagement, focus). The spec's loose labels (Nurturing, Hope,
   Obsession…) map to these via `structure.aliases`; config is authored in
   the canonical set with the original term kept in `_spec` for review.

## Run

```bash
cd backend
# CLI
python -m emotion.api 1995-08-20 14:30 17.44 78.35
# standalone server
uvicorn emotion.api:app --reload --port 8200
# or via the main backend (mounted at /emotion/*)
uvicorn api:app --reload --port 8000
curl "http://localhost:8000/emotion/daily?dob=1995-08-20&tob=14:30&place=Hyderabad"
```

## Output shape

```jsonc
{
  "inputs": { "natal_moon": "...", "dba": "...", "transit_moon": "..." },
  "scores": { "sensitivity": 54, "stress": 50, ... },        // the vector
  "dominant_themes": [ { "dimension": "motivation", "score": 63 }, ... ],
  "chandra_ashtama": false,
  "narrative": "…",
  "trace": [                                                  // full transparency
    { "step": 1, "title": "Natal emotional baseline", "narration": "…", "data": {…} },
    …
    { "step": 9, "title": "Final emotional dimensions",
      "data": { "composition": { "stress": { "natal":0, "dba":0, "transit":4.5, "raw":54.5 } } } }
  ]
}
```

Step 9's `composition` shows, per dimension, exactly how much each layer
contributed — the conclusion is fully traceable.

## Config (astrologer-tunable, no code change)

| File | Contents |
|---|---|
| `structure.json` | layer/sub weights, aliases, amplification, conjunction, chandra-ashtama, clamp |
| `planet_vectors.json` | 9 grahas' emotional vectors |
| `sign.json` | 12 rashi emotional characters |
| `nakshatra.json` | 27 nakshatra emotional characters |
| `house_tables.json` | natal Moon house + transit-from-natal-Moon modifiers |
| `tara_bala.json` | 9 Tara categories |
| `narrative.json` | threshold → sentence rules |

## POC notes / pending Durga

- All magnitudes are starting values — the spec explicitly defers tuning to
  the astrologer. `_spec` fields preserve the original spec numbers; entries
  without `_spec` are reasoned defaults (most of the 27 nakshatras, most
  signs) awaiting calibration.
- Natal-baseline magnitudes intentionally land scores near 50 on ordinary
  days; strong days come from DBA amplification, conjunctions, Tara, and
  Chandra Ashtama. Tune `transit_scale` / sub-weights to make days swing more.
- Narrative is rule-based (deterministic). An LLM phrasing pass can slot in
  after the payload, same as elsewhere in Kitab.
