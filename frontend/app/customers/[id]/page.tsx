"use client";
import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { use, useState } from "react";
import { api, inr, tierColor, WhatIfResult } from "@/lib/api";
import { ImpactBars } from "@/components/charts";
import { ErrorBox, Meter, Section, Spinner, Stat } from "@/components/ui";

export default function CustomerPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: p, isLoading, error } = useQuery({
    queryKey: ["customer", id],
    queryFn: () => api.customer(id),
  });
  const { data: explain } = useQuery({
    queryKey: ["explain", id],
    queryFn: () => api.explain("risk", id),
    enabled: !!p,
  });

  if (isLoading) return <Spinner label="Loading customer profile…" />;
  if (error) return <ErrorBox error={error as Error} />;
  if (!p) return null;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <Link href="/dashboard" className="text-sm text-muted hover:text-zinc-100">← Dashboard</Link>
        <h1 className="text-2xl font-bold">{p.name}</h1>
        <span className="text-sm text-muted">{p.customer_id}</span>
        <span className={`badge ${tierColor(p.lead.tier)}`}>{p.lead.tier} · {p.lead.score}</span>
        <span className="badge bg-surface text-muted">Risk {p.risk.risk_grade}</span>
        <Link href={`/chat?customer=${p.customer_id}`}
          className="ml-auto rounded-lg bg-primary px-4 py-2 text-sm font-semibold hover:bg-primary/85">
          Ask AI about this customer
        </Link>
      </div>

      <p className="card text-sm text-zinc-300">{p.recommendation.summary}</p>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Est. Monthly Income" value={inr(p.income.monthly_income)} />
        <Stat label="Disposable Income" value={inr(p.income.disposable_income)} />
        <Stat label="Eligible EMI" value={inr(p.repayment.eligible_emi)} />
        <Stat label="Financial Health" value={`${p.recommendation.financial_health_score}/100`} accent="text-success" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Section title="Income Analysis" right={<span className="text-xs text-muted">confidence {Math.round(p.income.confidence * 100)}%</span>}>
          <div className="space-y-3 text-sm">
            {[
              ["Fixed expenses", inr(p.income.fixed_expense)],
              ["Variable expenses", inr(p.income.variable_expense)],
              ["Average balance", inr(p.income.average_balance)],
              ["Savings rate", `${Math.round(p.income.savings_rate * 100)}%`],
              ["Salary regularity", `${Math.round(p.income.salary_regularity * 100)}%`],
              ["Income sources", p.income.income_sources.join(", ")],
            ].map(([k, v]) => (
              <div key={k as string} className="flex justify-between border-b border-border/50 pb-2">
                <span className="text-muted">{k}</span><span className="font-medium">{v}</span>
              </div>
            ))}
            <div>
              <p className="mb-1 flex justify-between text-muted">
                <span>Cash-flow stability</span><span>{Math.round(p.income.cash_flow_stability * 100)}%</span>
              </p>
              <Meter value={p.income.cash_flow_stability * 100} color="bg-success" />
            </div>
          </div>
        </Section>

        <Section title="Lead Score Breakdown">
          <div className="space-y-4 text-sm">
            {Object.entries(p.lead.components).map(([k, v]) => (
              <div key={k}>
                <p className="mb-1 flex justify-between"><span className="capitalize text-muted">{k.replace("_", " ")}</span><span>{v}</span></p>
                <Meter value={v} />
              </div>
            ))}
            <ul className="mt-2 list-inside list-disc text-muted">
              {p.lead.explanation.map((e) => <li key={e}>{e}</li>)}
            </ul>
          </div>
        </Section>

        <Section title="Borrowing Intent" right={<span className="text-xs text-muted">score {p.intent.intent_score}/100</span>}>
          <div className="mb-4 grid grid-cols-3 gap-3 text-center">
            {p.intent.windows.map((w) => (
              <div key={w.days} className="rounded-lg bg-surface p-3">
                <p className="text-xl font-bold">{Math.round(w.probability * 100)}%</p>
                <p className="text-xs text-muted">within {w.days}d</p>
              </div>
            ))}
          </div>
          <ul className="list-inside list-disc space-y-1 text-sm text-muted">
            {p.intent.reason_codes.map((r) => <li key={r}>{r}</li>)}
          </ul>
        </Section>

        <Section title="Risk Assessment" right={<span className="text-xs text-muted">PD {(p.risk.probability_of_default * 100).toFixed(1)}%</span>}>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between"><span className="text-muted">Financial stability</span><span>{p.risk.financial_stability}/100</span></div>
            <Meter value={p.risk.financial_stability} color="bg-success" />
            <div className="flex justify-between"><span className="text-muted">Behaviour stability</span><span>{p.risk.behavior_stability}/100</span></div>
            <Meter value={p.risk.behavior_stability} color="bg-cold" />
            <div className="flex justify-between border-b border-border/50 pb-2">
              <span className="text-muted">Liquidity risk</span><span>{p.risk.liquidity_risk}</span>
            </div>
            <div>
              <p className="mb-1 text-muted">Fraud indicators</p>
              {p.risk.fraud_indicators.length === 0
                ? <p className="text-success">None detected</p>
                : <ul className="list-inside list-disc text-hot">{p.risk.fraud_indicators.map((f) => <li key={f}>{f}</li>)}</ul>}
            </div>
          </div>
        </Section>
      </div>

      <Section title="Recommended Offers">
        <div className="grid gap-4 lg:grid-cols-3">
          {p.recommendation.offers.length === 0 && <p className="text-muted">No qualifying offers.</p>}
          {p.recommendation.offers.map((o) => (
            <div key={o.product} className="rounded-lg border border-border bg-surface p-4">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold">{o.product}</h3>
                <span className="badge bg-primary/15 text-primary-foreground">#{o.priority}</span>
              </div>
              <p className="mt-2 text-2xl font-bold">{inr(o.eligible_amount)}</p>
              <p className="text-xs text-muted">
                {o.interest_rate_min}–{o.interest_rate_max}% · {o.tenure_months} months · EMI {inr(o.monthly_emi)}
              </p>
              <ul className="mt-3 list-inside list-disc space-y-1 text-xs text-muted">
                {o.reasons.map((r) => <li key={r}>{r}</li>)}
              </ul>
            </div>
          ))}
        </div>
      </Section>

      {explain && (
        <Section title="Why (SHAP) — Risk Model Drivers" right={<span className="text-xs text-muted">green lowers approval risk concern · red raises it</span>}>
          <ImpactBars drivers={explain.top_drivers} />
        </Section>
      )}

      <WhatIf customerId={p.customer_id} />
    </div>
  );
}

