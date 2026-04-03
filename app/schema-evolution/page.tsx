import { Badge, EmptyState, InlinePath, PageHeader, SectionLabel, SurfaceCard } from "@/components/ui";
import { loadSchemaEvolution } from "@/lib/data/artifacts";
import { decisionTone, formatNumber, severityTone } from "@/lib/utils";

export default async function SchemaEvolutionPage() {
  const schemaEvolution = await loadSchemaEvolution();
  const compatibility = schemaEvolution.compatibility as Record<string, unknown> | null;
  const summary = schemaEvolution.evolutionSummary as Record<string, unknown> | null;

  if (!compatibility || !summary) {
    return (
      <EmptyState
        description="Schema evolution artifacts were not available for the producer-side CI view."
        expectedFile="schema_snapshots/compatibility_report.json"
        title="No schema evolution data found"
      />
    );
  }

  const previousFields = Object.keys(
    ((schemaEvolution.previousSnapshot as Record<string, unknown> | null)?.schema as Record<string, unknown> | undefined) ??
      {},
  );
  const currentFields = Object.keys(
    ((schemaEvolution.currentSnapshot as Record<string, unknown> | null)?.schema as Record<string, unknown> | undefined) ??
      {},
  );
  const changes = (compatibility.changes as Array<Record<string, unknown>> | undefined) ?? [];
  const producerActions = (compatibility.producer_next_actions as string[] | undefined) ?? [];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Schema evolution"
        title="Producer-side CI gate"
        description={
          <p>
            This page is intentionally not a runtime validation screen. It shows the SchemaEvolutionAnalyzer
            view: can the producer safely release a schema change before any consumer sees it?
          </p>
        }
        aside={
          <SurfaceCard>
            <div className="space-y-3">
              <Badge tone={decisionTone(String(summary.decision ?? compatibility.decision ?? ""))}>
                {String(summary.decision ?? compatibility.decision ?? "Unknown")}
              </Badge>
              <p className="text-sm leading-7 text-[var(--muted)]">
                {String(summary.recommendation ?? compatibility.recommendation ?? "No recommendation captured.")}
              </p>
            </div>
          </SurfaceCard>
        }
      />

      <div className="grid gap-4 md:grid-cols-4">
        <SurfaceCard>
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Total changes</p>
          <p className="mt-3 font-display text-2xl text-[var(--ink)]">{formatNumber(Number(summary.total_changes ?? 0))}</p>
        </SurfaceCard>
        <SurfaceCard>
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Breaking changes</p>
          <p className="mt-3 font-display text-2xl text-[var(--ink)]">{formatNumber(Number(summary.breaking_changes ?? 0))}</p>
        </SurfaceCard>
        <SurfaceCard>
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Impacted systems</p>
          <p className="mt-3 font-display text-2xl text-[var(--ink)]">
            {formatNumber(((summary.impacted_systems as string[] | undefined) ?? []).length)}
          </p>
        </SurfaceCard>
        <SurfaceCard>
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Snapshot catalogs</p>
          <p className="mt-3 font-display text-2xl text-[var(--ink)]">{formatNumber(schemaEvolution.snapshotInventory.length)}</p>
        </SurfaceCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <SurfaceCard>
          <SectionLabel title="Before vs after" subtitle="The analyzer compares snapshots, not live ingestion rows." />
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <div className="rounded-3xl border border-[var(--line)] bg-white/75 p-5">
              <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Previous snapshot</p>
              <div className="mt-3">
                <InlinePath>{schemaEvolution.previousSnapshotPath ?? "Unavailable"}</InlinePath>
              </div>
              <p className="mt-4 text-sm text-[var(--muted)]">
                Fields captured: <span className="font-semibold text-[var(--ink)]">{formatNumber(previousFields.length)}</span>
              </p>
            </div>
            <div className="rounded-3xl border border-[var(--line)] bg-white/75 p-5">
              <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Current snapshot</p>
              <div className="mt-3">
                <InlinePath>{schemaEvolution.currentSnapshotPath ?? "Unavailable"}</InlinePath>
              </div>
              <p className="mt-4 text-sm text-[var(--muted)]">
                Fields captured: <span className="font-semibold text-[var(--ink)]">{formatNumber(currentFields.length)}</span>
              </p>
            </div>
          </div>
        </SurfaceCard>

        <SurfaceCard>
          <SectionLabel title="Producer next steps" subtitle="What the producer should do before release." />
          <ol className="mt-5 space-y-3">
            {producerActions.map((action, index) => (
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
        <SectionLabel title="Detected changes" subtitle="Each change is already classified as backward-compatible or breaking." />
        <div className="mt-5 space-y-4">
          {changes.map((change) => (
            <div className="rounded-3xl border border-[var(--line)] bg-white/75 p-5" key={String(change.field)}>
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={severityTone(String(change.classification ?? ""))}>
                  {String(change.classification ?? "Unknown")}
                </Badge>
                <Badge tone="neutral">{String(change.change_type ?? "Unknown change type")}</Badge>
              </div>
              <h2 className="mt-4 font-display text-2xl text-[var(--ink)]">{String(change.field ?? "Unknown field")}</h2>
              <p className="mt-3 text-sm leading-7 text-[var(--muted)]">{String(change.rationale ?? "No rationale recorded.")}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                <Badge tone="warning">Impact level: {String(change.impact_level ?? "Unknown")}</Badge>
                <Badge tone={Boolean(change.requires_registry_update) ? "danger" : "success"}>
                  Registry update {Boolean(change.requires_registry_update) ? "required" : "not required"}
                </Badge>
              </div>
              <p className="mt-4 text-sm leading-7 text-[var(--muted)]">
                Affected consumers:{" "}
                {((change.affected_consumers as Array<{ subscriber_id?: string }> | undefined) ?? [])
                  .map((consumer) => consumer.subscriber_id)
                  .join(", ") || "None"}
              </p>
            </div>
          ))}
        </div>
      </SurfaceCard>

      <SurfaceCard>
        <SectionLabel title="Available snapshot history" subtitle="Snapshot inventory from schema_snapshots/contracts." />
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          {schemaEvolution.snapshotInventory.map((inventory) => (
            <div className="rounded-3xl border border-[var(--line)] bg-white/75 p-5" key={inventory.contractId}>
              <p className="font-semibold text-[var(--ink)]">{inventory.contractId}</p>
              <p className="mt-2 text-sm text-[var(--muted)]">
                Versions: {formatNumber(inventory.versionCount)}
              </p>
              <p className="mt-2 text-sm text-[var(--muted)]">
                Latest: {inventory.latestPath ?? "No latest snapshot"}
              </p>
            </div>
          ))}
        </div>
      </SurfaceCard>
    </div>
  );
}
