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

```bash
cd backend
vercel login          # one-time OAuth
vercel link           # create a NEW Vercel project for the backend
```

In the Vercel dashboard for this project:

- **Settings → General → Root Directory** → `backend`
- **Settings → Environment Variables**, add:
  - `FIREBASE_CREDENTIALS_JSON` — the whole service-account JSON, one line:
    ```bash
    python -c "import json;print(json.dumps(json.load(open('secrets/firebase-adminsdk.json'))))" | pbcopy
    ```
  - `FIRESTORE_PROJECT_ID` = `lendiq-dc313`
  - `FIRESTORE_DATABASE` = `(default)`
  - `MODEL_DIR` = `ml_models` (points at `backend/ml_models/`, the copy of
    the trained artifacts bundled inside the backend project — Vercel's
    Python builder can't reach outside its Root Directory to `../ml/models`)
  - `CORS_ORIGINS` = your frontend's Vercel domain, once you know it
  - `GEMINI_API_KEY` — optional; offline advisor covers chat without it

Deploy:

```bash
vercel --prod
```

Vercel auto-detects `backend/vercel.json` (routes every path to
`api/index.py`, which imports the real FastAPI `app`) and installs from
`backend/requirements.txt` — the trimmed runtime set. The trained model
files under `backend/ml_models/` are force-bundled into the function via the
`includeFiles` key in `vercel.json`.

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

Paste the build log. Two failure modes we've already hit and fixed on this
repo, for reference:
- **"Root Directory not found" / dies right after cloning** → Root Directory
  isn't set to `backend` in the Vercel project settings.
- **`llvmlite` / `numba` / `Cannot install on Python version 3.12`** → SHAP
  (which pulls in numba → llvmlite, and llvmlite has no 3.12 wheel) leaked
  into the installed set. It must not appear in `backend/requirements.txt` —
  that is the file Vercel's builder reads. The training-only extras live in
  `backend/requirements-dev.txt`, which Vercel does not install.
