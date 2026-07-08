import pytest
from app.schemas.models import IncomeEstimate
from app.services.repayment_engine import (
    PRODUCT_TERMS,
    assess_repayment,
    emi_for_principal,
    principal_for_emi,
)


class TestEmiMath:
    def test_emi_roundtrip_with_principal(self):
        principal = 500_000
        rate = 10.5
        months = 60
        emi = emi_for_principal(principal, rate, months)
        recovered = principal_for_emi(emi, rate, months)
        assert recovered == pytest.approx(principal, rel=1e-6)

    def test_zero_rate_is_simple_division(self):
        assert emi_for_principal(120_000, 0, 12) == pytest.approx(10_000)

    def test_longer_tenure_lowers_emi(self):
        short = emi_for_principal(500_000, 10, 24)
        long_ = emi_for_principal(500_000, 10, 60)
        assert long_ < short


class TestAssessRepayment:
    def _income(self, monthly=85_000, disposable=30_000):
        return IncomeEstimate(
            monthly_income=monthly,
            net_income=monthly - 15_000,
            disposable_income=disposable,
            fixed_expense=27_000,
            variable_expense=28_000,
            average_balance=100_000,
            cash_flow_stability=0.8,
            savings_rate=0.2,
            income_volatility=0.1,
            salary_regularity=1.0,
            income_sources=["SALARY"],
            confidence=0.9,
        )

    def test_eligible_emi_capped_by_income_minus_fixed_expense(self, sample_features):
        # Design choice: variable/discretionary spend is compressible and does not
        # cap the EMI; only fixed obligations do (see repayment_engine.py comment).
        income = self._income(disposable=5_000)
        result = assess_repayment(sample_features, income)
        hard_ceiling = max(income.monthly_income - sample_features["fixed_expense"], 0.0) * 0.9
        assert result.eligible_emi <= hard_ceiling + 1e-6

    def test_foir_reflects_existing_obligations(self, sample_features):
        income = self._income()
        result = assess_repayment(sample_features, income)
        assert result.foir == pytest.approx(
            sample_features["emi_outflow"] / income.monthly_income, rel=0.05
        )

    def test_loan_capacity_covers_all_products(self, sample_features):
        income = self._income()
        result = assess_repayment(sample_features, income)
        assert set(result.loan_capacity.keys()) == set(PRODUCT_TERMS.keys())
        assert all(v >= 0 for v in result.loan_capacity.values())

    def test_zero_income_gives_zero_capacity(self):
        income = self._income(monthly=0, disposable=0)
        features = dict.fromkeys(
            [
                "emi_outflow",
                "credit_card_spend",
                "fixed_expense",
                "variable_expense",
                "avg_balance",
            ],
            0.0,
        )
        result = assess_repayment(features, income)
        # monthly_income is floored at 1.0 internally to avoid division by zero,
        # so eligible_emi is a negligible fraction of a rupee, not exactly 0.
        assert result.eligible_emi < 1.0
        assert all(v == 0.0 for v in result.loan_capacity.values())

    def test_affordability_score_bounded(self, sample_features):
        income = self._income()
        result = assess_repayment(sample_features, income)
        assert 0.0 <= result.affordability_score <= 100.0
