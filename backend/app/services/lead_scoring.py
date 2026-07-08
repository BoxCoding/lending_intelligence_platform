"""AI Lead Scoring Engine.

Fuses income quality, borrowing intent, repayment capacity, risk and
transaction behaviour into a single 0-100 lead score with HOT/WARM/COLD
tiers and a calibrated conversion probability.
"""

from app.core.config import get_settings
from app.schemas.models import (
    BorrowingIntent,
    IncomeEstimate,
    LeadScore,
    RepaymentCapacity,
    RiskAssessment,
)

WEIGHTS = {
    "intent": 0.34,
    "capacity": 0.24,
    "income_quality": 0.18,
    "risk": 0.16,
    "behaviour": 0.08,
}


def score_lead(
    features: dict[str, float],
    income: IncomeEstimate,
    repayment: RepaymentCapacity,
    intent: BorrowingIntent,
    risk: RiskAssessment,
) -> LeadScore:
    settings = get_settings()

    income_quality = 100 * (
        0.5 * income.salary_regularity
        + 0.3 * income.cash_flow_stability
        + 0.2 * min(income.monthly_income / 200_000, 1.0)  # income band uplift, caps at 2L
    )
    risk_component = 100 * (1 - min(risk.probability_of_default / 0.25, 1.0))
    behaviour = 0.6 * risk.behavior_stability + 0.4 * risk.financial_stability

    components = {
        "intent": round(intent.intent_score, 1),
        "capacity": round(repayment.affordability_score, 1),
        "income_quality": round(income_quality, 1),
        "risk": round(risk_component, 1),
        "behaviour": round(behaviour, 1),
    }
    score = sum(WEIGHTS[k] * v for k, v in components.items())

    # Hard guards: never mark un-lendable customers HOT
    if risk.risk_grade == "E" or repayment.eligible_emi < 2000:
        score = min(score, 40.0)

    if score >= settings.min_lead_score_hot:
        tier = "HOT"
    elif score >= settings.min_lead_score_warm:
        tier = "WARM"
    else:
        tier = "COLD"

    # Conversion probability: intent probability tempered by affordability
    p90 = intent.windows[-1].probability if intent.windows else 0.2
    conversion = p90 * (0.5 + 0.5 * repayment.affordability_score / 100)

    explanation = _explain(components, tier)
    return LeadScore(
        score=round(score, 1),
        tier=tier,
        conversion_probability=round(conversion, 3),
        components=components,
        explanation=explanation,
    )


def _explain(components: dict[str, float], tier: str) -> list[str]:
    ranked = sorted(components.items(), key=lambda kv: kv[1], reverse=True)
    labels = {
        "intent": "borrowing intent signals",
        "capacity": "repayment capacity",
        "income_quality": "income quality & stability",
        "risk": "low default risk",
        "behaviour": "banking behaviour",
    }
    strongest = [labels[k] for k, v in ranked[:2] if v >= 55]
    weakest = [labels[k] for k, v in ranked[-2:] if v < 45]
    lines = [f"Lead classified {tier}"]
    if strongest:
        lines.append("Strengths: " + ", ".join(strongest))
    if weakest:
        lines.append("Watch-outs: " + ", ".join(weakest))
    return lines
