"""Synthetic Account Aggregator dataset generator.

Simulates realistic Indian retail-banking behaviour for N customers
across personas (salaried_stable, salaried_stretched, self_employed,
gig_worker, affluent). Each customer gets 6 months of transactions plus
ground-truth labels (true income, applied-in-90d, defaulted) used to
train and evaluate the ML models.

Usage:
    python data_generator.py --n 400 --out ../data/samples
"""

import argparse
import json
import random
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

FIRST = [
    "Aarav",
    "Vivaan",
    "Aditya",
    "Ananya",
    "Diya",
    "Ishaan",
    "Kavya",
    "Rohan",
    "Priya",
    "Arjun",
    "Sneha",
    "Karthik",
    "Meera",
    "Rahul",
    "Nisha",
    "Vikram",
    "Pooja",
    "Sanjay",
    "Divya",
    "Amit",
]
LAST = [
    "Sharma",
    "Verma",
    "Iyer",
    "Nair",
    "Patel",
    "Reddy",
    "Gupta",
    "Singh",
    "Das",
    "Kulkarni",
    "Menon",
    "Chopra",
    "Joshi",
    "Rao",
    "Mehta",
]
EMPLOYERS = [
    "Infosys Ltd",
    "TCS",
    "Wipro",
    "HDFC Bank",
    "Accenture",
    "Flipkart",
    "Reliance Ind",
    "Cognizant",
    "Zoho Corp",
    "Airtel",
]

PERSONAS = {
    #                weight, income_range,     vol,   emi_r,  save_r, cash_r, default_base, intent_base
    "salaried_stable": (0.30, (45_000, 180_000), 0.05, 0.15, 0.25, 0.05, 0.02, 0.25),
    "salaried_stretched": (0.25, (30_000, 90_000), 0.10, 0.45, 0.02, 0.15, 0.15, 0.45),
    "self_employed": (0.20, (40_000, 250_000), 0.45, 0.20, 0.15, 0.35, 0.08, 0.35),
    "gig_worker": (0.15, (18_000, 55_000), 0.60, 0.10, 0.03, 0.40, 0.20, 0.30),
    "affluent": (0.10, (150_000, 600_000), 0.10, 0.10, 0.35, 0.02, 0.01, 0.30),
}


def _txn(day, amount, ttype, mode, narration, balance):
    return {
        "txn_id": uuid.uuid4().hex[:12],
        "date": day.isoformat(),
        "amount": round(amount, 2),
        "type": ttype,
        "mode": mode,
        "narration": narration,
        "balance": round(balance, 2),
    }


