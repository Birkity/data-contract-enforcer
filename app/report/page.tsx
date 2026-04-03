import { Badge, EmptyState, InlinePath, PageHeader, SectionLabel, SurfaceCard } from "@/components/ui";
import { loadReportData } from "@/lib/data/artifacts";
import { formatNumber, formatPercent, severityTone } from "@/lib/utils";

export default async function ReportPage() {
  const reportData = await loadReportData();

  if (!reportData) {
    return (
      <EmptyState
        description="The final report artifact is not available yet."
        expectedFile="enforcer_report/report_data.json"
        title="No final report data found"
      />
    );
  }

  const blastRadius = (reportData.blast_radius as Record<string, unknown> | undefined) ?? {};
  const validationSummary = (reportData.validation_summary as Record<string, unknown> | undefined) ?? {};
  const schemaSummary = (reportData.schema_evolution_summary as Record<string, unknown> | undefined) ?? {};
  const aiSummary = (reportData.ai_risk_summary as Record<string, unknown> | undefined) ?? {};
  const recommendedActions = (reportData.recommended_actions as string[] | undefined) ?? [];
  const knownLimitations = (((reportData.artifact_state as Record<string, unknown> | undefined)?.known_limitations as string[] | undefined) ?? []);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Client walkthrough report"
        title="Explain the system without opening the CLI"
        description={
          <p>
            This page renders the generated enforcer report in business language. It is still grounded in the
            actual machine-readable artifact, but it prioritizes stakeholder clarity over raw file structure.
          </p>
        }
        aside={
          <SurfaceCard className="bg-[linear-gradient(145deg,rgba(255,255,255,0.92),rgba(240,229,214,0.92))]">
            <Badge tone="success">Data health score</Badge>
            <p className="mt-4 font-display text-6xl leading-none text-[var(--ink)]">
              {formatNumber((reportData.data_health_score as number | undefined) ?? null)}
            </p>
            <p className="mt-3 text-sm leading-7 text-[var(--muted)]">
              Submission ready: {String(((reportData.artifact_state as Record<string, unknown> | undefined)?.submission_ready as boolean | undefined) ?? false)}
            </p>
          </SurfaceCard>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SurfaceCard>
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Baseline status</p>
          <p className="mt-3 font-display text-2xl text-[var(--ink)]">
            {String(((validationSummary.baseline as Record<string, unknown> | undefined)?.decision as string | undefined) ?? "Unknown")}
          </p>
        </SurfaceCard>
        <SurfaceCard>
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Injected failures</p>
          <p className="mt-3 font-display text-2xl text-[var(--ink)]">
            {formatNumber(Number(((reportData.violations_summary as Record<string, unknown> | undefined)?.injected_validation_failures ?? 0)))}
          </p>
        </SurfaceCard>
        <SurfaceCard>
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Affected subscribers</p>
          <p className="mt-3 font-display text-2xl text-[var(--ink)]">
            {formatNumber(Number(blastRadius.subscriber_count ?? 0))}
          </p>
        </SurfaceCard>
        <SurfaceCard>
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Schema gate</p>
          <p className="mt-3 font-display text-2xl text-[var(--ink)]">
            {String(schemaSummary.decision ?? "Unknown")}
          </p>
        </SurfaceCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <SurfaceCard>
          <SectionLabel title="What broke?" subtitle="The top validation failures surfaced in the final report artifact." />
          <div className="mt-5 space-y-4">
            {((((validationSummary.injected_violation as Record<string, unknown> | undefined)?.key_failures as Array<Record<string, unknown>> | undefined) ?? [])).map(
              (failure) => (
                <div className="rounded-3xl border border-[var(--line)] bg-white/75 p-5" key={String(failure.check_id)}>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={severityTone(String(failure.severity ?? ""))}>{String(failure.severity ?? "Unknown")}</Badge>
                    <Badge tone="neutral">{String(failure.check_id ?? "Unknown check")}</Badge>
                  </div>
                  <p className="mt-4 text-sm leading-7 text-[var(--muted)]">{String(failure.message ?? "No message recorded.")}</p>
                  <p className="mt-3 text-sm font-semibold text-[var(--ink)]">
                    Failing rows: {formatPercent(Number(failure.failing_percent ?? 0), 2)}
                  </p>
                </div>
              ),
            )}
          </div>
        </SurfaceCard>

        <SurfaceCard>
          <SectionLabel title="How bad is it?" subtitle="Business-level risk summary pulled from the generated report." />
          <div className="mt-5 space-y-4 text-sm leading-7 text-[var(--muted)]">
            <p>
              Blast radius primary source: <span className="font-semibold text-[var(--ink)]">{String(((reportData.architecture as Record<string, unknown> | undefined)?.blast_radius_primary_source ?? "Unknown"))}</span>
            </p>
            <p>
              Lineage role: <span className="font-semibold text-[var(--ink)]">{String(((reportData.architecture as Record<string, unknown> | undefined)?.lineage_role ?? "Unknown"))}</span>
            </p>
            <p>
              AI risk summary: <span className="font-semibold text-[var(--ink)]">{String(aiSummary.overall_status ?? "Unknown")}</span>
            </p>
            <p>
              Top candidate file: <span className="font-semibold text-[var(--ink)]">{String(blastRadius.top_candidate_file ?? "Unknown")}</span>
            </p>
            <p>
              Schema recommendation: <span className="font-semibold text-[var(--ink)]">{String(schemaSummary.recommendation ?? "No recommendation recorded.")}</span>
            </p>
          </div>
        </SurfaceCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <SurfaceCard>
          <SectionLabel title="Who is affected?" subtitle="Primary audience from the contract registry." />
          <div className="mt-5 space-y-4">
            {(((blastRadius.affected_subscribers as Array<Record<string, unknown>> | undefined) ?? [])).map((subscriber) => (
              <div className="rounded-3xl border border-[var(--line)] bg-white/75 p-5" key={String(subscriber.subscriber_id)}>
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-semibold text-[var(--ink)]">{String(subscriber.subscriber_id)}</p>
                  <Badge tone="info">{String(subscriber.validation_mode ?? "mode unavailable")}</Badge>
                </div>
                <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
                  {String((subscriber.contact as Record<string, unknown> | undefined)?.owner ?? "Unknown owner")}
                </p>
                <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
                  Fields consumed: {((subscriber.fields_consumed as string[] | undefined) ?? []).join(", ") || "Not documented"}
                </p>
              </div>
            ))}
          </div>
        </SurfaceCard>

        <SurfaceCard>
          <SectionLabel title="What should we do?" subtitle="Recommended actions surfaced by the generated report." />
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
      </div>

      <SurfaceCard>
        <SectionLabel title="Real artifact anchors" subtitle="Useful file paths for a reviewer or client walkthrough." />
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          {[
            "generated_contracts/week3_extractions.yaml",
            "validation_reports/injected_violation.json",
            "violation_log/blame_chain.json",
            "schema_snapshots/compatibility_report.json",
            "enforcer_report/ai_metrics.json",
            "enforcer_report/report_data.json",
          ].map((filePath) => (
            <div className="rounded-2xl border border-[var(--line)] bg-white/75 px-4 py-3" key={filePath}>
              <InlinePath>{filePath}</InlinePath>
            </div>
          ))}
        </div>
        {knownLimitations.length ? (
          <div className="mt-6 rounded-3xl border border-[var(--line)] bg-[var(--paper)]/85 p-5">
            <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Known limitations</p>
            <div className="mt-4 space-y-3 text-sm leading-7 text-[var(--muted)]">
              {knownLimitations.map((limitation) => (
                <p key={limitation}>{limitation}</p>
              ))}
            </div>
          </div>
        ) : null}
      </SurfaceCard>
    </div>
  );
}
