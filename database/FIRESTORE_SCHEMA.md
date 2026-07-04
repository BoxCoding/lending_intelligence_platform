# Firestore Collection Design (runtime store)

The API persists through `backend/app/db/store.py`, which targets Firestore
when `GOOGLE_APPLICATION_CREDENTIALS` is set (local JSON fallback otherwise).

| Collection | Doc ID | Content |
|---|---|---|
| `customers` | customer_id | name, employer, months_observed, updated_at |
| `features` | customer_id | canonical 34-feature vector (flat map) |
| `profiles` | customer_id | full scored profile: income, repayment, intent, risk, lead, recommendation |
| `lead_scores` | customer_id | score, tier, conversion_probability, components |
| `audit` | timestamp | action, detail — immutable trail of pipeline runs & chat |

Design notes
- `profiles` is a denormalized read-model: one fetch renders the whole customer page.
- Raw transactions stay out of Firestore in the demo (they live in the AA payload);
  in production land them in BigQuery/PostgreSQL (`database/schema.sql`) and keep
  Firestore for serving-layer reads.
- Composite index recommendation: `lead_scores` on (tier ASC, score DESC) for the queue.
