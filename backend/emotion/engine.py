"""
emotion.engine — the Daily Emotional Analysis Engine.

Implements the 10-step specification exactly. Output is an emotional vector
(10 dimensions, 0-100), dominant themes, and a narrative — plus a full
step-by-step TRACE so the caller can see how each number was reached.

Math model (reconciles the spec's two formulas):
    final[dim] = clamp( 50
                        + 0.30 * natal_delta[dim]
                        + 0.40 * dba_delta[dim]
                        + 0.30 * transit_delta[dim],  0, 100 )
One neutral 50 baseline; each layer's summed deltas weighted 30/40/30.
Within DBA, the three lords weight 50/30/20; amplification (Step 5) and
conjunction (Step 8) are multipliers on a lord's contribution. All weights
live in config/ — nothing numeric is hard-coded here.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from . import astro

_CFG = Path(__file__).parent / "config"


def _load(name):
    with open(_CFG / name, encoding="utf-8") as f:
        return json.load(f)


STRUCT = _load("structure.json")
PLANET_VECTORS = _load("planet_vectors.json")["vectors"]
SIGN = _load("sign.json")["signs"]
NAKSHATRA = _load("nakshatra.json")["nakshatras"]
HOUSE = _load("house_tables.json")
TARA = _load("tara_bala.json")
NARRATIVE = _load("narrative.json")

DIMS = STRUCT["dimensions"]


def _deltas(entry: dict) -> dict:
    """Pull canonical-dimension deltas from a config entry, skipping _meta keys."""
    return {k: v for k, v in (entry or {}).items() if not k.startswith("_")}


def _add(acc: dict, deltas: dict, factor: float = 1.0):
    for dim, val in deltas.items():
        acc[dim] = acc.get(dim, 0.0) + val * factor


def _angular_gap(a: float, b: float) -> float:
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def compute_emotion(birth: dt.datetime, on: dt.datetime, lat: float, lon: float, place: str = "") -> dict:
    trace = []

    def step(n, title, narration, data=None):
        trace.append({"step": n, "title": title, "narration": narration, "data": data or {}})

    natal_delta = {d: 0.0 for d in DIMS}
    dba_delta = {d: 0.0 for d in DIMS}
    transit_delta = {d: 0.0 for d in DIMS}

    # ===== Setup: charts =====================================================
    nat = astro.natal(birth, lat, lon)
    moon_n = nat["moon"]
    tmoon = astro.transit_moon(on)
    dba = astro.vimshottari(moon_n["longitude"], birth, on)
    md, ad, pd = dba["mahadasha"]["lord"], dba["bhukti"]["lord"], dba["antara"]["lord"]

    # ===== STEP 1 — Natal Emotional Baseline =================================
    sw = STRUCT["natal_subweights"]
    sign_d = _deltas(SIGN.get(moon_n["sign"], {}))
    nak_d = _deltas(NAKSHATRA.get(moon_n["nakshatra"], {}))
    house_d = _deltas(HOUSE["natal_moon_house"].get(str(moon_n["house"]), {}))
    _add(natal_delta, sign_d, sw["sign"])
    _add(natal_delta, nak_d, sw["nakshatra"])
    _add(natal_delta, house_d, sw["house"])

    # Natal Moon conjunctions (aspect sub-weight): any natal graha within orb of natal Moon.
    orb = STRUCT["conjunction"]["orb_degrees"]
    natal_conjuncts = []
    for g, gd in nat["grahas"].items():
        if g == "Moon":
            continue
        if _angular_gap(gd["longitude"], moon_n["longitude"]) <= orb:
            _add(natal_delta, _deltas(PLANET_VECTORS.get(g, {})), sw["aspect"])
            natal_conjuncts.append(g)
    step(1, "Natal emotional baseline",
         f"Natal Moon in {moon_n['sign']} ({moon_n['nakshatra']}, house {moon_n['house']}). "
         f"Baseline composed from sign({sw['sign']}) + nakshatra({sw['nakshatra']}) + "
         f"house({sw['house']}) + aspects({sw['aspect']})."
         + (f" Conjunct natal: {', '.join(natal_conjuncts)}." if natal_conjuncts else " No close natal conjunctions."),
         {"moon": moon_n, "sign_deltas": sign_d, "nakshatra_deltas": nak_d,
          "house_deltas": house_d, "conjunct": natal_conjuncts,
          "natal_delta_so_far": {k: round(v, 2) for k, v in natal_delta.items() if v}})

    # ===== STEP 2 + 5 + 8 — DBA Emotional Climate ===========================
    dsw = STRUCT["dba_subweights"]
    amp = STRUCT["nakshatra_lord_amplification"]
    conj = STRUCT["conjunction"]
    dba_breakdown = []
    levels = [("mahadasha", md, dsw["mahadasha"]),
              ("bhukti", ad, dsw["bhukti"]),
              ("antara", pd, dsw["antara"])]
    for level, lord, subweight in levels:
        vec = _deltas(PLANET_VECTORS.get(lord, {}))
        mult = 1.0
        notes = []
        # Step 5 — nakshatra-lord amplification
        if lord == tmoon["nakshatra_lord"]:
            mult *= amp[level]
            notes.append(f"transit-nakshatra-lord amplification ×{amp[level]}")
        # Step 8 — transit Moon conjunct this lord's natal position
        if lord in nat["grahas"] and _angular_gap(tmoon["longitude"], nat["grahas"][lord]["longitude"]) <= conj["orb_degrees"]:
            cf = conj["factor_overrides"].get(lord, conj["factor_default"])
            mult *= cf
            notes.append(f"transit Moon conjunct natal {lord} ×{cf}")
        _add(dba_delta, vec, subweight * mult)
        dba_breakdown.append({"level": level, "lord": lord, "subweight": subweight,
                              "multiplier": round(mult, 3), "vector": vec, "notes": notes})
    step(2, "DBA emotional climate (+ amplification, conjunction)",
         f"Current period: {md} Mahadasha / {ad} Bhukti / {pd} Antara, weighted "
         f"{dsw['mahadasha']}/{dsw['bhukti']}/{dsw['antara']}. Each lord's emotional "
         f"vector is scaled by its level, then by any Step-5 amplification or "
         f"Step-8 conjunction multiplier.",
         {"dba": dba, "breakdown": dba_breakdown,
          "dba_delta_so_far": {k: round(v, 2) for k, v in dba_delta.items() if v}})

    # ===== STEP 3 — Daily Moon Transit (sign + nakshatra) ===================
    ts = STRUCT["transit_scale"]
    tsign_d = _deltas(SIGN.get(tmoon["sign"], {}))
    tnak_d = _deltas(NAKSHATRA.get(tmoon["nakshatra"], {}))
    _add(transit_delta, tsign_d, ts["sign"])
    _add(transit_delta, tnak_d, ts["nakshatra"])
    step(3, "Daily Moon transit — sign & nakshatra",
         f"Transit Moon in {tmoon['sign']} ({tmoon['nakshatra']}, pada {tmoon['pada']}). "
         f"Sign and nakshatra character applied at transit scale "
         f"({ts['sign']}/{ts['nakshatra']}).",
         {"transit_moon": tmoon, "sign_deltas": tsign_d, "nakshatra_deltas": tnak_d})

    # ===== STEP 4 — Moon position from natal Moon ===========================
    house_from_moon = astro.house_from(moon_n["sign_index"], tmoon["sign_index"])
    hfm_d = _deltas(HOUSE["transit_from_natal_moon"].get(str(house_from_moon), {}))
    _add(transit_delta, hfm_d)
    step(4, "Moon position from natal Moon",
         f"Transit Moon is in the {house_from_moon}th from the natal Moon "
         f"({moon_n['sign']} → {tmoon['sign']}).",
         {"house_from_natal_moon": house_from_moon, "deltas": hfm_d})

    # ===== STEP 6 — Tara Bala ===============================================
    tnum = astro.tara_number(moon_n["nakshatra_index"], tmoon["nakshatra_index"])
    cat = TARA["category_order"][(tnum - 1) % 9]
    tara_d = _deltas(TARA["categories"][cat])
    _add(transit_delta, tara_d)
    step(6, "Tara Bala",
         f"Tara number {tnum} from the natal nakshatra → {cat}.",
         {"tara_number": tnum, "category": cat, "deltas": tara_d})

    # ===== STEP 7 — Chandra Ashtama =========================================
    chandra_ashtama = (house_from_moon == 8)
    if chandra_ashtama:
        _add(transit_delta, STRUCT["chandra_ashtama"]["deltas"])
    step(7, "Chandra Ashtama check",
         "Transit Moon IS in the 8th from natal Moon — Chandra Ashtama is active."
         if chandra_ashtama else
         "Transit Moon is not in the 8th from natal Moon — no Chandra Ashtama.",
         {"chandra_ashtama": chandra_ashtama,
          "deltas": STRUCT["chandra_ashtama"]["deltas"] if chandra_ashtama else {}})

    # ===== STEP 9 — Final Emotional Dimensions ==============================
    lw = STRUCT["layer_weights"]
    base = STRUCT["baseline"]
    gain = STRUCT["intensity_gain"]["value"]
    lo, hi = STRUCT["clamp"]["min"], STRUCT["clamp"]["max"]
    scores = {}
    composition = {}
    for d in DIMS:
        n, b, t = natal_delta[d], dba_delta[d], transit_delta[d]
        nc, bc, tc = lw["natal"] * n, lw["dba"] * b, lw["transit"] * t
        raw = base + gain * (nc + bc + tc)
        scores[d] = max(lo, min(hi, round(raw)))
        composition[d] = {
            "natal": round(gain * nc, 2), "dba": round(gain * bc, 2),
            "transit": round(gain * tc, 2), "raw": round(raw, 2),
        }
    step(9, "Final emotional dimensions",
         f"Each dimension = {base} + {gain} × ({lw['natal']}·natal + {lw['dba']}·dba + "
         f"{lw['transit']}·transit), clamped {lo}-{hi}.",
         {"scores": scores, "composition": composition, "intensity_gain": gain})

    # ===== STEP 10 — Narrative ==============================================
    dominant = sorted(scores.items(), key=lambda kv: -abs(kv[1] - 50))
    dominant_themes = [{"dimension": d, "score": s} for d, s in dominant[:4]]
    lines = []
    for r in NARRATIVE["rules"]:
        s = scores[r["dimension"]]
        if (r["op"] == ">" and s > r["value"]) or (r["op"] == "<" and s < r["value"]):
            lines.append(r["text"])
    if chandra_ashtama:
        lines.insert(0, NARRATIVE["chandra_ashtama_line"])
    if not lines:
        lines.append("A steady, unremarkable emotional day — nothing pulls strongly in any direction.")
    step(10, "Narrative",
         "Threshold rules fired against the final scores.",
         {"dominant_themes": dominant_themes, "lines": lines})

    return {
        "inputs": {
            "birth": birth.isoformat(), "as_of": on.isoformat(), "place": place,
            "lat": lat, "lon": lon,
            "natal_moon": f"{moon_n['sign']} / {moon_n['nakshatra']} / house {moon_n['house']}",
            "dba": f"{md} / {ad} / {pd}",
            "transit_moon": f"{tmoon['sign']} / {tmoon['nakshatra']} / pada {tmoon['pada']}",
        },
        "scores": scores,
        "dominant_themes": dominant_themes,
        "chandra_ashtama": chandra_ashtama,
        "narrative": " ".join(lines),
        "trace": trace,
        "_model_note": "Designed psychological model (spec-driven). Weights in emotion/config are starting values pending Durga calibration — not verse-cited.",
    }
