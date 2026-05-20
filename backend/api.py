"""
api.py
FastAPI search API — wraps the semantic search engine.
Durga's frontend calls this to get astrology matches for any query.

Run:
    uvicorn api:app --reload --port 8000

Endpoints:
    GET  /search?q=career&top_k=5
    GET  /health
    GET  /stats
"""

from fastapi import FastAPI, Query, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import os
import time

from search import semantic_search, trinity_search
from prashna import compute_chart
from narrate import cosmic_pulse
from interpret import answer as interpret_question
from dasha_table import DASHA_TENURE, DASHA_YEARS, VIMSHOTTARI_ORDER
from dasha_analysis import analyze_dasha
import audit_log
import datetime as _dt

DB_PATH = os.path.join(os.path.dirname(__file__), "vedic_astrology.db")

app = FastAPI(
    title="Vedic Astrology Search API",
    description="Semantic search across Vedic astrology houses, planets, and zodiac signs.",
    version="1.0.0",
)

# Allow all origins so Durga's frontend can call it locally
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Initialize the audit DB (idempotent — creates table + indexes if missing).
audit_log.init_db()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    """Simple health check."""
    return {"status": "ok", "message": "Vedic Astrology API is running"}


@app.get("/stats")
def stats():
    """Returns counts of all entities in the DB."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM houses")
    houses = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM planets")
    planets = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM zodiac_signs")
    zodiac = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM embeddings")
    embeddings = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM synonyms")
    synonyms = cursor.fetchone()[0]

    conn.close()

    return {
        "houses": houses,
        "planets": planets,
        "zodiac_signs": zodiac,
        "embeddings": embeddings,
        "synonyms": synonyms,
    }


def _rows_to_dicts(cursor, rows):
    cols = [c[0] for c in cursor.description]
    return [dict(zip(cols, r)) for r in rows]


@app.get("/houses")
def list_houses():
    """All 12 Bhavas with full details."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT house_number, sanskrit_name, english_name, ruling_sign, ruling_planet, significance, keywords FROM houses ORDER BY house_number")
    data = _rows_to_dicts(cur, cur.fetchall())
    conn.close()
    return {"count": len(data), "items": data}


@app.get("/planets")
def list_planets():
    """All 9 Grahas with full details."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT english_name, sanskrit_name, symbol, rules_sign, exalted_in, debilitated_in, significance, keywords FROM planets ORDER BY id")
    data = _rows_to_dicts(cur, cur.fetchall())
    conn.close()
    return {"count": len(data), "items": data}


@app.get("/zodiac")
def list_zodiac():
    """All 12 Rashis with full details."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT sign_number, english_name, sanskrit_name, ruling_planet, element, quality, significance, keywords FROM zodiac_signs ORDER BY sign_number")
    data = _rows_to_dicts(cur, cur.fetchall())
    conn.close()
    return {"count": len(data), "items": data}


@app.get("/today")
def today(
    lat: float = Query(17.4399, description="Latitude (default: Gachibowli, Hyderabad)"),
    lon: float = Query(78.3489, description="Longitude (default: Gachibowli, Hyderabad)"),
    place: str = Query("Gachibowli, Hyderabad, India", description="Display name for the location"),
    when: str | None = Query(None, description="ISO 8601 datetime; defaults to 'now' UTC"),
    pulse: bool = Query(True, description="Include the LLM/template cosmic pulse summary"),
):
    """
    Live Vedic chart for the current moment (or a given moment) at a given place.
    No personal data required.
    """
    dt_obj = None
    if when:
        try:
            dt_obj = _dt.datetime.fromisoformat(when.replace("Z", "+00:00"))
        except ValueError:
            return {"error": f"Bad datetime: {when}"}

    chart = compute_chart(when=dt_obj, lat=lat, lon=lon, place=place)
    if pulse:
        chart["pulse"] = cosmic_pulse(chart)
    return chart


