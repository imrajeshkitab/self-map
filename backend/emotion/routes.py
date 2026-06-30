"""
emotion.routes — the emotional-engine endpoints as a FastAPI APIRouter.

Mount into the main backend (backend/api.py):
    from emotion.routes import router as emotion_router
    app.include_router(emotion_router)
"""

from __future__ import annotations

import datetime as dt
from fastapi import APIRouter, Query, HTTPException

from .engine import compute_emotion

router = APIRouter(prefix="/emotion", tags=["emotion"])


@router.get("/health")
def emotion_health():
    return {"ok": True, "service": "emotional-engine", "version": "0.1.0"}


@router.get("/daily")
def daily_emotion(
    dob: str = Query(..., description="Date of birth, YYYY-MM-DD"),
    tob: str = Query("12:00", description="Time of birth, HH:MM (24h)"),
    lat: float = Query(17.4399, description="Birth latitude"),
    lon: float = Query(78.3489, description="Birth longitude"),
    place: str = Query("", description="Birth place label"),
    on: str | None = Query(None, description="ISO datetime to read for; defaults to now (UTC)"),
):
    """Daily emotional vector + dominant themes + narrative + full step trace."""
    try:
        birth = dt.datetime.fromisoformat(f"{dob}T{tob}")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Bad dob/tob: {dob} {tob}")
    if on:
        try:
            as_of = dt.datetime.fromisoformat(on.replace("Z", ""))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Bad 'on' datetime: {on}")
    else:
        as_of = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    return compute_emotion(birth, as_of, lat=lat, lon=lon, place=place)
