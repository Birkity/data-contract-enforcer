# Frontend UI Report

## Why this UI is optional

The frontend is an optional presentation layer over the Week 7 Data Contract Enforcer. It does not replace
the CLI scripts, the generated artifacts, or the existing enforcement logic. The core system still lives in:

- `contracts/`
- `generated_contracts/`
- `validation_reports/`
- `violation_log/`
- `schema_snapshots/`
- `enforcer_report/`

The dashboard exists for reviewer clarity, demo walkthroughs, and client-facing explanation. It makes the
system easier to understand quickly, especially for people who do not want to inspect raw JSON, JSONL, and
YAML files directly.

## Artifacts visualized

The frontend reads the real local artifacts instead of inventing demo data.

Primary files visualized:

- `enforcer_report/report_data.json`
- `enforcer_report/ai_metrics.json`
- `generated_contracts/*.yaml`
- `validation_reports/*.json`
- `violation_log/violations.jsonl`
- `violation_log/blame_chain.json`
- `schema_snapshots/compatibility_report.json`
- `schema_snapshots/evolution_summary.json`
- `schema_snapshots/contracts/**/*.yaml`
- `contract_registry/subscriptions.yaml`

The data-access layer is intentionally file-based and read-only. If a file is missing, the UI shows an empty
state that names the expected path.

## Page-by-page explanation

### `/`

The dashboard is the executive landing page. It shows:

- Data Health Score
- total contracts
- total validation runs
- total violations
- severity posture
- top recommended actions
- quick links to deeper investigation routes

This page is optimized for the “two minute reviewer summary” experience.

### `/contracts`

This page lists every generated contract and combines contract metadata with registry subscriptions. It helps
the reviewer see:

- which contracts exist
- which dataset each contract applies to
- clause counts
- subscriber counts
- highlighted risky fields such as confidence or sequence semantics

The detail page at `/contracts/[contractId]` shows field-level clauses, constraints, samples, implementation
notes, and registry subscribers.

### `/validations`

This page renders the validation reports created by `ValidationRunner`. It makes clean and violated runs easy
to compare by surfacing:

- mode used
- decision
- passed vs failed checks
- blocking status
- timestamps

The detail page at `/validations/[reportId]` shows the failing checks table with actual vs expected values,
failing rows, sample failing values, and severity.

### `/violations`

This page reads `violation_log/violations.jsonl` directly and adds simple server-side filters for:

- severity
- contract
- injected vs real

It is meant for triage. Reviewers can see the current open signals without reading the raw JSONL manually.

### `/attribution`

This page is the most architecture-sensitive view. It explains:

- violating field
- producer system
- primary blast radius from the registry
- secondary lineage enrichment
- blame chain ranking
- top candidate file, commit, author, and rationale

The page intentionally makes the updated architecture obvious:
registry first, lineage second.

### `/schema-evolution`

This page presents `SchemaEvolutionAnalyzer` as a producer-side CI gate, not a runtime validator. It shows:

- before vs after snapshot paths
- detected changes
- compatibility verdict
- impacted consumers
- producer next actions
- snapshot history inventory

This route helps explain how Week 7 prevents breaking releases before consumers ingest the change.

### `/ai`

This page visualizes the AI extension metrics, including:

- embedding drift
- prompt input schema validation
- LLM output schema validation
- trace contract risk

If any AI artifact is missing, the page is designed to say that explicitly rather than hiding the gap.

### `/report`

This is the business-friendly report view over `enforcer_report/report_data.json`. It is structured for a
client walkthrough and emphasizes:

- health score
- top failures
- severity/impact summary
- affected subscribers
- recommended actions
- real artifact anchors

## How this supports a video demo or client walkthrough

The frontend supports a clean walkthrough sequence:

1. Start on `/` to summarize overall system health and the main issue.
2. Move to `/contracts` to show what is under contract and why the contract exists.
3. Move to `/validations` to show proof that the injected break is caught.
4. Move to `/violations` to show the machine-readable log.
5. Move to `/attribution` to explain who is affected and where the likely producer-side cause sits.
6. Move to `/schema-evolution` to show how the system blocks breaking releases before runtime.
7. Move to `/ai` to show that AI-specific checks are also visible.
8. Finish on `/report` for a client-friendly summary.

This sequence is useful because it mirrors the real Week 7 story:

- define the interface
- validate it
- detect breakage
- explain impact
- prevent future breakage

## Known limitations

- The frontend is read-only and intentionally does not trigger the CLI pipeline itself.
- It depends on the generated artifacts already existing locally.
- Week 4 lineage is visualized honestly, but registry data remains the clearer blast-radius source.
- The UI is optimized for clarity and traceability rather than interaction-heavy workflows.
- It does not attempt to replace notebook-style artifact inspection for deep technical debugging.
