import pytest
from app.services import income_engine


@pytest.fixture(autouse=True)
def _no_ml_model(monkeypatch):
    """Pin these tests to the deterministic rule-based path."""
    monkeypatch.setattr(income_engine.registry, "get", lambda name: None)


class TestEstimateIncome:
    def test_salaried_income_anchors_to_salary(self, sample_features):
        result = income_engine.estimate_income(sample_features)
        # salary-dominant profile: monthly_income should be close to the salary
        assert result.monthly_income == pytest.approx(85_000, rel=0.2)

    def test_income_sources_include_salary(self, sample_features):
        result = income_engine.estimate_income(sample_features)
        assert "SALARY" in result.income_sources

    def test_disposable_income_non_negative_for_healthy_profile(self, sample_features):
        result = income_engine.estimate_income(sample_features)
        assert result.disposable_income >= 0

    def test_confidence_between_zero_and_one(self, sample_features):
        result = income_engine.estimate_income(sample_features)
        assert 0.0 <= result.confidence <= 0.99

    def test_zero_income_profile_does_not_crash(self):
        zero_features = dict.fromkeys(
            [
                "avg_monthly_salary",
                "avg_monthly_income",
                "income_volatility",
                "salary_regularity",
                "avg_monthly_debits",
                "fixed_expense",
                "variable_expense",
                "avg_balance",
                "cash_deposit_ratio",
                "months_observed",
                "emi_outflow",
                "savings_rate",
            ],
            0.0,
        )
        result = income_engine.estimate_income(zero_features)
        assert result.monthly_income == 0.0
        assert result.income_sources == ["UNCLASSIFIED"]

    def test_self_employed_profile_haircuts_volatile_income(self):
        features = {
            "avg_monthly_salary": 0.0,
            "avg_monthly_income": 100_000.0,
            "income_volatility": 1.0,
            "salary_regularity": 0.0,
            "avg_monthly_debits": 60_000.0,
            "fixed_expense": 20_000.0,
            "variable_expense": 40_000.0,
            "avg_balance": 50_000.0,
            "cash_deposit_ratio": 0.4,
            "months_observed": 6.0,
            "emi_outflow": 0.0,
            "savings_rate": 0.1,
        }
        result = income_engine.estimate_income(features)
        assert result.monthly_income < features["avg_monthly_income"]
        assert result.income_sources  # sanity: engine produced some source list, did not crash


class TestIncomeEngineBlendsMlWhenAvailable:
    def test_blend_uses_both_ml_and_rule_signal(self, sample_features, monkeypatch):
        class FakeModel:
            def predict(self, X):
                return [200_000.0]

        monkeypatch.setattr(income_engine.registry, "get", lambda name: FakeModel())
        result = income_engine.estimate_income(sample_features)
        # blended = 0.6*ML + 0.4*rule; ML (200k) pulls the estimate up vs rule-only (~85k)
        rule_only = income_engine._rule_based_income(sample_features)
        assert result.monthly_income > rule_only

    def test_ml_failure_falls_back_gracefully(self, sample_features, monkeypatch):
        class BrokenModel:
            def predict(self, X):
                raise RuntimeError("model incompatible")

        monkeypatch.setattr(income_engine.registry, "get", lambda name: BrokenModel())
        result = income_engine.estimate_income(sample_features)
        assert result.monthly_income >= 0
