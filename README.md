# LendIQ — Retail Lending Intelligence Platform

AI-powered pre-qualified lead generation for retail lending, built on
**Account Aggregator** transaction data. Identifies customers with high
repayment capacity, high borrowing intent, stable financial behaviour and
low default probability — then recommends the right loan product with an
explainable WHY.

**Products covered:** Personal Loan · Home Loan · Mortgage (LAP) · Auto Loan

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

Optional: set `GEMINI_API_KEY` in `backend/.env` for live Gemini answers,
and `GOOGLE_APPLICATION_CREDENTIALS` for Firestore (local JSON store otherwise).

### Docker

```bash
docker compose -f docker/docker-compose.yml up --build
```

### Deploy

- Backend → Render: `deployment/render.yaml`
- Frontend → Vercel: `deployment/vercel.json`
- Helper: `deployment/deploy.sh [local|render|vercel]`

## Repository layout

```
backend/    FastAPI app (routers, 6 engines, model registry, store)
ml/         data_generator, train (LightGBM/XGBoost/SHAP), drift_detection, models/
agents/     LangGraph underwriting-assistant workflow
frontend/   Next.js 15 + Tailwind + React Query + Recharts (dark theme)
database/   PostgreSQL DDL + Firestore collection design
docker/     Dockerfiles + compose
deployment/ Render/Vercel/deploy.sh
docs/       Architecture (mermaid diagrams), API reference
data/       synthetic AA payloads + labels + sample payload
```

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
