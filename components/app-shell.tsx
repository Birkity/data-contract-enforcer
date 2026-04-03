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
  const architectureLabels = [
    {
      tone: "info" as const,
      label:
        architecture?.enforcement_boundary === "consumer"
          ? "Consumer boundary"
          : architecture?.enforcement_boundary ?? "Consumer boundary",
    },
    {
      tone: "warning" as const,
      label:
        architecture?.blast_radius_primary_source === "contract_registry"
          ? "Registry-first blast radius"
          : architecture?.blast_radius_primary_source ?? "Registry-first blast radius",
    },
    {
      tone: "neutral" as const,
      label:
        architecture?.lineage_role === "enrichment_only"
          ? "Lineage enrichment"
          : architecture?.lineage_role ?? "Lineage enrichment",
    },
    {
      tone: "success" as const,
      label:
        architecture?.schema_evolution_role === "producer_side_ci_gate"
          ? "Producer-side CI gate"
          : architecture?.schema_evolution_role ?? "Producer-side CI gate",
    },
  ];

  return (
    <div className="relative min-h-screen overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(22,98,196,0.18),transparent_26%),radial-gradient(circle_at_top_right,rgba(15,109,132,0.14),transparent_30%),linear-gradient(180deg,rgba(250,252,255,0.9),rgba(237,243,249,0.98))]" />
      <div className="relative">
        <header className="sticky top-0 z-20 border-b border-[var(--line)] bg-[rgba(248,251,255,0.88)] backdrop-blur-xl">
          <div className="mx-auto max-w-7xl px-6 py-5">
            <div className="flex flex-col gap-5">
              <div className="grid gap-5 xl:grid-cols-[1.5fr_1fr]">
                <div className="rounded-[28px] border border-[var(--line)] bg-[rgba(255,255,255,0.8)] px-6 py-5 shadow-[0_18px_50px_var(--shadow)]">
                  <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--accent)]">
                    Operational review console
                  </p>
                  <Link
                    className="font-display text-3xl leading-tight text-[var(--ink)] transition-opacity hover:opacity-80 sm:text-4xl"
                    href="/"
                  >
                    TRP Week 7 Data Contract Enforcer
                  </Link>
                  <p className="mt-3 max-w-3xl text-sm leading-7 text-[var(--muted)]">
                    A read-only operational view over the real Week 7 artifact set. It helps technical
                    reviewers and client stakeholders inspect contract coverage, validation outcomes,
                    blast radius, and recommended actions without replacing the CLI workflow underneath.
                  </p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Link
                      className="rounded-full bg-[var(--ink)] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[var(--accent-strong)]"
                      href="/report"
                    >
                      Open system report
                    </Link>
                    <Link
                      className="rounded-full border border-[var(--line-strong)] bg-white/85 px-4 py-2 text-sm font-semibold text-[var(--ink)] transition-colors hover:border-[var(--accent)] hover:text-[var(--accent)]"
                      href="/attribution"
                    >
                      Inspect blast radius
                    </Link>
                  </div>
                </div>
                <div className="rounded-[28px] border border-[var(--line)] bg-[rgba(255,255,255,0.76)] px-6 py-5 shadow-[0_18px_50px_var(--shadow)]">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--muted)]">
                        Architecture snapshot
                      </p>
                      <p className="mt-2 text-sm leading-7 text-[var(--muted)]">
                        The interface follows the updated Week 7 operating model: consumer-boundary
                        enforcement, registry-first blast radius, lineage enrichment, and producer-side
                        schema gating.
                      </p>
                    </div>
                    <p className="text-right text-xs uppercase tracking-[0.24em] text-[var(--muted)]">
                      {generatedAt ? `Refreshed ${formatDate(generatedAt)}` : "Refresh unavailable"}
                    </p>
                  </div>
                  <div className="mt-5 flex flex-wrap gap-2">
                    {architectureLabels.map((item) => (
                      <Badge key={item.label} tone={item.tone}>
                        {item.label}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
              <nav className="flex flex-wrap gap-2 rounded-full border border-[var(--line)] bg-[rgba(255,255,255,0.68)] p-2 shadow-[0_10px_30px_var(--shadow)]">
                {navItems.map((item) => (
                  <Link
                    className="rounded-full border border-transparent bg-white/76 px-4 py-2 text-sm font-medium text-[var(--ink)] transition-colors hover:border-[var(--accent-soft)] hover:bg-white hover:text-[var(--accent)]"
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
        <footer className="border-t border-[var(--line)] bg-[rgba(255,255,255,0.76)]">
          <div className="mx-auto flex max-w-7xl flex-col gap-2 px-6 py-6 text-sm text-[var(--muted)] sm:flex-row sm:items-center sm:justify-between">
            <p>
              Frontend consumes local JSON, JSONL, and YAML artifacts only. It is a presentation layer,
              not a replacement for the contract-enforcement CLI.
            </p>
            <p>{generatedAt ? `Latest report refresh: ${formatDate(generatedAt)}` : "Latest report refresh unavailable"}</p>
          </div>
        </footer>
      </div>
    </div>
  );
}
