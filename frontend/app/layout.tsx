import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
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
    <html lang="en" className="dark">
      <body>
        <Providers>
          <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur">
            <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-4">
              <Link href="/" className="flex items-center gap-2 font-bold tracking-tight">
                <span className="grid h-7 w-7 place-items-center rounded-lg bg-primary text-sm">₹</span>
                LendIQ
              </Link>
              <nav className="flex gap-4 text-sm text-muted">
                {nav.map((n) => (
                  <Link key={n.href} href={n.href} className="transition hover:text-zinc-100">
                    {n.label}
                  </Link>
                ))}
              </nav>
              <span className="ml-auto rounded-full border border-border px-3 py-1 text-xs text-muted">
                AA-powered · Explainable AI
              </span>
            </div>
          </header>
          <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
