import Link from "next/link";
import { ArrowRight, Brain, LineChart, ShieldCheck, Sparkles, Wallet, Zap } from "lucide-react";

const features = [
  {
    icon: Wallet,
    title: "Income Estimation",
    href: "/analytics",
    desc: "AA transaction intelligence estimates true income, expenses and disposable surplus with a confidence score.",
  },
  {
    icon: Zap,
    title: "Borrowing Intent",
    href: "/analytics",
    desc: "Life-event signals — property tokens, vehicle bookings, loan enquiries — predict 30/60/90-day application probability.",
  },
  {
    icon: LineChart,
    title: "Lead Scoring",
    href: "/dashboard",
    desc: "Income × intent × capacity × risk fused into a 0–100 score with HOT / WARM / COLD tiers.",
  },
  {
    icon: ShieldCheck,
    title: "Risk Engine",
    href: "/analytics",
    desc: "PD estimation, risk grades A–E, fraud indicators and liquidity risk from banking behaviour.",
  },
  {
    icon: Brain,
    title: "Explainable AI",
    href: "/dashboard",
    desc: "SHAP drivers behind every prediction — underwriters see the WHY, not a black box.",
  },
  {
    icon: Sparkles,
    title: "GenAI Advisor",
    href: "/chat",
    desc: "Gemini-powered underwriting assistant grounded in the scored profile. What-if simulation included.",
  },
];

export default function Landing() {
  return (
    <div className="space-y-16 py-10">
      <section className="mx-auto max-w-3xl text-center">
        <p className="mb-4 inline-block rounded-full border border-primary/40 bg-primary/10 px-4 py-1 text-xs text-primary">
          Banking Hackathon · Account Aggregator × AI
        </p>
        <h1 className="text-5xl font-extrabold leading-tight tracking-tight">
          Find borrowers <span className="text-primary">before they apply</span>
        </h1>
        <p className="mt-5 text-lg text-muted">
          LendIQ turns Account Aggregator data into pre-qualified Personal, Home, Mortgage and Auto
          loan leads — with estimated income, repayment capacity, borrowing intent and default risk,
          all explainable.
        </p>
        <div className="mt-8 flex justify-center gap-4">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-3 font-semibold text-white transition hover:bg-primary/85"
          >
            Open Dashboard <ArrowRight size={18} aria-hidden="true" />
          </Link>
          <Link
            href="/chat"
            className="rounded-lg border border-border px-6 py-3 font-semibold text-muted transition hover:text-foreground"
          >
            Ask the AI Advisor
          </Link>
        </div>
      </section>

      <section
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
        aria-label="Platform capabilities"
      >
        {features.map((f) => (
          <Link
            key={f.title}
            href={f.href}
            className="card group transition hover:border-primary/60 hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            <f.icon className="mb-3 text-primary" size={22} aria-hidden="true" />
            <h3 className="flex items-center gap-2 font-semibold">
              {f.title}
              <ArrowRight
                size={14}
                className="opacity-0 transition group-hover:opacity-100"
                aria-hidden="true"
              />
            </h3>
            <p className="mt-1 text-sm text-muted">{f.desc}</p>
          </Link>
        ))}
      </section>

      <section className="card mx-auto max-w-4xl text-center">
        <h2 className="text-xl font-bold">Target outcome</h2>
        <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
          <div>
            <p className="text-3xl font-extrabold text-success">&gt;30%</p>
            <p className="text-muted">lead conversion</p>
          </div>
          <div>
            <p className="text-3xl font-extrabold text-success">-60%</p>
            <p className="text-muted">manual verification</p>
          </div>
          <div>
            <p className="text-3xl font-extrabold text-success">min</p>
            <p className="text-muted">not days, to approve</p>
          </div>
        </div>
      </section>
    </div>
  );
}
