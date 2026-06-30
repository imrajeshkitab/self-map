"""
emotion.api — standalone FastAPI app for isolated testing.

    cd backend
    uvicorn emotion.api:app --reload --port 8200

In production the router mounts into backend/api.py at /emotion/*.
"""

from __future__ import annotations

import datetime as dt
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .engine import compute_emotion
from .routes import router as emotion_router

app = FastAPI(title="Kitab Emotional Engine (standalone POC)", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(emotion_router)


@app.get("/health")
def health():
    return {"ok": True, "service": "emotional-engine-standalone", "version": "0.1.0"}


# CLI: python -m emotion.api 1995-08-20 14:30 17.44 78.35
if __name__ == "__main__":
    import sys, json
    dob = sys.argv[1] if len(sys.argv) > 1 else "1995-08-20"
    tob = sys.argv[2] if len(sys.argv) > 2 else "14:30"
    lat = float(sys.argv[3]) if len(sys.argv) > 3 else 17.4399
    lon = float(sys.argv[4]) if len(sys.argv) > 4 else 78.3489
    birth = dt.datetime.fromisoformat(f"{dob}T{tob}")
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    print(json.dumps(compute_emotion(birth, now, lat=lat, lon=lon, place="CLI"), indent=2, ensure_ascii=False))
