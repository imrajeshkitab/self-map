"""
audit_log.py
=============
Append-only audit trail for /ask requests.

Closes May 19 Durga MOM action item #3:
  "A database logging all queries, responses, and the underlying reasoning.
   Use case: provides data for post-mortem analysis to continuously improve
   the model."

Storage is a separate SQLite DB (`backend/audit.db`) rather than the
reference DB (`vedic_astrology.db`) — different lifecycles, different
backup needs, easier to reset.

Writes happen via FastAPI's BackgroundTasks so the user's /ask response
is never blocked by the audit insert. Failures are logged to stderr but
do NOT propagate to the request handler — the user gets their reading
either way.

Reads are surfaced via three endpoints in api.py:
  GET /audit/recent          — paginated list with filters
  GET /audit/summary         — aggregate counts + rates
  GET /audit/unmatched-tokens — top tokens that fell through, with examples
"""

from __future__ import annotations
import json
import os
import sqlite3
import sys
import time
import datetime as dt
from collections import Counter
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "audit.db")


# ---------------------------------------------------------------------------
# Schema + connection
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS ask_log (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at          TEXT    NOT NULL,
    request_ms          INTEGER,
    question            TEXT    NOT NULL,
    lat                 REAL,
    lon                 REAL,
    place               TEXT,
    chart_datetime      TEXT,
    source              TEXT,                  -- 'dictionary' | 'dictionary+llm' | 'dictionary+top_score' | 'domain_map_fallback(*)'
    selected_houses     TEXT,                  -- comma-separated, e.g. "10,6"
    natural_karakas     TEXT,                  -- comma-separated
    intent_label        TEXT,
    llm_reasoning       TEXT,
    mapping_trace_json  TEXT,                  -- the full MappingTrace as JSON
    total_score         REAL,
    verdict_label       TEXT,
    verdict_confidence  TEXT,
    answer_source       TEXT,                  -- 'gemini' | 'template'
    answer_md           TEXT,
    chart_summary_json  TEXT,                  -- {lagna, md, ad, pd} only — full chart is too big
    error               TEXT,                  -- non-null if pipeline raised
    user_feedback       TEXT                   -- nullable placeholder for future thumbs-up/down
);

CREATE INDEX IF NOT EXISTS idx_ask_log_created ON ask_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ask_log_source  ON ask_log(source);
CREATE INDEX IF NOT EXISTS idx_ask_log_verdict ON ask_log(verdict_label);
"""


def _connect() -> sqlite3.Connection:
    """Open a fresh connection. FastAPI is async so we open per-call rather
    than caching a single connection across threads."""
    conn = sqlite3.connect(DB_PATH, isolation_level=None)  # autocommit
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Idempotent — safe to call at every process startup."""
    conn = _connect()
    try:
        conn.executescript(SCHEMA)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Write path — called from /ask via BackgroundTasks
# ---------------------------------------------------------------------------

