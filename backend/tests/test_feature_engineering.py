from app.services.feature_engineering import FEATURE_NAMES, build_features, to_vector


class TestBuildFeatures:
    def test_returns_every_canonical_feature(self, sample_features):
        assert set(sample_features.keys()) == set(FEATURE_NAMES)

    def test_salary_regularity_is_full_for_regular_salary(self, sample_features):
        assert sample_features["salary_regularity"] == 1.0

    def test_avg_monthly_salary_matches_fixture(self, sample_features):
        assert sample_features["avg_monthly_salary"] == 85_000

    def test_emi_outflow_matches_fixture(self, sample_features):
        assert sample_features["emi_outflow"] == 15_000

    def test_property_payment_flag_set(self, sample_features):
        assert sample_features["property_payment_flag"] == 1.0

    def test_vehicle_payment_flag_unset(self, sample_features):
        assert sample_features["vehicle_payment_flag"] == 0.0

    def test_loan_enquiry_count_positive(self, sample_features):
        assert sample_features["loan_enquiry_count"] >= 1.0

    def test_months_observed(self, sample_features):
        assert sample_features["months_observed"] == 3.0

    def test_savings_rate_bounded(self, sample_features):
        assert -1.0 <= sample_features["savings_rate"] <= 1.0

    def test_empty_input_does_not_crash(self):
        empty_parsed = {
            "customer_id": "EMPTY",
            "transactions": [],
            "monthly": {},
            "monthly_meta": {},
            "employer": None,
            "months": [],
        }
        features = build_features(empty_parsed)
        assert set(features.keys()) == set(FEATURE_NAMES)
        assert features["avg_monthly_income"] == 0.0
        # months_observed is floored at 1 to avoid div-by-zero downstream
        assert features["months_observed"] == 1.0


class TestToVector:
    def test_length_matches_feature_names(self, sample_features):
        vector = to_vector(sample_features)
        assert len(vector) == len(FEATURE_NAMES)

    def test_order_matches_feature_names(self, sample_features):
        vector = to_vector(sample_features)
        for name, value in zip(FEATURE_NAMES, vector, strict=True):
            assert value == float(sample_features[name])

    def test_missing_key_defaults_to_zero(self):
        partial = {FEATURE_NAMES[0]: 5.0}
        vector = to_vector(partial)
        assert vector[0] == 5.0
        assert all(v == 0.0 for v in vector[1:])
