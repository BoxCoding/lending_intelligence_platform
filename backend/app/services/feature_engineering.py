"""Feature engineering: turns parsed AA aggregates into a flat ML feature vector.

The same feature builder is used at training time (ml/train.py) and at
inference time (API), which prevents training/serving skew.
"""

import statistics

from app.services.aa_parser import FIXED_EXPENSE_CATEGORIES, INCOME_CATEGORIES

# Canonical feature order used by every model. Do not reorder — retrain instead.
FEATURE_NAMES = [
    "avg_monthly_salary",
    "avg_monthly_income",
    "income_volatility",
    "salary_regularity",
    "avg_monthly_debits",
    "fixed_expense",
    "variable_expense",
    "avg_balance",
    "min_balance_ratio",
    "savings_rate",
    "emi_outflow",
    "existing_debt_ratio",
    "credit_card_spend",
    "cash_withdrawal_ratio",
    "cash_deposit_ratio",
    "upi_txn_share",
    "investment_rate",
    "insurance_spend",
    "utilities_spend",
    "shopping_spend",
    "discretionary_ratio",
    "rent_outflow",
    "salary_growth_rate",
    "balance_trend",
    "property_payment_flag",
    "vehicle_payment_flag",
    "education_payment_flag",
    "wedding_expense_flag",
    "loan_enquiry_count",
    "high_value_purchase_count",
    "savings_growth_rate",
    "months_observed",
    "txn_count_monthly",
    "bounce_indicator",
]


def _monthly_series(monthly: dict, months: list[str], category: str) -> list[float]:
    return [monthly.get(m, {}).get(category, 0.0) for m in months]


def _safe_mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _cv(values: list[float]) -> float:
    """Coefficient of variation — volatility measure, 0 when mean is 0."""
    mean = _safe_mean(values)
    if mean <= 0 or len(values) < 2:
        return 0.0
    return statistics.pstdev(values) / mean


