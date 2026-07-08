from app.schemas.models import (
    BorrowingIntent,
    IncomeEstimate,
    IntentWindow,
    LeadScore,
    RepaymentCapacity,
    RiskAssessment,
)
from app.services.recommendation_engine import PRODUCT_TERMS, recommend


def _income():
    return IncomeEstimate(
        monthly_income=150_000,
        net_income=130_000,
        disposable_income=60_000,
        fixed_expense=40_000,
        variable_expense=30_000,
        average_balance=300_000,
        cash_flow_stability=0.9,
        savings_rate=0.3,
        income_volatility=0.08,
        salary_regularity=1.0,
        income_sources=["SALARY"],
        confidence=0.95,
    )


def _repayment():
    capacity = dict.fromkeys(PRODUCT_TERMS, 2000000.0)
    return RepaymentCapacity(
        eligible_emi=40_000,
        debt_to_income=0.1,
        foir=0.2,
        surplus_cash=50_000,
        affordability_score=85.0,
        loan_capacity=capacity,
    )


def _intent():
    return BorrowingIntent(
        intent_score=70.0,
        windows=[
            IntentWindow(days=30, probability=0.3),
            IntentWindow(days=60, probability=0.5),
            IntentWindow(days=90, probability=0.7),
        ],
        reason_codes=["loan enquiry"],
        signals={},
    )


def _risk(grade="A"):
    return RiskAssessment(
        probability_of_default=0.02,
        risk_grade=grade,
        fraud_indicators=[],
        financial_stability=85.0,
        behavior_stability=80.0,
        liquidity_risk="LOW",
    )


def _lead(tier="HOT"):
    return LeadScore(
        score=80.0,
        tier=tier,
        conversion_probability=0.6,
        components={
            "intent": 70,
            "capacity": 85,
            "income_quality": 90,
            "risk": 95,
            "behaviour": 80,
        },
        explanation=["Lead classified HOT"],
    )


class TestRecommend:
    def test_returns_offers_for_strong_profile(self, sample_features):
        result = recommend(
            "CUST1", sample_features, _income(), _repayment(), _intent(), _risk(), _lead()
        )
        assert len(result.offers) > 0
        assert len(result.offers) <= 3

    def test_offers_priced_within_grade_spread(self, sample_features):
        result = recommend(
            "CUST1", sample_features, _income(), _repayment(), _intent(), _risk("A"), _lead()
        )
        for offer in result.offers:
            assert offer.interest_rate_max > offer.interest_rate_min
            assert offer.eligible_amount > 0
            assert offer.monthly_emi > 0

    def test_worse_grade_gets_higher_rate(self, sample_features):
        good = recommend(
            "CUST1", sample_features, _income(), _repayment(), _intent(), _risk("A"), _lead()
        )
        bad = recommend(
            "CUST1", sample_features, _income(), _repayment(), _intent(), _risk("D"), _lead()
        )
        assert bad.offers[0].interest_rate_min > good.offers[0].interest_rate_min

    def test_low_capacity_yields_no_offers(self, sample_features):
        poor_repayment = _repayment()
        poor_repayment.loan_capacity = dict.fromkeys(PRODUCT_TERMS, 10000.0)
        result = recommend(
            "CUST1", sample_features, _income(), poor_repayment, _intent(), _risk(), _lead("COLD")
        )
        assert result.offers == []
        assert "No pre-qualified offers" in result.summary

    def test_financial_health_score_bounded(self, sample_features):
        result = recommend(
            "CUST1", sample_features, _income(), _repayment(), _intent(), _risk(), _lead()
        )
        assert 0.0 <= result.financial_health_score <= 100.0

    def test_credit_limit_non_negative(self, sample_features):
        result = recommend(
            "CUST1", sample_features, _income(), _repayment(), _intent(), _risk(), _lead()
        )
        assert result.credit_limit >= 0

    def test_offers_have_reasons(self, sample_features):
        result = recommend(
            "CUST1", sample_features, _income(), _repayment(), _intent(), _risk(), _lead()
        )
        for offer in result.offers:
            assert len(offer.reasons) > 0
