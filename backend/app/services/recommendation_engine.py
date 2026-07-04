"""Loan Recommendation Engine.

Matches customer signals to loan products, sizes the offer within
repayment capacity, prices by risk grade, and produces reason strings
for every recommendation.
"""
from app.schemas.models import (
    BorrowingIntent,
    IncomeEstimate,
    LeadScore,
    LoanOffer,
    Recommendation,
    RepaymentCapacity,
    RiskAssessment,
)
from app.services.repayment_engine import PRODUCT_TERMS, emi_for_principal

# Risk grade -> interest rate spread added over the product base rate
GRADE_SPREAD = {"A": 0.0, "B": 0.75, "C": 1.75, "D": 3.25, "E": 6.0}

PRODUCT_LABELS = {
    "PERSONAL_LOAN": "Personal Loan",
    "HOME_LOAN": "Home Loan",
    "MORTGAGE_LOAN": "Mortgage Loan (LAP)",
    "AUTO_LOAN": "Auto Loan",
}


def recommend(
    customer_id: str,
    features: dict[str, float],
    income: IncomeEstimate,
    repayment: RepaymentCapacity,
    intent: BorrowingIntent,
    risk: RiskAssessment,
    lead: LeadScore,
) -> Recommendation:
    offers: list[LoanOffer] = []

    product_signals = {
        "HOME_LOAN": (
            features["property_payment_flag"] * 3
            + features["rent_outflow"] / max(income.monthly_income, 1) * 2
            + max(features["savings_growth_rate"], 0) * 2
        ),
        "AUTO_LOAN": features["vehicle_payment_flag"] * 3 + features["salary_growth_rate"],
        "PERSONAL_LOAN": (
            features["wedding_expense_flag"] * 2
            + features["education_payment_flag"] * 1.5
            + features["high_value_purchase_count"] * 0.5
            + min(features["loan_enquiry_count"], 2.0)
            + 0.5  # baseline: PL fits nearly everyone with capacity
        ),
        "MORTGAGE_LOAN": (
            (1.0 if income.monthly_income > 150_000 else 0.0)
            + ("BUSINESS_INCOME" in income.income_sources) * 1.5
        ),
    }

    for product, signal in sorted(product_signals.items(), key=lambda kv: kv[1], reverse=True):
        base_rate, max_tenure, _ = PRODUCT_TERMS[product]
        capacity = repayment.loan_capacity.get(product, 0.0)
        if capacity < 50_000 or signal <= 0.2:
            continue
        spread = GRADE_SPREAD[risk.risk_grade]
        # Offer sized conservatively: 80% of hard capacity, scaled by affordability
        amount = round(capacity * 0.8 * (0.6 + 0.4 * repayment.affordability_score / 100), -4)
        if amount < 50_000:
            continue
        tenure = _suggest_tenure(product, max_tenure, income)
        emi = emi_for_principal(amount, base_rate + spread + 0.5, tenure)
        offers.append(
            LoanOffer(
                product=PRODUCT_LABELS[product],
                eligible_amount=amount,
                interest_rate_min=round(base_rate + spread, 2),
                interest_rate_max=round(base_rate + spread + 1.0, 2),
                tenure_months=tenure,
                monthly_emi=round(emi, 0),
                priority=len(offers) + 1,
                reasons=_offer_reasons(product, features, income, repayment, risk),
            )
        )
        if len(offers) >= 3:
            break

    credit_limit = round(min(income.monthly_income * 3, repayment.eligible_emi * 24), -3)
    health = _financial_health_score(income, repayment, risk)
    summary = _summary(offers, lead, health)

    return Recommendation(
        customer_id=customer_id,
        offers=offers,
        credit_limit=max(credit_limit, 0.0),
        financial_health_score=round(health, 1),
        summary=summary,
    )


def _suggest_tenure(product: str, max_tenure: int, income: IncomeEstimate) -> int:
    # Younger/growing income profiles can take longer tenures; keep it simple:
    defaults = {"PERSONAL_LOAN": 48, "AUTO_LOAN": 60, "HOME_LOAN": 240, "MORTGAGE_LOAN": 144}
    return min(defaults.get(product, 60), max_tenure)


def _offer_reasons(product, f, income, repayment, risk) -> list[str]:
    reasons = []
    if product == "HOME_LOAN":
        if f["property_payment_flag"]:
            reasons.append("Property token/registration payments detected in transactions")
        if f["rent_outflow"] > 0:
            reasons.append(f"Paying ₹{f['rent_outflow']:,.0f}/mo rent — EMI can replace rent")
    if product == "AUTO_LOAN" and f["vehicle_payment_flag"]:
        reasons.append("Vehicle booking/showroom payment detected")
    if product == "PERSONAL_LOAN":
        if f["wedding_expense_flag"]:
            reasons.append("Wedding-related expenses observed")
        if f["loan_enquiry_count"] > 0:
            reasons.append("Active loan enquiries indicate immediate credit need")
    if product == "MORTGAGE_LOAN":
        reasons.append("High income profile suits loan-against-property for larger ticket")
    reasons.append(
        f"EMI headroom ₹{repayment.eligible_emi:,.0f}/mo at FOIR ≤55%, risk grade {risk.risk_grade}"
    )
    reasons.append(f"Income estimated at ₹{income.monthly_income:,.0f}/mo (confidence {income.confidence:.0%})")
    return reasons[:4]


def _financial_health_score(income, repayment, risk) -> float:
    return min(
        0.30 * risk.financial_stability
        + 0.25 * repayment.affordability_score
        + 0.25 * (100 * income.cash_flow_stability)
        + 0.20 * risk.behavior_stability,
        100.0,
    )


def _summary(offers, lead, health) -> str:
    if not offers:
        return "No pre-qualified offers — capacity or risk constraints not met. Nurture lead."
    top = offers[0]
    return (
        f"{lead.tier} lead (score {lead.score}). Best fit: {top.product} up to "
        f"₹{top.eligible_amount:,.0f} at {top.interest_rate_min}–{top.interest_rate_max}% "
        f"for {top.tenure_months} months (EMI ≈ ₹{top.monthly_emi:,.0f}). "
        f"Financial health {health:.0f}/100."
    )
