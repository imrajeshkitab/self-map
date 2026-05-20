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

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import os

from search import semantic_search, trinity_search
from prashna import compute_chart
from narrate import cosmic_pulse
from interpret import answer as interpret_question
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
      2. Classify the question into a Vedic life-domain (Gemini).
      3. Gather evidence from the chart (deterministic).
      4. Score → verdict (deterministic).
      5. Synthesize narrative (Gemini).
    """
    dt_obj = None
    if when:
        try:
            dt_obj = _dt.datetime.fromisoformat(when.replace("Z", "+00:00"))
        except ValueError:
            return {"error": f"Bad datetime: {when}"}

    chart = compute_chart(when=dt_obj, lat=lat, lon=lon, place=place)
    chart["pulse"] = cosmic_pulse(chart)
    result = interpret_question(q.strip(), chart)
    result["chart"] = chart  # include the chart so the frontend can show it inline
    return result


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
