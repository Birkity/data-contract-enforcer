# Data Contract Enforcer

This repository contains a full Week 7 `Data Contract Enforcer` implementation aligned to the updated challenge document and the updated Practitioner Manual.

It now includes:

- Phase 0 domain analysis and architecture notes
- ContractGenerator
- ValidationRunner
- ViolationAttributor
- SchemaEvolutionAnalyzer
- AI Contract Extensions
- final Enforcer Report generation

The implementation follows the updated architecture:

- enforcement runs at the consumer boundary
- the contract registry is the primary blast-radius source
- lineage is enrichment only
- schema evolution acts as a producer-side CI gate

## Submission snapshot

The current repo state is ready for review:

- Data health score: `100 / 100`
- Clean validation: `38 / 38` checks passed
- Injected confidence violation: correctly blocked in `WARN` and `ENFORCE`
- AI contract metrics: `PASS`
- dbt smoke verification: `PASS`
- Main remaining limitation: lineage specificity is still weaker than registry-based blast radius

## Current artifact state

### Inputs

- `outputs/week1/intent_records.jsonl`
- `outputs/week2/verdicts.jsonl`
- `outputs/week3/extractions.jsonl`
- `outputs/week4/lineage_snapshots.jsonl`
- `outputs/week5/events.jsonl`
- `outputs/traces/runs.jsonl`

### Generated contracts

- `generated_contracts/week3_extractions.yaml`
- `generated_contracts/week3_extractions_dbt.yml`
- `generated_contracts/week5_events.yaml`
- `generated_contracts/week5_events_dbt.yml`

### Validation outputs

- `validation_reports/thursday_baseline.json`
- `validation_reports/injected_violation_audit.json`
- `validation_reports/injected_violation_warn.json`
- `validation_reports/injected_violation.json`
- `violation_log/violations.jsonl`
- `schema_snapshots/baselines.json`

### Attribution and schema evolution

- `violation_log/blame_chain.json`
- `schema_snapshots/compatibility_report.json`
- `schema_snapshots/evolution_summary.json`

### AI and final report outputs

- `enforcer_report/ai_metrics.json`
- `enforcer_report/report_data.json`
- `enforcer_report/report_summary.md`

## Current data reality

### Week 3

The current canonical Week 3 export contains:

- `50` extraction rows
- `13` rows with extracted facts
- `29` rows with entities
- `136` fact-level confidence values
- clean confidence range `0.55` to `0.9`
- clean confidence mean `0.818015`

### Week 4

The current Week 4 lineage file is now canonical JSONL:

- `4` snapshot rows
- includes a Week 7 consumer-side snapshot with persisted `git_commit`
- includes a real Week 3 repo snapshot with `80` nodes and `47` edges
- required top-level fields:
  - `snapshot_id`
  - `codebase_root`
  - `git_commit`
  - `nodes`
  - `edges`
  - `captured_at`

Current limitation:

- the file is structurally correct, but it still does not expose a clean explicit Week 3 extraction consumer path
- the Week 7 consumer-side snapshot now has `38` nodes and `19` edges, but those consumer-side lineage nodes are still mostly dynamic file-I/O observations rather than a contract-level edge
- downstream enrichment is therefore useful, but still weaker than registry-based blast radius

### Week 5

The current Week 5 export contains:

- `1198` event rows
- canonical event-envelope fields
- generated contract coverage in both Bitol and dbt-compatible form

### Traces

The current trace export contains:

- `153` rows
- enough volume for the Week 7 requirement
- a cleaned contract-source file at `outputs/traces/runs.jsonl`
- a preserved raw backup at `outputs/traces/runs_raw.jsonl`
- a canonical consumer-boundary file at `outputs/traces/runs_contract_boundary.jsonl` with `153` normalized rows

This means the repo now keeps both:

- the original raw trace export for forensic reference
- the cleaned contract-facing trace input used by Week 7 checks

## How to rerun the full flow

Use the repo virtualenv:

```powershell
.\.venv\Scripts\python.exe
```

### 1. Generate contracts

```powershell
.\.venv\Scripts\python.exe contracts/generator.py --source outputs/week3/extractions.jsonl --lineage outputs/week4/lineage_snapshots.jsonl --registry contract_registry/subscriptions.yaml --output generated_contracts/week3_extractions.yaml --snapshot-dir schema_snapshots/contracts --contract-id week3-extractions

.\.venv\Scripts\python.exe contracts/generator.py --source outputs/week5/events.jsonl --lineage outputs/week4/lineage_snapshots.jsonl --registry contract_registry/subscriptions.yaml --output generated_contracts/week5_events.yaml --snapshot-dir schema_snapshots/contracts --contract-id week5-events
```

### 2. Run clean validation

```powershell
.\.venv\Scripts\python.exe contracts/runner.py --contract generated_contracts/week3_extractions.yaml --data outputs/week3/extractions.jsonl --output validation_reports/thursday_baseline.json --registry contract_registry/subscriptions.yaml --mode AUDIT --baselines schema_snapshots/baselines.json --violation-log violation_log/violations.jsonl
```

