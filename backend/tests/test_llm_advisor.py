from app.services import llm_advisor


class TestOfflineChat:
    def test_no_profile_prompts_for_customer(self):
        result = llm_advisor.chat("hello", None, [])
        assert "select a customer" in result["reply"].lower()

    def _profile(self):
        return {
            "name": "Arjun Mehta",
            "income": {
                "monthly_income": 150_000,
                "fixed_expense": 40_000,
                "variable_expense": 30_000,
                "disposable_income": 60_000,
                "salary_regularity": 1.0,
                "income_volatility": 0.1,
            },
            "repayment": {
                "eligible_emi": 30_000,
                "foir": 0.2,
                "debt_to_income": 0.1,
                "surplus_cash": 40_000,
                "affordability_score": 80,
            },
            "risk": {
                "probability_of_default": 0.02,
                "risk_grade": "A",
                "financial_stability": 85,
                "behavior_stability": 80,
                "liquidity_risk": "LOW",
                "fraud_indicators": [],
            },
            "lead": {
                "score": 82.0,
                "tier": "HOT",
                "conversion_probability": 0.6,
                "components": {"intent": 70, "capacity": 80},
            },
            "intent": {"intent_score": 70, "reason_codes": ["loan enquiry"]},
            "recommendation": {
                "offers": [
                    {
                        "product": "Personal Loan",
                        "eligible_amount": 800_000,
                        "interest_rate_min": 12.5,
                        "interest_rate_max": 13.5,
                        "tenure_months": 48,
                        "monthly_emi": 22_000,
                        "reasons": ["Active loan enquiries"],
                    }
                ],
                "summary": "HOT lead, best fit Personal Loan.",
            },
        }

    def test_income_question_routes_to_income_branch(self):
        result = llm_advisor.chat("What is their income?", self._profile(), [])
        assert "Income analysis" in result["reply"]
        assert "1,50,000" in result["reply"] or "150,000" in result["reply"]

    def test_repayment_question_routes_to_capacity_branch(self):
        result = llm_advisor.chat("What is the EMI capacity?", self._profile(), [])
        assert "Repayment capacity" in result["reply"]

    def test_risk_question_routes_to_risk_branch(self):
        result = llm_advisor.chat("Any default risk or fraud?", self._profile(), [])
        assert "Risk assessment" in result["reply"]

    def test_lead_question_routes_to_lead_branch(self):
        result = llm_advisor.chat("Why is this lead scored so high?", self._profile(), [])
        assert "Lead score" in result["reply"]

    def test_recommend_question_routes_to_product_branch(self):
        result = llm_advisor.chat("What loan products should we recommend?", self._profile(), [])
        assert "Personal Loan" in result["reply"]

    def test_generic_question_falls_back_to_summary(self):
        result = llm_advisor.chat("Tell me something", self._profile(), [])
        assert "Summary for Arjun Mehta" in result["reply"]

    def test_suggestions_present_with_profile(self):
        result = llm_advisor.chat("hi", self._profile(), [])
        assert len(result["suggestions"]) > 0

    def test_no_gemini_key_uses_offline_path(self, monkeypatch):
        from app.core.config import get_settings

        get_settings.cache_clear()
        result = llm_advisor.chat("hello", None, [])
        assert result["sources"] == ["offline_advisor"]
