from app.services.pipeline import get_profile


class TestProcessAAPayload:
    def test_returns_fully_populated_profile(self, scored_profile):
        assert scored_profile.customer_id == "TEST0001"
        assert scored_profile.income is not None
        assert scored_profile.repayment is not None
        assert scored_profile.intent is not None
        assert scored_profile.risk is not None
        assert scored_profile.lead is not None
        assert scored_profile.recommendation is not None

    def test_lead_tier_is_valid(self, scored_profile):
        assert scored_profile.lead.tier in ("HOT", "WARM", "COLD")

    def test_persists_to_store_and_is_retrievable(self, scored_profile):
        fetched = get_profile("TEST0001")
        assert fetched is not None
        assert fetched["customer_id"] == "TEST0001"
        assert fetched["lead"]["tier"] == scored_profile.lead.tier

    def test_unknown_customer_returns_none(self, scored_profile):
        assert get_profile("DOES_NOT_EXIST") is None

    def test_features_persisted_separately(self, scored_profile):
        from app.db.store import store

        features = store.get("features", "TEST0001")
        assert features is not None
        assert "avg_monthly_salary" in features
