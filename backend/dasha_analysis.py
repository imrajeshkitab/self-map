"""
dasha_analysis.py
==================
Personal Vimshottari Dasa analysis — anchored to a user's **natal Moon**.

Different from `prashna._vimshottari`, which is anchored to the *moment* a
question is asked (Prashna). For a person's life-arc analysis we must:
  1. Determine the first MD lord from the *natal* Moon's nakshatra.
  2. Determine how much of that first MD was already elapsed *at birth*
     (because the person was born mid-nakshatra).
  3. Walk forward from birth through the cycle, tracking when each MD,
     AD, PD ends, until we reach the "as of" datetime.

This is the building block for May 19 Durga MOM action item #2:
  "Identify users completing a Dasa cycle and prepare them for the next one."
"""

from __future__ import annotations
import datetime as dt
from typing import Optional

import swisseph as swe

from dasha_table import (
    DASHA_TENURE, DASHA_YEARS, VIMSHOTTARI_ORDER,
    next_md_lord, tenure_metadata,
)
from prashna import _nakshatra_of, _walk_periods, YR


# ---------------------------------------------------------------------------
# Thresholds for the "completing soon" flag
# ---------------------------------------------------------------------------

MD_COMPLETING_THRESHOLD_DAYS = 365   # within last 1 year of MD
AD_COMPLETING_THRESHOLD_DAYS = 30    # within last 1 month of AD
PD_COMPLETING_THRESHOLD_DAYS = 7     # within last 1 week of PD


# ---------------------------------------------------------------------------
# Moon longitude at birth
# ---------------------------------------------------------------------------

def compute_natal_moon_longitude(birth_utc: dt.datetime) -> float:
    """Sidereal (Lahiri) Moon longitude at the moment of birth, in degrees [0, 360).

    Moon's celestial longitude is location-independent — we only need the instant.
    """
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    if birth_utc.tzinfo is not None:
        birth_utc = birth_utc.astimezone(dt.timezone.utc).replace(tzinfo=None)
    jd = swe.julday(
        birth_utc.year, birth_utc.month, birth_utc.day,
        birth_utc.hour + birth_utc.minute / 60 + birth_utc.second / 3600,
    )
    pos, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_SIDEREAL | swe.FLG_SPEED)
    return pos[0] % 360


# ---------------------------------------------------------------------------
# Natal Vimshottari walker — anchored to birth, walks forward to `when_utc`
# ---------------------------------------------------------------------------

def vimshottari_natal(
    natal_moon_lon: float,
    birth_utc: dt.datetime,
    when_utc: dt.datetime,
) -> dict:
    """Build the user's MD timeline starting from birth, plus AD/PD within the
    MD that contains `when_utc`.

    The first MD is truncated by the fraction of the first nakshatra that had
    already elapsed at birth — that's why it can be shorter than DASHA_YEARS.
    For AD/PD computation within the first MD we use a "phantom" MD-start
    (slightly before birth) so the AD cycle proportions are correct.
    """
    nak = _nakshatra_of(natal_moon_lon)
    first_lord = nak["lord"]
    nak_size = 360 / 27
    fraction_done_at_birth = nak["deg_in_nakshatra"] / nak_size
    first_md_remaining_at_birth = DASHA_YEARS[first_lord] * (1 - fraction_done_at_birth)

    # Build the MD timeline by walking forward from birth. We walk 2 full
    # cycles (240 years) for safety — long enough for any human lifespan.
    start_idx = VIMSHOTTARI_ORDER.index(first_lord)
    cycle_lords = [VIMSHOTTARI_ORDER[(start_idx + i) % 9] for i in range(18)]

    md_timeline: list[dict] = []
    cursor = birth_utc
    current_md_idx = -1
    current_md_phantom_start: Optional[dt.datetime] = None

    for i, lord in enumerate(cycle_lords):
        # First MD is truncated by the fraction already elapsed at birth.
        yrs_this_md = (
            first_md_remaining_at_birth if i == 0 else DASHA_YEARS[lord]
        )
        end = cursor + dt.timedelta(days=yrs_this_md * YR)
        is_current = cursor <= when_utc < end

        entry = {
            "lord":         lord,
            "starts":       cursor.date().isoformat(),
            "ends":         end.date().isoformat(),
            "years_in_md":  round(yrs_this_md, 3),
            "years_total":  DASHA_YEARS[lord],   # full natural length
            "current":      is_current,
        }
        if is_current:
            current_md_idx = i
            elapsed = (when_utc - cursor).total_seconds() / 86400 / YR
            remaining = (end - when_utc).total_seconds() / 86400 / YR
            entry["years_elapsed"]   = round(elapsed, 3)
            entry["years_remaining"] = round(remaining, 3)
            entry["remaining_days"]  = round(remaining * YR, 1)
            entry["percent_done"]    = round((elapsed / yrs_this_md) * 100, 1) if yrs_this_md > 0 else 0.0
            # Phantom start: when this MD would have begun if it ran its full
            # natural length. Used for AD cycle alignment when current MD is
            # the first one (truncated).
            if i == 0:
                current_md_phantom_start = cursor - dt.timedelta(
                    days=fraction_done_at_birth * DASHA_YEARS[lord] * YR
                )
            else:
                current_md_phantom_start = cursor

        md_timeline.append(entry)
        cursor = end

    if current_md_idx == -1:
        raise ValueError("Could not locate current MD — when_utc may be outside the 240-year window")

    current_md = md_timeline[current_md_idx]
    assert current_md_phantom_start is not None  # set above when is_current branch ran

    # AD within current MD — proportional cycle anchored at the (phantom) MD start
    ad_parent_years = float(DASHA_YEARS[current_md["lord"]])
    ad_timeline, current_ad = _walk_periods(
        current_md["lord"], current_md_phantom_start, ad_parent_years, when_utc, VIMSHOTTARI_ORDER,
    )

    # PD within current AD
    if current_ad is not None:
        pd_timeline, current_pd = _walk_periods(
            current_ad["lord"], current_ad["_start_dt"], current_ad["years"], when_utc, VIMSHOTTARI_ORDER,
        )
    else:
        pd_timeline, current_pd = [], None

    # Strip internal fields
    for e in ad_timeline:
        e.pop("_start_dt", None)
    for e in pd_timeline:
        e.pop("_start_dt", None)

    return {
        "natal_moon_nakshatra": nak["name"],
        "natal_moon_pada":      nak["pada"],
        "first_md_lord":        first_lord,
        "md_timeline":          md_timeline,
        "current_md":           current_md,
        "current_md_idx":       current_md_idx,
        "ad_timeline":          ad_timeline,
        "current_ad":           current_ad,
        "pd_timeline":          pd_timeline,
        "current_pd":           current_pd,
    }


