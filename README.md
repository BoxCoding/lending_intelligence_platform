# LendIQ — Retail Lending Intelligence Platform

AI-powered pre-qualified lead generation for retail lending, built on
**Account Aggregator** transaction data. Identifies customers with high
repayment capacity, high borrowing intent, stable financial behaviour and
low default probability — then recommends the right loan product with an
explainable WHY.

**Products covered:** Personal Loan · Home Loan · Mortgage (LAP) · Auto Loan

## Problem statement alignment

Traditional retail lending relies on bureau scores and static financial
metrics. Every named pain point in the problem statement maps to a specific
LendIQ module — this isn't a generic lending demo retrofitted to the brief:

| Problem statement says… | LendIQ answers with… |
|---|---|
| Low lead conversion | AI Lead Scoring Engine (HOT/WARM/COLD, 0–100) — demo run hits **30.2%** predicted conversion, above the >30% target |
| Poor understanding of customer intent | Borrowing Intent Model — 30/60/90-day application probability + human-readable reason codes |
| Inaccurate income estimation | Income Estimation Engine — confidence-scored monthly/net/disposable income, **7% MAPE** on held-out test data |
| High underwriting effort | Repayment Capacity Model (FOIR/DTI/EMI headroom) automates what a credit officer reads off bank statements by hand |
| Manual verification | AA Parser — 25-category transaction classification replaces manual statement reading; SHAP explainability gives an auditable paper trail |
| High acquisition cost | Pre-qualified targeting via Lead Scoring replaces blanket marketing spend with a ranked, explainable queue |
| High repayment capacity (objective) | Repayment Capacity Model — eligible EMI, DTI, per-product loan capacity |
| High borrowing intent (objective) | Borrowing Intent Model — life-event signals (property tokens, vehicle bookings, loan enquiries) |
| Stable financial behaviour (objective) | Risk Engine's `financial_stability`/`behavior_stability` scores + Income Engine's `cash_flow_stability`/`salary_regularity` |
| Low default probability (objective) | Risk Engine — probability of default, grade A–E, fraud indicators |

## What it does

| Module | Output |
|---|---|
| AA Parser | 25 semantic categories from raw bank narrations (salary, EMI, rent, UPI, property tokens, loan-enquiry fees, …) |
| Income Engine | Monthly/net/disposable income, volatility, salary regularity, **confidence score** |
| Repayment Model | Eligible EMI, FOIR, DTI, per-product loan capacity |
| Intent Model | P(applies within 30/60/90 days) + reason codes |
| Risk Engine | PD, grade A–E, fraud indicators, liquidity risk |
| Lead Scoring | 0–100 fusion → **HOT / WARM / COLD** |
| Recommendations | Sized, priced (rate band by grade), tenured offers with reasons |
| Explainable AI | SHAP drivers per prediction |
| GenAI Advisor | Gemini (LangGraph agent) grounded in the scored profile; offline fallback |
| Dashboard | Executive KPIs, funnel, distributions, lead queue, what-if simulator |

Demo run (80 synthetic customers): predicted conversion rate **30.2%**
(target >30%), models: income MAPE 7%, risk KS 0.36.

## Quickstart (offline, no keys needed)

```bash
# 1. Backend + ML
cd backend
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd ../ml
../backend/.venv/bin/python data_generator.py --n 400   # synthetic AA dataset
../backend/.venv/bin/python train.py                    # trains 3 models + metrics
cd ../backend
.venv/bin/python scripts/seed.py --n 80                 # score 80 demo customers
.venv/bin/uvicorn app.main:app --port 8080              # API on :8080  (docs at /docs)

# 2. Frontend
cd ../frontend
npm install
npm run dev                                             # UI on :3000
```

Optional: set `GEMINI_API_KEY` in `backend/.env` for live Gemini answers.

**Firestore**: put the Firebase Admin SDK key at `backend/secrets/firebase-adminsdk.json`
(gitignored) and set `GOOGLE_APPLICATION_CREDENTIALS`/`FIRESTORE_PROJECT_ID` in
`backend/.env` — without credentials the app falls back to a local JSON store.
Hosted platforms use `FIREBASE_CREDENTIALS_JSON` (inline) instead; see
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the full Vercel walkthrough.

### Docker (local dev only)

```bash
docker compose -f docker/docker-compose.yml up --build
```

### Deploy — both backend and frontend on Vercel (two separate projects)

- Backend → `backend/vercel.json` + `backend/api/index.py`; installs from
  `backend/requirements.txt`, a trimmed dependency set (~187MB — native
  LightGBM/XGBoost Boosters instead of sklearn, Firestore over REST instead
  of the grpc SDK, SHAP dropped with a graceful fallback) that fits Vercel's
  serverless function size limit.
- Frontend → `deployment/vercel.json`
- Helper: `deployment/deploy.sh [local|backend|frontend]`

## Repository layout

```
backend/    FastAPI app (routers, 6 engines, model registry, store)
ml/         data_generator, train (LightGBM/XGBoost/SHAP), drift_detection, models/
agents/     LangGraph underwriting-assistant workflow
frontend/   Next.js 15 + Tailwind + React Query + Recharts (dark theme)
database/   PostgreSQL DDL + Firestore collection design
docker/     Dockerfiles + compose
deployment/ Vercel (frontend) config + deploy.sh
docs/       Architecture (mermaid diagrams), API reference
data/       synthetic AA payloads + labels + sample payload
```

## Testing & code quality

```bash
cd backend
.venv/bin/python -m pytest ../ -q --cov --cov-report=term-missing   # 113 tests, 92% coverage on app/
.venv/bin/ruff check backend/app ml agents backend/tests             # lint
.venv/bin/ruff format backend/app ml agents backend/tests            # format

cd ../frontend
npm run lint          # ESLint (next/core-web-vitals + next/typescript)
npm run format:check  # Prettier
npx tsc --noEmit      # type-check
```

Tests cover every engine (income, repayment, intent, risk, lead scoring,
recommendation), the AA parser/feature pipeline, explainability, the offline
LLM advisor, and all API routes end-to-end via `TestClient` — isolated from
the live Firestore project with a throwaway local store per test.

## Evaluation metrics (written to `ml/models/model_registry.json`)

- Income: RMSE, MAE, MAPE
- Intent: AUC, Precision, Recall, F1
- Risk: ROC-AUC, KS, Gini
- Drift: z-score report via `ml/drift_detection.py`

## Hackathon innovations

GenAI underwriting assistant with APPROVE/REFER/DECLINE checklist ·
SHAP explainability on every prediction · natural-language credit summaries ·
financial health score · real-time eligibility · what-if repayment simulation ·
fully offline-capable demo (no external keys required).
