"""Recommendation, chat (LLM advisor) and what-if simulation endpoints."""

from fastapi import APIRouter, HTTPException

from app.db.store import store
from app.schemas.models import (
    ChatRequest,
    ChatResponse,
    CustomerIdRequest,
    Recommendation,
    WhatIfRequest,
)
from app.services import llm_advisor
from app.services.pipeline import get_profile
from app.services.repayment_engine import emi_for_principal

router = APIRouter(tags=["Insights"])


@router.post("/recommend", response_model=Recommendation)
def recommend(req: CustomerIdRequest):
    profile = get_profile(req.customer_id)
    if not profile or not profile.get("recommendation"):
        raise HTTPException(
            status_code=404, detail="Customer not scored yet. Upload AA data first."
        )
    return profile["recommendation"]


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    profile = get_profile(req.customer_id) if req.customer_id else None
    result = llm_advisor.chat(req.message, profile, req.history)
    store.audit("chat", {"customer_id": req.customer_id, "q": req.message[:200]})
    return ChatResponse(**result)


@router.post("/whatif", summary="Scenario simulation: can the customer afford this loan?")
def what_if(req: WhatIfRequest):
    profile = get_profile(req.customer_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Customer not found")
    income = profile["income"]["monthly_income"] * (1 + req.income_change_pct / 100)
    existing_emi = profile["features"].get("emi_outflow", 0.0)
    new_emi = emi_for_principal(req.loan_amount, req.interest_rate, req.tenure_months)
    total_obligation = existing_emi + new_emi + req.extra_monthly_expense
    foir = total_obligation / max(income, 1.0)
    disposable_after = (
        income
        - profile["features"].get("fixed_expense", 0.0)
        - profile["features"].get("variable_expense", 0.0)
        - new_emi
        - req.extra_monthly_expense
    )
    verdict = (
        "AFFORDABLE"
        if foir <= 0.55 and disposable_after > 0
        else ("STRETCHED" if foir <= 0.65 else "NOT_AFFORDABLE")
    )
    return {
        "monthly_emi": round(new_emi, 0),
        "projected_foir": round(foir, 3),
        "disposable_after_emi": round(disposable_after, 0),
        "verdict": verdict,
        "note": f"Policy FOIR cap is 55%. Projected FOIR {foir:.0%} → {verdict}.",
    }
