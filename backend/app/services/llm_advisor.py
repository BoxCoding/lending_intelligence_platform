"""LLM Financial Advisor (Gemini).

Answers underwriter / customer questions grounded in the computed profile.
Uses Gemini when GEMINI_API_KEY is configured; otherwise a deterministic
template advisor so the demo works fully offline.
"""

import json

from app.core.config import get_settings
from app.core.logging import logger

SYSTEM_PROMPT = """You are LendIQ Advisor, an expert retail-lending underwriting assistant
for an Indian bank. You are given a customer's AI-computed financial profile derived from
Account Aggregator data. Ground every answer strictly in this profile — never invent numbers.
Explain income estimation, repayment capacity, loan eligibility, lead score, risk and product
recommendations in clear, banker-friendly language. Amounts are INR. Be concise, use bullet
points, and always state the WHY behind a recommendation. If asked for financial advice,
be responsible: mention FOIR limits and avoid over-leverage."""


def chat(message: str, profile: dict | None, history: list[dict]) -> dict:
    settings = get_settings()
    if settings.gemini_api_key:
        try:
            return _gemini_chat(message, profile, history, settings)
        except Exception as exc:
            logger.warning("Gemini call failed, using offline advisor: %s", exc)
    return _offline_chat(message, profile)


def _gemini_chat(message: str, profile: dict | None, history: list[dict], settings) -> dict:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)
    context = (
        f"CUSTOMER PROFILE:\n{json.dumps(profile, indent=2, default=str)}"
        if profile
        else "No customer selected."
    )
    contents = []
    for turn in history[-6:]:
        contents.append(
            types.Content(
                role=turn.get("role", "user"), parts=[types.Part(text=turn.get("content", ""))]
            )
        )
    contents.append(
        types.Content(role="user", parts=[types.Part(text=f"{context}\n\nQUESTION: {message}")])
    )
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.3),
    )
    return {
        "reply": response.text,
        "sources": ["gemini", "customer_profile"],
        "suggestions": _suggestions(profile),
    }


# --------------------------------------------------------------- offline advisor
def _offline_chat(message: str, profile: dict | None) -> dict:
    """Deterministic grounded advisor — keeps the demo working without an API key."""
    if not profile:
        return {
            "reply": "Select a customer to get a grounded analysis, or upload AA data via POST /aa/upload.",
            "sources": ["offline_advisor"],
            "suggestions": ["Show me the hottest leads", "Explain the lead scoring model"],
        }

    q = message.lower()
    income = profile.get("income") or {}
    repay = profile.get("repayment") or {}
    risk = profile.get("risk") or {}
    lead = profile.get("lead") or {}
    intent = profile.get("intent") or {}
    reco = profile.get("recommendation") or {}
    name = profile.get("name", "the customer")

    if any(k in q for k in ["income", "salary", "earn"]):
        reply = (
            f"**Income analysis for {name}**\n"
            f"- Estimated monthly income: ₹{income.get('monthly_income', 0):,.0f} "
            f"(confidence {income.get('confidence', 0):.0%})\n"
            f"- Fixed expenses ₹{income.get('fixed_expense', 0):,.0f}, variable ₹{income.get('variable_expense', 0):,.0f}\n"
            f"- Disposable income: ₹{income.get('disposable_income', 0):,.0f}/month\n"
            f"- Salary regularity {income.get('salary_regularity', 0):.0%}, "
            f"volatility {income.get('income_volatility', 0):.2f}\n"
            f"Why: estimate blends categorized salary credits with total inflows, "
            f"haircut for volatility, cross-checked by the ML income model."
        )
    elif any(k in q for k in ["emi", "repay", "afford", "capacity", "foir"]):
        reply = (
            f"**Repayment capacity for {name}**\n"
            f"- Eligible EMI headroom: ₹{repay.get('eligible_emi', 0):,.0f}/month\n"
            f"- Current FOIR: {repay.get('foir', 0):.0%} (policy cap 55%)\n"
            f"- Debt-to-income: {repay.get('debt_to_income', 0):.0%}\n"
            f"- Monthly surplus: ₹{repay.get('surplus_cash', 0):,.0f}\n"
            f"- Affordability score: {repay.get('affordability_score', 0)}/100\n"
            f"Why: headroom = 55% of income minus existing obligations, capped at disposable income."
        )
    elif any(k in q for k in ["risk", "default", "fraud", "grade"]):
        flags = risk.get("fraud_indicators") or ["None"]
        reply = (
            f"**Risk assessment for {name}**\n"
            f"- Probability of default: {risk.get('probability_of_default', 0):.1%} → grade {risk.get('risk_grade', '?')}\n"
            f"- Financial stability {risk.get('financial_stability', 0)}/100, "
            f"behavioural stability {risk.get('behavior_stability', 0)}/100\n"
            f"- Liquidity risk: {risk.get('liquidity_risk', '?')}\n"
            f"- Fraud indicators: {'; '.join(flags)}"
        )
    elif any(k in q for k in ["lead", "score", "hot", "convert"]):
        reply = (
            f"**Lead score for {name}: {lead.get('score', 0)}/100 → {lead.get('tier', '?')}**\n"
            f"- Conversion probability: {lead.get('conversion_probability', 0):.0%}\n"
            f"- Components: "
            + ", ".join(f"{k} {v}" for k, v in (lead.get("components") or {}).items())
            + "\n"
            f"- Intent (90d): {intent.get('intent_score', 0)}/100 — "
            + "; ".join((intent.get("reason_codes") or [])[:3])
        )
    elif any(k in q for k in ["recommend", "product", "loan", "offer", "eligib"]):
        offers = reco.get("offers") or []
        lines = [
            f"- **{o['product']}**: up to ₹{o['eligible_amount']:,.0f} at "
            f"{o['interest_rate_min']}–{o['interest_rate_max']}%, {o['tenure_months']}m, "
            f"EMI ≈ ₹{o['monthly_emi']:,.0f}. Why: {o['reasons'][0] if o['reasons'] else ''}"
            for o in offers
        ]
        reply = f"**Recommended products for {name}**\n" + (
            "\n".join(lines) if lines else "No qualifying offers."
        )
    else:
        reply = (
            f"**Summary for {name}**\n{reco.get('summary', '')}\n"
            f"- Income ₹{income.get('monthly_income', 0):,.0f}/mo | EMI headroom ₹{repay.get('eligible_emi', 0):,.0f}\n"
            f"- Lead: {lead.get('tier', '?')} ({lead.get('score', 0)}/100) | Risk grade {risk.get('risk_grade', '?')}\n"
            f"Ask me about income, repayment capacity, risk, lead score, or recommendations."
        )
    return {
        "reply": reply,
        "sources": ["offline_advisor", "customer_profile"],
        "suggestions": _suggestions(profile),
    }


def _suggestions(profile: dict | None) -> list[str]:
    if not profile:
        return ["Show hot leads", "Explain lead scoring"]
    return [
        "Why is this lead scored this way?",
        "Explain the income estimation",
        "What loan products fit best?",
        "Any fraud indicators?",
    ]
