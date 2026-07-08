"""Risk Engine.

Estimates probability of default (PD), assigns a risk grade, flags fraud
indicators, and scores financial/behavioural stability and liquidity risk.
Uses trained classifier when available, else a calibrated scorecard.
"""

import math

from app.core.logging import logger
from app.ml_registry import registry
from app.schemas.models import RiskAssessment
from app.services.feature_engineering import to_vector

GRADE_BANDS = [(0.03, "A"), (0.07, "B"), (0.13, "C"), (0.22, "D"), (1.01, "E")]


def assess_risk(features: dict[str, float]) -> RiskAssessment:
    ml_pd = None
    model = registry.get("risk")
    if model is not None:
        try:
            ml_pd = float(model.predict_proba([to_vector(features)])[0][1])
        except Exception as exc:
            logger.warning("Risk model inference failed, using scorecard: %s", exc)

    scorecard_pd = _scorecard_pd(features)
    pd_final = 0.65 * ml_pd + 0.35 * scorecard_pd if ml_pd is not None else scorecard_pd
    pd_final = min(max(pd_final, 0.005), 0.95)

    grade = next(g for cutoff, g in GRADE_BANDS if pd_final < cutoff)

    fin_stability = _financial_stability(features)
    beh_stability = _behavior_stability(features)
    liquidity = _liquidity_risk(features)

    return RiskAssessment(
        probability_of_default=round(pd_final, 4),
        risk_grade=grade,
        fraud_indicators=_fraud_indicators(features),
        financial_stability=round(fin_stability, 1),
        behavior_stability=round(beh_stability, 1),
        liquidity_risk=liquidity,
    )


def _scorecard_pd(f: dict[str, float]) -> float:
    """Logistic scorecard over the strongest default drivers."""
    logit = -3.2
    logit += 2.2 * min(f["existing_debt_ratio"], 1.0)  # leverage
    logit += 1.6 * min(f["income_volatility"], 1.5)  # unstable income
    logit -= 1.4 * f["salary_regularity"]  # regular salary protects
    logit -= 1.2 * min(max(f["savings_rate"], 0.0), 0.6)  # savings buffer
    logit -= 0.8 * min(f["avg_balance"] / max(f["avg_monthly_income"], 1.0), 3.0) / 3.0
    logit += 1.5 * f["bounce_indicator"]  # negative balance events
    logit += 0.9 * min(f["cash_withdrawal_ratio"], 1.0)  # cash-heavy behaviour
    logit += 0.5 * min(f["discretionary_ratio"], 1.0)  # lifestyle burn
    logit -= 0.4 * min(f["months_observed"] / 12.0, 1.0)  # longer history derisks
    return 1 / (1 + math.exp(-logit))


def _fraud_indicators(f: dict[str, float]) -> list[str]:
    flags = []
    if f["cash_deposit_ratio"] > 0.6:
        flags.append("HIGH_CASH_DEPOSITS: >60% of income arrives as cash — verify source")
    if f["salary_regularity"] > 0 and f["salary_regularity"] < 0.5 and f["avg_monthly_salary"] > 0:
        flags.append("IRREGULAR_SALARY: salary credits missing in some months")
    if f["bounce_indicator"] > 0:
        flags.append("NEGATIVE_BALANCE: account dipped below zero (possible bounce)")
    if f["income_volatility"] > 1.0:
        flags.append("VOLATILE_INFLOWS: erratic credit pattern — possible circular transactions")
    if f["avg_balance"] < 0.05 * max(f["avg_monthly_income"], 1) and f["avg_monthly_income"] > 0:
        flags.append("BALANCE_SWEEP: funds exit immediately after credit")
    return flags


def _financial_stability(f: dict[str, float]) -> float:
    score = 50.0
    score += 20 * max(0.0, 1 - f["income_volatility"])
    score += 15 * min(max(f["savings_rate"], 0.0), 0.5) / 0.5
    score += 10 * min(f["investment_rate"], 0.25) / 0.25
    score -= 25 * min(f["existing_debt_ratio"], 1.0)
    score += 5 * f["salary_regularity"]
    return min(max(score, 0.0), 100.0)


def _behavior_stability(f: dict[str, float]) -> float:
    score = 55.0
    score += 15 * f["salary_regularity"]
    score += 10 * max(0.0, min(f["balance_trend"], 1.0))
    score -= 20 * f["bounce_indicator"]
    score -= 10 * min(f["cash_withdrawal_ratio"], 1.0)
    score += 10 * min(f["months_observed"] / 12.0, 1.0)
    return min(max(score, 0.0), 100.0)


def _liquidity_risk(f: dict[str, float]) -> str:
    """Months of expenses covered by average balance."""
    burn = max(f["fixed_expense"] + f["variable_expense"], 1.0)
    cover = f["avg_balance"] / burn
    if cover >= 2.0:
        return "LOW"
    if cover >= 0.75:
        return "MEDIUM"
    return "HIGH"
