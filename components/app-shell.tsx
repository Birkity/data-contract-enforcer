import type { ReactNode } from "react";
import Link from "next/link";

import { Badge } from "@/components/ui";
import { formatDate } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Dashboard" },
  { href: "/contracts", label: "Contracts" },
  { href: "/validations", label: "Validations" },
  { href: "/violations", label: "Violations" },
  { href: "/attribution", label: "Attribution" },
  { href: "/schema-evolution", label: "Schema evolution" },
  { href: "/ai", label: "AI checks" },
  { href: "/report", label: "Report" },
];

export function AppShell({
  children,
  architecture,
  generatedAt,
}: {
  children: ReactNode;
  architecture?: {
    enforcement_boundary?: string;
    blast_radius_primary_source?: string;
    lineage_role?: string;
    schema_evolution_role?: string;
  } | null;
  generatedAt?: string | null;
}) {
  return (
    <div className="relative min-h-screen overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(210,107,48,0.18),transparent_28%),radial-gradient(circle_at_top_right,rgba(24,89,101,0.16),transparent_30%),linear-gradient(180deg,rgba(255,252,246,0.88),rgba(246,239,229,0.96))]" />
      <div className="relative">
        <header className="sticky top-0 z-20 border-b border-[var(--line)] bg-[rgba(250,244,234,0.88)] backdrop-blur-xl">
          <div className="mx-auto max-w-7xl px-6 py-6">
            <div className="flex flex-col gap-5">
              <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
                <div className="max-w-3xl space-y-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--accent)]">
                    Optional reviewer dashboard
                  </p>
                  <Link
                    className="font-display text-3xl leading-tight text-[var(--ink)] transition-opacity hover:opacity-80 sm:text-4xl"
                    href="/"
                  >
                    TRP Week 7 Data Contract Enforcer
                  </Link>
                  <p className="max-w-3xl text-sm leading-7 text-[var(--muted)]">
                    Read-only demo frontend over the real Week 7 artifacts. It explains what contracts
                    exist, what broke, who is affected, and what the next action should be without
                    replacing the CLI system underneath.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2 xl:justify-end">
                  <Badge tone="info">
                    {architecture?.enforcement_boundary ?? "consumer"} enforcement
                  </Badge>
                  <Badge tone="warning">
                    {architecture?.blast_radius_primary_source ?? "registry"} first blast radius
                  </Badge>
                  <Badge tone="neutral">
                    {architecture?.lineage_role ?? "enrichment_only"} lineage
                  </Badge>
                  <Badge tone="success">
                    {architecture?.schema_evolution_role ?? "producer_side_ci_gate"}
                  </Badge>
                </div>
              </div>
              <nav className="flex flex-wrap gap-2">
                {navItems.map((item) => (
                  <Link
                    className="rounded-full border border-[var(--line)] bg-white/70 px-4 py-2 text-sm font-medium text-[var(--ink)] transition-colors hover:border-[var(--accent)] hover:text-[var(--accent)]"
                    href={item.href}
                    key={item.href}
                  >
                    {item.label}
                  </Link>
                ))}
              </nav>
            </div>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-6 py-10">{children}</main>
        <footer className="border-t border-[var(--line)] bg-[rgba(255,255,255,0.68)]">
          <div className="mx-auto flex max-w-7xl flex-col gap-2 px-6 py-6 text-sm text-[var(--muted)] sm:flex-row sm:items-center sm:justify-between">
            <p>Frontend consumes local JSON, JSONL, and YAML artifacts only. No backend service required.</p>
            <p>{generatedAt ? `Latest report refresh: ${formatDate(generatedAt)}` : "Latest report refresh unavailable"}</p>
          </div>
        </footer>
      </div>
    </div>
  );
}
