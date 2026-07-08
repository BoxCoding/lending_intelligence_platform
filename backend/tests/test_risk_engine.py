import pytest
from app.services import risk_engine


@pytest.fixture(autouse=True)
def _no_ml_model(monkeypatch):
    monkeypatch.setattr(risk_engine.registry, "get", lambda name: None)


def _healthy_features(**overrides):
    base = {
        "existing_debt_ratio": 0.1,
        "income_volatility": 0.1,
        "salary_regularity": 1.0,
        "savings_rate": 0.3,
        "avg_balance": 200_000,
        "avg_monthly_income": 85_000,
        "bounce_indicator": 0.0,
        "cash_withdrawal_ratio": 0.05,
        "discretionary_ratio": 0.1,
        "months_observed": 12.0,
        "cash_deposit_ratio": 0.0,
        "avg_monthly_salary": 85_000,
        "investment_rate": 0.1,
        "fixed_expense": 30_000,
        "variable_expense": 20_000,
        "balance_trend": 0.1,
    }
    base.update(overrides)
    return base


class TestAssessRisk:
    def test_healthy_profile_gets_low_risk_grade(self):
        result = risk_engine.assess_risk(_healthy_features())
        assert result.risk_grade in ("A", "B")
        assert result.probability_of_default < 0.13

    def test_risky_profile_gets_worse_grade(self):
        risky = _healthy_features(
            existing_debt_ratio=0.9,
            income_volatility=1.4,
            salary_regularity=0.0,
            savings_rate=0.0,
            bounce_indicator=1.0,
            cash_withdrawal_ratio=0.8,
        )
        result = risk_engine.assess_risk(risky)
        assert result.risk_grade in ("D", "E")

    def test_grade_bands_are_ordered(self):
        healthy = risk_engine.assess_risk(_healthy_features())
        risky = risk_engine.assess_risk(_healthy_features(existing_debt_ratio=0.9))
        assert healthy.probability_of_default < risky.probability_of_default

    def test_bounce_indicator_triggers_fraud_flag(self):
        result = risk_engine.assess_risk(_healthy_features(bounce_indicator=1.0))
        assert any("NEGATIVE_BALANCE" in f for f in result.fraud_indicators)

    def test_high_cash_deposit_triggers_fraud_flag(self):
        result = risk_engine.assess_risk(_healthy_features(cash_deposit_ratio=0.7))
        assert any("HIGH_CASH_DEPOSITS" in f for f in result.fraud_indicators)

    def test_no_fraud_indicators_for_clean_profile(self):
        result = risk_engine.assess_risk(_healthy_features())
        assert result.fraud_indicators == []

    def test_stability_scores_bounded(self, sample_features):
        result = risk_engine.assess_risk(sample_features)
        assert 0.0 <= result.financial_stability <= 100.0
        assert 0.0 <= result.behavior_stability <= 100.0

    def test_liquidity_risk_levels(self):
        low = risk_engine.assess_risk(_healthy_features(avg_balance=500_000))
        high = risk_engine.assess_risk(_healthy_features(avg_balance=1_000))
        assert low.liquidity_risk == "LOW"
        assert high.liquidity_risk == "HIGH"
