# Data Contract Enforcer

This repository currently contains:

- completed Phase 0 analysis and domain notes
- regenerated **Phase 1 ContractGenerator**
- regenerated **Phase 2 ValidationRunner**
- generated **dbt-compatible contract counterparts**
- real Week 1 to Week 5 output snapshots under `outputs/`

## Current Phase 1 deliverables

- `contracts/generator.py`
- `generated_contracts/week3_extractions.yaml`
- `generated_contracts/week3_extractions_dbt.yml`
- `generated_contracts/week5_events.yaml`
- `generated_contracts/week5_events_dbt.yml`
- `reports/phase_0.md`
- `reports/phase_1.md`
- `contracts/runner.py`
- `validation_reports/thursday_baseline.json`
- `validation_reports/injected_violation.json`
- `violation_log/violations.jsonl`
- `schema_snapshots/baselines.json`
- `reports/phase_2.md`
- `DOMAIN_NOTES.md`

## What Phase 1 does

The generator is scoped to **ContractGenerator only**.

It:

- reads the real Week 3 extraction snapshot from `outputs/week3/extractions.jsonl`
- validates that the source file is present and non-empty
- prints the record count and one sample record
- explodes `extracted_facts[]` into one profiled row per fact
- profiles observed columns with pandas
- generates a human-readable Bitol-style YAML contract
- generates a parallel dbt-compatible `schema.yml` counterpart with equivalent tests
- injects lineage notes from `outputs/week4/lineage_snapshots.jsonl`
- runs a quality check before finishing

It does **not**:

- run validation
- create violation reports
- perform blame attribution
- call an LLM or use Ollama during generation

## Current Phase 2 deliverables

Phase 2 is now restored with:

- `contracts/runner.py`
- `validation_reports/thursday_baseline.json`
- `validation_reports/injected_violation.json`
- `violation_log/violations.jsonl`
- `schema_snapshots/baselines.json`
- `reports/phase_2.md`

The runner:

- loads the generated contract
- flattens Week 3 data the same way as the generator
- runs structural checks first
- runs statistical checks second
- creates a clean baseline report
- detects the injected confidence-scale violation
- logs all non-pass results in structured JSONL format

## Run Phase 1

From the repo root:

```powershell
.\.venv\Scripts\python.exe contracts/generator.py --source outputs/week3/extractions.jsonl --lineage outputs/week4/lineage_snapshots.jsonl --output generated_contracts
```

The generated contract is written to:

```text
generated_contracts/week3_extractions.yaml
generated_contracts/week3_extractions_dbt.yml
generated_contracts/week5_events.yaml
generated_contracts/week5_events_dbt.yml
```

## Contract verification status

The generated contract artifacts have been verified at the file and YAML-structure level:

- all four generated contract files exist
- all four parse successfully as YAML
- the Bitol contracts include schema clauses and lineage metadata
- the dbt counterparts include `version: 2`, a `models` block, column definitions, and generated tests
- key checks are present, including the Week 3 `fact_confidence` range test and the Week 5 `event_id` uniqueness/UUID checks

What is **not** yet verified in this environment:

- `dbt test` runtime execution

The reason is simple: the `dbt` CLI is not installed in this local environment, so artifact generation is verified, but live dbt execution is still pending.

## Current Week 3 observations

Using the current canonical Week 3 file:

- `50` extraction records were loaded
- flattening produced `402` profiled rows
- `extracted_facts[]` is the repeated field used for profiling
- `374` fact-level confidence values were observed
- fact confidence range is `0.55` to `1.0`
- fact confidence mean is `0.8063636363636363`

## Current Phase 2 observations

From the regenerated validation runs:

- clean baseline report: `37` checks, all passed
- injected violation report: `37` checks, `2` failed
- the injected failure is correctly caught on `fact_confidence`
- the two detected failures are:
  - `week3-extractions.fact_confidence.range`
  - `week3-extractions.fact_confidence.drift`
- rerunning without cleanup appends new non-pass entries to `violation_log/violations.jsonl`

## Lineage caveat

The current Week 4 lineage file is still a dbt-style whole-file JSON graph, not the canonical Week 7 node/edge snapshot format.

Phase 1 still loads it and records lineage context, but the generated contract honestly notes that:

- no explicit downstream consumer of the Week 3 extraction output was found
- blast-radius detail will improve once Week 4 lineage is migrated

## Local models

Your available Ollama/cloud models are useful for later AI-assisted phases, but this Phase 1 generator is deterministic and does not invoke them.