# ---------------------------------------------------------------------------
# High-level analysis with tenure metadata + "completing soon" detection
# ---------------------------------------------------------------------------

def analyze_dasha(birth_utc: dt.datetime, when_utc: Optional[dt.datetime] = None) -> dict:
    """Return the user's Vimshottari position at `when_utc` (default: now)
    with full tenure metadata and transition flags.

    See the module docstring for the output schema.
    """
    if when_utc is None:
        when_utc = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    elif when_utc.tzinfo is not None:
        when_utc = when_utc.astimezone(dt.timezone.utc).replace(tzinfo=None)
    if birth_utc.tzinfo is not None:
        birth_utc = birth_utc.astimezone(dt.timezone.utc).replace(tzinfo=None)

    moon_lon = compute_natal_moon_longitude(birth_utc)
    vims = vimshottari_natal(moon_lon, birth_utc, when_utc)

    md = vims["current_md"]
    ad = vims["current_ad"]
    pd = vims["current_pd"]

    current_md = {
        "lord":              md["lord"],
        "starts":            md["starts"],
        "ends":              md["ends"],
        "years_total":       md["years_total"],
        "years_in_md":       md["years_in_md"],
        "years_elapsed":     md["years_elapsed"],
        "years_remaining":   md["years_remaining"],
        "remaining_days":    md["remaining_days"],
        "percent_done":      md["percent_done"],
        "metadata":          tenure_metadata(md["lord"]),
    }

    current_ad = None
    if ad is not None:
        ad_total = float(ad["years"])
        ad_remaining = float(ad.get("remaining_years") or 0)
        current_ad = {
            "lord":              ad["lord"],
            "starts":            ad["starts"],
            "ends":              ad["ends"],
            "years_total":       round(ad_total, 3),
            "months_total":      round(ad_total * 12, 1),
            "years_remaining":   round(ad_remaining, 3),
            "remaining_days":    ad.get("remaining_days"),
            "percent_done":      round(((ad_total - ad_remaining) / ad_total) * 100, 1) if ad_total > 0 else 0.0,
            "metadata":          tenure_metadata(ad["lord"]),
        }

    current_pd = None
    if pd is not None:
        pd_total_days = round(pd["years"] * YR, 2)
        pd_remaining_days = float(pd.get("remaining_days") or 0)
        current_pd = {
            "lord":              pd["lord"],
            "starts":            pd["starts"],
            "ends":              pd["ends"],
            "total_days":        pd_total_days,
            "remaining_days":    round(pd_remaining_days, 1),
            "percent_done":      round(((pd_total_days - pd_remaining_days) / pd_total_days) * 100, 1) if pd_total_days > 0 else 0.0,
            "metadata":          tenure_metadata(pd["lord"]),
        }

    # Next MD
    next_md = None
    next_md_entry = (
        vims["md_timeline"][vims["current_md_idx"] + 1]
        if vims["current_md_idx"] + 1 < len(vims["md_timeline"])
        else None
    )
    if next_md_entry:
        next_md = {
            "lord":        next_md_entry["lord"],
            "starts":      next_md_entry["starts"],
            "years_total": next_md_entry["years_total"],
            "metadata":    tenure_metadata(next_md_entry["lord"]),
        }

    # Transition flags
    completing_md = md["remaining_days"] <= MD_COMPLETING_THRESHOLD_DAYS
    completing_ad = bool(ad and (ad.get("remaining_days") or 0) <= AD_COMPLETING_THRESHOLD_DAYS)
    completing_pd = bool(pd and (pd.get("remaining_days") or 0) <= PD_COMPLETING_THRESHOLD_DAYS)

    advice_parts = []
    if completing_md and next_md:
        advice_parts.append(
            f"You're in the final ~{int(md['remaining_days'])} days of "
            f"{md['lord']} Mahadasha — {next_md['lord']} MD "
            f"({next_md['years_total']} years) begins on {next_md['starts']}. "
            f"{tenure_metadata(md['lord'])['transition_advice']}"
        )
    elif completing_ad and ad:
        advice_parts.append(
            f"You're in the final ~{int(ad.get('remaining_days') or 0)} days of "
            f"{ad['lord']} Antardasha — a sub-period shift is imminent."
        )
    elif completing_pd and pd:
        advice_parts.append(
            f"You're in the final ~{int(pd.get('remaining_days') or 0)} days of "
            f"{pd['lord']} Pratyantar — this immediate window closes soon."
        )
    if not advice_parts:
        advice_parts.append(
            f"You're roughly {md['percent_done']}% through {md['lord']} Mahadasha. "
            f"No imminent dasha transition."
        )

    transition = {
        "completing_md": completing_md,
        "completing_ad": completing_ad,
        "completing_pd": completing_pd,
        "advice":        " ".join(advice_parts),
    }

    # Lifecycle: all MDs from birth onwards with summary
    lifecycle = []
    for t in vims["md_timeline"][:10]:    # first 10 = up to ~120 years
        meta = tenure_metadata(t["lord"])
        lifecycle.append({
            "lord":     t["lord"],
            "starts":   t["starts"],
            "ends":     t["ends"],
            "years":    t["years_in_md"],
            "current":  t["current"],
            "tone":     meta["tone"],
            "themes":   meta["themes"][:3],
            "nature":   meta["nature"],
        })

    return {
        "natal": {
            "moon_longitude":      round(moon_lon, 4),
            "moon_nakshatra":      vims["natal_moon_nakshatra"],
            "moon_pada":           vims["natal_moon_pada"],
            "first_md_lord":       vims["first_md_lord"],
            "birth_utc":           birth_utc.isoformat() + "Z",
        },
        "as_of":      when_utc.isoformat() + "Z",
        "current":    {"md": current_md, "ad": current_ad, "pd": current_pd},
        "next":       {"md": next_md},
        "transition": transition,
        "lifecycle":  lifecycle,
    }


