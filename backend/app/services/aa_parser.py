"""Account Aggregator data parser.

Categorizes raw bank transactions from an AA FI-data payload into
semantic buckets (salary, EMI, rent, UPI spend, investments, ...) using
narration keyword rules, then produces month-wise structured aggregates
that downstream feature engineering consumes.
"""

import re
from collections import defaultdict
from datetime import datetime

from app.core.logging import logger
from app.schemas.models import AAPayload

# Ordered rules: first match wins. (category, credit/debit/any, patterns)
CATEGORY_RULES: list[tuple[str, str, list[str]]] = [
    ("SALARY", "CREDIT", [r"salary", r"sal cr", r"payroll", r"wages", r"stipend", r"\bsal\b"]),
    (
        "BUSINESS_INCOME",
        "CREDIT",
        [r"gst", r"invoice", r"settlement.*pos", r"razorpay", r"payu", r"vendor payment recd"],
    ),
    ("INTEREST_INCOME", "CREDIT", [r"\bint\b.*cr", r"interest credit", r"fd int", r"dividend"]),
    ("RENT_INCOME", "CREDIT", [r"rent received", r"rent cr"]),
    ("CASH_DEPOSIT", "CREDIT", [r"cash dep", r"cdm", r"by cash"]),
    ("REFUND", "CREDIT", [r"refund", r"reversal", r"rev\b"]),
    ("LOAN_DISBURSAL", "CREDIT", [r"loan disb", r"disbursement"]),
    (
        "EMI",
        "DEBIT",
        [
            r"\bemi\b",
            r"ach d",
            r"nach",
            r"ecs",
            r"loan repay",
            r"bajaj fin",
            r"hdfc ltd",
            r"lic hfl",
        ],
    ),
    (
        "CREDIT_CARD",
        "DEBIT",
        [
            r"credit card",
            r"cc payment",
            r"card pmt",
            r"visa pmt",
            r"amex",
            r"cred\b",
            r"creditcard",
        ],
    ),
    ("RENT", "DEBIT", [r"rent paid", r"house rent", r"rent to", r"nobroker", r"\brent\b"]),
    (
        "INVESTMENT",
        "DEBIT",
        [
            r"\bsip\b",
            r"mutual fund",
            r"zerodha",
            r"groww",
            r"upstox",
            r"\bmf\b",
            r"nps",
            r"ppf",
            r"etmoney",
            r"kuvera",
        ],
    ),
    (
        "INSURANCE",
        "DEBIT",
        [r"insurance", r"lic of india", r"premium", r"policybazaar", r"hdfc life", r"icici pru"],
    ),
    (
        "UTILITIES",
        "DEBIT",
        [
            r"electricity",
            r"bescom",
            r"tneb",
            r"broadband",
            r"jio",
            r"airtel",
            r"\bvi\b",
            r"gas bill",
            r"water bill",
            r"dth",
            r"recharge",
        ],
    ),
    (
        "EDUCATION",
        "DEBIT",
        [r"school fee", r"tuition", r"college", r"university", r"coaching", r"byjus", r"course"],
    ),
    (
        "MEDICAL",
        "DEBIT",
        [r"hospital", r"pharmacy", r"apollo", r"medplus", r"clinic", r"diagnostic"],
    ),
    (
        "SHOPPING",
        "DEBIT",
        [
            r"amazon",
            r"flipkart",
            r"myntra",
            r"ajio",
            r"bigbasket",
            r"dmart",
            r"blinkit",
            r"zepto",
            r"reliance retail",
        ],
    ),
    (
        "FOOD_DINING",
        "DEBIT",
        [r"swiggy", r"zomato", r"restaurant", r"cafe", r"eatery", r"dominos", r"mcdonald"],
    ),
    (
        "TRAVEL_FUEL",
        "DEBIT",
        [
            r"irctc",
            r"makemytrip",
            r"uber",
            r"ola\b",
            r"rapido",
            r"petrol",
            r"fuel",
            r"hpcl",
            r"iocl",
            r"bpcl",
            r"fastag",
        ],
    ),
    (
        "PROPERTY_PAYMENT",
        "DEBIT",
        [
            r"builder",
            r"property",
            r"real estate",
            r"registration fee",
            r"stamp duty",
            r"token advance",
            r"booking amount.*flat",
        ],
    ),
    (
        "VEHICLE_PAYMENT",
        "DEBIT",
        [r"vehicle booking", r"car booking", r"showroom", r"automobiles", r"motors\b", r"rto\b"],
    ),
    (
        "WEDDING",
        "DEBIT",
        [r"wedding", r"marriage hall", r"caterer", r"banquet", r"jewell", r"tanishq", r"kalyan"],
    ),
    (
        "LOAN_ENQUIRY",
        "DEBIT",
        [r"loan processing fee", r"cibil", r"credit report", r"login fee", r"bureau fee"],
    ),
    ("CASH_WITHDRAWAL", "DEBIT", [r"atm", r"atw", r"cash wdl", r"self cheque", r"csh wdr"]),
    ("UPI_SPEND", "DEBIT", [r"upi", r"gpay", r"phonepe", r"paytm", r"bhim"]),
    ("UPI_INCOME", "CREDIT", [r"upi", r"gpay", r"phonepe", r"paytm", r"bhim"]),
]

