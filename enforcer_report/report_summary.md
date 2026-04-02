# Enforcer Report

- Generated at: `2026-04-02T11:46:09.433109+00:00`
- Data Health Score: **90 / 100**
- Architecture: consumer enforcement, registry-first blast radius, lineage enrichment only

## What is healthy

- Clean baseline validation passed `37/37` checks with decision `ALLOW_WITH_AUDIT_TRAIL`.
- Injected confidence violation was caught in all three modes; `WARN` and `ENFORCE` both blocked as expected.
- Attribution identified `src/agents/fact_table.py` as the strongest producer-side source candidate.
- Schema evolution CI gate returned `FAIL` on the simulated rename and blocked deployment correctly.

## What broke in testing

- Injected violation failed `2` checks in ENFORCE mode.
- `week3-extractions.fact_confidence.range` failed at `93.03%` affected rows: fact_confidence is outside the configured range. Breaking change detected.
- `week3-extractions.fact_confidence.drift` failed at `93.03%` affected rows: fact_confidence mean drifted 700.4 stddev from baseline.

## AI risk summary

- Overall AI status: **FAIL**
- Embedding drift score: `0.28237`
- Prompt input schema violation rate: `0.0`
- LLM output schema violation rate: `0.0`
- Trace contract violation rate: `0.176471`

## Blast radius

- Registered subscribers affected: `3`
- Lineage enrichment confidence: `low`

## Recommended actions

- Keep consumer-side validation in AUDIT first for any new subscriber, then move to WARN or ENFORCE after a clean baseline is established.
- Normalize LangSmith run_type values or narrow the exported trace set before treating trace telemetry as a strict contract boundary.
- Migrate Week 4 lineage into the canonical Week 7 node/edge snapshot shape so blast radius enrichment becomes stronger than the current low-confidence fallback.
- Keep SchemaEvolutionAnalyzer in the producer CI path so breaking schema changes are blocked before consumers see them.
- Block producer deployment until impacted consumers have a migration plan.
- Update contract_registry/subscriptions.yaml with any new field names, aliases, or migration notes before release.
- Publish a compatibility notice to affected subscribers and regenerate the contract snapshot after the schema fix or migration.
- Prefer deprecating the old field with an alias period before removing or renaming it outright.

## Submission view

- The system is ready for submission because the registry-aware contracts, validation modes, attribution, schema evolution gate, AI extensions, and final report outputs are all present and connected.
- The main remaining weakness is still Week 4 lineage quality, which limits enrichment depth but does not invalidate the registry-first architecture.
