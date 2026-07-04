"""Repayment Capacity Model.

Computes FOIR, DTI, eligible EMI headroom and translates it into a
maximum loan capacity per product using standard EMI mathematics.
"""
from app.core.config import get_settings
from app.schemas.models import IncomeEstimate, RepaymentCapacity

# product -> (annual rate % used for capacity calc, max tenure months, income multiple cap)
PRODUCT_TERMS = {
    "PERSONAL_LOAN": (12.5, 60, 20),
    "AUTO_LOAN": (9.5, 84, 30),
    "HOME_LOAN": (8.6, 240, 70),
    "MORTGAGE_LOAN": (9.8, 180, 55),
}


def emi_for_principal(principal: float, annual_rate: float, months: int) -> float:
    r = annual_rate / 12 / 100
    if r == 0:
        return principal / months
    factor = (1 + r) ** months
    return principal * r * factor / (factor - 1)


def principal_for_emi(emi: float, annual_rate: float, months: int) -> float:
    r = annual_rate / 12 / 100
    if r == 0:
        return emi * months
    factor = (1 + r) ** months
    return emi * (factor - 1) / (r * factor)


def assess_repayment(features: dict[str, float], income: IncomeEstimate) -> RepaymentCapacity:
    settings = get_settings()
    monthly_income = max(income.monthly_income, 1.0)

    existing_obligations = features["emi_outflow"] + 0.05 * features["credit_card_spend"]
    foir_current = existing_obligations / monthly_income
    dti = features["emi_outflow"] / monthly_income

    # EMI headroom under the FOIR policy cap, floored at 0.
    # Variable/discretionary spend is compressible, so it does not cap the EMI;
    # only fixed obligations do (standard FOIR treatment).
    eligible_emi = max(settings.max_foir * monthly_income - existing_obligations, 0.0)
    hard_ceiling = max(monthly_income - features["fixed_expense"], 0.0) * 0.9
    eligible_emi = min(eligible_emi, hard_ceiling)

    surplus = max(monthly_income - features["fixed_expense"] - features["variable_expense"], 0.0)

    loan_capacity = {}
    for product, (rate, tenure, multiple) in PRODUCT_TERMS.items():
        by_emi = principal_for_emi(eligible_emi, rate, tenure)
        by_multiple = monthly_income * multiple
        loan_capacity[product] = round(min(by_emi, by_multiple), -3)  # round to 1000s

    affordability = _affordability_score(foir_current, income, features)

    return RepaymentCapacity(
        eligible_emi=round(eligible_emi, 2),
        debt_to_income=round(dti, 3),
        foir=round(foir_current, 3),
        surplus_cash=round(surplus, 2),
        affordability_score=round(affordability, 1),
        loan_capacity=loan_capacity,
    )


def _affordability_score(foir: float, income: IncomeEstimate, features: dict) -> float:
    """0-100 score: how comfortably can this customer absorb a new EMI."""
    foir_component = max(0.0, 1 - foir / 0.55) * 40          # low obligations
    savings_component = max(0.0, min(income.savings_rate, 0.5)) / 0.5 * 25
    stability_component = income.cash_flow_stability * 20
    balance_component = min(features["avg_balance"] / max(income.monthly_income, 1) / 2, 1.0) * 15
    return min(foir_component + savings_component + stability_component + balance_component, 100.0)