RECURRING_CATEGORIES = {"EMI", "RENT", "INVESTMENT", "INSURANCE", "UTILITIES"}
FIXED_EXPENSE_CATEGORIES = {"EMI", "RENT", "INSURANCE", "UTILITIES", "EDUCATION"}
INCOME_CATEGORIES = {"SALARY", "BUSINESS_INCOME", "RENT_INCOME", "INTEREST_INCOME"}


def categorize(narration: str, txn_type: str) -> str:
    """Classify a single transaction narration into a semantic category."""
    text = narration.lower()
    for category, direction, patterns in CATEGORY_RULES:
        if direction != "ANY" and direction != txn_type:
            continue
        for pattern in patterns:
            if re.search(pattern, text):
                return category
    return "OTHER_INCOME" if txn_type == "CREDIT" else "OTHER_SPEND"


def parse_aa_payload(payload: AAPayload) -> dict:
    """Parse an AA payload into categorized transactions and monthly aggregates.

    Returns a dict with:
      transactions   – flat list with category labels
      monthly        – {month: {category: total_amount}}
      monthly_meta   – {month: {credits, debits, txn_count, avg_balance, min_balance}}
      employer       – detected employer string (from salary narration) or None
      months         – sorted list of months covered
    """
    transactions: list[dict] = []
    monthly: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    monthly_meta: dict[str, dict] = defaultdict(
        lambda: {"credits": 0.0, "debits": 0.0, "txn_count": 0, "balances": []}
    )
    employer = None

    for account in payload.accounts:
        for txn in account.transactions:
            try:
                month = datetime.fromisoformat(txn.date).strftime("%Y-%m")
            except ValueError:
                logger.warning("Skipping txn %s with bad date %s", txn.txn_id, txn.date)
                continue
            category = txn.category or categorize(txn.narration, txn.type)
            if category == "SALARY" and employer is None:
                employer = _extract_employer(txn.narration)

            transactions.append(
                {
                    "txn_id": txn.txn_id,
                    "date": txn.date,
                    "month": month,
                    "amount": abs(txn.amount),
                    "type": txn.type,
                    "mode": txn.mode,
                    "category": category,
                    "narration": txn.narration,
                    "account_id": account.account_id,
                }
            )
            monthly[month][category] += abs(txn.amount)
            meta = monthly_meta[month]
            meta["txn_count"] += 1
            if txn.type == "CREDIT":
                meta["credits"] += abs(txn.amount)
            else:
                meta["debits"] += abs(txn.amount)
            if txn.balance is not None:
                meta["balances"].append(txn.balance)

    for meta in monthly_meta.values():
        balances = meta.pop("balances")
        meta["avg_balance"] = sum(balances) / len(balances) if balances else 0.0
        meta["min_balance"] = min(balances) if balances else 0.0

    months = sorted(monthly.keys())
    logger.info(
        "Parsed AA payload for %s: %d txns across %d months",
        payload.customer_id,
        len(transactions),
        len(months),
    )
    return {
        "customer_id": payload.customer_id,
        "name": payload.name,
        "transactions": transactions,
        "monthly": {m: dict(v) for m, v in monthly.items()},
        "monthly_meta": dict(monthly_meta),
        "employer": employer,
        "months": months,
    }


def _extract_employer(narration: str) -> str | None:
    """Best-effort employer extraction from a salary credit narration."""
    match = re.search(
        r"(?:salary|sal|payroll)[\s\-/]*(?:from|by|cr)?[\s\-/]*([a-zA-Z][a-zA-Z0-9 &._]{2,40})",
        narration,
        re.I,
    )
    if match:
        return match.group(1).strip().title()
    return None
