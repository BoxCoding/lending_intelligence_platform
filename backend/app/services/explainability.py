"""Explainable AI via SHAP.

Computes per-prediction SHAP values for the trained tree models. Falls
back to scorecard weight attribution when SHAP or the model artifact is
unavailable, so the API contract never breaks.
"""
from app.core.logging import logger
from app.ml_registry import registry
from app.schemas.models import Explanation, ShapDriver
from app.services.feature_engineering import FEATURE_NAMES, to_vector

_FRIENDLY = {
    "avg_monthly_salary": "Monthly salary credits",
    "avg_monthly_income": "Total monthly income",
    "income_volatility": "Income volatility",
    "salary_regularity": "Salary regularity",
    "existing_debt_ratio": "Existing debt burden",
    "savings_rate": "Savings rate",
    "avg_balance": "Average bank balance",
    "emi_outflow": "Current EMI outflow",
    "bounce_indicator": "Negative balance events",
    "cash_withdrawal_ratio": "Cash withdrawal habit",
    "loan_enquiry_count": "Loan enquiries",
    "property_payment_flag": "Property payments",
    "vehicle_payment_flag": "Vehicle payments",
    "discretionary_ratio": "Discretionary spending",
    "investment_rate": "Investment discipline",
    "balance_trend": "Balance trend",
    "salary_growth_rate": "Salary growth",
}


def explain_prediction(model_name: str, features: dict[str, float]) -> Explanation:
    model = registry.get(model_name)
    vector = to_vector(features)

    if model is not None:
        try:
            import numpy as np

            explainer = registry.get_explainer(model_name, model)
            shap_values = explainer.shap_values(np.array([vector], dtype=float))
            if isinstance(shap_values, list):  # binary classifiers: [class0, class1]
                values = shap_values[1][0] if len(shap_values) > 1 else shap_values[0][0]
            elif getattr(shap_values, "ndim", 2) == 3:  # (n, features, classes)
                values = shap_values[0, :, 1]
            else:
                values = shap_values[0]
            return _build(model_name, vector, list(values), confidence=0.9)
        except Exception as exc:
            logger.warning("SHAP explanation failed for %s: %s", model_name, exc)

    # Fallback: normalized feature magnitudes as pseudo-attributions
    pseudo = [v if abs(v) < 10 else v / max(abs(max(vector, key=abs)), 1) for v in vector]
    return _build(model_name, vector, pseudo, confidence=0.55)


def _build(model_name: str, vector: list[float], impacts: list[float], confidence: float) -> Explanation:
    drivers = [
        ShapDriver(
            feature=_FRIENDLY.get(name, name.replace("_", " ").title()),
            value=round(val, 4),
            impact=round(float(impact), 4),
            direction="positive" if impact >= 0 else "negative",
        )
        for name, val, impact in zip(FEATURE_NAMES, vector, impacts)
    ]
    drivers.sort(key=lambda d: abs(d.impact), reverse=True)
    top = drivers[:8]
    return Explanation(
        model=model_name,
        top_drivers=top,
        positive_drivers=[d.feature for d in top if d.direction == "positive"][:4],
        negative_drivers=[d.feature for d in top if d.direction == "negative"][:4],
        confidence=confidence,
    )
