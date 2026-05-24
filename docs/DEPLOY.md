# Deploying to Vercel

This repo is laid out as two Vercel projects sharing one GitHub repo:

```
self-map/
├── backend/   →  Vercel project "kitab-api"   (Python / FastAPI)
└── web/       →  Vercel project "kitab-web"   (Next.js)
```

The two halves communicate over HTTPS. The web project's
`NEXT_PUBLIC_API_BASE_URL` env var points at the backend's deployed URL.

---

## Prerequisites

1. **Neon Postgres DB** — already created. Connection string lives in
   `backend/.env` as `NEON_DB_SELF_MAP_CONNECTION_STRING` (not committed).
2. **Google Gemini API key** — already in `backend/.env` as `GEMINI_API_KEY`.
3. **GitHub repo connected to Vercel** — push has already been done to
   `git@github.com:imrajeshkitab/self-map.git`.

---

## Step 1 — Deploy the backend (`kitab-api`)

In the Vercel dashboard → **Add New Project** → import the
`imrajeshkitab/self-map` repo.

Configure:

| Setting | Value |
|---|---|
| Project name | `kitab-api` (or whatever you prefer) |
| Framework preset | `Other` (Vercel auto-detects FastAPI via `requirements.txt` + the `app` export in `backend/api/index.py`) |
| Root directory | `backend` |
| Build command | *(leave empty — Vercel runs `pip install -r requirements.txt`)* |
| Output directory | *(leave empty)* |
| Install command | *(leave empty — auto)* |

Add environment variables (**Settings → Environment Variables**):

| Name | Value | Environments |
|---|---|---|
| `GEMINI_API_KEY` | *(paste from `backend/.env`)* | Production, Preview, Development |
| `NEON_DB_SELF_MAP_CONNECTION_STRING` | *(paste from `backend/.env`)* | Production, Preview, Development |

Click **Deploy**. First deploy installs deps and bundles the function
(~3–5 minutes). After it succeeds, note the URL — something like
`https://kitab-api.vercel.app`.

### Smoke-test the backend

```bash
curl 'https://YOUR-API.vercel.app/health'
# expect: {"status":"ok","message":"Vedic Astrology API is running"}

curl 'https://YOUR-API.vercel.app/ask?q=Should%20I%20take%20this%20job'
# expect: full /ask JSON response, source/intent/answer/chart populated

curl 'https://YOUR-API.vercel.app/audit/recent?limit=5'
# expect: the request you just fired, now logged in Neon
```

---

## Step 2 — Deploy the web app (`kitab-web`)

Same GitHub repo, **Add New Project** again.

| Setting | Value |
|---|---|
| Project name | `kitab-web` |
| Framework preset | `Next.js` (auto-detected) |
| Root directory | `web` |
| Build / install / output | *(leave default)* |

Environment variables:

| Name | Value | Environments |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `https://kitab-api.vercel.app` (the URL from Step 1) | Production, Preview, Development |

Deploy. Next.js builds in ~1–2 minutes. Visit the URL — `/ask`, `/today`,
`/browse`, `/admin/audit` should all work.

---

## Step 3 — Verify end-to-end

1. Open the web app's `/ask` page.
2. Submit a question.
3. Expand the **"How is this answered?"** trace — confirm it shows the
   live mapping stages.
4. Visit `/admin/audit` — the question you just fired should appear in
   the table within ~1 second (BackgroundTask write to Neon).
5. Open the **unmatched-tokens panel** — should aggregate over all
   logged questions.

If `/admin/audit` is empty:
- Check Neon dashboard — table `ask_log` exists?
- Check Vercel function logs for the backend — any `[audit_log]` stderr?
- Verify `NEON_DB_SELF_MAP_CONNECTION_STRING` is set on the backend project.

---

## Step 4 — Production hardening (when ready)

The current deploy is fine for an internal demo. Before exposing publicly:

### 1. Lock down CORS

`backend/api.py` currently allows `allow_origins=["*"]`. That's defensible
for a read-only public API, but if you add anything sensitive (auth,
user data, the audit-log admin route), tighten to:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.vercel\.app$|http://localhost:3000",
    allow_methods=["GET"],
    allow_headers=["*"],
)
```

### 2. Gate `/admin/audit` + `/audit/*` endpoints

Right now anyone with the URL can read every logged question. Add a
shared-secret check or full auth before this faces real users:

```python
from fastapi import Header, HTTPException
ADMIN_TOKEN = os.environ["ADMIN_TOKEN"]

def require_admin(x_admin_token: str = Header(None)):
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")

# Apply to every /audit/* route:
@app.get("/audit/recent", dependencies=[Depends(require_admin)])
def audit_recent(...): ...
```

Web side: pass the token from a `NEXT_ADMIN_TOKEN` env var via a server-only
fetch wrapper.

### 3. Audit log retention

`ask_log` grows unbounded. Once you're past the demo, add a Vercel Cron
that prunes rows older than 90 days. Either:

- An endpoint `GET /admin/cleanup` that deletes old rows, hit by a cron
- Or a separate Python function bound to a cron schedule

The Vercel `vercel.ts` can declare crons:

```ts
crons: [{ path: '/admin/cleanup', schedule: '0 3 * * *' }]
```

---

## Re-deploys

Any push to `master` triggers a redeploy of both projects. Preview URLs
are generated per branch automatically.

To rebuild the embedding indexes (`dict_embeddings.pkl`,
`search_index.pkl`) after dictionary edits:

```bash
cd backend
python3 build_dict_embeddings.py   # rebuild dict
python3 embeddings.py              # rebuild /search index
git add backend/dict_embeddings.pkl backend/search_index.pkl
git commit -m "Rebuild embedding indexes"
git push
```

The next deploy picks them up automatically.

---

## File map relevant to deploy

| File | Role |
|---|---|
| `backend/api/index.py` | Vercel Python entry point — re-exports `app` from `api.py` |
| `backend/requirements.txt` | Pinned runtime deps, sized to fit Vercel's 250 MB function limit |
| `backend/.python-version` | Pins Python 3.13 |
| `backend/dict_embeddings.pkl` | Pre-built dictionary embedding index (15 MB, bundled with function) |
| `backend/search_index.pkl` | Pre-built houses/planets/zodiac embedding index (99 KB, bundled) |
| `backend/vedic_astrology.db` | Read-only reference DB (gitignored, but stable enough to either commit or rebuild on deploy) |
| `web/package.json` | Standard Next.js deps |
| `web/.env.example` | Documents `NEXT_PUBLIC_API_BASE_URL` |
| `.gitignore` | Excludes `.env`, `*.db`, but explicitly allows the two `.pkl` indexes |
