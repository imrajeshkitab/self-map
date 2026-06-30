"""
emotion.astro — self-contained astronomical layer for the emotional engine.

Independent of all other Kitab code. Uses pyswisseph directly (sidereal,
Lahiri). Exposes exactly what the 10-step spec needs:

  • natal(birth, lat, lon)  → natal Moon (sign, nakshatra, house) + all
                              natal graha longitudes (for conjunction, Step 8)
  • transit_moon(when)      → transit Moon sign / nakshatra / pada / degree
  • vimshottari(...)        → current MD / AD / PD ("the DBA climate")
  • tara_number(...)        → 9-fold Tara distance (Step 6)
  • house_from / nakshatra helpers
"""

from __future__ import annotations

import datetime as dt
import swisseph as swe

swe.set_sid_mode(swe.SIDM_LAHIRI)

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
    "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

GRAHAS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
_SWE_ID = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY,
           "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN, "Rahu": swe.MEAN_NODE}

VIM_LORDS = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
VIM_YEARS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
             "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17}
VIM_TOTAL = 120
NAK_SPAN = 360.0 / 27.0
YEAR_DAYS = 365.2425


def _to_jd(when: dt.datetime) -> float:
    if when.tzinfo is not None:
        when = when.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return swe.julday(when.year, when.month, when.day,
                      when.hour + when.minute / 60 + when.second / 3600)


def _lon(jd: float, body: str) -> float:
    flag = swe.FLG_SIDEREAL | swe.FLG_SPEED
    if body == "Ketu":
        pos, _ = swe.calc_ut(jd, swe.MEAN_NODE, flag)
        return (pos[0] + 180.0) % 360.0
    pos, _ = swe.calc_ut(jd, _SWE_ID[body], flag)
    return pos[0] % 360.0


def sign_index(lon: float) -> int:
    return int(lon // 30)


def nakshatra_index(lon: float) -> int:
    return int(lon // NAK_SPAN)


def _nak(lon: float) -> dict:
    idx = nakshatra_index(lon)
    return {"name": NAKSHATRAS[idx], "index": idx, "lord": VIM_LORDS[idx % 9],
            "fraction_elapsed": (lon % NAK_SPAN) / NAK_SPAN}


def house_from(reference_sign_idx: int, target_sign_idx: int) -> int:
    """Whole-sign house of target counted from reference (1-12)."""
    return (target_sign_idx - reference_sign_idx) % 12 + 1


def tara_number(natal_nak_idx: int, transit_nak_idx: int) -> int:
    """1-27, counted from the natal nakshatra (Step 6)."""
    return ((transit_nak_idx - natal_nak_idx) % 27) + 1


def natal(birth: dt.datetime, lat: float, lon: float) -> dict:
    """Natal Moon details + all natal graha longitudes."""
    jd = _to_jd(birth)
    _, ascmc = swe.houses_ex(jd, lat, lon, b"W", swe.FLG_SIDEREAL)
    lagna_idx = sign_index(ascmc[0])

    grahas = {}
    for g in GRAHAS:
        gl = _lon(jd, g)
        grahas[g] = {"longitude": round(gl, 4), "sign": SIGNS[sign_index(gl)],
                     "sign_index": sign_index(gl)}

    mlon = grahas["Moon"]["longitude"]
    nak = _nak(mlon)
    return {
        "lagna_sign": SIGNS[lagna_idx], "lagna_index": lagna_idx,
        "moon": {
            "longitude": mlon, "sign": SIGNS[sign_index(mlon)], "sign_index": sign_index(mlon),
            "nakshatra": nak["name"], "nakshatra_index": nak["index"],
            "nakshatra_lord": nak["lord"],
            "house": house_from(lagna_idx, sign_index(mlon)),
        },
        "grahas": grahas,
    }


def transit_moon(when: dt.datetime) -> dict:
    jd = _to_jd(when)
    ml = _lon(jd, "Moon")
    nak = _nak(ml)
    return {
        "longitude": round(ml, 4), "sign": SIGNS[sign_index(ml)], "sign_index": sign_index(ml),
        "degree_in_sign": round(ml % 30, 2), "nakshatra": nak["name"],
        "nakshatra_index": nak["index"], "nakshatra_lord": nak["lord"],
        "pada": int((ml % NAK_SPAN) / (NAK_SPAN / 4)) + 1,
    }


def all_transit_longitudes(when: dt.datetime) -> dict:
    jd = _to_jd(when)
    return {g: round(_lon(jd, g), 4) for g in GRAHAS}


def vimshottari(moon_longitude: float, birth: dt.datetime, on: dt.datetime) -> dict:
    nak = _nak(moon_longitude)
    start_idx = nak["index"] % 9
    elapsed = nak["fraction_elapsed"]

    seq = []
    cursor = birth
    first = VIM_LORDS[start_idx]
    seq.append((first, cursor, cursor + dt.timedelta(days=VIM_YEARS[first] * YEAR_DAYS * (1 - elapsed))))
    cursor = seq[-1][2]
    for k in range(1, 11):
        lord = VIM_LORDS[(start_idx + k) % 9]
        seq.append((lord, cursor, cursor + dt.timedelta(days=VIM_YEARS[lord] * YEAR_DAYS)))
        cursor = seq[-1][2]

    md = next((s for s in seq if s[1] <= on < s[2]), seq[0])

    def subperiods(lord, start, end):
        total = (end - start).total_seconds() / 86400
        out, cur, i = [], start, VIM_LORDS.index(lord)
        for j in range(9):
            L = VIM_LORDS[(i + j) % 9]
            out.append((L, cur, cur + dt.timedelta(days=total * VIM_YEARS[L] / VIM_TOTAL)))
            cur = out[-1][2]
        return out

    ad_list = subperiods(md[0], md[1], md[2])
    ad = next((s for s in ad_list if s[1] <= on < s[2]), ad_list[0])
    pd_list = subperiods(ad[0], ad[1], ad[2])
    pd = next((s for s in pd_list if s[1] <= on < s[2]), pd_list[0])

    def days_left(end):
        return max(0, round((end - on).total_seconds() / 86400, 1))

    return {
        "mahadasha": {"lord": md[0], "days_remaining": days_left(md[2])},
        "bhukti":    {"lord": ad[0], "days_remaining": days_left(ad[2])},
        "antara":    {"lord": pd[0], "days_remaining": days_left(pd[2])},
    }