@app.get("/ask")
def ask(
    bg: BackgroundTasks,
    q: str = Query(..., description="The life question being asked"),
    lat: float = Query(17.4399),
    lon: float = Query(78.3489),
    place: str = Query("Gachibowli, Hyderabad, India"),
    when: str | None = Query(None, description="ISO datetime; defaults to now"),
):
    """
    Prashna Q&A — answer a life question from the live chart cast at the moment.

    Pipeline:
      1. Compute chart at the moment (datetime + lat/lon).
      2. Map the question to candidate houses via word→house dictionary
         (semantic fallback) → LLM picks within the narrowed set.
      3. Gather evidence from the chart (deterministic).
      4. Score → verdict (deterministic).
      5. Synthesize narrative (Gemini).

    Every request is recorded in the audit log (audit_log.log_ask) via a
    BackgroundTask so the audit write never blocks the user's response.
    """
    started_at = time.time()
    dt_obj = None
    if when:
        try:
            dt_obj = _dt.datetime.fromisoformat(when.replace("Z", "+00:00"))
        except ValueError:
            # Still log the bad-input case so we can spot client bugs.
            bg.add_task(
                audit_log.log_ask, q, lat, lon, place, when, None, started_at,
                f"Bad datetime: {when}",
            )
            return {"error": f"Bad datetime: {when}"}

    try:
        chart = compute_chart(when=dt_obj, lat=lat, lon=lon, place=place)
        chart["pulse"] = cosmic_pulse(chart)
        result = interpret_question(q.strip(), chart)
        result["chart"] = chart  # include the chart so the frontend can show it inline
        bg.add_task(
            audit_log.log_ask,
            q.strip(), lat, lon, place,
            (dt_obj.isoformat() if dt_obj else None),
            result, started_at, None,
        )
        return result
    except Exception as e:
        # Pipeline-level failures get audited too — error column tracks them.
        bg.add_task(
            audit_log.log_ask,
            q.strip(), lat, lon, place,
            (dt_obj.isoformat() if dt_obj else None),
            None, started_at, str(e),
        )
        raise


# ---------------------------------------------------------------------------
# Dasa Tenure Table  (May 19 Durga MOM — action item #2)
# ---------------------------------------------------------------------------

@app.get("/dasha/tenure")
def dasha_tenure():
    """The static Dasa Tenure Table — durations + Parashari signification
    metadata for the 9 Vimshottari Mahadasha lords.

    Use case: surface "what is Saturn dasha like?" in onboarding,
    UI tooltips, or LLM context.
    """
    return {
        "cycle_total_years": 120,
        "order":             VIMSHOTTARI_ORDER,
        "tenure":            DASHA_TENURE,
        "years_only":        DASHA_YEARS,
    }


@app.get("/dasha/analyze")
def dasha_analyze(
    birth_dt: str = Query(..., description="Birth datetime in ISO 8601 (UTC). Example: 1990-06-15T10:30:00"),
    when:     str | None = Query(None, description="ISO datetime to evaluate at; defaults to now"),
):
    """Personalized Vimshottari dasha analysis for a user.

    Returns where they are in their MD/AD/PD journey, with metadata,
    plus "completing soon" flags so the app can prepare them for the
    next dasha cycle (May 19 MOM use case).

    Note: only requires birth datetime — Moon longitude is location-
    independent. Lat/lon would be needed for natal Lagna (not used here).
    """
    try:
        birth = _dt.datetime.fromisoformat(birth_dt.replace("Z", "+00:00"))
    except ValueError:
        return {"error": f"Bad birth_dt: {birth_dt}"}

    when_dt = None
    if when:
        try:
            when_dt = _dt.datetime.fromisoformat(when.replace("Z", "+00:00"))
        except ValueError:
            return {"error": f"Bad when: {when}"}

    return analyze_dasha(birth, when_dt)


