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

## What I read before building

I re-read the Phase 2 sections in:

- `TRP1 Challenge Week 7_ Data Contract Enforcer.md`
- `TRP1 Practitioner Manual_ Data Contract Enforcer.md`

The main implementation requirements I used were:

- ValidationRunner must never crash
- structural checks come first
- statistical checks come second
- missing columns must return `ERROR` instead of crashing
- baseline means and stddevs must be written to `schema_snapshots/baselines.json`
- the injected confidence scale change must be detected
- results must be written as structured JSON plus a violation log

## 1. What I implemented

### ValidationRunner structure

I created:

- `contracts/runner.py`

The runner does the following:

1. Loads the contract YAML
2. Loads the JSONL data snapshot
3. Flattens the data using the **same flattening logic as the generator**
4. Executes structural checks
5. Executes statistical checks
6. Writes a structured validation report JSON
7. Appends non-pass results to `violation_log/violations.jsonl`
8. Writes baseline statistics to `schema_snapshots/baselines.json` on first run

### Types of checks implemented

#### Structural checks

- required field check
- type check
- enum conformance check
- UUID format check
- datetime parse check
- regex pattern check

#### Statistical checks

- minimum / maximum range check
- baseline drift check using the exact manual logic:
  - `WARN` if deviation > 2 stddev
  - `FAIL` if deviation > 3 stddev

## 2. Baseline results

Command run:

```powershell
.\.venv\Scripts\python.exe contracts/runner.py --contract generated_contracts/week3_extractions.yaml --data outputs/week3/extractions.jsonl --output validation_reports/thursday_baseline.json
```

### Baseline summary

- total checks: `22`
- passed: `22`
- failed: `0`
- warned: `0`
- errored: `0`

### What happened

The baseline run passed cleanly and also created:

- `schema_snapshots/baselines.json`

Observed baseline numeric statistics written:

- `confidence_score`
  - mean: `0.5492940000000001`
  - stddev: `0.40966975022446994`
- `processing_time_s`
  - mean: `27.084928`
  - stddev: `60.39388920786484`

### Unexpected findings

There were no runner failures on the clean file, but there is an important project-level caveat:

- the live Week 3 data is still a legacy summary schema
- so the contract and runner are validating `confidence_score`
- not canonical `extracted_facts[].confidence`

That is honest to the real data, but it means this Phase 2 validation is currently record-level, not fact-level.

## 3. Injected violation

I created:

- `outputs/week3/extractions_violated.jsonl`

### What I changed

I multiplied the live Week 3 confidence field by `100`.

Because the real current file does **not** contain canonical `extracted_facts[].confidence`, I applied the change to the field that actually exists:

- `confidence_score`

The injection changed values such as:

- `1.0 -> 100.0`
- `0.15 -> 15.0`
- `0.55 -> 55.0`

### Why this is a breaking change

The contract says confidence must stay in the `0.0` to `1.0` range.

Changing the scale to `0` to `100` is dangerous because:

- type checks may still pass since the values are still numeric
- downstream logic may still run
- the outputs become silently wrong

This is exactly the failure mode the Week 7 challenge warns about.

## 4. Validation results after injection

Command run:

```powershell
.\.venv\Scripts\python.exe contracts/runner.py --contract generated_contracts/week3_extractions.yaml --data outputs/week3/extractions_violated.jsonl --output validation_reports/injected_violation.json
```

### Injected-run summary

- total checks: `24`
- passed: `22`
- failed: `2`
- warned: `0`
- errored: `0`

### Which checks failed

#### 1. Confidence range check

- check id: `week3-extractions.confidence_score.range`
- status: `FAIL`
- severity: `CRITICAL`
- actual: `min=0.0, max=100.0`
- expected: `min>=0.0, max<=1.0`
- failing records: `38`
- sample failing values:
  - `100.0`
  - `15.0`
  - `100.0`
  - `100.0`
  - `55.0`

Meaning:

- the explicit contract range check caught the scale break immediately

#### 2. Confidence drift check

- check id: `week3-extractions.confidence_score.drift`
- status: `FAIL`
- severity: `HIGH`
- actual: `mean=54.93, z_score=132.74`
- expected baseline:
  - mean: `0.5492940000000001`
  - stddev: `0.40966975022446994`
- failing records: `50`

Meaning:

- even if someone removed or weakened the hard range check later, the drift logic would still catch this change because the mean moved massively from baseline

### What passed after injection

- all structural checks still passed
- `processing_time_s.drift` stayed `PASS`

This is an important proof point:

- the system can distinguish a targeted statistical violation from unrelated stable fields

## 5. Issues encountered

### Issue 1: The real Week 3 schema is not canonical

The Week 3 file still uses:

- `document_id`
- `confidence_score`

instead of canonical:

- `doc_id`
- `extracted_facts[].confidence`

Impact:

- the injected violation had to target `confidence_score`
- the failing check name is therefore `confidence_score.range`, not `extracted_facts.confidence.range`

### Issue 2: Baseline drift checks only appear after baseline creation

On the first clean run, the runner created `schema_snapshots/baselines.json`.

Because there was no prior baseline yet:

- the first run did not emit drift results
- the second run did

This matches the manual’s intended flow, but it means baseline and violated reports do not have the exact same total check count.

### Issue 3: The contract is honest to the live file, not the ideal schema

This is not a bug in the runner, but it is a real constraint:

- the runner is correctly validating the actual contract it was given
- the contract itself reflects the legacy Week 3 data shape

So Phase 2 is working, but full canonical Week 7 validation still depends on upstream schema migration.

## 6. Key insights

### Insight 1

The ValidationRunner is doing the right job:

- it catches hard structural/constraint violations
- it also catches statistical drift that could otherwise slip past type checks

### Insight 2

The confidence scale example is now proven end-to-end on real repo data.

The injected change:

- did not crash the pipeline
- did not break numeric typing
- but it was still detected correctly by both:
  - the range check
  - the drift check

That is exactly the kind of silent production failure Phase 2 is supposed to prevent.

### Insight 3

The main remaining risk is upstream schema quality, not runner stability.

The runner itself stayed stable across:

- clean data
- broken data
- real legacy schema

The bigger project risk is that Week 3 still is not in canonical `extracted_facts[]` form, so later phases will only be as strong as the migrated upstream data.

## Output files produced in this phase

- `contracts/runner.py`
- `validation_reports/thursday_baseline.json`
- `validation_reports/injected_violation.json`
- `violation_log/violations.jsonl`
- `outputs/week3/extractions_violated.jsonl`
- `schema_snapshots/baselines.json`

## Final outcome

Phase 2 succeeded.

The runner:

- executes structural and statistical checks
- writes structured validation reports
- writes a violation log
- survives bad input without crashing
- catches the injected confidence scale violation
