"use client";
import { useQuery } from "@tanstack/react-query";
import { api, API_URL } from "@/lib/api";
import { DonutChart, SimpleBar } from "@/components/charts";
import { ErrorBox, Section, Spinner, Stat } from "@/components/ui";

interface ModelMetrics {
  trained_at: string;
  n_train: number;
  n_test: number;
  models: Record<string, Record<string, number>>;
  loaded: Record<string, boolean>;
}

const METRIC_LABELS: Record<string, string> = {
  rmse: "RMSE (₹)",
  mae: "MAE (₹)",
  mape: "MAPE",
  auc: "AUC",
  precision: "Precision",
  recall: "Recall",
  f1: "F1",
  roc_auc: "ROC-AUC",
  ks: "KS",
  gini: "Gini",
};

const MODEL_TITLES: Record<string, string> = {
  income: "Income Estimation (LightGBM)",
  intent: "Borrowing Intent (XGBoost)",
  risk: "Default Risk (LightGBM)",
};

function fmtMetric(key: string, v: number) {
  if (key === "mape") return `${(v * 100).toFixed(1)}%`;
  if (key === "rmse" || key === "mae") return Math.round(v).toLocaleString("en-IN");
  return v.toFixed(3);
}

export default function Analytics() {
  const dash = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard });
  const metrics = useQuery({
    queryKey: ["model-metrics"],
    queryFn: async (): Promise<ModelMetrics> => {
      const res = await fetch(`${API_URL}/models/metrics`);
      if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
      return res.json();
    },
  });

  if (dash.isLoading) return <Spinner label="Loading analytics…" />;
  if (dash.error) return <ErrorBox error={dash.error as Error} />;
  if (!dash.data) return null;

  const { charts, kpis } = dash.data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Analytics & Model Performance</h1>
        <p className="text-sm text-muted">
          Portfolio distributions and held-out evaluation metrics for the three production models
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Scored Customers" value={kpis.total_leads} />
        <Stat
          label="Predicted Conv. Rate"
          value={`${kpis.predicted_conversion_rate}%`}
          accent="text-success"
        />
        <Stat
          label="Train / Test Split"
          value={metrics.data ? `${metrics.data.n_train} / ${metrics.data.n_test}` : "—"}
        />
        <Stat
          label="Models Live"
          value={
            metrics.data ? Object.values(metrics.data.loaded).filter(Boolean).length + " / 3" : "—"
          }
          accent="text-primary"
        />
      </div>

      {metrics.data && (
        <div className="grid gap-4 lg:grid-cols-3">
          {Object.entries(metrics.data.models).map(([name, vals]) => (
            <Section
              key={name}
              title={MODEL_TITLES[name] ?? name}
              right={
                <span
                  className={`badge ${metrics.data!.loaded[name] ? "bg-success/15 text-success" : "bg-warm/15 text-warm"}`}
                >
                  {metrics.data!.loaded[name] ? "serving" : "rules fallback"}
                </span>
              }
            >
              <div className="space-y-2 text-sm">
                {Object.entries(vals).map(([k, v]) => (
                  <div key={k} className="flex justify-between border-b border-border/50 pb-2">
                    <span className="text-muted">{METRIC_LABELS[k] ?? k}</span>
                    <span className="font-semibold">{fmtMetric(k, v)}</span>
                  </div>
                ))}
              </div>
            </Section>
          ))}
        </div>
      )}
      {metrics.error && (
        <p className="card text-sm text-warm">
          Model metrics unavailable: train models via <code>ml/train.py</code>.
        </p>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Section title="Intent Distribution">
          <SimpleBar data={charts.intent_distribution ?? []} x="bucket" y="count" color="#d97706" />
        </Section>
        <Section title="Risk Grade Distribution">
          <SimpleBar data={charts.risk_distribution ?? []} x="grade" y="count" color="#e11d48" />
        </Section>
        <Section title="Income Histogram">
          <SimpleBar data={charts.income_histogram ?? []} x="range" y="count" color="#059669" />
        </Section>
        <Section title="Recommended Loan Mix">
          <DonutChart data={charts.loan_distribution ?? []} nameKey="product" valueKey="count" />
        </Section>
      </div>
    </div>
  );
}
