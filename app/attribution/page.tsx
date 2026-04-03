import { Badge, EmptyState, PageHeader, SectionLabel, SurfaceCard } from "@/components/ui";
import { loadAttribution } from "@/lib/data/artifacts";
import { formatDate, formatNumber, formatPercent, severityTone, shortHash } from "@/lib/utils";

export default async function AttributionPage() {
  const attribution = await loadAttribution();
  const entries = attribution.attributions ?? [];

  if (!entries.length) {
    return (
      <EmptyState
        description="No blame-chain artifact was found for the dashboard to visualize."
        expectedFile="violation_log/blame_chain.json"
        title="No attribution data found"
      />
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Blast radius and blame chain"
        title="Registry first, lineage second"
        description={
          <p>
            This page makes the updated architecture explicit. Registered consumers are the primary blast-radius
            source. Lineage is still useful, but only as enrichment after the subscribed audience is known.
          </p>
        }
        aside={
          <SurfaceCard>
            <SectionLabel title="Confidence scoring" subtitle="The file ranking is explainable rather than opaque." />
            <p className="mt-4 text-sm leading-7 text-[var(--muted)]">
              {attribution.confidence_scoring_method?.summary ??
                "Confidence blends path relevance, git blame support, and recent commit context."}
            </p>
          </SurfaceCard>
        }
      />

      <div className="space-y-6">
        {entries.map((entry) => {
          const topCandidate = entry.blame_chain?.[0];
          const registrySubscribers = entry.blast_radius?.primary?.subscribers ?? [];
          const enrichment = entry.blast_radius?.enrichment;

          return (
            <SurfaceCard key={entry.violation_id}>
              <div className="space-y-6">
                <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                  <div className="space-y-3">
                    <div className="flex flex-wrap gap-2">
                      <Badge tone={severityTone(entry.severity)}>{entry.severity ?? "Unknown"}</Badge>
                      <Badge tone="neutral">{entry.check_id}</Badge>
                    </div>
                    <h2 className="font-display text-3xl text-[var(--ink)]">{entry.field}</h2>
                    <p className="max-w-3xl text-sm leading-7 text-[var(--muted)]">{entry.message}</p>
                  </div>
                  <div className="rounded-3xl border border-[var(--line)] bg-white/75 p-5 text-sm text-[var(--muted)]">
                    <p>
                      Producer system: <span className="font-semibold text-[var(--ink)]">{entry.producer_system}</span>
                    </p>
                    <p className="mt-2">
                      Failing rows: <span className="font-semibold text-[var(--ink)]">{formatNumber(entry.records_failing ?? null)}</span>
                    </p>
                    <p className="mt-2">
                      Sample values: <span className="font-semibold text-[var(--ink)]">{entry.sample_failing?.join(" • ") || "None captured"}</span>
                    </p>
                  </div>
                </div>

                <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
                  <SurfaceCard className="bg-[var(--paper)]/80">
                    <SectionLabel
                      title="Primary blast radius"
                      subtitle="Direct subscribers from the contract registry."
                    />
                    <div className="mt-5 space-y-4">
                      {registrySubscribers.map((subscriber) => (
                        <div className="rounded-2xl border border-[var(--line)] bg-white/80 p-4" key={subscriber.subscriber_id}>
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="font-semibold text-[var(--ink)]">{subscriber.subscriber_id}</p>
                            <Badge tone="info">{subscriber.validation_mode ?? "mode unavailable"}</Badge>
                          </div>
                          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
                            {(subscriber.contact?.owner ?? "Unknown owner")} • {(subscriber.contact?.role ?? "Unknown role")}
                          </p>
                          <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
                            Breaking fields: {(subscriber.breaking_fields ?? []).map((item) => item.field).join(", ") || "Not documented"}
                          </p>
                        </div>
                      ))}
                    </div>
                  </SurfaceCard>

                  <SurfaceCard className="bg-[var(--paper)]/80">
                    <SectionLabel
                      title="Secondary lineage enrichment"
                      subtitle="Helpful propagation clues from Week 4, but not the primary impact source."
                    />
                    <div className="mt-5 space-y-4 text-sm leading-7 text-[var(--muted)]">
                      <p>
                        Matched nodes: <span className="font-semibold text-[var(--ink)]">{formatNumber(enrichment?.matched_nodes?.length ?? 0)}</span>
                      </p>
                      <p>
                        Downstream nodes: <span className="font-semibold text-[var(--ink)]">{formatNumber(enrichment?.downstream_nodes?.length ?? 0)}</span>
                      </p>
                      <p>
                        Confidence: <span className="font-semibold text-[var(--ink)]">{enrichment?.confidence ?? "Not available"}</span>
                      </p>
                      <p>{enrichment?.summary ?? "No lineage enrichment summary was recorded."}</p>
                    </div>
                  </SurfaceCard>
                </div>

                <SurfaceCard className="overflow-hidden p-0">
                  <div className="border-b border-[var(--line)] px-6 py-5">
                    <SectionLabel title="Blame chain" subtitle="Likely producer-side files ranked by explainable confidence." />
                  </div>
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-[var(--line)]">
                      <thead className="bg-[var(--paper)]/90 text-left text-xs uppercase tracking-[0.2em] text-[var(--muted)]">
                        <tr>
                          <th className="px-6 py-4">Ranked file</th>
                          <th className="px-6 py-4">Commit</th>
                          <th className="px-6 py-4">Author</th>
                          <th className="px-6 py-4">Confidence</th>
                          <th className="px-6 py-4">Rationale</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[var(--line)] bg-white/70">
                        {(entry.blame_chain ?? []).map((candidate) => (
                          <tr className="align-top" key={`${entry.violation_id}:${candidate.rank}:${candidate.file_path}`}>
                            <td className="px-6 py-5">
                              <div className="space-y-2">
                                <div className="flex flex-wrap items-center gap-2">
                                  <Badge tone="neutral">#{candidate.rank ?? "?"}</Badge>
                                  <p className="font-semibold text-[var(--ink)]">{candidate.file_path}</p>
                                </div>
                                <p className="text-sm text-[var(--muted)]">{candidate.repo_root}</p>
                              </div>
                            </td>
                            <td className="px-6 py-5 text-sm leading-6 text-[var(--muted)]">
                              <p className="font-semibold text-[var(--ink)]">{shortHash(candidate.commit_hash ?? "")}</p>
                              <p>{formatDate(candidate.commit_timestamp)}</p>
                              <p>{candidate.commit_message}</p>
                            </td>
                            <td className="px-6 py-5 text-sm leading-6 text-[var(--muted)]">
                              <p className="font-semibold text-[var(--ink)]">{candidate.author}</p>
                              <p>{candidate.author_email}</p>
                            </td>
                            <td className="px-6 py-5 text-sm leading-6 text-[var(--muted)]">
                              <p className="font-semibold text-[var(--ink)]">
                                {formatPercent((candidate.confidence_score ?? 0) * 100, 1)}
                              </p>
                              <p>Path relevance: {formatPercent((candidate.path_relevance ?? 0) * 100, 1)}</p>
                              <p>Blame hits: {formatNumber(candidate.line_blame_hits ?? null)}</p>
                            </td>
                            <td className="px-6 py-5 text-sm leading-7 text-[var(--muted)]">{candidate.rationale}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </SurfaceCard>

                {topCandidate ? (
                  <div className="rounded-[28px] border border-[var(--line)] bg-[linear-gradient(135deg,rgba(255,255,255,0.9),rgba(236,228,218,0.95))] p-6">
                    <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Headline takeaway</p>
                    <p className="mt-3 text-lg leading-8 text-[var(--ink)]">
                      The strongest current explanation is that <strong>{topCandidate.file_path}</strong> introduced or
                      persisted the field behavior that triggered this contract break. The direct impact audience is{" "}
                      <strong>{formatNumber(registrySubscribers.length)}</strong> registered consumers.
                    </p>
                  </div>
                ) : null}
              </div>
            </SurfaceCard>
          );
        })}
      </div>
    </div>
  );
}