### 3. Inject the known violation

`outputs/week3/extractions_violated.jsonl` is the test artifact where `extracted_facts[].confidence` values are multiplied by `100`.

### 4. Run violated validation

```powershell
.\.venv\Scripts\python.exe contracts/runner.py --contract generated_contracts/week3_extractions.yaml --data outputs/week3/extractions_violated.jsonl --output validation_reports/injected_violation_audit.json --registry contract_registry/subscriptions.yaml --mode AUDIT --baselines schema_snapshots/baselines.json --violation-log violation_log/violations.jsonl

.\.venv\Scripts\python.exe contracts/runner.py --contract generated_contracts/week3_extractions.yaml --data outputs/week3/extractions_violated.jsonl --output validation_reports/injected_violation_warn.json --registry contract_registry/subscriptions.yaml --mode WARN --baselines schema_snapshots/baselines.json --violation-log violation_log/violations.jsonl

.\.venv\Scripts\python.exe contracts/runner.py --contract generated_contracts/week3_extractions.yaml --data outputs/week3/extractions_violated.jsonl --output validation_reports/injected_violation.json --registry contract_registry/subscriptions.yaml --mode ENFORCE --baselines schema_snapshots/baselines.json --violation-log violation_log/violations.jsonl
```

### 5. Run attribution

```powershell
.\.venv\Scripts\python.exe contracts/attributor.py --report validation_reports/injected_violation.json --baseline-report validation_reports/thursday_baseline.json --violation-log violation_log/violations.jsonl --lineage outputs/week4/lineage_snapshots.jsonl --registry contract_registry/subscriptions.yaml --contract generated_contracts/week3_extractions.yaml --output violation_log/blame_chain.json
```

### 6. Run schema evolution analysis

```powershell
.\.venv\Scripts\python.exe contracts/schema_analyzer.py --contract-id week3-extractions --snapshot-root schema_snapshots/contracts --registry contract_registry/subscriptions.yaml --simulate rename_confidence_field --compatibility-output schema_snapshots/compatibility_report.json --summary-output schema_snapshots/evolution_summary.json
```

### 7. Run AI extensions

```powershell
.\.venv\Scripts\python.exe contracts/ai_extensions.py --week3 outputs/week3/extractions.jsonl --week2 outputs/week2/verdicts.jsonl --traces outputs/traces/runs.jsonl --canonical-traces-output outputs/traces/runs_contract_boundary.jsonl --registry contract_registry/subscriptions.yaml --output enforcer_report/ai_metrics.json --violation-log violation_log/violations.jsonl
```

### 8. Generate the final report

```powershell
.\.venv\Scripts\python.exe contracts/report_generator.py --baseline validation_reports/thursday_baseline.json --injected validation_reports/injected_violation.json --audit-injected validation_reports/injected_violation_audit.json --warn-injected validation_reports/injected_violation_warn.json --blame-chain violation_log/blame_chain.json --compatibility schema_snapshots/compatibility_report.json --evolution-summary schema_snapshots/evolution_summary.json --ai-metrics enforcer_report/ai_metrics.json --violation-log violation_log/violations.jsonl --output-dir enforcer_report
```

## Current verification status

### Contracts

Verified:

- all four generated contract files exist
- all four parse successfully as YAML
- the Bitol contracts include structural, numeric, registry, and lineage sections
- the dbt counterparts include generated tests for required fields, enums, patterns, and numeric ranges
- live dbt smoke verification now passes via `contracts/dbt_smoke_verify.py`
- `enforcer_report/dbt_verification.json` records successful `seed`, `run`, and `test` execution

### Validation

Current rerun status:

- clean baseline: `38 / 38` checks passed
- injected violation in `AUDIT`: `2` failures, allowed with audit trail
- injected violation in `WARN`: `2` failures, blocked
- injected violation in `ENFORCE`: `2` failures, blocked

The two expected failed checks are:

- `week3-extractions.fact_confidence.range`
- `week3-extractions.fact_confidence.drift`

### Attribution

Current strongest attribution result:

- top file: `src/agents/fact_table.py`
- top commit: `033135cc46c7b8889cb8bf4f6607f940469bed5b`

### Schema evolution

Current CI-gate result:

- simulated rename of the confidence field is classified as breaking
- overall decision: `FAIL`

### AI risk

Current AI findings:

- embedding drift: `PASS`
- prompt input schema validation: `PASS`
- LLM output schema validation: `PASS`
- trace contract risk: `PASS`

## Remaining honest limitations

- Week 4 lineage is now canonical and useful, but it still does not expose a clean explicit Week 3 consumer path, so lineage specificity is weaker than registry-based impact analysis.

## Best current truth sources

If you want the current repo-wide truth rather than historical phase snapshots, start with:

- `reports/final_audit.md`
- `DOMAIN_NOTES.md`
- `enforcer_report/report_summary.md`
- `enforcer_report/report_data.json`