if __name__ == "__main__":
    # Quick CLI sanity check.
    birth = dt.datetime(1990, 6, 15, 10, 30, 0)
    result = analyze_dasha(birth)

    print(f"Birth: {birth} UTC")
    print(f"Natal Moon: {result['natal']['moon_nakshatra']} "
          f"(pada {result['natal']['moon_pada']}, lon {result['natal']['moon_longitude']}°)")
    print(f"First MD lord: {result['natal']['first_md_lord']}")
    print()

    md = result["current"]["md"]
    print(f"Current MD: {md['lord']}  "
          f"({md['years_elapsed']} / {md['years_in_md']} yrs, "
          f"{md['percent_done']}% done, {md['years_remaining']} yrs left)")
    print(f"   starts {md['starts']}  ends {md['ends']}")

    if result["current"]["ad"]:
        ad = result["current"]["ad"]
        print(f"Current AD: {ad['lord']}  ({ad['remaining_days']} days left)")
    if result["current"]["pd"]:
        pd_ = result["current"]["pd"]
        print(f"Current PD: {pd_['lord']}  ({pd_['remaining_days']} days left)")

    print()
    print("Transition:", result["transition"]["advice"])
    if result["next"]["md"]:
        nxt = result["next"]["md"]
        print(f"Next MD: {nxt['lord']} starting {nxt['starts']} ({nxt['years_total']} yrs)")
    print()
    print("Lifecycle (first 10 MDs from birth):")
    for t in result["lifecycle"]:
        flag = " ← NOW" if t["current"] else ""
        print(f"  {t['lord']:<10} {t['starts']} → {t['ends']}  "
              f"({t['years']:5.2f} yrs, {t['tone']:<13}){flag}")
