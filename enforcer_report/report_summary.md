# Enforcer Report

- Generated at: `2026-04-02T21:01:16.345231+00:00`
- Data Health Score: **100 / 100**
- Architecture: consumer enforcement, registry-first blast radius, lineage enrichment only

## What is healthy

- Clean baseline validation passed `38/38` checks with decision `ALLOW_WITH_AUDIT_TRAIL`.
- Injected confidence violation was caught in all three modes; `WARN` and `ENFORCE` both blocked as expected.
- Attribution identified `src/agents/fact_table.py` as the strongest producer-side source candidate.
- Schema evolution CI gate returned `FAIL` on the simulated rename and blocked deployment correctly.

## What broke in testing

- Injected violation failed `2` checks in ENFORCE mode.
- `week3-extractions.fact_confidence.range` failed at `78.61%` affected rows: fact_confidence is outside the configured range. Breaking change detected.
- `week3-extractions.fact_confidence.drift` failed at `78.61%` affected rows: fact_confidence mean drifted 923.4 stddev from baseline.

## AI risk summary

- Overall AI status: **PASS**
- Embedding drift score: `0.0`
- Prompt input schema violation rate: `0.0`
- LLM output schema violation rate: `0.0`
- Trace contract violation rate: `0.0`

## Blast radius

- Registered subscribers affected: `3`
- Lineage enrichment confidence: `high`

## Recommended actions

- Keep consumer-side validation in AUDIT first for any new subscriber, then move to WARN or ENFORCE after a clean baseline is established.
- Keep SchemaEvolutionAnalyzer in the producer CI path so breaking schema changes are blocked before consumers see them.
- AI-specific contract metrics are stable on the current artifacts; keep tracing and schema snapshots in place as the next safety layer.
- Block producer deployment until impacted consumers have a migration plan.
- Update contract_registry/subscriptions.yaml with any new field names, aliases, or migration notes before release.
- Publish a compatibility notice to affected subscribers and regenerate the contract snapshot after the schema fix or migration.
- Prefer deprecating the old field with an alias period before removing or renaming it outright.

## Submission view

- The system is ready for submission because the registry-aware contracts, validation modes, attribution, schema evolution gate, AI extensions, and final report outputs are all present and connected.
- The main remaining weakness is lineage specificity, not missing implementation: Week 4 now contributes canonical enrichment, but the consumer-side graph is still more file-I/O-shaped than contract-edge-shaped.
