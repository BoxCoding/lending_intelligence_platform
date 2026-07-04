"""Pydantic data contracts shared across the platform."""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------- AA payload
class AATransaction(BaseModel):
    txn_id: str
    date: str                      # ISO date
    amount: float                  # positive number
    type: str                      # CREDIT | DEBIT
    mode: str = "OTHERS"           # UPI | NEFT | IMPS | ATM | CARD | CASH | ECS
    narration: str = ""
    balance: Optional[float] = None
    category: Optional[str] = None # optional pre-labelled category


class AAAccount(BaseModel):
    account_id: str
    fip_name: str = "Unknown Bank"
    account_type: str = "SAVINGS"
    transactions: list[AATransaction]


class AAPayload(BaseModel):
    """JSON delivered by the Account Aggregator (FI data pull)."""
    customer_id: str
    name: str = "Customer"
    pan: Optional[str] = None
    consent_id: Optional[str] = None
    fetched_at: Optional[str] = None
    accounts: list[AAAccount]


# ------------------------------------------------------------ engine outputs
class IncomeEstimate(BaseModel):
    monthly_income: float
    net_income: float
    disposable_income: float
    fixed_expense: float
    variable_expense: float
    average_balance: float
    cash_flow_stability: float = Field(ge=0, le=1)
    savings_rate: float
    income_volatility: float
    salary_regularity: float = Field(ge=0, le=1)
    income_sources: list[str] = []
    confidence: float = Field(ge=0, le=1)


class RepaymentCapacity(BaseModel):
    eligible_emi: float
    debt_to_income: float
    foir: float
    surplus_cash: float
    affordability_score: float = Field(ge=0, le=100)
    loan_capacity: dict[str, float]   # product -> max eligible amount


class IntentWindow(BaseModel):
    days: int
    probability: float = Field(ge=0, le=1)


class BorrowingIntent(BaseModel):
    intent_score: float = Field(ge=0, le=100)
    windows: list[IntentWindow]
    reason_codes: list[str]
    signals: dict[str, float] = {}


class RiskAssessment(BaseModel):
    probability_of_default: float = Field(ge=0, le=1)
    risk_grade: str                   # A / B / C / D / E
    fraud_indicators: list[str]
    financial_stability: float = Field(ge=0, le=100)
    behavior_stability: float = Field(ge=0, le=100)
    liquidity_risk: str               # LOW / MEDIUM / HIGH


class LeadScore(BaseModel):
    score: float = Field(ge=0, le=100)
    tier: str                         # HOT / WARM / COLD
    conversion_probability: float
    components: dict[str, float]
    explanation: list[str]


class LoanOffer(BaseModel):
    product: str
    eligible_amount: float
    interest_rate_min: float
    interest_rate_max: float
    tenure_months: int
    monthly_emi: float
    priority: int
    reasons: list[str]


class Recommendation(BaseModel):
    customer_id: str
    offers: list[LoanOffer]
    credit_limit: float
    financial_health_score: float
    summary: str


class ShapDriver(BaseModel):
    feature: str
    value: float
    impact: float
    direction: str  # positive | negative


class Explanation(BaseModel):
    model: str
    top_drivers: list[ShapDriver]
    positive_drivers: list[str]
    negative_drivers: list[str]
    confidence: float


# ------------------------------------------------------------- API requests
class CustomerIdRequest(BaseModel):
    customer_id: str


class ChatRequest(BaseModel):
    customer_id: Optional[str] = None
    message: str
    history: list[dict] = []


class ChatResponse(BaseModel):
    reply: str
    sources: list[str] = []
    suggestions: list[str] = []


class WhatIfRequest(BaseModel):
    customer_id: str
    loan_amount: float
    tenure_months: int
    interest_rate: float = 11.5
    extra_monthly_expense: float = 0
    income_change_pct: float = 0


class CustomerProfile(BaseModel):
    customer_id: str
    name: str
    features: dict
    income: Optional[IncomeEstimate] = None
    repayment: Optional[RepaymentCapacity] = None
    intent: Optional[BorrowingIntent] = None
    risk: Optional[RiskAssessment] = None
    lead: Optional[LeadScore] = None
    recommendation: Optional[Recommendation] = None
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
