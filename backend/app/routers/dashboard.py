"""Executive dashboard aggregation and customer detail endpoints."""
import json
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.db.store import store
from app.ml_registry import registry
from app.services.pipeline import get_profile

router = APIRouter(tags=["Dashboard"])


@router.get("/models/metrics", summary="Training metrics from the model registry")
def model_metrics():
    from app.core.config import get_settings

    configured = get_settings().model_dir
    base = Path(__file__).resolve().parents[2]  # backend/
    model_dir = Path(configured) if Path(configured).is_absolute() else (base / configured).resolve()
    registry_file = model_dir / "model_registry.json"
    if not registry_file.exists():
        raise HTTPException(status_code=404, detail="Models not trained yet — run ml/train.py")
    data = json.loads(registry_file.read_text())
    return {
        "trained_at": data.get("trained_at"),
        "n_train": data.get("n_train"),
        "n_test": data.get("n_test"),
        "models": data.get("models", {}),
        "loaded": registry.status(),
    }


@router.get("/dashboard", summary="Executive KPIs, funnel, and chart series")
def dashboard():
    profiles = store.list("profiles")
    if not profiles:
        return {"kpis": _empty_kpis(), "charts": {}, "leads": [], "models": registry.status()}

    tiers = Counter(p["lead"]["tier"] for p in profiles)
    incomes = [p["income"]["monthly_income"] for p in profiles]
    grades = Counter(p["risk"]["risk_grade"] for p in profiles)
    eligible = [max(p["repayment"]["loan_capacity"].values(), default=0) for p in profiles]
    conversions = [p["lead"]["conversion_probability"] for p in profiles]

    product_counter: Counter = Counter()
    for p in profiles:
        for offer in p["recommendation"]["offers"]:
            product_counter[offer["product"]] += 1

    intent_buckets = Counter(
        "High" if p["intent"]["intent_score"] >= 60 else "Medium" if p["intent"]["intent_score"] >= 30 else "Low"
        for p in profiles
    )

    leads = sorted(
        (
            {
                "customer_id": p["customer_id"],
                "name": p["name"],
                "score": p["lead"]["score"],
                "tier": p["lead"]["tier"],
                "income": round(p["income"]["monthly_income"]),
                "risk_grade": p["risk"]["risk_grade"],
                "intent_score": p["intent"]["intent_score"],
                "top_product": (p["recommendation"]["offers"][0]["product"]
                                if p["recommendation"]["offers"] else "—"),
                "conversion_probability": p["lead"]["conversion_probability"],
            }
            for p in profiles
        ),
        key=lambda x: x["score"],
        reverse=True,
    )

    return {
        "kpis": {
            "total_leads": len(profiles),
            "hot_leads": tiers.get("HOT", 0),
            "warm_leads": tiers.get("WARM", 0),
            "cold_leads": tiers.get("COLD", 0),
            "predicted_conversions": round(sum(conversions), 1),
            "predicted_conversion_rate": round(100 * sum(conversions) / len(profiles), 1),
            "avg_income": round(sum(incomes) / len(incomes)),
            "avg_eligibility": round(sum(eligible) / len(eligible)),
        },
        "charts": {
            "lead_funnel": [
                {"stage": "All Leads", "count": len(profiles)},
                {"stage": "Qualified (Warm+)", "count": tiers.get("HOT", 0) + tiers.get("WARM", 0)},
                {"stage": "Hot", "count": tiers.get("HOT", 0)},
                {"stage": "Predicted Conversions", "count": round(sum(conversions))},
            ],
            "risk_distribution": [{"grade": g, "count": grades.get(g, 0)} for g in "ABCDE"],
            "loan_distribution": [{"product": k, "count": v} for k, v in product_counter.most_common()],
            "income_histogram": _histogram(incomes),
            "intent_distribution": [{"bucket": b, "count": intent_buckets.get(b, 0)} for b in ("High", "Medium", "Low")],
        },
        "leads": leads,
        "models": registry.status(),
    }


@router.get("/customer/{customer_id}", summary="Full scored profile for one customer")
def customer_detail(customer_id: str):
    profile = get_profile(customer_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Customer not found")
    return profile


def _histogram(values: list[float], bins: int = 6) -> list[dict]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    width = max((hi - lo) / bins, 1.0)
    buckets = [0] * bins
    for v in values:
        idx = min(int((v - lo) / width), bins - 1)
        buckets[idx] += 1
    return [
        {"range": f"₹{(lo + i * width) / 1000:.0f}k–{(lo + (i + 1) * width) / 1000:.0f}k", "count": c}
        for i, c in enumerate(buckets)
    ]


def _empty_kpis() -> dict:
    return {k: 0 for k in (
        "total_leads", "hot_leads", "warm_leads", "cold_leads",
        "predicted_conversions", "predicted_conversion_rate", "avg_income", "avg_eligibility",
    )}
