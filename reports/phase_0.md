# Phase 0 Report

## Goal

Complete **Phase 0 only** for TRP Week 7 by reading the challenge doc and Practitioner Manual, inspecting the real upstream outputs, and documenting what is ready, what is mismatched, and what must be fixed before Phase 1.

## What I read first

- `TRP1 Challenge Week 7_ Data Contract Enforcer.md`
- `TRP1 Practitioner Manual_ Data Contract Enforcer.md`

Key requirements taken from those docs:

- `DOMAIN_NOTES.md` is a primary graded deliverable.
- Phase 0 must use evidence from the real systems, not generic examples.
- The manual expects:
  - `outputs/week1/intent_records.jsonl >= 10`
  - `outputs/week3/extractions.jsonl >= 50`
  - `outputs/week4/lineage_snapshots.jsonl >= 1`
  - `outputs/week5/events.jsonl >= 50`
  - `outputs/traces/runs.jsonl >= 50`
- If actual output schemas differ from the canonical Week 7 schemas, the differences must be documented and migration scripts must be written before proceeding.

## Files inspected

- `outputs/week1/intent_records.jsonl`
- `outputs/week2/verdicts.jsonl`
- `outputs/week3/extractions.jsonl`
- `outputs/week4/lineage_snapshots.jsonl`
- `outputs/week5/events.jsonl`
- `outputs/traces/runs.jsonl`

## What was checked

For each file, I checked:

- existence
- record count
- whether the file is valid JSONL or some other JSON shape
- top-level keys
- fit against the canonical Week 7 schema
- obvious contract-relevant signals such as confidence ranges, event envelope shape, and trace run types

## Current output status

### Week 1

- file exists
- 16 records
- top-level keys match the canonical Week 7 intent schema
- confidence values in `code_refs[]` are in the 0.91 to 0.98 range

Assessment: usable as-is for Phase 0 evidence.

### Week 2

- file exists
- 3 records
- top-level keys match the canonical Week 7 verdict schema
- `overall_verdict` values observed: `PASS`

Assessment: structurally usable, but sparse. This is not a formal Phase 0 blocker, though it is thin input for later AI extension work.

### Week 3

- file exists
- 50 records
- meets the required minimum of 50
- current schema is summary-style output, not canonical extraction output

Observed real keys:

- `document_id`
- `source_filename`
- `strategy_used`
- `confidence_score`
- `escalation_triggered`
- `escalation_reason`
- `estimated_cost`
- `processing_time_s`
- `flagged_for_review`

Missing canonical keys include:

- `doc_id`
- `source_path`
- `source_hash`
- `extracted_facts`
- `entities`
- `extraction_model`
- `processing_time_ms`
- `token_count`
- `extracted_at`

Observed statistics on the real field that exists:

- `confidence_score` min = `0.000`
- `confidence_score` max = `1.000`
- `confidence_score` mean = `0.549294`

Canonical `extracted_facts[].confidence` count found: `0`

Assessment: the volume requirement is now satisfied, but schema migration is still required before the canonical Week 7 extraction contract can run.

### Week 4

- canonical file expected by the docs: `outputs/week4/lineage_snapshots.jsonl`
- canonical filename now exists
- current file content is still a single pretty-printed JSON document, not JSONL
- top-level keys are `datasets`, `edges`, and `transformations`

Observed graph evidence:

- 25 datasets
- 30 edges
- 13 transformations
- sample edge: `source.ecom.raw_customers -> sql:models/staging/stg_customers.sql`
- sample transformation source file: `models/marts/customers.sql`

Assessment: Phase 0 blocker. The file is useful lineage evidence and now lives at the expected path, but it still does not match the canonical snapshot schema or JSONL format.

### Week 5

- file exists
- 1198 records
- exceeds the required minimum of 50
- schema is event-stream oriented but not canonical Week 7 event-contract shape

Observed real keys:

- `stream_id`
- `event_type`
- `event_version`
- `payload`
- `recorded_at`

Missing canonical keys include:

- `event_id`
- `aggregate_id`
- `aggregate_type`
- `sequence_number`
- `metadata`
- `schema_version`
- `occurred_at`

Assessment: enough real data is present, but migration is required before the Week 7 event contract can be applied.

### Traces

- file exists
- 153 records
- exceeds the required minimum of 50
- token arithmetic is clean across all 153 records
- observed run types: `llm`, `chain`, `tool`, `prompt`, `parser`

Important mismatch:

- canonical Week 7 trace contract expects run types from `llm|chain|tool|retriever|embedding`
- current export includes `prompt` and `parser`

Assessment: usable for Phase 0 and strong on volume, but still needs contract-aware normalization or explicit documented deviation.

## Transformations performed in this Phase 0 workflow

Phase 0 was intentionally documentation-first. I did **not** start Phase 1 implementation code such as `contracts/generator.py` or `contracts/runner.py`.

What was done in this phase:

1. Read the Week 7 challenge document and Practitioner Manual.
2. Inspected the real upstream outputs under `outputs/`.
3. Compared each real output to the canonical Week 7 schema.
4. Calculated real Week 3 confidence statistics using the field that actually exists.
5. Verified the current LangSmith trace export volume and basic invariants.
6. Refreshed `outputs/week3/extractions.jsonl` from the real Week 3 system so the file now contains 50 real records while preserving the source system's current schema shape.
7. Wrote the Phase 0 artifacts:
   - `DOMAIN_NOTES.md`
   - `README.md`
   - `reports/phase_0.md`

Relevant repo support work completed during this broader setup:

- `export_langsmith_runs.py` was added because the `langsmith export` CLI was not available in this environment.
- `.env` support was added for local LangSmith API loading.
- `.env` was added to `.gitignore`.
- `outputs/traces/runs.jsonl` is now present and exportable from local tooling.

## Schema mismatches that matter before Phase 1

### Week 3 mismatch

Canonical Week 7 expects a document extraction record with nested `extracted_facts[]` and `entities[]`.

Current file is a record-level operational summary, not an extraction payload.

Impact:

- confidence range contract cannot be applied to `extracted_facts[].confidence`
- entity relationship checks cannot run
- extraction text drift and embedding checks cannot run on the intended data shape

### Week 4 mismatch

Canonical Week 7 expects JSONL snapshots with `snapshot_id`, `codebase_root`, `git_commit`, `nodes`, `edges`, and `captured_at`.

Current file is a single JSON document with `datasets`, `edges`, and `transformations`.

Impact:

- the expected snapshot interface is absent
- the exact file path the manual references is absent
- git-anchored blame attribution will be weaker unless the lineage graph is migrated

### Week 5 mismatch

Canonical Week 7 expects a full event-contract envelope.

Current file is a smaller event-stream record shape.

Impact:

- aggregate sequence checks cannot run
- `occurred_at` vs `recorded_at` timing checks cannot run
- metadata-based lineage and ownership checks are not available yet

### Trace mismatch

Canonical Week 7 expects a tighter run-type enum than the raw export currently uses.

Impact:

- a strict trace contract would flag part of the current export immediately

## Risks and blockers before Phase 1

The main blockers are:

1. Week 3, Week 4, and Week 5 do not match the canonical Week 7 schemas.
2. `outputs/week4/lineage_snapshots.jsonl` is not valid JSONL and does not expose canonical snapshot records.
3. `outputs/migrate/` and the required migration scripts do not yet exist.

## Recommendation

Do not start Phase 1 contract generation against the raw Week 3, Week 4, and Week 5 files as they currently stand.

The clean next step is:

1. create `outputs/migrate/`
2. write migration scripts for Week 3, Week 4, and Week 5
3. produce canonical Week 7-compatible views
4. document those migrations in the repo
5. then begin Phase 1 using the migrated canonical inputs
