"""End-to-end scoring pipeline orchestrator.

AA payload → parse → features → income → repayment → intent → risk →
lead score → recommendation. Persists every stage so the dashboard and
advisor can read the full profile.
"""

from datetime import UTC, datetime

from app.core.logging import logger
from app.db.store import store
from app.schemas.models import AAPayload, CustomerProfile
from app.services import (
    aa_parser,
    feature_engineering,
    income_engine,
    intent_engine,
    lead_scoring,
    recommendation_engine,
    risk_engine,
)
from app.services.repayment_engine import assess_repayment


def process_aa_payload(payload: AAPayload) -> CustomerProfile:
    """Run the full intelligence pipeline for one customer and persist results."""
    parsed = aa_parser.parse_aa_payload(payload)
    features = feature_engineering.build_features(parsed)

    income = income_engine.estimate_income(features)
    repayment = assess_repayment(features, income)
    intent = intent_engine.predict_intent(features)
    risk = risk_engine.assess_risk(features)
    lead = lead_scoring.score_lead(features, income, repayment, intent, risk)
    recommendation = recommendation_engine.recommend(
        payload.customer_id, features, income, repayment, intent, risk, lead
    )

    profile = CustomerProfile(
        customer_id=payload.customer_id,
        name=payload.name,
        features=features,
        income=income,
        repayment=repayment,
        intent=intent,
        risk=risk,
        lead=lead,
        recommendation=recommendation,
        updated_at=datetime.now(UTC).isoformat(),
    )

    doc = profile.model_dump()
    store.put(
        "customers",
        payload.customer_id,
        {
            "customer_id": payload.customer_id,
            "name": payload.name,
            "employer": parsed.get("employer"),
            "months_observed": len(parsed["months"]),
            "updated_at": profile.updated_at,
        },
    )
    store.put("features", payload.customer_id, features)
    store.put("profiles", payload.customer_id, doc)
    store.put(
        "lead_scores", payload.customer_id, doc["lead"] | {"customer_id": payload.customer_id}
    )
    store.audit("pipeline_run", {"customer_id": payload.customer_id, "lead_tier": lead.tier})

    logger.info(
        "Pipeline complete for %s: income=%.0f lead=%s(%.1f) risk=%s",
        payload.customer_id,
        income.monthly_income,
        lead.tier,
        lead.score,
        risk.risk_grade,
    )
    return profile


def get_profile(customer_id: str) -> dict | None:
    return store.get("profiles", customer_id)
