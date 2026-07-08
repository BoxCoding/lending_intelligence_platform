import pytest
from app.services import explainability
from app.services.feature_engineering import FEATURE_NAMES


class TestExplainPrediction:
    def test_fallback_path_when_no_model(self, sample_features, monkeypatch):
        monkeypatch.setattr(explainability.registry, "get", lambda name: None)
        result = explainability.explain_prediction("risk", sample_features)
        assert result.model == "risk"
        assert len(result.top_drivers) <= 8
        assert result.confidence == pytest.approx(0.55)

    def test_drivers_sorted_by_absolute_impact(self, sample_features, monkeypatch):
        monkeypatch.setattr(explainability.registry, "get", lambda name: None)
        result = explainability.explain_prediction("income", sample_features)
        impacts = [abs(d.impact) for d in result.top_drivers]
        assert impacts == sorted(impacts, reverse=True)

    def test_direction_matches_impact_sign(self, sample_features, monkeypatch):
        monkeypatch.setattr(explainability.registry, "get", lambda name: None)
        result = explainability.explain_prediction("risk", sample_features)
        for driver in result.top_drivers:
            expected = "positive" if driver.impact >= 0 else "negative"
            assert driver.direction == expected

    def test_real_model_path_does_not_crash(self, sample_features):
        # Uses whatever artifact ships in ml/models/ (committed to the repo)
        result = explainability.explain_prediction("risk", sample_features)
        assert result.model == "risk"
        assert len(result.top_drivers) > 0
        assert result.positive_drivers is not None or result.negative_drivers is not None

    def test_positive_and_negative_lists_are_subsets_of_top_drivers(self, sample_features):
        result = explainability.explain_prediction("intent", sample_features)
        top_features = {d.feature for d in result.top_drivers}
        assert set(result.positive_drivers).issubset(top_features)
        assert set(result.negative_drivers).issubset(top_features)

    def test_friendly_names_used_when_available(self, sample_features, monkeypatch):
        monkeypatch.setattr(explainability.registry, "get", lambda name: None)
        result = explainability.explain_prediction("risk", sample_features)
        friendly_values = set(explainability._FRIENDLY.values())
        # at least one driver should use a mapped friendly name
        assert any(d.feature in friendly_values for d in result.top_drivers)

    def test_all_feature_names_covered_by_vector(self, sample_features, monkeypatch):
        monkeypatch.setattr(explainability.registry, "get", lambda name: None)
        result = explainability.explain_prediction("risk", sample_features)
        assert len(result.top_drivers) == min(8, len(FEATURE_NAMES))
