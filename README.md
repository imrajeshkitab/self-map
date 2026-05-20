# Kitab — Vedic Astrology Engine

A Prashna (horary) astrology engine with deterministic chart computation,
DBA timing analysis, and LLM-synthesized readings.

## Repository layout

```
.
├── backend/      FastAPI + Swiss Ephemeris + Gemini synthesis
├── web/          Next.js (App Router) — TypeScript + Tailwind
└── docs/         Architecture & interpretation pipeline docs
```

## Quick start

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn api:app --reload --port 8000
```

**Frontend (Next.js):**
```bash
cd web
cp .env.example .env.local      # one-time; defaults to http://localhost:8000
npm install
npm run dev
# open http://localhost:3000
```

## Docs

- [Interpretation pipeline](docs/INTERPRETATION.md) — 6 context sources, 5-stage flow
- [Database schema](docs/DATABASE.md) — entity tables, embeddings, synonyms
- [Backend README](backend/README.md) — run, rebuild dictionary, env vars
