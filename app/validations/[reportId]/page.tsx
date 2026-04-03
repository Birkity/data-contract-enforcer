import { notFound } from "next/navigation";

import { Badge, PageHeader, SectionLabel, SurfaceCard } from "@/components/ui";
import { loadValidationReports } from "@/lib/data/artifacts";
import { decisionTone, formatDate, formatNumber, formatPercent, severityTone } from "@/lib/utils";

export default async function ValidationDetailPage({
  params,
}: {
  params: Promise<{ reportId: string }>;
}) {
  const { reportId } = await params;
  const reports = await loadValidationReports();
  const report = reports.find((item) => item.slug === reportId);

  if (!report) {
    notFound();
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Validation detail"
        title={report.fileName}
        description={
          <p>
            Validation reports are consumer-boundary evidence. They show the exact checks, severities, and
            blocking behavior that the ValidationRunner emitted for this artifact.
          </p>
        }
        aside={
          <SurfaceCard>
            <div className="space-y-3">
              <Badge tone={decisionTone(report.decision)}>{report.decision ?? "Unknown decision"}</Badge>
              <p className="text-sm leading-7 text-[var(--muted)]">
                Mode {report.validation_mode ?? "unknown"} • {formatDate(report.run_timestamp)}
              </p>
              <p className="text-sm leading-7 text-[var(--muted)]">
                {report.passed}/{report.total_checks} checks passed with {report.failed} failures.
              </p>
            </div>
          </SurfaceCard>
        }
      />

      <div className="grid gap-4 md:grid-cols-4">
        <SurfaceCard>
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Contract</p>
          <p className="mt-3 font-display text-2xl text-[var(--ink)]">{report.contract_id}</p>
        </SurfaceCard>
        <SurfaceCard>
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Failed checks</p>
          <p className="mt-3 font-display text-2xl text-[var(--ink)]">{formatNumber(report.failed)}</p>
        </SurfaceCard>
        <SurfaceCard>
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Errored checks</p>
          <p className="mt-3 font-display text-2xl text-[var(--ink)]">{formatNumber(report.errored)}</p>
        </SurfaceCard>
        <SurfaceCard>
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Profiled rows</p>
          <p className="mt-3 font-display text-2xl text-[var(--ink)]">{formatNumber(report.profiled_row_count ?? null)}</p>
        </SurfaceCard>
      </div>

      <SurfaceCard className="overflow-hidden p-0">
        <div className="border-b border-[var(--line)] px-6 py-5">
          <SectionLabel
            title="Failing checks"
            subtitle="Technical detail stays one level down so the page is still easy to scan."
          />
        </div>
        {report.failingChecks.length ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-[var(--line)]">
              <thead className="bg-[var(--paper)]/90 text-left text-xs uppercase tracking-[0.2em] text-[var(--muted)]">
                <tr>
                  <th className="px-6 py-4">Check</th>
                  <th className="px-6 py-4">Severity</th>
                  <th className="px-6 py-4">Actual vs expected</th>
                  <th className="px-6 py-4">Failing rows</th>
                  <th className="px-6 py-4">Sample values</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--line)] bg-white/70">
                {report.failingChecks.map((result) => (
                  <tr className="align-top" key={result.check_id}>
                    <td className="px-6 py-5">
                      <div className="space-y-2">
                        <p className="font-semibold text-[var(--ink)]">{result.check_id}</p>
                        <p className="text-sm leading-6 text-[var(--muted)]">{result.message}</p>
                      </div>
                    </td>
                    <td className="px-6 py-5">
                      <Badge tone={severityTone(result.severity)}>{result.severity ?? "Unknown"}</Badge>
                    </td>
                    <td className="px-6 py-5 text-sm leading-6 text-[var(--muted)]">
                      <p>Actual: {result.actual_value ?? "—"}</p>
                      <p>Expected: {result.expected ?? "—"}</p>
                    </td>
                    <td className="px-6 py-5 text-sm leading-6 text-[var(--ink)]">
                      <p>{formatNumber(result.records_failing ?? null)} of {formatNumber(result.records_total ?? null)}</p>
                      <p className="text-[var(--muted)]">{formatPercent(result.failing_percent ?? null, 2)}</p>
                    </td>
                    <td className="px-6 py-5 text-sm leading-6 text-[var(--muted)]">
                      {result.sample_failing?.length ? result.sample_failing.join(" • ") : "No sample values recorded"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="px-6 py-8">
            <Badge tone="success">No failing checks</Badge>
            <p className="mt-3 text-sm leading-7 text-[var(--muted)]">
              This validation report passed cleanly, so there is no failure table to show.
            </p>
          </div>
        )}
      </SurfaceCard>
    </div>
  );
}
