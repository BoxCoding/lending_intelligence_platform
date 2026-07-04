"""LangGraph underwriting-assistant workflow.

Graph:
    fetch_profile -> analyze_intent -> route
        route == "underwrite" -> underwrite -> compose
        route == "advise"     -> advise    -> compose

The agent grounds every step in the scored customer profile from the
platform store. Gemini powers the compose node when GEMINI_API_KEY is
set; otherwise the deterministic advisor composes the answer, so the
graph runs fully offline too.

Usage:
    python loan_advisor_graph.py CUST00001 "Should we offer a home loan?"
"""
import sys
from pathlib import Path
from typing import Literal, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from langgraph.graph import END, StateGraph

from app.services import llm_advisor
from app.services.pipeline import get_profile


class AgentState(TypedDict, total=False):
    customer_id: str
    question: str
    profile: dict
    route: str
    analysis: dict
    answer: str


# ------------------------------------------------------------------ nodes
def fetch_profile(state: AgentState) -> AgentState:
    profile = get_profile(state["customer_id"]) or {}
    return {"profile": profile}


def analyze_intent(state: AgentState) -> AgentState:
    """Classify the question: underwriting decision vs. general advice."""
    q = state["question"].lower()
    underwrite_keywords = ("approve", "underwrit", "sanction", "offer", "eligib",
                           "should we", "decision", "risk", "lend")
    route = "underwrite" if any(k in q for k in underwrite_keywords) else "advise"
    return {"route": route}


def underwrite(state: AgentState) -> AgentState:
    """Deterministic underwriting checklist over the scored profile."""
    p = state.get("profile") or {}
    if not p:
        return {"analysis": {"decision": "NO_DATA", "checks": []}}
    risk, repay, lead = p.get("risk", {}), p.get("repayment", {}), p.get("lead", {})
    checks = [
        ("Risk grade A–C", risk.get("risk_grade", "E") in ("A", "B", "C")),
        ("PD below 13%", risk.get("probability_of_default", 1) < 0.13),
        ("FOIR headroom exists", repay.get("eligible_emi", 0) >= 2000),
        ("No fraud indicators", not risk.get("fraud_indicators")),
        ("Lead not COLD", lead.get("tier") != "COLD"),
    ]
    passed = sum(1 for _, ok in checks if ok)
    decision = "APPROVE" if passed == len(checks) else "REFER" if passed >= 3 else "DECLINE"
    return {"analysis": {"decision": decision,
                         "checks": [{"check": c, "passed": ok} for c, ok in checks]}}


def advise(state: AgentState) -> AgentState:
    p = state.get("profile") or {}
    return {"analysis": {"decision": "ADVISORY",
                         "highlights": (p.get("recommendation") or {}).get("summary", "")}}


def compose(state: AgentState) -> AgentState:
    """Turn the structured analysis into a natural-language answer via the advisor."""
    analysis = state.get("analysis", {})
    prefix = ""
    if analysis.get("decision") in ("APPROVE", "REFER", "DECLINE"):
        failed = [c["check"] for c in analysis.get("checks", []) if not c["passed"]]
        prefix = (f"UNDERWRITING DECISION: {analysis['decision']}."
                  + (f" Failed checks: {', '.join(failed)}." if failed else " All checks passed."))
    result = llm_advisor.chat(f"{prefix}\n{state['question']}", state.get("profile"), [])
    answer = (prefix + "\n\n" if prefix else "") + result["reply"]
    return {"answer": answer}


def route_decision(state: AgentState) -> Literal["underwrite", "advise"]:
    return state["route"]  # type: ignore[return-value]


# ------------------------------------------------------------------ graph
def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("fetch_profile", fetch_profile)
    graph.add_node("analyze_intent", analyze_intent)
    graph.add_node("underwrite", underwrite)
    graph.add_node("advise", advise)
    graph.add_node("compose", compose)

    graph.set_entry_point("fetch_profile")
    graph.add_edge("fetch_profile", "analyze_intent")
    graph.add_conditional_edges("analyze_intent", route_decision,
                                {"underwrite": "underwrite", "advise": "advise"})
    graph.add_edge("underwrite", "compose")
    graph.add_edge("advise", "compose")
    graph.add_edge("compose", END)
    return graph.compile()


def run(customer_id: str, question: str) -> str:
    app = build_graph()
    final = app.invoke({"customer_id": customer_id, "question": question})
    return final["answer"]


if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "CUST00001"
    q = sys.argv[2] if len(sys.argv) > 2 else "Should we approve a personal loan for this customer?"
    print(run(cid, q))
