# LendIQ — System Architecture

## High-level architecture

```mermaid
flowchart TD
    AA[Account Aggregator API\nFI data JSON] --> ING[Data Ingestion\nPOST /aa/upload]
    ING --> PARSE[AA Parser\nnarration → 25 categories]
    PARSE --> FE[Feature Engineering\n34 canonical features]
    FE --> INC[Income Estimation\nLightGBM + rules blend]
    FE --> INT[Borrowing Intent\nXGBoost + signal logit]
    FE --> RSK[Risk Engine\nLightGBM PD + scorecard]
    INC --> REP[Repayment Capacity\nFOIR / EMI math]
    INC --> LS[Lead Scoring Engine\nweighted fusion 0-100]
    INT --> LS
    REP --> LS
    RSK --> LS
    LS --> REC[Loan Recommendation\nproduct match + pricing]
    REC --> API[FastAPI REST layer]
    RSK -.SHAP.-> XAI[Explainability]
    XAI --> API
    API <--> LLM[Gemini Advisor\nLangGraph agent]
    API <--> DB[(Firestore /\nlocal JSON store)]
    API --> UI[Next.js 15 Dashboard\nReact Query + Recharts]
```

## Scoring sequence (one customer)

```mermaid
sequenceDiagram
    participant AA as Account Aggregator
    participant API as FastAPI /aa/upload
    participant P as Pipeline
    participant ML as Model Registry
    participant DB as Store
    participant UI as Dashboard

    AA->>API: FI data payload (consented)
    API->>P: process_aa_payload()
    P->>P: parse + categorize transactions
    P->>P: build 34-feature vector
    P->>ML: income / intent / risk inference
    ML-->>P: predictions (+ rule fallback)
    P->>P: FOIR capacity → lead fusion → offers
    P->>DB: customers, features, profiles, lead_scores, audit
    UI->>API: GET /dashboard, GET /customer/{id}
    UI->>API: POST /chat (Gemini advisor, grounded)
```

## Layers

| Layer | Technology | Responsibility |
|---|---|---|
| Ingestion | FastAPI + Pydantic | Validate AA payloads, consent metadata |
| Intelligence | 6 engines (`backend/app/services/`) | Income, capacity, intent, risk, lead, offers |
| ML | LightGBM, XGBoost, SHAP (`ml/`) | Training, registry, drift detection |
| Agent | LangGraph (`agents/`) | fetch → classify → underwrite/advise → compose |
| Serving | Firestore / local JSON | Denormalized profile read-model |
| UX | Next.js 15, Tailwind, Recharts | Executive dashboard, profile, chat, what-if |

## Design decisions

1. **Rules + ML blend, never ML alone.** Every engine has a calibrated
   deterministic core; model artifacts sharpen it (60/40 blend). Missing
   artifacts degrade gracefully — the demo never breaks.
2. **One feature builder for training and serving** (`feature_engineering.py`)
   eliminates skew; the vector order is the model contract.
3. **Denormalized profile document** = single read per screen, ideal for
   Firestore pricing and sub-100ms dashboards.
4. **Hard policy guards over model scores** (FOIR cap 55%, grade-E cap):
   regulatory constraints must never be learned away.
5. **Offline-first demo**: no Gemini key → deterministic grounded advisor;
   no Firestore creds → local JSON store; same code paths.

## Scalability path (enterprise)

- Swap ingestion to Pub/Sub + Cloud Run workers; land raw transactions in
  BigQuery, keep Firestore as serving layer.
- Model registry → Vertex AI Model Registry; drift job (`ml/drift_detection.py`)
  on Cloud Scheduler; champion/challenger via traffic split.
- Add consent lifecycle service (AA FIU module) and PII tokenization before
  feature store; audit collection already provides the trail.