def log_ask(
    question: str,
    lat: float | None,
    lon: float | None,
    place: str | None,
    chart_datetime: str | None,
    result: dict | None,
    started_at: float,
    error: str | None = None,
) -> None:
    """Write one ask_log row. Never raises — audit failures go to stderr.

    `started_at` is a `time.time()` capture from the start of the request
    so we can record total latency.
    """
    try:
        intent = (result or {}).get("intent") or {}
        evidence = (result or {}).get("evidence") or {}
        verdict = (result or {}).get("verdict") or {}
        chart = (result or {}).get("chart") or {}

        mapping = intent.get("mapping")
        chart_summary = None
        if chart:
            chart_summary = {
                "lagna":             chart.get("lagna", {}).get("sign"),
                "lagna_lord":        chart.get("lagna", {}).get("lord"),
                "current_mahadasha": chart.get("dasha", {}).get("current_mahadasha"),
                "current_antardasha": chart.get("dasha", {}).get("current_antardasha"),
                "current_pratyantar": chart.get("dasha", {}).get("current_pratyantar"),
            }

        request_ms = int((time.time() - started_at) * 1000)
        created_at = dt.datetime.now(dt.timezone.utc).isoformat()

        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO ask_log (
                    created_at, request_ms, question, lat, lon, place,
                    chart_datetime, source, selected_houses, natural_karakas,
                    intent_label, llm_reasoning, mapping_trace_json,
                    total_score, verdict_label, verdict_confidence,
                    answer_source, answer_md, chart_summary_json, error
                ) VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?
                )
                """,
                (
                    created_at,
                    request_ms,
                    question,
                    lat, lon, place,
                    chart_datetime,
                    intent.get("source"),
                    ",".join(str(h) for h in (intent.get("selected_houses") or [])),
                    ",".join(intent.get("natural_karakas") or []),
                    intent.get("label"),
                    intent.get("llm_reasoning"),
                    json.dumps(mapping) if mapping else None,
                    evidence.get("total_score"),
                    verdict.get("label"),
                    verdict.get("confidence"),
                    (result or {}).get("answer_source"),
                    (result or {}).get("answer"),
                    json.dumps(chart_summary) if chart_summary else None,
                    error,
                ),
            )
        finally:
            conn.close()
    except Exception as e:
        # Audit must never break the user's response.
        print(f"[audit_log] WRITE FAILED: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Read path — queried by /audit/* endpoints
# ---------------------------------------------------------------------------

def list_recent(
    limit: int = 50,
    source: Optional[str] = None,
    verdict: Optional[str] = None,
    since: Optional[str] = None,
    include_trace: bool = False,
) -> list[dict]:
    """Paginated recent entries. Filters: source, verdict_label, since (ISO datetime)."""
    where = []
    params: list = []
    if source:
        where.append("source = ?")
        params.append(source)
    if verdict:
        where.append("verdict_label = ?")
        params.append(verdict)
    if since:
        where.append("created_at >= ?")
        params.append(since)
    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    cols = (
        "id, created_at, request_ms, question, source, selected_houses, "
        "natural_karakas, intent_label, total_score, verdict_label, "
        "verdict_confidence, answer_source"
    )
    if include_trace:
        cols += ", mapping_trace_json, llm_reasoning, chart_summary_json, answer_md, error"

    conn = _connect()
    try:
        rows = conn.execute(
            f"SELECT {cols} FROM ask_log {where_clause} ORDER BY created_at DESC LIMIT ?",
            params + [limit],
        ).fetchall()
        return [_row_to_dict(r, include_trace) for r in rows]
    finally:
        conn.close()


def get_by_id(entry_id: int) -> dict | None:
    """Single entry with all detail — for the per-row detail view."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM ask_log WHERE id = ?", (entry_id,)
        ).fetchone()
        return _row_to_dict(row, include_trace=True) if row else None
    finally:
        conn.close()


