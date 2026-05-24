"""
audit_log.py
=============
Append-only audit trail for /ask requests, backed by Neon (Postgres).

Closes May 19 Durga MOM action item #3:
  "A database logging all queries, responses, and the underlying reasoning."

Previously SQLite — migrated to hosted Postgres so this works on Vercel
serverless functions (which have ephemeral disk; SQLite writes would
silently disappear across cold starts).

Connection: read from env `NEON_DB_SELF_MAP_CONNECTION_STRING`.
On import, the module DOES NOT eagerly connect — that's deferred until
`init_db()` runs (at FastAPI startup) and to per-write/-read calls. This
matters for cold-start latency and for letting the app start when the
env var is mis-configured (we surface a warning instead of crashing).

JSON-shaped columns (`mapping_trace`, `chart_summary`) are stored as
JSONB so we can query into them with Postgres operators later. Writes
never raise — audit failures go to stderr but never break the /ask
response.
"""

from __future__ import annotations
import json
import os
import sys
import time
import datetime as dt
from collections import Counter
from typing import Optional

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json

DSN = os.environ.get("NEON_DB_SELF_MAP_CONNECTION_STRING")


# ---------------------------------------------------------------------------
# Schema + connection
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS ask_log (
    id                  BIGSERIAL    PRIMARY KEY,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    request_ms          INTEGER,
    question            TEXT         NOT NULL,
    lat                 DOUBLE PRECISION,
    lon                 DOUBLE PRECISION,
    place               TEXT,
    chart_datetime      TIMESTAMPTZ,
    source              TEXT,
    selected_houses     TEXT,
    natural_karakas     TEXT,
    intent_label        TEXT,
    llm_reasoning       TEXT,
    mapping_trace       JSONB,
    total_score         DOUBLE PRECISION,
    verdict_label       TEXT,
    verdict_confidence  TEXT,
    answer_source       TEXT,
    answer_md           TEXT,
    chart_summary       JSONB,
    error               TEXT,
    user_feedback       TEXT
);

CREATE INDEX IF NOT EXISTS idx_ask_log_created  ON ask_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ask_log_source   ON ask_log (source);
CREATE INDEX IF NOT EXISTS idx_ask_log_verdict  ON ask_log (verdict_label);
"""


def _connect() -> psycopg.Connection:
    """Open a fresh connection. Neon supports connection-per-request fine
    via its pooled endpoint; we don't keep a long-lived pool here because
    FastAPI + serverless is short-lived per invocation."""
    if not DSN:
        raise RuntimeError(
            "NEON_DB_SELF_MAP_CONNECTION_STRING is not set — audit logging disabled"
        )
    return psycopg.connect(DSN, autocommit=True, row_factory=dict_row)


def init_db() -> None:
    """Idempotent — safe to call at every process startup. Silent no-op if
    the env var isn't set so the rest of the API still boots in local
    dev (an admin can wire up Neon later)."""
    if not DSN:
        print(
            "[audit_log] NEON_DB_SELF_MAP_CONNECTION_STRING not set — "
            "audit logging is DISABLED. Set it to enable.",
            file=sys.stderr,
        )
        return
    try:
        with _connect() as conn:
            conn.execute(SCHEMA)
    except Exception as e:
        print(f"[audit_log] schema init failed: {e}", file=sys.stderr)


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
    if not DSN:
        return  # silently skip if audit isn't configured

    try:
        intent = (result or {}).get("intent") or {}
        evidence = (result or {}).get("evidence") or {}
        verdict = (result or {}).get("verdict") or {}
        chart = (result or {}).get("chart") or {}

        mapping = intent.get("mapping")
        chart_summary = None
        if chart:
            chart_summary = {
                "lagna":               chart.get("lagna", {}).get("sign"),
                "lagna_lord":          chart.get("lagna", {}).get("lord"),
                "current_mahadasha":   chart.get("dasha", {}).get("current_mahadasha"),
                "current_antardasha":  chart.get("dasha", {}).get("current_antardasha"),
                "current_pratyantar":  chart.get("dasha", {}).get("current_pratyantar"),
            }

        request_ms = int((time.time() - started_at) * 1000)

        # Postgres accepts ISO 8601 directly; if it's already a datetime, fine too.
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO ask_log (
                    request_ms, question, lat, lon, place,
                    chart_datetime, source, selected_houses, natural_karakas,
                    intent_label, llm_reasoning, mapping_trace,
                    total_score, verdict_label, verdict_confidence,
                    answer_source, answer_md, chart_summary, error
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s
                )
                """,
                (
                    request_ms,
                    question,
                    lat, lon, place,
                    chart_datetime,
                    intent.get("source"),
                    ",".join(str(h) for h in (intent.get("selected_houses") or [])),
                    ",".join(intent.get("natural_karakas") or []),
                    intent.get("label"),
                    intent.get("llm_reasoning"),
                    Json(mapping) if mapping else None,
                    evidence.get("total_score"),
                    verdict.get("label"),
                    verdict.get("confidence"),
                    (result or {}).get("answer_source"),
                    (result or {}).get("answer"),
                    Json(chart_summary) if chart_summary else None,
                    error,
                ),
            )
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
    if not DSN:
        return []

    where: list[str] = []
    params: list = []
    if source:
        where.append("source = %s")
        params.append(source)
    if verdict:
        where.append("verdict_label = %s")
        params.append(verdict)
    if since:
        where.append("created_at >= %s")
        params.append(since)
    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    cols = (
        "id, created_at, request_ms, question, source, selected_houses, "
        "natural_karakas, intent_label, total_score, verdict_label, "
        "verdict_confidence, answer_source"
    )
    if include_trace:
        cols += (
            ", mapping_trace, llm_reasoning, chart_summary, "
            "answer_md, error"
        )

    try:
        with _connect() as conn:
            rows = conn.execute(
                f"SELECT {cols} FROM ask_log {where_clause} "
                f"ORDER BY created_at DESC LIMIT %s",
                params + [limit],
            ).fetchall()
        return [_normalize_row(r) for r in rows]
    except Exception as e:
        print(f"[audit_log] list_recent failed: {e}", file=sys.stderr)
        return []


