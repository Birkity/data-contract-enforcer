# Phase 2 Report

## Scope

This report covers **TRP Week 7 Phase 2 only**:

- `contracts/runner.py`
- `validation_reports/thursday_baseline.json`
- `validation_reports/injected_violation.json`
- `violation_log/violations.jsonl`
- `outputs/week3/extractions_violated.jsonl`
- `schema_snapshots/baselines.json`

This phase does **not** implement:

- attribution
- schema evolution analysis
- AI extensions

## What I re-read before building

I re-read the Phase 2 sections in:

- `TRP1 Challenge Week 7_ Data Contract Enforcer.md`
- `TRP1 Practitioner Manual_ Data Contract Enforcer.md`

The main expectations I implemented were:

- the runner must execute the generated contract against a real JSONL snapshot
- structural checks run before statistical checks
- missing columns return structured `ERROR` results instead of crashing
- numeric baselines are stored in `schema_snapshots/baselines.json`
- a known confidence-scale violation is injected and detected
- the output must include machine-readable validation reports and a violation log

## 1. What I implemented

I recreated:

- `contracts/runner.py`

The runner does the following:

1. Loads the contract YAML
2. Loads the input JSONL data snapshot
3. Flattens the data using the same logic as `contracts/generator.py`
4. Runs structural checks first
5. Runs statistical checks second
6. Writes a structured validation report JSON
7. Appends all non-pass results to `violation_log/violations.jsonl`
8. Writes numeric baselines after the first clean run

## 2. Types of checks implemented

### Structural checks

- required field check
- type check
- enum conformance check
- UUID format check
- datetime parse check
- regex pattern check

### Statistical checks

- minimum / maximum range check
- baseline drift check
  - `WARN` if deviation is greater than 2 standard deviations
  - `FAIL` if deviation is greater than 3 standard deviations

## 3. Baseline results

Command run:

```powershell
.\.venv\Scripts\python.exe contracts/runner.py --contract generated_contracts/week3_extractions.yaml --data outputs/week3/extractions.jsonl --output validation_reports/thursday_baseline.json
```

### Baseline summary

- total checks: `37`
- passed: `37`
- failed: `0`
- warned: `0`
- errored: `0`

### What happened

The clean rerun passed completely and overwrote:

- `validation_reports/thursday_baseline.json`

The baseline file in `schema_snapshots/baselines.json` already existed before this rerun, so drift checks were included in the clean report this time.

Because the Week 3 file is now canonical, validation is happening at fact level for:

- `fact_confidence`
- `fact_fact_id`
- `fact_text`
- `fact_page_ref`
- `fact_source_excerpt`

The flattening step preserved document-level fields while exploding `extracted_facts[]`.

Observed baseline shape:

- `50` extraction records
- `402` flattened validation rows
- `374` fact-level confidence values

### Baseline statistics stored

The baseline file recorded:

- `entities_count`
  - mean: `50.92537313432836`
  - stddev: `45.068851765785624`
- `processing_time_ms`
  - mean: `61470.49751243781`
  - stddev: `76363.12733440478`
- `token_count_input`
  - mean: `451.3134328358209`
  - stddev: `420.2289855162144`
- `token_count_output`
  - mean: `123.81592039800995`
  - stddev: `80.43988133383296`
- `fact_entity_refs_count`
  - mean: `0.93048128342246`
  - stddev: `0.7542418265335848`
- `fact_confidence`
  - mean: `0.8063636363636365`
  - stddev: `0.11398526015257286`
- `fact_page_ref`
  - mean: `29.17379679144385`
  - stddev: `32.76890008669152`

## 4. Injected violation

I recreated:

- `outputs/week3/extractions_violated.jsonl`

### What I changed

I multiplied every numeric `extracted_facts[].confidence` value by `100`.

Examples:

- `1.0 -> 100.0`
- `0.9 -> 90.0`
- `0.55 -> 55.00000000000001`

### Why this is a breaking change

The contract says fact confidence must remain in the `0.0` to `1.0` range.

Changing the scale to `0` to `100` is dangerous because:

- the values are still numeric, so a simple type check would still pass
- downstream ranking and filtering logic would keep running but produce the wrong decisions
- the failure looks plausible unless range and drift checks exist

This is the exact failure mode the Week 7 docs call out.

## 5. Validation results after injection

Command run:

```powershell
.\.venv\Scripts\python.exe contracts/runner.py --contract generated_contracts/week3_extractions.yaml --data outputs/week3/extractions_violated.jsonl --output validation_reports/injected_violation.json
```

### Injected-run summary

- total checks: `37`
- passed: `35`
- failed: `2`
- warned: `0`
- errored: `0`

### Which checks failed

#### 1. Fact confidence range check

- check id: `week3-extractions.fact_confidence.range`
- status: `FAIL`
- severity: `CRITICAL`
- actual: `min=55.00000000000001, max=100.0`
- expected: `min>=0.0, max<=1.0`
- failing records: `374`
- sample failing values:
  - `100.0`
  - `100.0`
  - `100.0`
  - `100.0`
  - `100.0`

Meaning:

- the explicit contract range rule caught the breaking scale change immediately

#### 2. Fact confidence drift check

- check id: `week3-extractions.fact_confidence.drift`
- status: `FAIL`
- severity: `HIGH`
- actual: `mean=80.63636363636364, z_score=700.35`
- expected baseline:
  - mean: `0.8063636363636365`
  - stddev: `0.11398526015257286`
- failing records: `374`

Meaning:

- even without the hard range rule, the baseline drift check still catches the same violation because the mean moved far outside the normal distribution

### What still passed after injection

- all structural checks
- all unrelated numeric checks

This is important because it shows the runner is specific. It did not create noisy failures on fields that were not modified.

## 6. Issues encountered

### Issue 1: First-run and rerun baseline reports have different total check counts

This is expected.

On the first run, there is no baseline yet, so drift checks are not emitted. Once `schema_snapshots/baselines.json` exists, later clean reruns include drift checks too.

Impact:

- first clean run: `30` checks
- later clean rerun: `37` checks
- violated report: `37` checks

### Issue 2: Flattened row count is larger than document count

This is also expected.

The runner validates fact-level fields, so it explodes `extracted_facts[]`.

Impact:

- `50` document-level extraction records
- `402` flattened validation rows
- `374` fact rows with numeric confidence values

### Issue 3: Week 4 lineage enrichment is still limited

This did not block Phase 2 itself, but it remains a real downstream constraint for later attribution work.

Impact:

- validation works
- later blame-chain quality will still depend on fixing Week 4 lineage shape

### Issue 4: Violation log grows on rerun

This is expected with the current runner behavior.

The runner appends non-pass results to `violation_log/violations.jsonl` instead of deduplicating by `snapshot_id` or `check_id`.

Impact:

- after the earlier violated run, the log had `2` entries
- after rerunning Phase 2 without cleanup, the log now has `4` entries

## 7. Key insights

### Insight 1

Phase 2 is now validating the canonical Week 3 schema, not the old legacy summary format.

### Insight 2

The confidence-scale breaking change is now caught at the correct field:

- `fact_confidence`

That is a stronger result than the earlier legacy-field version.

### Insight 3

The runner proves why Week 7 needs both structural and statistical checks:

- structural checks alone would not catch `0.0-1.0` changing to `0-100`
- range and drift checks turn that silent semantic break into a clear failure

### Insight 4

The runner stayed stable end to end:

- no crashes
- valid JSON reports
- clean baseline creation
- clear machine-readable violation log entries
