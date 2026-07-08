"""Per-engine prediction endpoints. Each reads the persisted feature vector."""

from fastapi import APIRouter, HTTPException

from app.db.store import store
from app.schemas.models import (
    BorrowingIntent,
    CustomerIdRequest,
    Explanation,
    IncomeEstimate,
    LeadScore,
    RepaymentCapacity,
    RiskAssessment,
)
from app.services import income_engine, intent_engine, lead_scoring, risk_engine
from app.services.explainability import explain_prediction
from app.services.repayment_engine import assess_repayment

router = APIRouter(prefix="/predict", tags=["Predictions"])


def _features_or_404(customer_id: str) -> dict:
    features = store.get("features", customer_id)
    if not features:
        raise HTTPException(
            status_code=404, detail=f"No features for customer {customer_id}. Upload AA data first."
        )
    return features


@router.post("/income", response_model=IncomeEstimate)
def predict_income(req: CustomerIdRequest):
    return income_engine.estimate_income(_features_or_404(req.customer_id))


@router.post("/repayment", response_model=RepaymentCapacity)
def predict_repayment(req: CustomerIdRequest):
    features = _features_or_404(req.customer_id)
    income = income_engine.estimate_income(features)
    return assess_repayment(features, income)


@router.post("/intent", response_model=BorrowingIntent)
def predict_intent(req: CustomerIdRequest):
    return intent_engine.predict_intent(_features_or_404(req.customer_id))


@router.post("/risk", response_model=RiskAssessment)
def predict_risk(req: CustomerIdRequest):
    return risk_engine.assess_risk(_features_or_404(req.customer_id))


@router.post("/lead", response_model=LeadScore)
def predict_lead(req: CustomerIdRequest):
    features = _features_or_404(req.customer_id)
    income = income_engine.estimate_income(features)
    repayment = assess_repayment(features, income)
    intent = intent_engine.predict_intent(features)
    risk = risk_engine.assess_risk(features)
    return lead_scoring.score_lead(features, income, repayment, intent, risk)


@router.post("/explain/{model_name}", response_model=Explanation)
def explain(model_name: str, req: CustomerIdRequest):
    if model_name not in {"income", "intent", "risk"}:
        raise HTTPException(status_code=422, detail="model_name must be income | intent | risk")
    return explain_prediction(model_name, _features_or_404(req.customer_id))
