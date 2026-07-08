# Deployment Guide

Architecture: **both frontend and backend on Vercel** as two separate
projects from the same repo, **Firestore** as the database (project
`lendiq-dc313`, database `(default)`).

The backend is a FastAPI app with a real ML stack (LightGBM + XGBoost), which
normally blows past Vercel's ~250MB serverless function size limit. To fit,
this deployment:

- Saves trained models as **native LightGBM/XGBoost Boosters**, not sklearn
  wrappers — drops scikit-learn+scipy (~145MB) as a runtime dependency.
  Predictions are numerically identical (see `ml/train.py`, `*_engine.py`).
- Ships **without SHAP** (~155MB with its numba/llvmlite chain, and it was
  also incompatible with Vercel's Python 3.12 build resolver). Every
  explainability call gracefully falls back to a pseudo-attribution when SHAP
  isn't installed — same API contract, `confidence: 0.55` instead of `0.9`.
- Talks to Firestore over its **plain REST API** (`google-auth` + `requests`)
  instead of the official SDK, which pulls in ~40MB of grpc/protobuf.

Result: **~187MB** installed — `backend/requirements.txt` is the trimmed
runtime set (what Vercel installs). `backend/requirements-dev.txt` adds
scikit-learn + SHAP for training (`ml/train.py`) and full local dev.

## 0. One-time prerequisites

```bash
npm i -g vercel
git add . && git commit -m "LendIQ"
git push
```

> The service-account key lives at `backend/secrets/firebase-adminsdk.json`
> and is **gitignored** — never commit it. Vercel receives it via the
> `FIREBASE_CREDENTIALS_JSON` env var instead.

## 1. Backend → Vercel

**Deploy via git, not the CLI from your machine.** The local `backend/.venv`
is ~700MB of the full ML stack; a CLI deploy can sweep it into the upload and
blow past the function size limit. It is **git-ignored**, so a git-based
deploy never sees it — the function ends up ~250MB (fresh Linux deps only).

1. Push the repo to GitHub (already done for `BoxCoding/lending_intelligence_platform`).
2. Vercel dashboard → **Add New → Project** → import the repo → this is a
   **separate project** from the frontend.
3. **Settings → General → Root Directory** → `backend`
4. **Settings → Environment Variables**, add:
   - `FIREBASE_CREDENTIALS_JSON` — the whole service-account JSON, one line:
     ```bash
     python -c "import json;print(json.dumps(json.load(open('backend/secrets/firebase-adminsdk.json'))))" | pbcopy
     ```
   - `FIRESTORE_PROJECT_ID` = `lendiq-dc313`
   - `FIRESTORE_DATABASE` = `(default)`
   - `MODEL_DIR` = `ml_models` (points at `backend/ml_models/`, the trained
     artifacts bundled inside the backend project — Vercel can't reach outside
     its Root Directory to `../ml/models`)
   - `CORS_ORIGINS` = your frontend's Vercel domain, once you know it
   - `GEMINI_API_KEY` — optional; offline advisor covers chat without it
5. Deploy (happens automatically on import / push).

`backend/vercel.json` uses the modern **`functions` + `rewrites`** config (not
the legacy `builds` key). This matters: `builds` bundles the *entire* Root
Directory into the function — including `.venv` — whereas `functions` bundles
only what `api/index.py` imports plus the `includeFiles` glob (`ml_models/**`,
the trained models, which are loaded by path so wouldn't be traced otherwise).
Deps install from `backend/requirements.txt` (the trimmed runtime set);
Python 3.12 is pinned via `backend/.python-version`.

Note the URL it gives you, e.g. `https://lendiq-api.vercel.app`.

## 2. Frontend → Vercel

```bash
cd ../frontend
vercel login
vercel link            # a SEPARATE Vercel project from the backend
vercel env add NEXT_PUBLIC_API_URL production   # paste the backend URL from step 1
vercel --prod
```

**Settings → General → Root Directory** must be `frontend` for this project.

## 3. Close the CORS loop

Back in the backend project's env vars, set `CORS_ORIGINS` to the frontend's
real domain (the backend also allows any `*.vercel.app` preview URL via
regex already). Redeploy the backend for the change to take effect.

## 4. Seed production data

Firestore is shared external state — seeding doesn't happen at deploy time.
Run it from your machine, pointed at the same project (your local
`backend/.env` already has the right credentials):

```bash
cd backend
.venv/bin/python scripts/seed.py --n 80
```

The deployed backend reads from the same Firestore project, so this data
shows up immediately without a redeploy.

## Checklist

- [ ] `GET https://<backend-url>/` → `models: {income: true, intent: true, risk: true}`
- [ ] `GET https://<backend-url>/dashboard` → KPIs with 80 leads (after seeding)
- [ ] `POST https://<backend-url>/predict/explain/risk` → `confidence: 0.55`
      (expected — SHAP isn't installed in this deployment; this is not a bug)
- [ ] Frontend URL loads the dashboard with data (no CORS errors in console)
- [ ] Chat answers (offline advisor if no Gemini key)

## If the deploy still fails

Paste the build log. Three failure modes we've already hit and fixed on this
repo, for reference:
- **"Root Directory not found" / dies right after cloning** → Root Directory
  isn't set to `backend` in the Vercel project settings.
- **`llvmlite` / `numba` / `Cannot install on Python version 3.12`** → SHAP
  (which pulls in numba → llvmlite, and llvmlite has no 3.12 wheel) leaked
  into the installed set. It must not appear in `backend/requirements.txt` —
  that is the file Vercel's builder reads. The training-only extras live in
  `backend/requirements-dev.txt`, which Vercel does not install.
- **`Total bundle size (NNN MB) exceeds the maximum function size`** → the
  local `backend/.venv` (~700MB) got bundled. Two things prevent this and both
  are in the repo now: `vercel.json` uses the modern `functions` config (not
  `builds`, which bundles the whole directory), and `.vercelignore` excludes
  `.venv`. If it still recurs, you're deploying via the CLI from a working
  copy where those aren't taking effect — **deploy via git push instead**,
  where `.venv` is git-ignored and simply isn't there. The trimmed deps alone
  are ~250MB on Linux (scipy is the biggest at ~130MB), comfortably under the
  limit.
