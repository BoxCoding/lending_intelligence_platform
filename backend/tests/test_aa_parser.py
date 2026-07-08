from app.schemas.models import AAPayload
from app.services.aa_parser import categorize, parse_aa_payload


class TestCategorize:
    def test_salary_credit(self):
        assert categorize("SALARY INFOSYS LTD SAL CR", "CREDIT") == "SALARY"

    def test_emi_debit(self):
        assert categorize("ACH D- BAJAJ FIN EMI", "DEBIT") == "EMI"

    def test_rent_debit(self):
        assert categorize("UPI/DR/RENT TO LANDLORD", "DEBIT") == "RENT"

    def test_cash_withdrawal(self):
        assert categorize("ATM CASH WDL", "DEBIT") == "CASH_WITHDRAWAL"

    def test_property_payment(self):
        assert categorize("NEFT BUILDER TOKEN ADVANCE PROPERTY", "DEBIT") == "PROPERTY_PAYMENT"

    def test_loan_enquiry(self):
        assert categorize("CIBIL CREDIT REPORT FEE", "DEBIT") == "LOAN_ENQUIRY"

    def test_upi_income_vs_spend(self):
        assert categorize("UPI/CR/PAYMENT RECD", "CREDIT") == "UPI_INCOME"
        assert categorize("UPI/DR/GROCERY STORE", "DEBIT") == "UPI_SPEND"

    def test_unrecognised_narration_falls_back(self):
        assert categorize("XYZQZQZQ RANDOM TEXT", "CREDIT") == "OTHER_INCOME"
        assert categorize("XYZQZQZQ RANDOM TEXT", "DEBIT") == "OTHER_SPEND"

    def test_case_insensitive(self):
        assert categorize("salary infosys sal cr", "CREDIT") == "SALARY"


class TestParseAAPayload:
    def test_returns_expected_shape(self, sample_aa_payload):
        parsed = parse_aa_payload(AAPayload(**sample_aa_payload))
        assert parsed["customer_id"] == "TEST0001"
        assert set(parsed["months"]) == {"2026-04", "2026-05", "2026-06"}
        assert len(parsed["transactions"]) == len(sample_aa_payload["accounts"][0]["transactions"])

    def test_employer_extracted_from_salary(self, sample_aa_payload):
        parsed = parse_aa_payload(AAPayload(**sample_aa_payload))
        assert parsed["employer"] is not None
        assert "Infosys" in parsed["employer"]

    def test_monthly_aggregates_bucket_salary(self, sample_aa_payload):
        parsed = parse_aa_payload(AAPayload(**sample_aa_payload))
        assert parsed["monthly"]["2026-04"]["SALARY"] == 85_000

    def test_monthly_meta_tracks_credits_and_debits(self, sample_aa_payload):
        parsed = parse_aa_payload(AAPayload(**sample_aa_payload))
        meta = parsed["monthly_meta"]["2026-04"]
        assert meta["credits"] > 0
        assert meta["debits"] > 0
        assert meta["txn_count"] > 0

    def test_bad_date_is_skipped_not_raised(self):
        payload = AAPayload(
            customer_id="BADDATE",
            name="X",
            accounts=[
                {
                    "account_id": "A1",
                    "transactions": [
                        {
                            "txn_id": "T1",
                            "date": "not-a-date",
                            "amount": 100,
                            "type": "CREDIT",
                            "narration": "SALARY",
                        }
                    ],
                }
            ],
        )
        parsed = parse_aa_payload(payload)
        assert parsed["transactions"] == []
        assert parsed["months"] == []

    def test_property_and_loan_enquiry_categories_present(self, sample_aa_payload):
        parsed = parse_aa_payload(AAPayload(**sample_aa_payload))
        categories = {t["category"] for t in parsed["transactions"]}
        assert "PROPERTY_PAYMENT" in categories
        assert "LOAN_ENQUIRY" in categories