def get_by_id(entry_id: int) -> dict | None:
    """Single entry with all detail."""
    if not DSN:
        return None
    try:
        with _connect() as conn:
            row = conn.execute(
                "SELECT * FROM ask_log WHERE id = %s", (entry_id,)
            ).fetchone()
        return _normalize_row(row) if row else None
    except Exception as e:
        print(f"[audit_log] get_by_id failed: {e}", file=sys.stderr)
        return None


def summary(since: Optional[str] = None) -> dict:
    """Aggregate stats."""
    if not DSN:
        return _empty_summary(since)

    where = "WHERE created_at >= %s" if since else ""
    params: list = [since] if since else []

    try:
        with _connect() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) AS n FROM ask_log {where}", params
            ).fetchone()["n"]

            by_source = {
                r["source"] or "(none)": r["n"]
                for r in conn.execute(
                    f"SELECT source, COUNT(*) AS n FROM ask_log {where} GROUP BY source",
                    params,
                ).fetchall()
            }
            by_verdict = {
                r["verdict_label"] or "(none)": r["n"]
                for r in conn.execute(
                    f"SELECT verdict_label, COUNT(*) AS n FROM ask_log {where} GROUP BY verdict_label",
                    params,
                ).fetchall()
            }
            by_answer_source = {
                r["answer_source"] or "(none)": r["n"]
                for r in conn.execute(
                    f"SELECT answer_source, COUNT(*) AS n FROM ask_log {where} GROUP BY answer_source",
                    params,
                ).fetchall()
            }

            avg_ms_row = conn.execute(
                f"SELECT AVG(request_ms)::FLOAT AS avg_ms FROM ask_log {where}", params
            ).fetchone()
            avg_ms = round(avg_ms_row["avg_ms"]) if avg_ms_row and avg_ms_row["avg_ms"] else None

            err_where = where + (" AND " if where else " WHERE ") + "error IS NOT NULL"
            error_count = conn.execute(
                f"SELECT COUNT(*) AS n FROM ask_log {err_where}", params
            ).fetchone()["n"]

        fallback_count = sum(n for src, n in by_source.items() if src.startswith("domain_map_fallback"))
        hiccup_count = by_source.get("dictionary+top_score", 0)
        single_count = by_source.get("dictionary", 0)
        llm_pick_count = by_source.get("dictionary+llm", 0)

        return {
            "total":                 total,
            "by_source":             by_source,
            "by_verdict":            by_verdict,
            "by_answer_source":      by_answer_source,
            "fallback_rate":         round(fallback_count / total, 3) if total else 0,
            "llm_hiccup_rate":       round(hiccup_count / total, 3) if total else 0,
            "single_candidate_rate": round(single_count / total, 3) if total else 0,
            "llm_pick_rate":         round(llm_pick_count / total, 3) if total else 0,
            "avg_request_ms":        avg_ms,
            "error_count":           error_count,
            "since":                 since,
        }
    except Exception as e:
        print(f"[audit_log] summary failed: {e}", file=sys.stderr)
        return _empty_summary(since)


