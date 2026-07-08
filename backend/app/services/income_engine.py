"""Income Estimation Engine.

Blends a deterministic estimate from categorized cash flows with an ML
regressor (LightGBM, trained in ml/train.py) when the artifact is
available. Produces a confidence score based on data depth and salary
regularity.
"""

from app.core.logging import logger
from app.ml_registry import registry
from app.schemas.models import IncomeEstimate
from app.services.feature_engineering import to_vector


def estimate_income(features: dict[str, float]) -> IncomeEstimate:
    rule_income = _rule_based_income(features)
    ml_income = None

    model = registry.get("income")
    if model is not None:
        try:
            ml_income = float(model.predict([to_vector(features)])[0])
        except Exception as exc:  # model artifact incompatible — degrade gracefully
            logger.warning("Income model inference failed, using rules: %s", exc)

    # Blend: ML model captures non-linear patterns, rules anchor to observed flows
    monthly_income = 0.6 * ml_income + 0.4 * rule_income if ml_income else rule_income
    monthly_income = max(monthly_income, 0.0)

    fixed = features["fixed_expense"]
    variable = features["variable_expense"]
    total_expense = fixed + variable
    net_income = monthly_income - features["emi_outflow"]
    disposable = max(monthly_income - total_expense, 0.0)

    confidence = _confidence(features, ml_income is not None)

    sources = []
    if features["avg_monthly_salary"] > 0:
        sources.append("SALARY")
    if features["cash_deposit_ratio"] > 0.1:
        sources.append("CASH_DEPOSITS")
    if features["avg_monthly_income"] > features["avg_monthly_salary"] * 1.15:
        sources.append("OTHER_CREDITS")

    return IncomeEstimate(
        monthly_income=round(monthly_income, 2),
        net_income=round(net_income, 2),
        disposable_income=round(disposable, 2),
        fixed_expense=round(fixed, 2),
        variable_expense=round(variable, 2),
        average_balance=round(features["avg_balance"], 2),
        cash_flow_stability=round(max(0.0, min(1.0, 1 - features["income_volatility"])), 3),
        savings_rate=round(features["savings_rate"], 3),
        income_volatility=round(features["income_volatility"], 3),
        salary_regularity=round(features["salary_regularity"], 3),
        income_sources=sources or ["UNCLASSIFIED"],
        confidence=round(confidence, 3),
    )


def _rule_based_income(features: dict[str, float]) -> float:
    """Deterministic income estimate anchored to observed credit flows."""
    salary = features["avg_monthly_salary"]
    total_income = features["avg_monthly_income"]
    if salary > 0:
        # Salaried: salary + haircut on non-salary credits (refunds, transfers noise)
        other = max(total_income - salary, 0.0)
        return salary + 0.5 * other
    # Self-employed / cash economy: haircut total credits by volatility
    volatility_haircut = min(features["income_volatility"] * 0.5, 0.35)
    return total_income * (1 - volatility_haircut)


def _confidence(features: dict[str, float], ml_used: bool) -> float:
    """Confidence grows with observation depth, regularity and low volatility."""
    depth = min(features["months_observed"] / 6.0, 1.0)  # 6+ months is ideal
    regularity = features["salary_regularity"]
    stability = max(0.0, 1 - features["income_volatility"])
    base = 0.45 * depth + 0.30 * regularity + 0.25 * stability
    return min(base + (0.05 if ml_used else 0.0), 0.99)
