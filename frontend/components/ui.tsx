"use client";
/** Minimal shadcn-style primitives used across pages. */

export function Stat({ label, value, accent }: { label: string; value: string | number; accent?: string }) {
  return (
    <div className="card">
      <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${accent ?? ""}`}>{value}</p>
    </div>
  );
}

export function Section({ title, children, right }: {
  title: string; children: React.ReactNode; right?: React.ReactNode;
}) {
  return (
    <section className="card">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-semibold">{title}</h2>
        {right}
      </div>
      {children}
    </section>
  );
}

export function Meter({ value, max = 100, color = "bg-primary" }: { value: number; max?: number; color?: string }) {
  return (
    <div className="h-2 w-full rounded-full bg-border">
      <div className={`h-2 rounded-full ${color}`} style={{ width: `${Math.min(100, (value / max) * 100)}%` }} />
    </div>
  );
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 py-16 justify-center text-muted">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      {label}
    </div>
  );
}

export function ErrorBox({ error }: { error: Error }) {
  return (
    <div className="card border-hot/40 text-sm">
      <p className="font-semibold text-hot">Backend unreachable</p>
      <p className="mt-1 text-muted">{error.message}</p>
      <p className="mt-2 text-muted">Start it with: <code className="rounded bg-surface px-1">uvicorn app.main:app --reload</code></p>
    </div>
  );
}
