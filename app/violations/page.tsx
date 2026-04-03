import Link from "next/link";

import { Badge, EmptyState, PageHeader, SectionLabel, SurfaceCard } from "@/components/ui";
import { loadAttribution, loadContracts, loadViolations } from "@/lib/data/artifacts";
import { formatNumber, formatPercent, severityTone } from "@/lib/utils";

function firstValue(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function buildFilterHref(
  current: { severity?: string; contract?: string; source?: string },
  next: Partial<{ severity: string; contract: string; source: string }>,
) {
  const params = new URLSearchParams();
  const merged = { ...current, ...next };

  if (merged.severity && merged.severity !== "ALL") {
    params.set("severity", merged.severity);
  }

  if (merged.contract && merged.contract !== "ALL") {
    params.set("contract", merged.contract);
  }

  if (merged.source && merged.source !== "ALL") {
    params.set("source", merged.source);
  }

  const query = params.toString();
  return query ? `/violations?${query}` : "/violations";
}

export default async function ViolationsPage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const resolved = (await searchParams) ?? {};
  const severity = firstValue(resolved.severity) ?? "ALL";
  const contract = firstValue(resolved.contract) ?? "ALL";
  const source = firstValue(resolved.source) ?? "ALL";

  const [violations, contracts, attribution] = await Promise.all([
    loadViolations(),
    loadContracts(),
    loadAttribution(),
  ]);

  if (!violations.length) {
    return (
      <EmptyState
        description="No machine-readable violation log entries were found."
        expectedFile="violation_log/violations.jsonl"
        title="No violations found"
      />
    );
  }

  const filtered = violations.filter((violation) => {
    const severityMatch = severity === "ALL" || violation.severity === severity;
    const contractMatch = contract === "ALL" || violation.contract_id === contract;
    const sourceMatch = source === "ALL" || violation.sourceKind === source;
    return severityMatch && contractMatch && sourceMatch;
  });

  const attributionLookup = new Map(
    (attribution.attributions ?? []).map((item) => [item.check_id, item.blame_chain?.[0]?.file_path ?? null]),
  );

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Violations"
        title="Every logged failure in one place"
        description={
          <p>
            This page reads the violation log directly, then layers on filters and blame-chain links so the
            reviewer can move from failure detection to investigation without losing the machine-readable source.
          </p>
        }
        aside={
          <SurfaceCard>
            <SectionLabel title={`${violations.length} log entries`} subtitle="Injected vs real is inferred from the matching validation report artifact." />
            <div className="mt-4 flex flex-wrap gap-2">
              <Badge tone="danger">{formatNumber(violations.filter((item) => item.severity === "CRITICAL").length)} critical</Badge>
              <Badge tone="warning">{formatNumber(violations.filter((item) => item.severity === "HIGH").length)} high</Badge>
            </div>
          </SurfaceCard>
        }
      />

      <SurfaceCard>
        <SectionLabel title="Filters" subtitle="Server-side filters keep the page simple and deterministic." />
        <div className="mt-5 space-y-4">
          <div className="flex flex-wrap gap-2">
            {["ALL", "CRITICAL", "HIGH", "MEDIUM"].map((value) => (
              <Link
                className="rounded-full border border-[var(--line)] bg-white/80 px-4 py-2 text-sm font-medium text-[var(--ink)] transition-colors hover:border-[var(--accent)]"
                href={buildFilterHref({ severity, contract, source }, { severity: value })}
                key={value}
              >
                Severity: {value}
              </Link>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            {["ALL", ...contracts.map((item) => item.id)].map((value) => (
              <Link
                className="rounded-full border border-[var(--line)] bg-white/80 px-4 py-2 text-sm font-medium text-[var(--ink)] transition-colors hover:border-[var(--accent)]"
                href={buildFilterHref({ severity, contract, source }, { contract: value })}
                key={value}
              >
                Contract: {value}
              </Link>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            {["ALL", "Injected test", "Real finding"].map((value) => (
              <Link
                className="rounded-full border border-[var(--line)] bg-white/80 px-4 py-2 text-sm font-medium text-[var(--ink)] transition-colors hover:border-[var(--accent)]"
                href={buildFilterHref({ severity, contract, source }, { source: value })}
                key={value}
              >
                Source: {value}
              </Link>
            ))}
          </div>
        </div>
      </SurfaceCard>

      <div className="space-y-4">
        {filtered.map((violation) => (
          <SurfaceCard key={violation.id}>
            <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={severityTone(violation.severity)}>{violation.severity ?? "Unknown"}</Badge>
                  <Badge tone="neutral">{violation.contract_id}</Badge>
                  <Badge tone={violation.sourceKind === "Injected test" ? "warning" : "info"}>{violation.sourceKind}</Badge>
                </div>
                <h2 className="font-display text-2xl text-[var(--ink)]">
                  {violation.field ?? "Unknown field"} • {violation.check_type ?? "Unknown check"}
                </h2>
                <p className="max-w-3xl text-sm leading-7 text-[var(--muted)]">{violation.message}</p>
              </div>
              <div className="space-y-2 text-sm text-[var(--muted)]">
                <p>
                  Mode: <span className="font-semibold text-[var(--ink)]">{violation.validation_mode ?? "Unknown"}</span>
                </p>
                <p>
                  Action: <span className="font-semibold text-[var(--ink)]">{violation.action ?? "Unknown"}</span>
                </p>
                <p>
                  Failing rows:{" "}
                  <span className="font-semibold text-[var(--ink)]">
                    {formatNumber(violation.records_failing ?? null)} / {formatNumber(violation.records_total ?? null)}
                  </span>
                </p>
                <p>
                  Failing percent:{" "}
                  <span className="font-semibold text-[var(--ink)]">{formatPercent(violation.failing_percent ?? null, 2)}</span>
                </p>
              </div>
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              {violation.reportSlug ? (
                <Link
                  className="rounded-full border border-[var(--line)] bg-white/80 px-4 py-2 text-sm font-medium text-[var(--ink)] transition-colors hover:border-[var(--accent)]"
                  href={`/validations/${violation.reportSlug}`}
                >
                  Open validation report
                </Link>
              ) : null}
              <Link
                className="rounded-full border border-[var(--line)] bg-white/80 px-4 py-2 text-sm font-medium text-[var(--ink)] transition-colors hover:border-[var(--accent)]"
                href="/attribution"
              >
                Open attribution
              </Link>
              {violation.check_id && attributionLookup.get(violation.check_id) ? (
                <Badge tone="info">Top blame candidate: {attributionLookup.get(violation.check_id)}</Badge>
              ) : null}
            </div>
          </SurfaceCard>
        ))}
      </div>
    </div>
  );
}
