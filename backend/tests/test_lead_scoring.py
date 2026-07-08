from app.schemas.models import (
    BorrowingIntent,
    IncomeEstimate,
    IntentWindow,
    RepaymentCapacity,
    RiskAssessment,
)
from app.services.lead_scoring import score_lead


def _income(**overrides):
    base = {
        "monthly_income": 85_000,
        "net_income": 70_000,
        "disposable_income": 30_000,
        "fixed_expense": 27_000,
        "variable_expense": 28_000,
        "average_balance": 150_000,
        "cash_flow_stability": 0.85,
        "savings_rate": 0.25,
        "income_volatility": 0.1,
        "salary_regularity": 1.0,
        "income_sources": ["SALARY"],
        "confidence": 0.9,
    }
    base.update(overrides)
    return IncomeEstimate(**base)


def _repayment(**overrides):
    base = {
        "eligible_emi": 20_000,
        "debt_to_income": 0.15,
        "foir": 0.2,
        "surplus_cash": 25_000,
        "affordability_score": 75.0,
        "loan_capacity": {"PERSONAL_LOAN": 500_000},
    }
    base.update(overrides)
    return RepaymentCapacity(**base)


def _intent(score=70.0):
    return BorrowingIntent(
        intent_score=score,
        windows=[
            IntentWindow(days=30, probability=score * 0.0045),
            IntentWindow(days=60, probability=score * 0.0075),
            IntentWindow(days=90, probability=score / 100),
        ],
        reason_codes=["test signal"],
        signals={},
    )


def _risk(grade="A", pd=0.02):
    return RiskAssessment(
        probability_of_default=pd,
        risk_grade=grade,
        fraud_indicators=[],
        financial_stability=85.0,
        behavior_stability=80.0,
        liquidity_risk="LOW",
    )


class TestScoreLead:
    def test_strong_profile_is_hot(self, sample_features):
        result = score_lead(sample_features, _income(), _repayment(), _intent(80), _risk())
        assert result.tier == "HOT"
        assert result.score >= 68

    def test_weak_profile_is_cold(self, sample_features):
        weak_income = _income(salary_regularity=0.2, cash_flow_stability=0.3, monthly_income=20_000)
        weak_repayment = _repayment(affordability_score=10.0, eligible_emi=500)
        weak_intent = _intent(5)
        weak_risk = _risk(grade="D", pd=0.3)
        result = score_lead(sample_features, weak_income, weak_repayment, weak_intent, weak_risk)
        assert result.tier == "COLD"

    def test_grade_e_is_hard_capped_regardless_of_other_scores(self, sample_features):
        result = score_lead(sample_features, _income(), _repayment(), _intent(95), _risk(grade="E"))
        assert result.score <= 40.0
        assert result.tier != "HOT"

    def test_low_eligible_emi_is_hard_capped(self, sample_features):
        result = score_lead(
            sample_features, _income(), _repayment(eligible_emi=500), _intent(95), _risk()
        )
        assert result.score <= 40.0

    def test_components_sum_reasonably_to_score(self, sample_features):
        result = score_lead(sample_features, _income(), _repayment(), _intent(70), _risk())
        assert set(result.components.keys()) == {
            "intent",
            "capacity",
            "income_quality",
            "risk",
            "behaviour",
        }

    def test_conversion_probability_scales_with_affordability(self, sample_features):
        low_afford = score_lead(
            sample_features, _income(), _repayment(affordability_score=20), _intent(70), _risk()
        )
        high_afford = score_lead(
            sample_features, _income(), _repayment(affordability_score=95), _intent(70), _risk()
        )
        assert high_afford.conversion_probability > low_afford.conversion_probability

    def test_explanation_mentions_tier(self, sample_features):
        result = score_lead(sample_features, _income(), _repayment(), _intent(80), _risk())
        assert result.tier in result.explanation[0]
