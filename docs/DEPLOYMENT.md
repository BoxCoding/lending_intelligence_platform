# Deployment Guide

Architecture: **frontend on Vercel**, **backend on Render** (the FastAPI +
LightGBM/XGBoost/SHAP stack is far beyond Vercel's serverless size limits),
**Firestore** as the database (project `lendiq-dc313`, database `(default)`).

## 0. One-time prerequisites

```bash
npm i -g vercel          # Vercel CLI
git init && git add . && git commit -m "LendIQ"   # repo needed for Render
# push to GitHub (Render deploys from a repo)
```

> The service-account key lives at `backend/secrets/firebase-adminsdk.json`
> and is **gitignored** — never commit it. Hosted environments receive it via
> the `FIREBASE_CREDENTIALS_JSON` env var instead.

## 1. Backend → Render

1. Push the repo to GitHub.
2. In the Render dashboard: **New → Blueprint**, pick the repo — it reads
   `deployment/render.yaml` (Docker build via `docker/Dockerfile.backend`).
3. Set the secret env vars when prompted:
   - `FIREBASE_CREDENTIALS_JSON` — paste the full JSON. Generate a single-line
     version with:
     ```bash
     python -c "import json;print(json.dumps(json.load(open('backend/secrets/firebase-adminsdk.json'))))" | pbcopy
     ```
   - `GEMINI_API_KEY` — optional.
4. Note the service URL, e.g. `https://lendiq-api.onrender.com`, and check
   `GET /` returns the model registry status.

## 2. Frontend → Vercel

```bash
cd frontend
vercel login                                  # one-time OAuth
vercel link                                   # create the project
vercel env add NEXT_PUBLIC_API_URL production # paste the Render URL
vercel --prod
```

## 3. Close the CORS loop

In Render, set `CORS_ORIGINS` to your real Vercel domain, e.g.
`https://lendiq.vercel.app` (the backend also allows any `*.vercel.app`
preview URL via regex). Redeploy the backend.

## 4. Seed production data

Firestore is already seeded from local (`scripts/seed.py` writes straight to
Firestore when `backend/.env` has the credentials). To re-seed from the
deployed container, Render → Shell:

```bash
python scripts/seed.py --n 80
```

## Checklist

- [ ] `GET https://<render-url>/` → `models: {income: true, ...}`
- [ ] `GET https://<render-url>/dashboard` → KPIs with 80 leads
- [ ] Vercel URL loads dashboard with data (no CORS errors in console)
- [ ] Chat answers (offline advisor if no Gemini key)
