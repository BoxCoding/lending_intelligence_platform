"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api, inr, tierColor } from "@/lib/api";
import { DonutChart, LeadFunnel, SimpleBar } from "@/components/charts";
import { ErrorBox, Section, Spinner, Stat } from "@/components/ui";

export default function Dashboard() {
  const { data, isLoading, error } = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard });

  if (isLoading) return <Spinner label="Scoring pipeline results loading…" />;
  if (error) return <ErrorBox error={error as Error} />;
  if (!data) return null;

  const { kpis, charts, leads } = data;

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold">Executive Dashboard</h1>
          <p className="text-sm text-muted">Pre-qualified lending leads from Account Aggregator intelligence</p>
        </div>
        <span className="text-xs text-muted">
          Models: {Object.entries(data.models).map(([k, v]) => `${k} ${v ? "✓ML" : "rules"}`).join(" · ")}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Total Leads" value={kpis.total_leads} />
        <Stat label="Hot Leads" value={kpis.hot_leads} accent="text-hot" />
        <Stat label="Warm Leads" value={kpis.warm_leads} accent="text-warm" />
        <Stat label="Cold Leads" value={kpis.cold_leads} accent="text-cold" />
        <Stat label="Predicted Conversions" value={kpis.predicted_conversions} accent="text-success" />
        <Stat label="Predicted Conv. Rate" value={`${kpis.predicted_conversion_rate}%`} accent="text-success" />
        <Stat label="Avg Est. Income" value={inr(kpis.avg_income)} />
        <Stat label="Avg Eligibility" value={inr(kpis.avg_eligibility)} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Section title="Lead Funnel"><LeadFunnel data={charts.lead_funnel ?? []} /></Section>
        <Section title="Recommended Loan Mix"><DonutChart data={charts.loan_distribution ?? []} nameKey="product" valueKey="count" /></Section>
        <Section title="Risk Grade Distribution"><SimpleBar data={charts.risk_distribution ?? []} x="grade" y="count" color="#f43f5e" /></Section>
        <Section title="Income Histogram"><SimpleBar data={charts.income_histogram ?? []} x="range" y="count" color="#34d399" /></Section>
      </div>

      <Section title={`Lead Queue (${leads.length})`} right={<span className="text-xs text-muted">sorted by score</span>}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase text-muted">
              <tr className="border-b border-border">
                <th className="py-2 pr-4">Customer</th><th className="pr-4">Score</th><th className="pr-4">Tier</th>
                <th className="pr-4">Est. Income</th><th className="pr-4">Risk</th><th className="pr-4">Intent</th>
                <th className="pr-4">Best Product</th><th>Conv. Prob</th>
              </tr>
            </thead>
            <tbody>
              {leads.slice(0, 50).map((l) => (
                <tr key={l.customer_id} className="border-b border-border/50 transition hover:bg-surface">
                  <td className="py-2.5 pr-4">
                    <Link href={`/customers/${l.customer_id}`} className="font-medium text-primary-foreground hover:underline">
                      {l.name}
                    </Link>
                    <span className="ml-2 text-xs text-muted">{l.customer_id}</span>
                  </td>
                  <td className="pr-4 font-semibold">{l.score}</td>
                  <td className="pr-4"><span className={`badge ${tierColor(l.tier)}`}>{l.tier}</span></td>
                  <td className="pr-4">{inr(l.income)}</td>
                  <td className="pr-4">{l.risk_grade}</td>
                  <td className="pr-4">{l.intent_score}</td>
                  <td className="pr-4">{l.top_product}</td>
                  <td>{Math.round(l.conversion_probability * 100)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
    </div>
  );
}
