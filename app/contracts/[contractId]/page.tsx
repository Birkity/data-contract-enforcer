import { notFound } from "next/navigation";

import { Badge, InlinePath, PageHeader, SectionLabel, SurfaceCard } from "@/components/ui";
import { loadContracts } from "@/lib/data/artifacts";
import { humanizeSlug, normalizeFilePath, severityTone } from "@/lib/utils";

export default async function ContractDetailPage({
  params,
}: {
  params: Promise<{ contractId: string }>;
}) {
  const { contractId } = await params;
  const contracts = await loadContracts();
  const contract = contracts.find((item) => item.id === contractId);

  if (!contract) {
    notFound();
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Contract detail"
        title={contract.title}
        description={<p>{contract.description}</p>}
        aside={
          <SurfaceCard>
            <div className="space-y-3">
              <Badge tone="info">{contract.id}</Badge>
              <p className="text-sm leading-7 text-[var(--muted)]">
                {contract.registrySubscribers.length} registered subscribers and {contract.clauseCount} field clauses.
              </p>
              <InlinePath>{normalizeFilePath(contract.filePath)}</InlinePath>
            </div>
          </SurfaceCard>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <SurfaceCard className="overflow-hidden p-0">
          <div className="border-b border-[var(--line)] px-6 py-5">
            <SectionLabel title="Field clauses" subtitle="Required, type, format, range, enum, and sample evidence from the real generated contract." />
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-[var(--line)]">
              <thead className="bg-[var(--paper)]/90 text-left text-xs uppercase tracking-[0.2em] text-[var(--muted)]">
                <tr>
                  <th className="px-6 py-4">Field</th>
                  <th className="px-6 py-4">Type</th>
                  <th className="px-6 py-4">Constraints</th>
                  <th className="px-6 py-4">Notes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--line)] bg-white/70">
                {contract.fields.map((field) => (
                  <tr className="align-top" key={field.name}>
                    <td className="px-6 py-5">
                      <div className="space-y-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="font-semibold text-[var(--ink)]">{field.name}</p>
                          {field.isRisky ? <Badge tone={severityTone(field.name)}>Risk signal</Badge> : null}
                        </div>
                        <p className="text-sm leading-6 text-[var(--muted)]">{field.description}</p>
                      </div>
                    </td>
                    <td className="px-6 py-5">
                      <div className="space-y-2 text-sm text-[var(--ink)]">
                        <p>{field.type}</p>
                        {field.format ? <Badge tone="neutral">{field.format}</Badge> : null}
                        {field.required ? <Badge tone="success">Required</Badge> : <Badge tone="neutral">Optional</Badge>}
                      </div>
                    </td>
                    <td className="px-6 py-5">
                      <div className="space-y-2 text-sm text-[var(--muted)]">
                        {field.minimum !== null || field.maximum !== null ? (
                          <p>
                            Range: {field.minimum ?? "—"} to {field.maximum ?? "—"}
                          </p>
                        ) : null}
                        {field.enumValues.length ? (
                          <p>Enum: {field.enumValues.join(", ")}</p>
                        ) : (
                          <p>No explicit enum constraint.</p>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-5">
                      <div className="space-y-2 text-sm text-[var(--muted)]">
                        {field.observedMin !== null || field.observedMax !== null ? (
                          <p>
                            Observed: {field.observedMin ?? "—"} to {field.observedMax ?? "—"}
                          </p>
                        ) : null}
                        {field.sampleValues.length ? <p>Samples: {field.sampleValues.slice(0, 3).join(" • ")}</p> : <p>No sample values captured.</p>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SurfaceCard>

        <div className="space-y-6">
          <SurfaceCard>
            <SectionLabel title="Registry subscribers" subtitle="Primary blast-radius audience for this contract." />
            <div className="mt-5 space-y-4">
              {contract.registrySubscribers.map((subscriber) => (
                <div className="rounded-2xl border border-[var(--line)] bg-white/75 p-4" key={subscriber.subscriber_id}>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-semibold text-[var(--ink)]">{subscriber.subscriber_id}</p>
                    <Badge tone="info">{subscriber.validation_mode ?? "mode unavailable"}</Badge>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
                    {(subscriber.contact?.owner ?? "Unknown owner")} • {(subscriber.contact?.role ?? "Unknown role")}
                  </p>
                  <p className="mt-3 text-sm text-[var(--muted)]">
                    Fields consumed: {(subscriber.fields_consumed ?? []).join(", ") || "Not documented"}
                  </p>
                </div>
              ))}
            </div>
          </SurfaceCard>

          <SurfaceCard>
            <SectionLabel title="Implementation notes" subtitle="What the generated contract says about enforcement and enrichment." />
            <div className="mt-5 space-y-3 text-sm leading-7 text-[var(--muted)]">
              {Object.entries(contract.implementationModel ?? {}).map(([key, value]) => (
                <p key={key}>
                  <span className="font-semibold text-[var(--ink)]">{humanizeSlug(key)}:</span> {humanizeSlug(String(value))}
                </p>
              ))}
              {contract.lineageNotes.map((note) => (
                <p key={note}>{note}</p>
              ))}
              {contract.dbtPath ? (
                <p>
                  dbt counterpart: <InlinePath>{normalizeFilePath(contract.dbtPath)}</InlinePath>
                </p>
              ) : null}
            </div>
          </SurfaceCard>
        </div>
      </div>
    </div>
  );
}
