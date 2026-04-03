import Link from "next/link";

import { Badge, EmptyState, PageHeader, SectionLabel, SurfaceCard } from "@/components/ui";
import { loadContracts } from "@/lib/data/artifacts";
import { formatNumber, normalizeFilePath, severityTone } from "@/lib/utils";

export default async function ContractsPage() {
  const contracts = await loadContracts();

  if (!contracts.length) {
    return (
      <EmptyState
        description="No generated contracts were found for the frontend to render."
        expectedFile="generated_contracts/*.yaml"
        title="No contract artifacts found"
      />
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Contracts"
        title="Generated contract inventory"
        description={
          <p>
            Each row comes from the real generated contract YAML files and is enriched with registry
            subscriptions so reviewers can see both the clause surface and the downstream audience.
          </p>
        }
        aside={
          <SurfaceCard>
            <SectionLabel
              title={`${contracts.length} live contracts`}
              subtitle="Bitol-style contracts with dbt-compatible counterparts where available."
            />
            <div className="mt-4 flex flex-wrap gap-2">
              <Badge tone="info">Registry-aware</Badge>
              <Badge tone="neutral">Lineage-enriched</Badge>
              <Badge tone="success">Read-only UI</Badge>
            </div>
          </SurfaceCard>
        }
      />

      <SurfaceCard className="overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-[var(--line)]">
            <thead className="bg-[var(--paper)]/90">
              <tr className="text-left text-xs uppercase tracking-[0.2em] text-[var(--muted)]">
                <th className="px-6 py-4">Contract</th>
                <th className="px-6 py-4">Source dataset</th>
                <th className="px-6 py-4">Clauses</th>
                <th className="px-6 py-4">Subscribers</th>
                <th className="px-6 py-4">Risk signals</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--line)] bg-white/70">
              {contracts.map((contract) => (
                <tr className="align-top" key={contract.id}>
                  <td className="px-6 py-5">
                    <div className="space-y-2">
                      <Link className="font-semibold text-[var(--ink)] hover:text-[var(--accent)]" href={`/contracts/${contract.id}`}>
                        {contract.title}
                      </Link>
                      <p className="text-sm leading-6 text-[var(--muted)]">{contract.description}</p>
                      <div className="flex flex-wrap gap-2">
                        <Badge tone="neutral">{contract.id}</Badge>
                        {contract.dbtPath ? <Badge tone="success">dbt counterpart</Badge> : null}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-5">
                    <p className="font-mono text-sm text-[var(--ink)]">{normalizeFilePath(contract.sourceDataset)}</p>
                  </td>
                  <td className="px-6 py-5 text-sm font-semibold text-[var(--ink)]">
                    {formatNumber(contract.clauseCount)}
                  </td>
                  <td className="px-6 py-5">
                    <div className="space-y-2">
                      <p className="text-sm font-semibold text-[var(--ink)]">
                        {formatNumber(contract.registrySubscribers.length)}
                      </p>
                      <p className="text-sm text-[var(--muted)]">
                        {contract.registrySubscribers.map((subscriber) => subscriber.subscriber_id).join(", ") || "No registered subscribers"}
                      </p>
                    </div>
                  </td>
                  <td className="px-6 py-5">
                    <div className="flex flex-wrap gap-2">
                      {contract.riskyFields.slice(0, 4).map((field) => (
                        <Badge key={field} tone={severityTone(field)}>
                          {field}
                        </Badge>
                      ))}
                      {!contract.riskyFields.length ? <Badge tone="success">No highlighted risky field</Badge> : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SurfaceCard>
    </div>
  );
}
