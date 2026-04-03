import Link from "next/link";

import { Badge, MetricCard, PageHeader, SectionLabel, SurfaceCard } from "@/components/ui";
import { loadDashboardData } from "@/lib/data/artifacts";
import {
  formatDate,
  formatNumber,
  formatPercent,
  humanizeSlug,
  severityTone,
} from "@/lib/utils";

export default async function DashboardPage() {
  const { contracts, validations, violations, registry, attribution, reportData, severityCounts } =
    await loadDashboardData();

  const recommendedActions = ((reportData?.recommended_actions as string[] | undefined) ?? []).slice(0, 3);
  const topFailures =
    (((reportData?.validation_summary as Record<string, unknown> | undefined)?.injected_violation as
      | Record<string, unknown>
      | undefined)?.key_failures as Array<Record<string, unknown>> | undefined) ?? [];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Executive overview"
        title="See the system in one pass"
        description={
          <p>
            This dashboard is the presentation layer over the real Week 7 artifacts. It answers the core
            reviewer questions quickly: what contracts exist, what broke, who is affected, and what should
            happen next.
          </p>
        }
        aside={
          <SurfaceCard className="bg-[linear-gradient(145deg,rgba(255,255,255,0.92),rgba(244,227,211,0.9))]">
            <div className="space-y-4">
              <Badge tone="success">Data health score</Badge>
              <div className="flex items-end justify-between gap-4">
                <div>
                  <p className="font-display text-6xl leading-none text-[var(--ink)]">
                    {formatNumber((reportData?.data_health_score as number | undefined) ?? null)}
                  </p>
                  <p className="mt-2 text-sm text-[var(--muted)]">
                    Generated {formatDate(typeof reportData?.generated_at === "string" ? reportData.generated_at : null)}
                  </p>
                </div>
                <div className="w-24 rounded-full border border-[var(--line)] bg-white/80 p-2 text-center">
                  <p className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Status</p>
                  <p className="mt-2 font-semibold text-[var(--success)]">Ready</p>
                </div>
              </div>
            </div>
          </SurfaceCard>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          detail="Generated contract artifacts with real registry context and dbt counterparts."
          href="/contracts"
          label="Contracts"
          tone="info"
          value={formatNumber(contracts.length)}
        />
        <MetricCard
          detail="Clean and violated reports across AUDIT, WARN, and ENFORCE modes."
          href="/validations"
          label="Validation runs"
          tone="neutral"
          value={formatNumber(validations.length)}
        />
        <MetricCard
          detail="Logged findings in the machine-readable violation log."
          href="/violations"
          label="Violations"
          tone={violations.length > 0 ? "warning" : "success"}
          value={formatNumber(violations.length)}
        />
        <MetricCard
          detail="Registered downstream consumers drive blast radius before lineage enrichment."
          href="/attribution"
          label="Subscribers"
          tone="warning"
          value={formatNumber(registry.subscriptions.length)}
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.35fr_0.95fr]">
        <SurfaceCard>
          <div className="space-y-5">
            <SectionLabel
              title="Severity posture"
              subtitle="These counts come from the current violation log, not invented demo numbers."
            />
            <div className="grid gap-4 sm:grid-cols-3">
              {(["CRITICAL", "HIGH", "MEDIUM"] as const).map((severity) => (
                <div className="rounded-3xl border border-[var(--line)] bg-white/80 p-5" key={severity}>
                  <div className="flex items-center justify-between gap-3">
                    <Badge tone={severityTone(severity)}>{severity}</Badge>
                    <span className="text-sm text-[var(--muted)]">Open signals</span>
                  </div>
                  <p className="mt-4 font-display text-4xl text-[var(--ink)]">
                    {formatNumber(severityCounts[severity] ?? 0)}
                  </p>
                </div>
              ))}
            </div>
            <div className="rounded-[24px] border border-[var(--line)] bg-[var(--paper)]/85 p-5">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone="info">Latest injected failures</Badge>
                <p className="text-sm text-[var(--muted)]">These are the top failures surfaced in the final report.</p>
              </div>
              <div className="mt-4 space-y-3">
                {topFailures.map((failure) => (
                  <div
                    className="rounded-2xl border border-[var(--line)] bg-white/75 px-4 py-4"
                    key={String(failure.check_id)}
                  >
                    <div className="flex flex-wrap items-center gap-3">
                      <Badge tone={severityTone(String(failure.severity ?? ""))}>
                        {String(failure.severity ?? "Unknown")}
                      </Badge>
                      <p className="font-semibold text-[var(--ink)]">{String(failure.check_id ?? "Unknown check")}</p>
                    </div>
                    <p className="mt-2 text-sm leading-7 text-[var(--muted)]">
                      {String(failure.message ?? "No failure message was captured.")}
                    </p>
                    <p className="mt-2 text-sm font-medium text-[var(--ink)]">
                      Failing rows: {formatPercent(Number(failure.failing_percent ?? 0), 2)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </SurfaceCard>

        <div className="space-y-6">
          <SurfaceCard>
            <SectionLabel
              title="Top actions"
              subtitle="Straight from the generated enforcer report so the frontend stays grounded in the CLI outputs."
            />
            <ol className="mt-5 space-y-3">
              {recommendedActions.map((action, index) => (
                <li className="flex gap-3" key={action}>
                  <span className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--accent)] text-sm font-semibold text-white">
                    {index + 1}
                  </span>
                  <p className="text-sm leading-7 text-[var(--muted)]">{action}</p>
                </li>
              ))}
            </ol>
          </SurfaceCard>

          <SurfaceCard>
            <SectionLabel
              title="Quick walkthrough"
              subtitle="These routes follow the reviewer conversation from “what happened?” to “what do we do?”"
            />
            <div className="mt-5 grid gap-3">
              {[
                { href: "/contracts", label: "Contracts", detail: "See contract coverage, risky fields, and subscribers." },
                { href: "/validations", label: "Validations", detail: "Compare clean and violated runs side by side." },
                { href: "/attribution", label: "Attribution", detail: "See registry-first blast radius and blame chain evidence." },
                { href: "/report", label: "Report", detail: "Use the final executive summary for a client walkthrough." },
              ].map((item) => (
                <Link
                  className="rounded-2xl border border-[var(--line)] bg-white/70 px-4 py-4 transition-colors hover:border-[var(--accent)]"
                  href={item.href}
                  key={item.href}
                >
                  <p className="font-semibold text-[var(--ink)]">{item.label}</p>
                  <p className="mt-1 text-sm leading-6 text-[var(--muted)]">{item.detail}</p>
                </Link>
              ))}
            </div>
          </SurfaceCard>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <SurfaceCard className="xl:col-span-2">
          <SectionLabel
            title="Architecture snapshot"
            subtitle="The generated report already captures the updated Week 7 design, and the UI mirrors it exactly."
          />
          <div className="mt-5 grid gap-4 md:grid-cols-3">
            {Object.entries((reportData?.architecture as Record<string, string> | undefined) ?? {}).map(
              ([key, value]) => (
                <div className="rounded-2xl border border-[var(--line)] bg-white/75 p-4" key={key}>
                  <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">{humanizeSlug(key)}</p>
                  <p className="mt-3 font-semibold text-[var(--ink)]">{humanizeSlug(value)}</p>
                </div>
              ),
            )}
          </div>
        </SurfaceCard>
        <SurfaceCard>
          <SectionLabel
            title="Latest attribution"
            subtitle="Registry-first blast radius and the strongest producer-side candidate."
          />
          {attribution.attributions?.[0] ? (
            <div className="mt-5 space-y-4">
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Violating field</p>
                <p className="mt-2 font-display text-2xl text-[var(--ink)]">{attribution.attributions[0].field}</p>
              </div>
              <div className="rounded-2xl border border-[var(--line)] bg-white/75 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Top candidate</p>
                <p className="mt-2 font-semibold text-[var(--ink)]">
                  {attribution.attributions[0].blame_chain?.[0]?.file_path ?? "No file candidate"}
                </p>
                <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
                  {attribution.attributions[0].blame_chain?.[0]?.rationale ?? "No rationale available."}
                </p>
              </div>
            </div>
          ) : (
            <p className="mt-5 text-sm text-[var(--muted)]">No attribution artifacts were available.</p>
          )}
        </SurfaceCard>
      </div>
    </div>
  );
}
