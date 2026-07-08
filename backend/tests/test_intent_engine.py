import pytest
from app.services import intent_engine


@pytest.fixture(autouse=True)
def _no_ml_model(monkeypatch):
    monkeypatch.setattr(intent_engine.registry, "get", lambda name: None)


def _flat_features(**overrides):
    base = dict.fromkeys(
        [
            "loan_enquiry_count",
            "property_payment_flag",
            "vehicle_payment_flag",
            "wedding_expense_flag",
            "education_payment_flag",
            "high_value_purchase_count",
            "salary_growth_rate",
            "savings_growth_rate",
            "existing_debt_ratio",
        ],
        0.0,
    )
    base.update(overrides)
    return base


class TestPredictIntent:
    def test_windows_are_monotonically_increasing(self, sample_features):
        result = intent_engine.predict_intent(sample_features)
        days = [w.days for w in result.windows]
        probs = [w.probability for w in result.windows]
        assert days == sorted(days)
        assert probs == sorted(probs)

    def test_no_signals_gives_low_intent(self):
        result = intent_engine.predict_intent(_flat_features())
        assert result.intent_score < 30
        assert result.reason_codes == ["No strong borrowing signals detected"]

    def test_loan_enquiry_raises_intent_and_produces_reason(self):
        result = intent_engine.predict_intent(_flat_features(loan_enquiry_count=2.0))
        assert result.intent_score > 20
        assert "Recent loan/bureau enquiry fees detected" in result.reason_codes

    def test_property_payment_is_strong_signal(self):
        low = intent_engine.predict_intent(_flat_features())
        high = intent_engine.predict_intent(_flat_features(property_payment_flag=1.0))
        assert high.intent_score > low.intent_score

    def test_reasons_ranked_by_contribution_strength(self):
        result = intent_engine.predict_intent(
            _flat_features(property_payment_flag=1.0, education_payment_flag=1.0)
        )
        # property (weight 0.85) should outrank education (weight 0.45)
        assert result.reason_codes.index(
            "Property-related payments (token/registration) observed"
        ) < result.reason_codes.index("Education fee payments observed")

    def test_intent_score_bounded(self, sample_features):
        result = intent_engine.predict_intent(sample_features)
        assert 0.0 <= result.intent_score <= 100.0
