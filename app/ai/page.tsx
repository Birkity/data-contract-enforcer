import { Badge, EmptyState, InlinePath, PageHeader, SurfaceCard } from "@/components/ui";
import { loadAiMetrics } from "@/lib/data/artifacts";
import { decisionTone, formatNumber, formatPercent, severityTone } from "@/lib/utils";

export default async function AiPage() {
  const aiMetrics = await loadAiMetrics();

  if (!aiMetrics) {
    return (
      <EmptyState
        description="AI extension metrics are not available yet for this repository state."
        expectedFile="enforcer_report/ai_metrics.json"
        title="No AI artifact found"
      />
    );
  }

  const checks = Object.entries((aiMetrics.checks as Record<string, Record<string, unknown>> | undefined) ?? {});

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="AI contract extensions"
        title="AI-specific stability signals"
        description={
          <p>
            This view stays transparent about what exists and what does not. If a metric is missing, the page
            says so. If a metric exists, it comes directly from the generated AI artifact.
          </p>
        }
        aside={
          <SurfaceCard>
            <div className="space-y-3">
              <Badge tone={decisionTone(String(aiMetrics.overall_status ?? ""))}>
                {String(aiMetrics.overall_status ?? "Unknown")}
              </Badge>
              <p className="text-sm leading-7 text-[var(--muted)]">
                Registered trace consumers: {formatNumber(Number((aiMetrics.summary as Record<string, unknown> | undefined)?.registered_trace_consumers ?? 0))}
              </p>
            </div>
          </SurfaceCard>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SurfaceCard>
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Embedding drift</p>
          <p className="mt-3 font-display text-2xl text-[var(--ink)]">
            {formatNumber(Number(((aiMetrics.checks as Record<string, Record<string, unknown>>).embedding_drift?.value as number | undefined) ?? 0))}
          </p>
        </SurfaceCard>
        <SurfaceCard>
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Prompt input violations</p>
          <p className="mt-3 font-display text-2xl text-[var(--ink)]">
            {formatPercent(
              Number(((aiMetrics.checks as Record<string, Record<string, unknown>>).prompt_input_schema_validation?.value as number | undefined) ?? 0) * 100,
              2,
            )}
          </p>
        </SurfaceCard>
        <SurfaceCard>
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Output schema violations</p>
          <p className="mt-3 font-display text-2xl text-[var(--ink)]">
            {formatPercent(
              Number(((aiMetrics.checks as Record<string, Record<string, unknown>>).llm_output_schema_validation?.value as number | undefined) ?? 0) * 100,
              2,
            )}
          </p>
        </SurfaceCard>
        <SurfaceCard>
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Trace contract rate</p>
          <p className="mt-3 font-display text-2xl text-[var(--ink)]">
            {formatPercent(
              Number(((aiMetrics.checks as Record<string, Record<string, unknown>>).trace_contract_risk?.value as number | undefined) ?? 0) * 100,
              2,
            )}
          </p>
        </SurfaceCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        {checks.map(([key, check]) => (
          <SurfaceCard key={key}>
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={severityTone(String(check.status ?? ""))}>{String(check.status ?? "Unknown")}</Badge>
              <Badge tone={severityTone(String(check.severity ?? ""))}>{String(check.severity ?? "Unknown")}</Badge>
            </div>
            <h2 className="mt-4 font-display text-2xl text-[var(--ink)]">{key}</h2>
            <p className="mt-3 text-sm leading-7 text-[var(--muted)]">
              {String(check.summary ?? "No summary recorded for this metric.")}
            </p>
            <div className="mt-5 space-y-3 text-sm leading-7 text-[var(--muted)]">
              {"metric_source" in check ? (
                <p>
                  Metric source: <span className="font-semibold text-[var(--ink)]">{String(check.metric_source ?? "Unknown")}</span>
                </p>
              ) : null}
              {"provider" in check && check.provider ? (
                <p>
                  Provider: <InlinePath>{String(check.provider)}</InlinePath>
                </p>
              ) : null}
              {"model" in check && check.model ? (
                <p>
                  Model: <span className="font-semibold text-[var(--ink)]">{String(check.model)}</span>
                </p>
              ) : null}
              {"thresholds" in check ? <p>Thresholds: {JSON.stringify(check.thresholds)}</p> : null}
              {"notes" in check && Array.isArray(check.notes) ? (
                <ul className="space-y-2">
                  {(check.notes as string[]).map((note) => (
                    <li key={note}>• {note}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          </SurfaceCard>
        ))}
      </div>
    </div>
  );
}
