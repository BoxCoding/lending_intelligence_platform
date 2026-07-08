"""Shared pytest fixtures.

Forces the store to a throwaway local-JSON directory (never the live
Firestore project) by clearing Firestore env vars *before* any `app.*`
module is imported — `app.db.store` picks its backend at import time.
"""

import os
import tempfile

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = ""
os.environ["FIREBASE_CREDENTIALS_JSON"] = ""
os.environ["FIRESTORE_PROJECT_ID"] = ""
os.environ["LOCAL_STORE_PATH"] = tempfile.mkdtemp(prefix="lendiq-test-store-")

import pytest  # noqa: E402


@pytest.fixture
def sample_aa_payload() -> dict:
    """Three months of realistic salaried-customer transactions covering
    every major category the parser recognises."""
    months = ["2026-04", "2026-05", "2026-06"]
    transactions = []
    txn_id = 0

    def add(date: str, amount: float, ttype: str, mode: str, narration: str, balance: float):
        nonlocal txn_id
        txn_id += 1
        transactions.append(
            {
                "txn_id": f"T{txn_id:04d}",
                "date": date,
                "amount": amount,
                "type": ttype,
                "mode": mode,
                "narration": narration,
                "balance": balance,
            }
        )

    balance = 150_000.0
    for m in months:
        balance += 85_000
        add(f"{m}-01", 85_000, "CREDIT", "NEFT", "SALARY INFOSYS LTD SAL CR", balance)
        balance -= 15_000
        add(f"{m}-03", 15_000, "DEBIT", "ECS", "ACH D- BAJAJ FIN EMI", balance)
        balance -= 12_000
        add(f"{m}-05", 12_000, "DEBIT", "UPI", "UPI/DR/RENT TO LANDLORD", balance)
        balance -= 5_000
        add(f"{m}-07", 5_000, "DEBIT", "ECS", "SIP ZERODHA MUTUAL FUND", balance)
        balance -= 3_500
        add(f"{m}-10", 3_500, "DEBIT", "UPI", "UPI/DR/SWIGGY ORDER", balance)
        balance += 2_000
        add(f"{m}-12", 2_000, "CREDIT", "CASH", "CASH DEP CDM BRANCH", balance)
        balance -= 2_500
        add(f"{m}-15", 2_500, "DEBIT", "ATM", "ATM CASH WDL", balance)

    # Life-event signals in the most recent month only
    balance -= 500
    add("2026-06-20", 500, "DEBIT", "UPI", "CIBIL CREDIT REPORT FEE", balance)
    balance -= 250_000
    add(
        "2026-06-22",
        250_000,
        "DEBIT",
        "NEFT",
        "NEFT PRESTIGE BUILDER TOKEN ADVANCE PROPERTY",
        balance,
    )

    return {
        "customer_id": "TEST0001",
        "name": "Test Customer",
        "pan": "ABCDE1234F",
        "consent_id": "consent-123",
        "fetched_at": "2026-07-01",
        "accounts": [
            {
                "account_id": "ACC0000001",
                "fip_name": "HDFC Bank",
                "account_type": "SAVINGS",
                "transactions": transactions,
            }
        ],
    }


@pytest.fixture
def sample_features(sample_aa_payload) -> dict:
    from app.schemas.models import AAPayload
    from app.services.aa_parser import parse_aa_payload
    from app.services.feature_engineering import build_features

    parsed = parse_aa_payload(AAPayload(**sample_aa_payload))
    return build_features(parsed)


@pytest.fixture
def client():
    from app.main import app
    from fastapi.testclient import TestClient

    return TestClient(app)


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path, monkeypatch):
    """Point the already-constructed local store at a fresh temp dir per test
    so tests never share state or touch the real dev-server data."""
    import app.db.store as store_module

    if isinstance(store_module.store, store_module.LocalJSONStore):
        fresh = store_module.LocalJSONStore(str(tmp_path))
        monkeypatch.setattr(store_module, "store", fresh)
        # Modules that did `from app.db.store import store` hold their own
        # reference; patch those too so routers/services see the fresh store.
        import app.services.pipeline as pipeline_module

        monkeypatch.setattr(pipeline_module, "store", fresh)
        for mod_name in ("app.routers.dashboard", "app.routers.predict", "app.routers.insights"):
            import importlib

            mod = importlib.import_module(mod_name)
            if hasattr(mod, "store"):
                monkeypatch.setattr(mod, "store", fresh)


@pytest.fixture
def scored_profile(sample_aa_payload):
    """Run the real pipeline once and return the resulting profile dict."""
    from app.schemas.models import AAPayload
    from app.services.pipeline import process_aa_payload

    profile = process_aa_payload(AAPayload(**sample_aa_payload))
    return profile