function WhatIf({ customerId }: { customerId: string }) {
  const [amount, setAmount] = useState(500000);
  const [tenure, setTenure] = useState(48);
  const [rate, setRate] = useState(11.5);
  const mutation = useMutation<WhatIfResult, Error>({
    mutationFn: () => api.whatIf({ customer_id: customerId, loan_amount: amount, tenure_months: tenure, interest_rate: rate }),
  });

  const verdictColor = (v: string) =>
    v === "AFFORDABLE" ? "text-success" : v === "STRETCHED" ? "text-warm" : "text-hot";

  return (
    <Section title="What-if Repayment Simulator">
      <div className="grid gap-4 sm:grid-cols-4">
        {[
          { label: "Loan amount (₹)", value: amount, set: setAmount, step: 50000 },
          { label: "Tenure (months)", value: tenure, set: setTenure, step: 6 },
          { label: "Interest rate (%)", value: rate, set: setRate, step: 0.5 },
        ].map((f) => (
          <label key={f.label} className="text-xs text-muted">
            {f.label}
            <input type="number" value={f.value} step={f.step}
              onChange={(e) => f.set(Number(e.target.value))}
              className="mt-1 w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-zinc-100 outline-none focus:border-primary" />
          </label>
        ))}
        <button onClick={() => mutation.mutate()} disabled={mutation.isPending}
          className="self-end rounded-lg bg-primary px-4 py-2 text-sm font-semibold hover:bg-primary/85 disabled:opacity-50">
          {mutation.isPending ? "Simulating…" : "Simulate"}
        </button>
      </div>
      {mutation.data && (
        <div className="mt-4 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
          <div><p className="text-muted">Monthly EMI</p><p className="text-lg font-bold">{inr(mutation.data.monthly_emi)}</p></div>
          <div><p className="text-muted">Projected FOIR</p><p className="text-lg font-bold">{Math.round(mutation.data.projected_foir * 100)}%</p></div>
          <div><p className="text-muted">Disposable after EMI</p><p className="text-lg font-bold">{inr(mutation.data.disposable_after_emi)}</p></div>
          <div><p className="text-muted">Verdict</p><p className={`text-lg font-bold ${verdictColor(mutation.data.verdict)}`}>{mutation.data.verdict}</p></div>
        </div>
      )}
    </Section>
  );
}