def unmatched_tokens(limit: int = 20, since: Optional[str] = None) -> list[dict]:
    """Rank tokens that most often fell through to 'unmatched' with up to 3
    example questions per token.

    Could use JSONB operators server-side, but Python aggregation on a
    2000-row window keeps the code symmetric with the SQLite version and
    well under any reasonable latency budget.
    """
    if not DSN:
        return []

    where = "WHERE created_at >= %s" if since else ""
    params: list = [since] if since else []

    try:
        with _connect() as conn:
            rows = conn.execute(
                f"SELECT id, question, mapping_trace FROM ask_log "
                f"{where} ORDER BY created_at DESC LIMIT 2000",
                params,
            ).fetchall()
    except Exception as e:
        print(f"[audit_log] unmatched_tokens failed: {e}", file=sys.stderr)
        return []

    counter: Counter[str] = Counter()
    examples: dict[str, list[dict]] = {}
    for r in rows:
        trace = r.get("mapping_trace")
        if not trace:
            continue
        # JSONB comes back as a dict already; no need to json.loads
        if isinstance(trace, str):  # defensive: some drivers return strings
            try:
                trace = json.loads(trace)
            except json.JSONDecodeError:
                continue
        for tok in trace.get("tokens_unmatched") or []:
            counter[tok] += 1
            if len(examples.setdefault(tok, [])) < 3:
                examples[tok].append({"id": r["id"], "question": r["question"]})

    return [
        {"token": tok, "count": cnt, "examples": examples.get(tok, [])}
        for tok, cnt in counter.most_common(limit)
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_row(row: dict | None) -> dict | None:
    """psycopg returns Python-native dicts (with `dict_row` factory) + JSONB
    columns auto-deserialized. We just need to:
      - alias mapping_trace / chart_summary into the `mapping_trace` /
        `chart_summary` keys our API contract uses
      - serialize datetime objects so JSON responses are clean (FastAPI
        handles this, but we still normalize for downstream consumers)
    """
    if row is None:
        return None
    d = dict(row)
    if isinstance(d.get("created_at"), dt.datetime):
        d["created_at"] = d["created_at"].isoformat()
    if isinstance(d.get("chart_datetime"), dt.datetime):
        d["chart_datetime"] = d["chart_datetime"].isoformat()
    return d


def _empty_summary(since: Optional[str]) -> dict:
    return {
        "total":                 0,
        "by_source":             {},
        "by_verdict":            {},
        "by_answer_source":      {},
        "fallback_rate":         0,
        "llm_hiccup_rate":       0,
        "single_candidate_rate": 0,
        "llm_pick_rate":         0,
        "avg_request_ms":        None,
        "error_count":           0,
        "since":                 since,
    }


if __name__ == "__main__":
    init_db()
    print(f"audit.db (Neon Postgres) — DSN set: {bool(DSN)}")
    print(f"recent rows ({len(list_recent(limit=5))}):")
    for r in list_recent(limit=5):
        print(f"  #{r['id']} {r['created_at']}  src={r['source']}  "
              f"verdict={r['verdict_label']}  q={r['question'][:60]}")
    print(f"\nsummary: {summary()}")