# ---------------------------------------------------------------------------
# Audit log  (May 19 Durga MOM — action item #3)
# ---------------------------------------------------------------------------
# Read-only endpoints over the append-only ask_log. Writes happen via a
# BackgroundTask inside /ask above. Unauthenticated for now (localhost-only
# trust model); add an admin gate before this faces real users.

# NOTE: Literal-path routes (/audit/recent, /audit/summary, /audit/unmatched-tokens)
# MUST be registered BEFORE the parametric /audit/{entry_id} — FastAPI matches
# in order, and {entry_id} would otherwise capture "summary" / "unmatched-tokens"
# as the id, then 422 because they can't parse to int.

@app.get("/audit/recent")
def audit_recent(
    limit:   int = Query(50, ge=1, le=500),
    source:  str | None = Query(None, description="Filter to one source bucket — 'dictionary', 'dictionary+llm', 'dictionary+top_score', or 'domain_map_fallback(*)'"),
    verdict: str | None = Query(None, description="Filter by verdict label, e.g. 'favorable', 'mixed'"),
    since:   str | None = Query(None, description="ISO datetime cutoff — only entries created at-or-after this"),
):
    """Paginated recent /ask entries — the spine of the admin view."""
    return {
        "count":   limit,
        "filters": {"source": source, "verdict": verdict, "since": since},
        "items":   audit_log.list_recent(limit=limit, source=source, verdict=verdict, since=since),
    }


@app.get("/audit/summary")
def audit_summary(
    since: str | None = Query(None, description="ISO datetime cutoff. Omit for all-time."),
):
    """Aggregate stats: counts by source / verdict / answer_source, fallback
    rate, LLM hiccup rate, avg latency. The dashboard at the top of /admin/audit."""
    return audit_log.summary(since=since)


@app.get("/audit/unmatched-tokens")
def audit_unmatched_tokens(
    limit: int = Query(20, ge=1, le=100),
    since: str | None = Query(None, description="ISO datetime cutoff."),
):
    """Ranked list of tokens that fell through to 'unmatched' in the mapper.
    The most-missed words are the highest-leverage candidates for adding to
    the seed dictionary or to PRIMARY_OVERRIDES."""
    return {
        "since":  since,
        "tokens": audit_log.unmatched_tokens(limit=limit, since=since),
    }


@app.get("/audit/{entry_id}")
def audit_entry(entry_id: int):
    """Full detail for one entry — includes the parsed mapping trace and
    chart summary so a UI can rehydrate the JourneyTrace view."""
    entry = audit_log.get_by_id(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"audit entry {entry_id} not found")
    return entry


@app.get("/search")
def search(
    q: str = Query(..., description="Search query, e.g. 'career', 'marriage', 'spiritual growth'"),
    top_k: int = Query(5, ge=1, le=20, description="Number of overflow results to return"),
    mode: str = Query("trinity", regex="^(trinity|ranked)$", description="'trinity' (1 house + 1 planet + 1 sign on top, then overflow) or 'ranked' (pure similarity)"),
    min_score: float = Query(0.20, ge=0.0, le=1.0, description="Minimum score for a trinity slot to be filled"),
):
    """
    Semantic search across Vedic astrology entities.

    - mode=trinity (default): returns {trinity: {house, planet, zodiac}, overflow: [...]}.
      Each trinity slot is filled only if it clears min_score.
    - mode=ranked: returns top_k results by pure similarity, any category.
    """
    if not q.strip():
        return {"query": q, "mode": mode, "results": [], "count": 0}

    if mode == "ranked":
        results = semantic_search(q.strip(), top_k=top_k)
        return {"query": q, "mode": "ranked", "count": len(results), "results": results}

    data = trinity_search(q.strip(), top_k=top_k, min_score=min_score)
    return {
        "query": q,
        "mode": "trinity",
        "trinity": data["trinity"],
        "overflow": data["overflow"],
    }