def summary(since: Optional[str] = None) -> dict:
    """Aggregate stats: counts by source/verdict, fallback + hiccup rates,
    LLM availability, total volume.

    `since` is an ISO datetime cutoff (e.g. last 24h, last 7d).
    """
    where = "WHERE created_at >= ?" if since else ""
    params: list = [since] if since else []

    conn = _connect()
    try:
        total = conn.execute(
            f"SELECT COUNT(*) FROM ask_log {where}", params
        ).fetchone()[0]

        by_source = {
            r["source"] or "(none)": r["n"]
            for r in conn.execute(
                f"SELECT source, COUNT(*) AS n FROM ask_log {where} GROUP BY source", params
            ).fetchall()
        }
        by_verdict = {
            r["verdict_label"] or "(none)": r["n"]
            for r in conn.execute(
                f"SELECT verdict_label, COUNT(*) AS n FROM ask_log {where} GROUP BY verdict_label", params
            ).fetchall()
        }
        by_answer_source = {
            r["answer_source"] or "(none)": r["n"]
            for r in conn.execute(
                f"SELECT answer_source, COUNT(*) AS n FROM ask_log {where} GROUP BY answer_source", params
            ).fetchall()
        }

        fallback_count = sum(n for src, n in by_source.items() if src.startswith("domain_map_fallback"))
        hiccup_count = by_source.get("dictionary+top_score", 0)
        single_count = by_source.get("dictionary", 0)
        llm_pick_count = by_source.get("dictionary+llm", 0)

        avg_ms_row = conn.execute(
            f"SELECT AVG(request_ms) AS avg_ms FROM ask_log {where}", params
        ).fetchone()
        avg_ms = round(avg_ms_row["avg_ms"]) if avg_ms_row and avg_ms_row["avg_ms"] else None

        error_count = conn.execute(
            f"SELECT COUNT(*) FROM ask_log {where} {('AND' if where else 'WHERE')} error IS NOT NULL",
            params,
        ).fetchone()[0]

        return {
            "total":               total,
            "by_source":           by_source,
            "by_verdict":          by_verdict,
            "by_answer_source":    by_answer_source,
            "fallback_rate":       round(fallback_count / total, 3) if total else 0,
            "llm_hiccup_rate":     round(hiccup_count / total, 3) if total else 0,
            "single_candidate_rate": round(single_count / total, 3) if total else 0,
            "llm_pick_rate":       round(llm_pick_count / total, 3) if total else 0,
            "avg_request_ms":      avg_ms,
            "error_count":         error_count,
            "since":               since,
        }
    finally:
        conn.close()


def unmatched_tokens(limit: int = 20, since: Optional[str] = None) -> list[dict]:
    """Rank tokens that most often fell through to 'unmatched' in the
    mapping trace, with up to 3 example questions per token.

    This is the actionable feed for dictionary expansion: Durga / you
    look at this list to see which words the dictionary is missing.
    """
    where = "WHERE created_at >= ?" if since else ""
    params: list = [since] if since else []

    conn = _connect()
    try:
        rows = conn.execute(
            f"SELECT id, question, mapping_trace_json FROM ask_log {where} ORDER BY created_at DESC LIMIT 2000",
            params,
        ).fetchall()
    finally:
        conn.close()

    counter: Counter[str] = Counter()
    examples: dict[str, list[dict]] = {}
    for r in rows:
        if not r["mapping_trace_json"]:
            continue
        try:
            trace = json.loads(r["mapping_trace_json"])
        except json.JSONDecodeError:
            continue
        for tok in trace.get("tokens_unmatched") or []:
            counter[tok] += 1
            if len(examples.setdefault(tok, [])) < 3:
                examples[tok].append({"id": r["id"], "question": r["question"]})

    ranked = counter.most_common(limit)
    return [
        {"token": tok, "count": cnt, "examples": examples.get(tok, [])}
        for tok, cnt in ranked
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row_to_dict(row: sqlite3.Row, include_trace: bool) -> dict:
    d = dict(row)
    if include_trace:
        if d.get("mapping_trace_json"):
            try:
                d["mapping_trace"] = json.loads(d["mapping_trace_json"])
            except json.JSONDecodeError:
                d["mapping_trace"] = None
        if d.get("chart_summary_json"):
            try:
                d["chart_summary"] = json.loads(d["chart_summary_json"])
            except json.JSONDecodeError:
                d["chart_summary"] = None
        # Drop the raw JSON columns from the response — the parsed versions
        # are what consumers want.
        d.pop("mapping_trace_json", None)
        d.pop("chart_summary_json", None)
    return d


if __name__ == "__main__":
    # CLI sanity check: init + show schema + dump recent.
    init_db()
    print(f"audit.db at: {DB_PATH}")
    print(f"recent rows ({len(list_recent(limit=5))}):")
    for r in list_recent(limit=5):
        print(f"  #{r['id']} {r['created_at']}  src={r['source']:25s}  "
              f"verdict={r['verdict_label']}  q={r['question'][:60]}")
    print(f"\nsummary: {summary()}")
