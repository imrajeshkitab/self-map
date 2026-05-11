"""
prashna.py
Compute a live Vedic chart from datetime + lat/lon — no birth data required.

Conventions:
    - Sidereal (Vedic) zodiac with Lahiri ayanamsa
    - Whole-sign house system (Lagna sign = 1st house, etc.)
    - Rahu = Mean North Node, Ketu = Rahu + 180°
"""

from __future__ import annotations
import datetime as dt
from typing import Optional
import swisseph as swe

swe.set_ephe_path(None)
swe.set_sid_mode(swe.SIDM_LAHIRI)

# ---------------------------------------------------------------------------
# Static reference data
# ---------------------------------------------------------------------------

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]
SIGN_SANSKRIT = [
    "Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
    "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena",
]
SIGN_LORDS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}

PLANET_DATA = {
    "Sun":     {"id": swe.SUN,       "domicile": ["Leo"],                "exalted": "Aries",     "debilitated": "Libra"},
    "Moon":    {"id": swe.MOON,      "domicile": ["Cancer"],             "exalted": "Taurus",    "debilitated": "Scorpio"},
    "Mars":    {"id": swe.MARS,      "domicile": ["Aries", "Scorpio"],   "exalted": "Capricorn", "debilitated": "Cancer"},
    "Mercury": {"id": swe.MERCURY,   "domicile": ["Gemini", "Virgo"],    "exalted": "Virgo",     "debilitated": "Pisces"},
    "Jupiter": {"id": swe.JUPITER,   "domicile": ["Sagittarius", "Pisces"], "exalted": "Cancer",  "debilitated": "Capricorn"},
    "Venus":   {"id": swe.VENUS,     "domicile": ["Taurus", "Libra"],    "exalted": "Pisces",    "debilitated": "Virgo"},
    "Saturn":  {"id": swe.SATURN,    "domicile": ["Capricorn", "Aquarius"], "exalted": "Libra",  "debilitated": "Aries"},
    "Rahu":    {"id": swe.MEAN_NODE, "domicile": [],                     "exalted": "Taurus",    "debilitated": "Scorpio"},
    "Ketu":    {"id": None,          "domicile": [],                     "exalted": "Scorpio",   "debilitated": "Taurus"},
}

NATURAL_KARAKAS = {
    "Sun": [1, 9, 10], "Moon": [4], "Mars": [3, 6], "Mercury": [4, 6, 10],
    "Jupiter": [2, 5, 9, 10, 11], "Venus": [7], "Saturn": [6, 8, 10, 12],
    "Rahu": [12], "Ketu": [12],
}

# 27 Nakshatras in order, each 13°20' (13.3333°)
NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira",
    "Ardra", "Punarvasu", "Pushya", "Ashlesha",
    "Magha", "Purvaphalguni", "Uttaraphalguni", "Hasta", "Chitra",
    "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purvashada", "Uttarashada", "Shravana", "Dhanishta",
    "Shatabhisha", "Purvabhadrapada", "Uttarabhadrapada", "Revati",
]
# Vimshottari dasha lords — cycle of 9, applied to nakshatras in order.
NAK_LORDS = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
DASHA_YEARS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
               "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17}  # total 120

# Permanent (Naisargika) friendships. Lookup: FRIENDSHIPS[planet][other_planet]
FRIENDSHIPS = {
    "Sun":     {"Moon": "F", "Mars": "F", "Mercury": "N", "Jupiter": "F", "Venus": "E", "Saturn": "E"},
    "Moon":    {"Sun": "F", "Mars": "N", "Mercury": "F", "Jupiter": "N", "Venus": "N", "Saturn": "N"},
    "Mars":    {"Sun": "F", "Moon": "F", "Mercury": "E", "Jupiter": "F", "Venus": "N", "Saturn": "N"},
    "Mercury": {"Sun": "F", "Moon": "E", "Mars": "N", "Jupiter": "N", "Venus": "F", "Saturn": "N"},
    "Jupiter": {"Sun": "F", "Moon": "F", "Mars": "F", "Mercury": "E", "Venus": "E", "Saturn": "N"},
    "Venus":   {"Sun": "E", "Moon": "E", "Mars": "N", "Mercury": "F", "Jupiter": "N", "Saturn": "F"},
    "Saturn":  {"Sun": "E", "Moon": "E", "Mars": "E", "Mercury": "F", "Jupiter": "N", "Venus": "F"},
}
REL_LABEL = {"F": "friend", "E": "enemy", "N": "neutral"}