def _trend(values: list[float]) -> float:
    """Normalized linear trend: slope / mean, clipped to [-1, 1]."""
    n = len(values)
    mean = _safe_mean(values)
    if n < 2 or mean <= 0:
        return 0.0
    x_mean = (n - 1) / 2
    num = sum((i - x_mean) * (v - mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    slope = num / den if den else 0.0
    return max(-1.0, min(1.0, slope / mean))


def build_features(parsed: dict) -> dict[str, float]:
    """Compute the canonical feature vector from parse_aa_payload output."""
    monthly = parsed["monthly"]
    meta = parsed["monthly_meta"]
    months = parsed["months"]
    n_months = max(len(months), 1)

    salary = _monthly_series(monthly, months, "SALARY")
    income_total = [sum(monthly.get(m, {}).get(c, 0.0) for c in INCOME_CATEGORIES) for m in months]
    debits = [meta.get(m, {}).get("debits", 0.0) for m in months]
    balances = [meta.get(m, {}).get("avg_balance", 0.0) for m in months]
    min_balances = [meta.get(m, {}).get("min_balance", 0.0) for m in months]
    txn_counts = [meta.get(m, {}).get("txn_count", 0) for m in months]

    fixed = [sum(monthly.get(m, {}).get(c, 0.0) for c in FIXED_EXPENSE_CATEGORIES) for m in months]
    avg_income = _safe_mean(income_total)
    avg_debits = _safe_mean(debits)
    avg_fixed = _safe_mean(fixed)
    avg_balance = _safe_mean(balances)

    emi = _safe_mean(_monthly_series(monthly, months, "EMI"))
    cc = _safe_mean(_monthly_series(monthly, months, "CREDIT_CARD"))
    cash_wdl = _safe_mean(_monthly_series(monthly, months, "CASH_WITHDRAWAL"))
    cash_dep = _safe_mean(_monthly_series(monthly, months, "CASH_DEPOSIT"))
    invest = _safe_mean(_monthly_series(monthly, months, "INVESTMENT"))
    insurance = _safe_mean(_monthly_series(monthly, months, "INSURANCE"))
    utilities = _safe_mean(_monthly_series(monthly, months, "UTILITIES"))
    shopping = _safe_mean(_monthly_series(monthly, months, "SHOPPING"))
    food = _safe_mean(_monthly_series(monthly, months, "FOOD_DINING"))
    travel = _safe_mean(_monthly_series(monthly, months, "TRAVEL_FUEL"))
    rent = _safe_mean(_monthly_series(monthly, months, "RENT"))

    salary_months = sum(1 for s in salary if s > 0)
    variable_expense = max(avg_debits - avg_fixed - emi, 0.0)
    discretionary = shopping + food + travel

    high_value_purchases = sum(
        1
        for t in parsed["transactions"]
        if t["type"] == "DEBIT"
        and t["amount"] > max(avg_income * 0.4, 50_000)
        and t["category"]
        in {
            "SHOPPING",
            "OTHER_SPEND",
            "TRAVEL_FUEL",
            "VEHICLE_PAYMENT",
            "PROPERTY_PAYMENT",
            "WEDDING",
        }
    )
    loan_enquiries = sum(1 for t in parsed["transactions"] if t["category"] == "LOAN_ENQUIRY")
    upi_txn_count = sum(1 for t in parsed["transactions"] if t["mode"] == "UPI")

    features = {
        "avg_monthly_salary": _safe_mean(salary),
        "avg_monthly_income": avg_income,
        "income_volatility": _cv(income_total),
        "salary_regularity": salary_months / n_months,
        "avg_monthly_debits": avg_debits,
        "fixed_expense": avg_fixed + emi,
        "variable_expense": variable_expense,
        "avg_balance": avg_balance,
        "min_balance_ratio": (_safe_mean(min_balances) / avg_balance) if avg_balance > 0 else 0.0,
        "savings_rate": max((avg_income - avg_debits) / avg_income, -1.0)
        if avg_income > 0
        else 0.0,
        "emi_outflow": emi,
        "existing_debt_ratio": (emi + cc) / avg_income if avg_income > 0 else 0.0,
        "credit_card_spend": cc,
        "cash_withdrawal_ratio": cash_wdl / avg_income if avg_income > 0 else 0.0,
        "cash_deposit_ratio": cash_dep / avg_income if avg_income > 0 else 0.0,
        "upi_txn_share": upi_txn_count / max(sum(txn_counts), 1),
        "investment_rate": invest / avg_income if avg_income > 0 else 0.0,
        "insurance_spend": insurance,
        "utilities_spend": utilities,
        "shopping_spend": shopping,
        "discretionary_ratio": discretionary / avg_income if avg_income > 0 else 0.0,
        "rent_outflow": rent,
        "salary_growth_rate": _trend(salary),
        "balance_trend": _trend(balances),
        "property_payment_flag": 1.0
        if any(_monthly_series(monthly, months, "PROPERTY_PAYMENT"))
        else 0.0,
        "vehicle_payment_flag": 1.0
        if any(_monthly_series(monthly, months, "VEHICLE_PAYMENT"))
        else 0.0,
        "education_payment_flag": 1.0
        if any(_monthly_series(monthly, months, "EDUCATION"))
        else 0.0,
        "wedding_expense_flag": 1.0 if any(_monthly_series(monthly, months, "WEDDING")) else 0.0,
        "loan_enquiry_count": float(loan_enquiries),
        "high_value_purchase_count": float(high_value_purchases),
        "savings_growth_rate": _trend(
            [max(i - d, 0.0) for i, d in zip(income_total, debits, strict=True)]
        ),
        "months_observed": float(n_months),
        "txn_count_monthly": _safe_mean([float(c) for c in txn_counts]),
        "bounce_indicator": 1.0 if any(b < 0 for b in min_balances) else 0.0,
    }
    return features


def to_vector(features: dict[str, float]) -> list[float]:
    """Order the feature dict into the canonical vector for model input."""
    return [float(features.get(name, 0.0)) for name in FEATURE_NAMES]
