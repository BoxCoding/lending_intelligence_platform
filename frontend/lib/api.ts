/** Typed API client for the LendIQ backend. */
export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body.slice(0, 300)}`);
  }
  return res.json();
}

export const api = {
  dashboard: () => request<DashboardData>("/dashboard"),
  customer: (id: string) => request<CustomerProfile>(`/customer/${id}`),
  explain: (model: string, customerId: string) =>
    request<Explanation>(`/predict/explain/${model}`, {
      method: "POST",
      body: JSON.stringify({ customer_id: customerId }),
    }),
  chat: (message: string, customerId?: string, history: ChatTurn[] = []) =>
    request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ message, customer_id: customerId || null, history }),
    }),
  whatIf: (body: WhatIfRequest) =>
    request<WhatIfResult>("/whatif", { method: "POST", body: JSON.stringify(body) }),
  uploadAA: (payload: unknown) =>
    request<CustomerProfile>("/aa/upload", { method: "POST", body: JSON.stringify(payload) }),
};

/* ------------------------------- types ------------------------------- */
export interface KPIs {
  total_leads: number;
  hot_leads: number;
  warm_leads: number;
  cold_leads: number;
  predicted_conversions: number;
  predicted_conversion_rate: number;
  avg_income: number;
  avg_eligibility: number;
}
export interface LeadRow {
  customer_id: string;
  name: string;
  score: number;
  tier: string;
  income: number;
  risk_grade: string;
  intent_score: number;
  top_product: string;
  conversion_probability: number;
}
export interface DashboardData {
  kpis: KPIs;
  charts: {
    lead_funnel?: { stage: string; count: number }[];
    risk_distribution?: { grade: string; count: number }[];
    loan_distribution?: { product: string; count: number }[];
    income_histogram?: { range: string; count: number }[];
    intent_distribution?: { bucket: string; count: number }[];
  };
  leads: LeadRow[];
  models: Record<string, boolean>;
}
export interface LoanOffer {
  product: string;
  eligible_amount: number;
  interest_rate_min: number;
  interest_rate_max: number;
  tenure_months: number;
  monthly_emi: number;
  priority: number;
  reasons: string[];
}
export interface CustomerProfile {
  customer_id: string;
  name: string;
  features: Record<string, number>;
  income: {
    monthly_income: number;
    net_income: number;
    disposable_income: number;
    fixed_expense: number;
    variable_expense: number;
    average_balance: number;
    cash_flow_stability: number;
    savings_rate: number;
    income_volatility: number;
    salary_regularity: number;
    income_sources: string[];
    confidence: number;
  };
  repayment: {
    eligible_emi: number;
    debt_to_income: number;
    foir: number;
    surplus_cash: number;
    affordability_score: number;
    loan_capacity: Record<string, number>;
  };
  intent: {
    intent_score: number;
    windows: { days: number; probability: number }[];
    reason_codes: string[];
    signals: Record<string, number>;
  };
  risk: {
    probability_of_default: number;
    risk_grade: string;
    fraud_indicators: string[];
    financial_stability: number;
    behavior_stability: number;
    liquidity_risk: string;
  };
  lead: {
    score: number;
    tier: string;
    conversion_probability: number;
    components: Record<string, number>;
    explanation: string[];
  };
  recommendation: {
    offers: LoanOffer[];
    credit_limit: number;
    financial_health_score: number;
    summary: string;
  };
  updated_at: string;
}
export interface Explanation {
  model: string;
  top_drivers: { feature: string; value: number; impact: number; direction: string }[];
  positive_drivers: string[];
  negative_drivers: string[];
  confidence: number;
}
export interface ChatTurn {
  role: string;
  content: string;
}
export interface ChatResponse {
  reply: string;
  sources: string[];
  suggestions: string[];
}
export interface WhatIfRequest {
  customer_id: string;
  loan_amount: number;
  tenure_months: number;
  interest_rate?: number;
  extra_monthly_expense?: number;
  income_change_pct?: number;
}
export interface WhatIfResult {
  monthly_emi: number;
  projected_foir: number;
  disposable_after_emi: number;
  verdict: string;
  note: string;
}

export const inr = (n: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n);

export const tierColor = (tier: string) =>
  tier === "HOT"
    ? "bg-hot/15 text-hot"
    : tier === "WARM"
      ? "bg-warm/15 text-warm"
      : "bg-cold/15 text-cold";
