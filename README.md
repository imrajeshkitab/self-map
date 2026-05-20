# Kitab — Vedic Astrology Engine

A Prashna (horary) astrology engine with deterministic chart computation,
DBA timing analysis, and LLM-synthesized readings.

## Repository layout

```
.
├── backend/      FastAPI + Swiss Ephemeris + Gemini synthesis
├── web/          Next.js (App Router) — new frontend (in progress)
├── frontend/     Original vanilla HTML/JS (retired once `web/` reaches parity)
└── docs/         Architecture & interpretation pipeline docs
```

## Quick start

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn api:app --reload --port 8000
```

**Frontend (vanilla, current):**
```bash
cd frontend
python3 -m http.server 5500
# open http://localhost:5500/ask.html
```

**Frontend (Next.js, in progress):**
```bash
cd web
npm install
npm run dev
# open http://localhost:3000
```

## Docs

- [Interpretation pipeline](docs/INTERPRETATION.md) — 6 context sources, 5-stage flow
- [Database schema](docs/DATABASE.md) — entity tables, embeddings, synonyms
- [Backend README](backend/README.md) — run, rebuild dictionary, env vars
