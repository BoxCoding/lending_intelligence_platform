class TestHealthEndpoint:
    def test_health_returns_service_info(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        body = resp.json()
        assert "service" in body
        assert "models" in body


class TestAAUpload:
    def test_upload_scores_customer_and_returns_profile(self, client, sample_aa_payload):
        resp = client.post("/aa/upload", json=sample_aa_payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["customer_id"] == "TEST0001"
        assert body["lead"]["tier"] in ("HOT", "WARM", "COLD")

    def test_upload_rejects_payload_with_no_transactions(self, client):
        payload = {
            "customer_id": "EMPTY1",
            "name": "Empty",
            "accounts": [{"account_id": "A1", "transactions": []}],
        }
        resp = client.post("/aa/upload", json=payload)
        assert resp.status_code == 422

    def test_upload_rejects_malformed_payload(self, client):
        resp = client.post("/aa/upload", json={"customer_id": "X"})
        assert resp.status_code == 422


class TestPredictEndpoints:
    def _seed(self, client, sample_aa_payload):
        client.post("/aa/upload", json=sample_aa_payload)

    def test_predict_income_requires_prior_upload(self, client):
        resp = client.post("/predict/income", json={"customer_id": "NEVER_UPLOADED"})
        assert resp.status_code == 404

    def test_predict_income_after_upload(self, client, sample_aa_payload):
        self._seed(client, sample_aa_payload)
        resp = client.post("/predict/income", json={"customer_id": "TEST0001"})
        assert resp.status_code == 200
        assert resp.json()["monthly_income"] > 0

    def test_predict_lead(self, client, sample_aa_payload):
        self._seed(client, sample_aa_payload)
        resp = client.post("/predict/lead", json={"customer_id": "TEST0001"})
        assert resp.status_code == 200
        assert resp.json()["tier"] in ("HOT", "WARM", "COLD")

    def test_predict_risk(self, client, sample_aa_payload):
        self._seed(client, sample_aa_payload)
        resp = client.post("/predict/risk", json={"customer_id": "TEST0001"})
        assert resp.status_code == 200
        assert resp.json()["risk_grade"] in "ABCDE"

    def test_explain_rejects_unknown_model_name(self, client, sample_aa_payload):
        self._seed(client, sample_aa_payload)
        resp = client.post("/predict/explain/bogus", json={"customer_id": "TEST0001"})
        assert resp.status_code == 422

    def test_explain_income(self, client, sample_aa_payload):
        self._seed(client, sample_aa_payload)
        resp = client.post("/predict/explain/income", json={"customer_id": "TEST0001"})
        assert resp.status_code == 200
        assert len(resp.json()["top_drivers"]) > 0


class TestInsightsEndpoints:
    def test_recommend_requires_scored_customer(self, client):
        resp = client.post("/recommend", json={"customer_id": "NEVER_UPLOADED"})
        assert resp.status_code == 404

    def test_recommend_after_upload(self, client, sample_aa_payload):
        client.post("/aa/upload", json=sample_aa_payload)
        resp = client.post("/recommend", json={"customer_id": "TEST0001"})
        assert resp.status_code == 200
        assert "offers" in resp.json()

    def test_chat_without_customer_context(self, client):
        resp = client.post("/chat", json={"message": "hello", "customer_id": None})
        assert resp.status_code == 200
        assert "reply" in resp.json()

    def test_chat_grounded_in_customer_profile(self, client, sample_aa_payload):
        client.post("/aa/upload", json=sample_aa_payload)
        resp = client.post(
            "/chat", json={"message": "Explain the income estimation", "customer_id": "TEST0001"}
        )
        assert resp.status_code == 200
        assert "income" in resp.json()["reply"].lower()

    def test_whatif_simulation(self, client, sample_aa_payload):
        client.post("/aa/upload", json=sample_aa_payload)
        resp = client.post(
            "/whatif",
            json={
                "customer_id": "TEST0001",
                "loan_amount": 300_000,
                "tenure_months": 48,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["verdict"] in ("AFFORDABLE", "STRETCHED", "NOT_AFFORDABLE")

    def test_whatif_requires_existing_customer(self, client):
        resp = client.post(
            "/whatif",
            json={"customer_id": "GHOST", "loan_amount": 100_000, "tenure_months": 24},
        )
        assert resp.status_code == 404


class TestDashboardEndpoints:
    def test_dashboard_empty_state(self, client):
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        assert resp.json()["kpis"]["total_leads"] == 0

    def test_dashboard_after_scoring_a_customer(self, client, sample_aa_payload):
        client.post("/aa/upload", json=sample_aa_payload)
        resp = client.get("/dashboard")
        body = resp.json()
        assert body["kpis"]["total_leads"] == 1
        assert len(body["leads"]) == 1

    def test_customer_detail_not_found(self, client):
        resp = client.get("/customer/GHOST")
        assert resp.status_code == 404

    def test_customer_detail_found(self, client, sample_aa_payload):
        client.post("/aa/upload", json=sample_aa_payload)
        resp = client.get("/customer/TEST0001")
        assert resp.status_code == 200
        assert resp.json()["customer_id"] == "TEST0001"