# Combustion orbs (degrees from Sun). Standard Parashara values.
COMBUST_ORBS = {"Moon": 12, "Mars": 17, "Mercury": 14, "Jupiter": 11, "Venus": 10, "Saturn": 15}

# Avastha (Baladi) — name by degree-in-sign for odd signs; reversed for even.
BALADI_ODD  = [("Bala", 6), ("Kumara", 12), ("Yuva", 18), ("Vriddha", 24), ("Mrita", 30)]
BALADI_EVEN = [("Mrita", 6), ("Vriddha", 12), ("Yuva", 18), ("Kumara", 24), ("Bala", 30)]

# Jaimini Chara Karakas — 7 names by descending degree
CHARA_KARAKA_NAMES = ["Atma", "Amatya", "Bhratri", "Matri", "Putra", "Gnati", "Dara"]


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _to_julian(dt_utc: dt.datetime) -> float:
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day,
                      dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600)


def _sign_of(longitude_deg: float) -> tuple[str, float]:
    lon = longitude_deg % 360
    idx = int(lon // 30)
    return SIGNS[idx], lon - idx * 30


def _strength_state(planet: str, sign: str) -> str:
    meta = PLANET_DATA[planet]
    if sign == meta["exalted"]:     return "exalted"
    if sign == meta["debilitated"]: return "debilitated"
    if sign in meta["domicile"]:    return "own"
    return "neutral"


def _house_of(planet_sign: str, lagna_sign: str) -> int:
    return ((SIGNS.index(planet_sign) - SIGNS.index(lagna_sign)) % 12) + 1


def _nakshatra_of(longitude_deg: float) -> dict:
    """Return {name, index(1-27), pada(1-4), lord, deg_in_nak}."""
    lon = longitude_deg % 360
    nak_size = 360 / 27  # 13.3333...
    idx = int(lon // nak_size)
    deg_in_nak = lon - idx * nak_size
    pada = int(deg_in_nak // (nak_size / 4)) + 1  # 4 padas of 3°20' each
    return {
        "name": NAKSHATRAS[idx],
        "index": idx + 1,
        "pada": pada,
        "lord": NAK_LORDS[idx % 9],
        "deg_in_nakshatra": round(deg_in_nak, 3),
    }


def _avastha_of(sign: str, deg_in_sign: float) -> str:
    sign_num = SIGNS.index(sign) + 1
    table = BALADI_ODD if sign_num % 2 == 1 else BALADI_EVEN
    for name, upper in table:
        if deg_in_sign < upper:
            return name
    return table[-1][0]


def _combust(name: str, lon: float, sun_lon: float, retrograde: bool) -> bool:
    if name not in COMBUST_ORBS:
        return False
    orb = COMBUST_ORBS[name]
    # Slightly tighter orb when retrograde, for Mercury/Venus
    if retrograde and name in ("Mercury", "Venus"):
        orb -= 2
    diff = abs((lon - sun_lon + 180) % 360 - 180)
    return diff <= orb


def _relation_to_sign(planet: str, sign_lord: str) -> str:
    if planet == sign_lord:
        return "own"
    if planet in ("Rahu", "Ketu") or sign_lord in ("Rahu", "Ketu"):
        return "neutral"
    return REL_LABEL[FRIENDSHIPS[planet][sign_lord]]


# ---------------------------------------------------------------------------
# Vimshottari Dasha — main period only (first level), from Moon's nakshatra.
# ---------------------------------------------------------------------------

def _vimshottari(moon_lon: float, when_utc: dt.datetime) -> dict:
    nak = _nakshatra_of(moon_lon)
    start_lord = nak["lord"]
    nak_size = 360 / 27
    fraction_done = nak["deg_in_nakshatra"] / nak_size  # 0..1 through this nakshatra
    remaining_years = DASHA_YEARS[start_lord] * (1 - fraction_done)

    # Walk forward through the 9-lord cycle.
    order = NAK_LORDS[:]
    start_idx = order.index(start_lord)
    cycle = [order[(start_idx + i) % 9] for i in range(9)]

    timeline = []
    cursor = when_utc + dt.timedelta(days=remaining_years * 365.25)
    timeline.append({
        "lord": start_lord,
        "starts": (when_utc - dt.timedelta(days=(DASHA_YEARS[start_lord] - remaining_years) * 365.25)).date().isoformat(),
        "ends":   cursor.date().isoformat(),
        "years":  round(DASHA_YEARS[start_lord], 2),
        "remaining_years": round(remaining_years, 2),
        "current": True,
    })
    for lord in cycle[1:]:
        yrs = DASHA_YEARS[lord]
        nxt = cursor + dt.timedelta(days=yrs * 365.25)
        timeline.append({
            "lord": lord,
            "starts": cursor.date().isoformat(),
            "ends":   nxt.date().isoformat(),
            "years":  yrs,
            "current": False,
        })
        cursor = nxt
    return {
        "moon_nakshatra": nak["name"],
        "current_mahadasha": start_lord,
        "remaining_years": round(remaining_years, 2),
        "timeline": timeline,
    }


# ---------------------------------------------------------------------------
# Chara Karakas (Jaimini) — 7-planet version, rank by degree desc.
# ---------------------------------------------------------------------------

def _chara_karakas(planets: list[dict]) -> list[dict]:
    visible = [p for p in planets if p["name"] not in ("Rahu", "Ketu")]
    visible.sort(key=lambda p: p["degree"], reverse=True)
    return [
        {"karaka": CHARA_KARAKA_NAMES[i], "planet": p["name"], "degree": p["degree"]}
        for i, p in enumerate(visible)
    ]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def compute_chart(when: Optional[dt.datetime] = None,
                  lat: float = 17.4399,
                  lon: float = 78.3489,
                  place: str = "Gachibowli, Hyderabad, India") -> dict:
    if when is None:
        when = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    elif when.tzinfo is not None:
        when = when.astimezone(dt.timezone.utc).replace(tzinfo=None)
    jd = _to_julian(when)

    # ---- Lagna ------------------------------------------------------------
    _, ascmc = swe.houses_ex(jd, lat, lon, b'W', swe.FLG_SIDEREAL)
    asc_lon = ascmc[0]
    lagna_sign, lagna_deg = _sign_of(asc_lon)
    lagna_lord = SIGN_LORDS[lagna_sign]

    # ---- Planets ----------------------------------------------------------
    flag = swe.FLG_SIDEREAL | swe.FLG_SPEED
    raw = {}
    for name, meta in PLANET_DATA.items():
        if name == "Ketu":
            r = raw["Rahu"]
            raw[name] = {"lon": (r["lon"] + 180.0) % 360, "speed": -r["speed"]}
        else:
            pos, _ = swe.calc_ut(jd, meta["id"], flag)
            raw[name] = {"lon": pos[0] % 360, "speed": pos[3]}

    sun_lon = raw["Sun"]["lon"]
    planets = []
    for name, meta in PLANET_DATA.items():
        plon = raw[name]["lon"]
        speed = raw[name]["speed"]
        sign, deg_in_sign = _sign_of(plon)
        sign_lord = SIGN_LORDS[sign]
        retro = speed < 0 and name not in ("Rahu", "Ketu")
        nak = _nakshatra_of(plon)
        planets.append({
            "name": name,
            "sign": sign,
            "sign_sanskrit": SIGN_SANSKRIT[SIGNS.index(sign)],
            "degree": round(deg_in_sign, 2),
            "longitude": round(plon, 4),
            "house": _house_of(sign, lagna_sign),
            "state": _strength_state(name, sign),
            "retrograde": retro,
            "combust": _combust(name, plon, sun_lon, retro),
            "relation": _relation_to_sign(name, sign_lord) if name not in ("Rahu", "Ketu") else "neutral",
            "sign_lord": sign_lord,
            "nakshatra": nak["name"],
            "nakshatra_lord": nak["lord"],
            "pada": nak["pada"],
            "avastha": _avastha_of(sign, deg_in_sign),
            "domicile_signs": meta["domicile"],
            "exalted_in": meta["exalted"],
            "debilitated_in": meta["debilitated"],
            "natural_karaka_houses": NATURAL_KARAKAS.get(name, []),
        })

    # ---- Houses (whole-sign) ---------------------------------------------
    houses = []
    for h in range(1, 13):
        sign_idx = (SIGNS.index(lagna_sign) + h - 1) % 12
        sign = SIGNS[sign_idx]
        houses.append({
            "number": h,
            "sign": sign,
            "sign_sanskrit": SIGN_SANSKRIT[sign_idx],
            "lord": SIGN_LORDS[sign],
            "occupants": [p["name"] for p in planets if p["house"] == h],
        })

    lord_planet = next(p for p in planets if p["name"] == lagna_lord)

    # ---- Dasha + Karakas -------------------------------------------------
    moon = next(p for p in planets if p["name"] == "Moon")
    dasha = _vimshottari(moon["longitude"], when)
    karakas = _chara_karakas(planets)

    return {
        "datetime_utc": when.isoformat() + "Z",
        "location": {"lat": lat, "lon": lon, "place": place},
        "ayanamsa": "Lahiri (Sidereal)",
        "house_system": "Whole Sign",
        "lagna": {
            "sign": lagna_sign,
            "sign_sanskrit": SIGN_SANSKRIT[SIGNS.index(lagna_sign)],
            "degree": round(lagna_deg, 2),
            "lord": lagna_lord,
            "lord_state": lord_planet["state"],
            "lord_sign": lord_planet["sign"],
            "lord_house": lord_planet["house"],
            "nakshatra": _nakshatra_of(asc_lon)["name"],
            "pada": _nakshatra_of(asc_lon)["pada"],
        },
        "planets": planets,
        "houses": houses,
        "dasha": dasha,
        "chara_karakas": karakas,
    }


if __name__ == "__main__":
    import json
    c = compute_chart()
    # Show a compact summary
    print(f"Lagna: {c['lagna']['sign']} {c['lagna']['degree']}° · {c['lagna']['nakshatra']} (pada {c['lagna']['pada']})")
    print(f"Current Mahadasha: {c['dasha']['current_mahadasha']} ({c['dasha']['remaining_years']} yrs remaining)")
    print()
    for p in c["planets"]:
        flags = []
        if p["retrograde"]: flags.append("R")
        if p["combust"]:    flags.append("C")
        f = " " + "".join(flags) if flags else ""
        print(f"  {p['name']:8s} {p['sign']:12s} {p['degree']:5.2f}° · H{p['house']:<2d} · {p['state']:11s} · rel={p['relation']:7s} · nak={p['nakshatra']:14s} pada{p['pada']} · {p['avastha']}{f}")
    print()
    print("Chara Karakas:")
    for k in c["chara_karakas"]:
        print(f"  {k['karaka']:8s} → {k['planet']:8s} ({k['degree']:.2f}°)")