def generate_customer(idx: int, rng: random.Random, months: int = 6) -> tuple[dict, dict]:
    persona = rng.choices(list(PERSONAS), weights=[p[0] for p in PERSONAS.values()])[0]
    _, (lo, hi), vol, emi_ratio, save_ratio, cash_ratio, pd_base, intent_base = PERSONAS[persona]

    income = rng.uniform(lo, hi)
    name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
    employer = rng.choice(EMPLOYERS)
    customer_id = f"CUST{idx:05d}"
    balance = income * rng.uniform(0.3, 2.5)
    salaried = persona.startswith("salaried") or persona == "affluent"

    # Life-event intent signals
    has_property = rng.random() < (0.25 if persona in ("affluent", "salaried_stable") else 0.08)
    has_vehicle = rng.random() < 0.15
    has_wedding = rng.random() < 0.10
    has_enquiry = rng.random() < (0.35 if persona == "salaried_stretched" else 0.15)
    salary_grew = rng.random() < 0.30

    txns = []
    today = date.today().replace(day=1)
    start = today - timedelta(days=30 * months)
    emi_amt = income * emi_ratio * rng.uniform(0.7, 1.2)
    rent_amt = income * rng.uniform(0.12, 0.25) if rng.random() < 0.55 else 0
    sip_amt = income * save_ratio * rng.uniform(0.4, 0.9)

    for m in range(months):
        month_start = start + timedelta(days=30 * m)
        month_income = income * (1 + (0.04 * m if salary_grew else 0)) * rng.gauss(1, vol)
        month_income = max(month_income, income * 0.15)

        if salaried:
            if rng.random() > 0.03:  # occasional missed month for stretched personas
                balance += month_income
                txns.append(
                    _txn(
                        month_start + timedelta(days=rng.randint(0, 2)),
                        month_income,
                        "CREDIT",
                        "NEFT",
                        f"SALARY {employer.upper()} SAL CR",
                        balance,
                    )
                )
        else:
            # business/gig inflows: many small credits, some cash deposits
            n_credits = rng.randint(6, 18)
            for _ in range(n_credits):
                amt = month_income / n_credits * rng.uniform(0.5, 1.6)
                balance += amt
                if rng.random() < cash_ratio:
                    txns.append(
                        _txn(
                            month_start + timedelta(days=rng.randint(0, 27)),
                            amt,
                            "CREDIT",
                            "CASH",
                            "CASH DEP CDM BRANCH",
                            balance,
                        )
                    )
                else:
                    txns.append(
                        _txn(
                            month_start + timedelta(days=rng.randint(0, 27)),
                            amt,
                            "CREDIT",
                            "UPI",
                            f"UPI/CR/{rng.randint(10**9, 10**10)}/PAYMENT RECD",
                            balance,
                        )
                    )

        # Fixed obligations
        if emi_amt > 500:
            balance -= emi_amt
            txns.append(
                _txn(
                    month_start + timedelta(days=5),
                    emi_amt,
                    "DEBIT",
                    "ECS",
                    "ACH D- BAJAJ FIN EMI",
                    balance,
                )
            )
        if rent_amt > 0:
            balance -= rent_amt
            txns.append(
                _txn(
                    month_start + timedelta(days=3),
                    rent_amt,
                    "DEBIT",
                    "UPI",
                    "UPI/DR/RENT TO LANDLORD",
                    balance,
                )
            )
        if sip_amt > 500:
            balance -= sip_amt
            txns.append(
                _txn(
                    month_start + timedelta(days=7),
                    sip_amt,
                    "DEBIT",
                    "ECS",
                    "SIP ZERODHA MUTUAL FUND",
                    balance,
                )
            )
        for narr, frac in [
            ("ELECTRICITY BESCOM BILL", 0.015),
            ("JIO RECHARGE", 0.005),
            ("HDFC LIFE INSURANCE PREMIUM", 0.02),
        ]:
            amt = income * frac * rng.uniform(0.6, 1.4)
            balance -= amt
            txns.append(
                _txn(
                    month_start + timedelta(days=rng.randint(8, 12)),
                    amt,
                    "DEBIT",
                    "UPI",
                    narr,
                    balance,
                )
            )

        # Variable spends
        n_spends = rng.randint(12, 30)
        spend_budget = (
            month_income
            * rng.uniform(0.25, 0.55)
            * (1 + (0.3 if persona == "salaried_stretched" else 0))
        )
        for _ in range(n_spends):
            amt = spend_budget / n_spends * rng.uniform(0.3, 2.0)
            narr = rng.choice(
                [
                    "UPI/DR/SWIGGY",
                    "UPI/DR/AMAZON PAY",
                    "UPI/DR/ZOMATO",
                    "UPI/DR/BIGBASKET",
                    "CARD PMT FLIPKART",
                    "UPI/DR/UBER",
                    "PETROL HPCL",
                    "UPI/DR/GROCERY STORE",
                ]
            )
            balance -= amt
            txns.append(
                _txn(
                    month_start + timedelta(days=rng.randint(0, 27)),
                    amt,
                    "DEBIT",
                    "UPI" if "UPI" in narr else "CARD",
                    narr,
                    balance,
                )
            )

        # Cash withdrawals
        for _ in range(rng.randint(0, 3)):
            amt = income * cash_ratio * rng.uniform(0.05, 0.25)
            if amt > 100:
                balance -= amt
                txns.append(
                    _txn(
                        month_start + timedelta(days=rng.randint(0, 27)),
                        amt,
                        "DEBIT",
                        "ATM",
                        "ATM CASH WDL",
                        balance,
                    )
                )

        # Life-event signals concentrated in recent months
        if m >= months - 3:
            if has_property and rng.random() < 0.5:
                amt = income * rng.uniform(1.5, 4.0)
                balance -= amt
                txns.append(
                    _txn(
                        month_start + timedelta(days=15),
                        amt,
                        "DEBIT",
                        "NEFT",
                        "NEFT PRESTIGE BUILDER TOKEN ADVANCE PROPERTY",
                        balance,
                    )
                )
            if has_vehicle and rng.random() < 0.5:
                amt = income * rng.uniform(0.4, 1.2)
                balance -= amt
                txns.append(
                    _txn(
                        month_start + timedelta(days=18),
                        amt,
                        "DEBIT",
                        "CARD",
                        "ADVANCE MARUTI SHOWROOM VEHICLE BOOKING",
                        balance,
                    )
                )
            if has_wedding and rng.random() < 0.6:
                amt = income * rng.uniform(0.3, 1.0)
                balance -= amt
                txns.append(
                    _txn(
                        month_start + timedelta(days=20),
                        amt,
                        "DEBIT",
                        "CARD",
                        "TANISHQ JEWELLERY PURCHASE",
                        balance,
                    )
                )
            if has_enquiry and rng.random() < 0.6:
                balance -= 500
                txns.append(
                    _txn(
                        month_start + timedelta(days=10),
                        500,
                        "DEBIT",
                        "UPI",
                        "CIBIL CREDIT REPORT FEE",
                        balance,
                    )
                )

    payload = {
        "customer_id": customer_id,
        "name": name,
        "pan": f"ABCDE{rng.randint(1000, 9999)}F",
        "consent_id": uuid.uuid4().hex,
        "fetched_at": date.today().isoformat(),
        "accounts": [
            {
                "account_id": f"ACC{idx:07d}",
                "fip_name": rng.choice(
                    ["HDFC Bank", "ICICI Bank", "SBI", "Axis Bank", "Kotak Bank"]
                ),
                "account_type": "SAVINGS",
                "transactions": sorted(txns, key=lambda t: t["date"]),
            }
        ],
    }

    # ---- Ground-truth labels ----
    intent_p = (
        intent_base
        + 0.25 * has_property
        + 0.20 * has_vehicle
        + 0.15 * has_wedding
        + 0.20 * has_enquiry
        + 0.05 * salary_grew
    )
    applied_90d = rng.random() < min(intent_p, 0.95)
    foir = (emi_amt + rent_amt) / income
    pd_p = pd_base + 0.20 * max(foir - 0.45, 0) + 0.10 * vol - 0.05 * save_ratio
    defaulted = rng.random() < min(max(pd_p, 0.01), 0.9)
    labels = {
        "customer_id": customer_id,
        "persona": persona,
        "true_monthly_income": round(income, 2),
        "applied_within_90d": int(applied_90d),
        "defaulted": int(defaulted),
    }
    return payload, labels


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=400)
    parser.add_argument("--out", default=str(Path(__file__).parent.parent / "data" / "samples"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    payloads, labels = [], []
    for i in range(1, args.n + 1):
        payload, label = generate_customer(i, rng)
        payloads.append(payload)
        labels.append(label)

    (out / "aa_payloads.json").write_text(json.dumps(payloads, indent=1))
    (out / "labels.json").write_text(json.dumps(labels, indent=1))
    # A single demo payload for quick manual API testing
    (out / "sample_aa_payload.json").write_text(json.dumps(payloads[0], indent=2))
    print(f"Generated {args.n} customers -> {out}/aa_payloads.json, labels.json")


if __name__ == "__main__":
    main()
