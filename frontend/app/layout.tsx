import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import FirebaseAnalytics from "@/components/firebase-analytics";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "LendIQ — Retail Lending Intelligence",
  description: "AI-powered pre-qualified lead generation from Account Aggregator data",
};

const nav = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/analytics", label: "Analytics" },
  { href: "/chat", label: "AI Advisor" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <FirebaseAnalytics />
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-primary focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-white focus:outline-none focus:ring-2 focus:ring-white"
        >
          Skip to main content
        </a>
        <Providers>
          <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur">
            <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-4">
              <Link
                href="/"
                className="flex items-center gap-2 rounded font-bold tracking-tight focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              >
                <span
                  className="grid h-7 w-7 place-items-center rounded-lg bg-primary text-sm"
                  aria-hidden="true"
                >
                  ₹
                </span>
                LendIQ
              </Link>
              <nav aria-label="Main" className="flex gap-4 text-sm text-muted">
                {nav.map((n) => (
                  <Link
                    key={n.href}
                    href={n.href}
                    className="rounded transition hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                  >
                    {n.label}
                  </Link>
                ))}
              </nav>
              <span className="ml-auto rounded-full border border-border px-3 py-1 text-xs text-muted">
                AA-powered · Explainable AI
              </span>
            </div>
          </header>
          <main
            id="main-content"
            tabIndex={-1}
            className="mx-auto max-w-7xl px-4 py-6 outline-none"
          >
            {children}
          </main>
        </Providers>
      </body>
    </html>
  );
}
