import Link from "next/link";

import { Badge, EmptyState, PageHeader, SectionLabel, SurfaceCard } from "@/components/ui";
import { loadValidationReports } from "@/lib/data/artifacts";
import { decisionTone, formatDate, formatNumber } from "@/lib/utils";

export default async function ValidationsPage() {
  const reports = await loadValidationReports();

  if (!reports.length) {
    return (
      <EmptyState
        description="No validation report JSON files were found for the dashboard."
        expectedFile="validation_reports/*.json"
        title="No validation runs found"
      />
    );
  }

  const totalFailed = reports.reduce((sum, report) => sum + report.failed, 0);
  const totalBlocked = reports.reduce((sum, report) => sum + (report.blocking ? 1 : 0), 0);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Validation runs"
        title="Clean and violated runs side by side"
        description={
          <p>
            These reports come straight from the ValidationRunner. They show how the same contract behaves
            under clean data and injected breakage across AUDIT, WARN, and ENFORCE modes.
          </p>
        }
        aside={
          <SurfaceCard>
            <SectionLabel title={`${reports.length} runs captured`} subtitle="Read-only view of the machine-generated report files." />
            <div className="mt-4 flex flex-wrap gap-2">
              <Badge tone="success">{formatNumber(reports.filter((report) => report.failed === 0).length)} clean</Badge>
              <Badge tone="warning">{formatNumber(totalFailed)} failed checks</Badge>
              <Badge tone={totalBlocked ? "danger" : "success"}>{formatNumber(totalBlocked)} blocking runs</Badge>
            </div>
          </SurfaceCard>
        }
      />

      <SurfaceCard className="overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-[var(--line)]">
            <thead className="bg-[var(--paper)]/90 text-left text-xs uppercase tracking-[0.2em] text-[var(--muted)]">
              <tr>
                <th className="px-6 py-4">Run</th>
                <th className="px-6 py-4">Mode</th>
                <th className="px-6 py-4">Decision</th>
                <th className="px-6 py-4">Checks</th>
                <th className="px-6 py-4">Failures</th>
                <th className="px-6 py-4">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--line)] bg-white/70">
              {reports.map((report) => (
                <tr className="align-top" key={report.report_id}>
                  <td className="px-6 py-5">
                    <div className="space-y-2">
                      <Link className="font-semibold text-[var(--ink)] hover:text-[var(--accent)]" href={`/validations/${report.slug}`}>
                        {report.fileName}
                      </Link>
                      <p className="text-sm text-[var(--muted)]">{report.sourceLabel}</p>
                    </div>
                  </td>
                  <td className="px-6 py-5">
                    <Badge tone="info">{report.validation_mode ?? "Unknown mode"}</Badge>
                  </td>
                  <td className="px-6 py-5">
                    <Badge tone={decisionTone(report.decision)}>{report.decision ?? "Unknown decision"}</Badge>
                  </td>
                  <td className="px-6 py-5 text-sm text-[var(--ink)]">
                    {report.passed}/{report.total_checks} passed
                  </td>
                  <td className="px-6 py-5">
                    <div className="flex flex-wrap gap-2">
                      <Badge tone={report.failed ? "danger" : "success"}>
                        {report.failed} failed
                      </Badge>
                      {report.blocking ? <Badge tone="danger">Blocking</Badge> : <Badge tone="neutral">Non-blocking</Badge>}
                    </div>
                  </td>
                  <td className="px-6 py-5 text-sm text-[var(--muted)]">{formatDate(report.run_timestamp)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SurfaceCard>
    </div>
  );
}
