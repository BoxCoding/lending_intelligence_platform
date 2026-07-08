"""Borrowing Intent Model.

Predicts the probability the customer applies for credit within 30/60/90
days. Uses an XGBoost classifier when the trained artifact exists;
otherwise a calibrated logistic rule over behavioural signals. Emits
human-readable reason codes for the sales team.
"""

import math

from app.core.logging import logger
from app.ml_registry import registry
from app.schemas.models import BorrowingIntent, IntentWindow
from app.services.feature_engineering import to_vector

# (feature, weight, threshold-normalizer, reason code shown to RM)
INTENT_SIGNALS = [
    ("loan_enquiry_count", 0.90, 2.0, "Recent loan/bureau enquiry fees detected"),
    ("property_payment_flag", 0.85, 1.0, "Property-related payments (token/registration) observed"),
    ("vehicle_payment_flag", 0.70, 1.0, "Vehicle booking/showroom payments observed"),
    ("wedding_expense_flag", 0.60, 1.0, "Wedding-related spends indicate upcoming expenses"),
    ("education_payment_flag", 0.45, 1.0, "Education fee payments observed"),
    ("high_value_purchase_count", 0.50, 3.0, "Multiple high-value purchases in recent months"),
    ("salary_growth_rate", 0.40, 0.15, "Salary is growing — upgrade purchases likely"),
    ("savings_growth_rate", 0.35, 0.20, "Savings build-up suggests planned big-ticket spend"),
    ("existing_debt_ratio", 0.30, 0.40, "Existing EMIs — possible consolidation/top-up need"),
]


def predict_intent(features: dict[str, float]) -> BorrowingIntent:
    ml_prob = None
    model = registry.get("intent")
    if model is not None:
        try:
            # model is a native xgboost.Booster (see ml/train.py): needs a
            # DMatrix input; predict() on a binary-objective booster returns
            # P(class=1) directly, no predict_proba()/column indexing needed.
            import xgboost as xgb

            ml_prob = float(model.predict(xgb.DMatrix([to_vector(features)]))[0])
        except Exception as exc:
            logger.warning("Intent model inference failed, using rules: %s", exc)

    rule_prob, signals, reasons = _rule_based_intent(features)
    p90 = 0.65 * ml_prob + 0.35 * rule_prob if ml_prob is not None else rule_prob

    # Shorter windows decay from the 90-day probability
    windows = [
        IntentWindow(days=30, probability=round(p90 * 0.45, 3)),
        IntentWindow(days=60, probability=round(p90 * 0.75, 3)),
        IntentWindow(days=90, probability=round(p90, 3)),
    ]
    return BorrowingIntent(
        intent_score=round(p90 * 100, 1),
        windows=windows,
        reason_codes=reasons[:5] or ["No strong borrowing signals detected"],
        signals=signals,
    )


def _rule_based_intent(features: dict[str, float]) -> tuple[float, dict, list[str]]:
    score = -1.6  # logit intercept: base ~17% intent
    signals: dict[str, float] = {}
    contributions: list[tuple[float, str]] = []
    for name, weight, normalizer, reason in INTENT_SIGNALS:
        raw = features.get(name, 0.0)
        contribution = weight * min(max(raw, 0.0) / normalizer, 1.0)
        if contribution > 0.05:
            signals[name] = round(contribution, 3)
            contributions.append((contribution, reason))
        score += contribution
    probability = 1 / (1 + math.exp(-score))
    reasons = [reason for _, reason in sorted(contributions, reverse=True)]
    return probability, signals, reasons
