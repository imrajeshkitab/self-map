# Backend — Prashna / Vedic Astrology API

FastAPI service that powers the Ask the Moment (Prashna), Today's Sky,
and semantic search features.

## Layout

| File | Role |
|---|---|
| `api.py` | FastAPI app — routes for `/ask`, `/today`, `/search`, `/houses`, `/planets`, `/zodiac` |
| `prashna.py` | Swiss Ephemeris chart computation. Lagna, planets, houses, Vimshottari DBA (MD → AD → PD) |
| `interpret.py` | Domain classification, evidence scoring, verdict, LLM narrative synthesis (markdown, 6 sections) |
| `narrate.py` | Cosmic pulse summary for the moment |
| `search.py` | Semantic + trinity search across houses / planets / zodiac signs |
| `embeddings.py` | Embedding generation for the DB |
| `db_setup.py` | SQLite schema + seed data |
| `scraper_*.py` | Source scrapers for houses / planets / zodiac signs |
| `view_db.py` | Quick DB inspection CLI |
| `run_all.py` | Convenience runner — scrape → DB → embeddings |
| `house_seeds.py` | Curated 240 word→house seed list (12 Vedic houses) |
| `build_house_dict.py` | WordNet expansion → `house_dictionary.{json,tsv}` |
| `house_dictionary.json` | 5,070-word generated word→house mapping (used by interpreter) |
| `house_dictionary.tsv` | Spreadsheet-friendly version for reviewer pass |
| `vedic_astrology.db` | SQLite DB (gitignored) |
| `search_index.pkl` | Cached embeddings (gitignored) |
| `.env` | `GEMINI_API_KEY=…` (gitignored) |

## Run the API

```bash
cd backend
pip install -r requirements.txt
uvicorn api:app --reload --port 8000
```

Then the API is at `http://localhost:8000`. Try:

```bash
curl 'http://localhost:8000/ask?q=Should%20I%20take%20this%20job'
curl 'http://localhost:8000/today'
```

## Rebuild the word→house dictionary

After editing `house_seeds.py`:

```bash
cd backend
python3 build_house_dict.py
```

Outputs `house_dictionary.json` and `house_dictionary.tsv`.

## Environment

Create `backend/.env`:

```
GEMINI_API_KEY=your_gemini_api_key_here
```

## Architecture docs

See [`../docs/INTERPRETATION.md`](../docs/INTERPRETATION.md) for the
full reasoning pipeline (the 6 context sources, the 5-stage flow,
and how deterministic scoring vs LLM synthesis interact).
