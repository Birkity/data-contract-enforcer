# Data Contract Enforcer

This repository now has the **Phase 1 ContractGenerator** in place for TRP Week 7.

## What is implemented

- `contracts/generator.py`
- `generated_contracts/week3_extractions.yaml`
- `reports/phase_0.md`
- `reports/phase_1.md`
- `DOMAIN_NOTES.md`

## Phase 1 scope

The current implementation is intentionally scoped to **ContractGenerator only**.

It:

- reads real Week 3 JSONL data
- profiles the observed columns with pandas
- generates a human-readable Bitol-style YAML contract
- injects lineage context from the provided Week 4 lineage file

It does **not** implement:

- `contracts/runner.py`
- ValidationRunner logic
- blame attribution
- schema evolution diffing
- later-phase AI enforcement

## Main command

Run the generator from the repo root:

```powershell
.\.venv\Scripts\python.exe contracts/generator.py --source outputs/week3/extractions.jsonl --output generated_contracts
```

The lineage input defaults to:

```text
outputs/week4/lineage_snapshots.jsonl
```

The generated contract is written to:

```text
generated_contracts/week3_extractions.yaml
```

## Real-data behavior

The generator is designed to handle both:

- canonical Week 3 records with `extracted_facts[]`
- the current live Week 3 legacy summary format in this repo

Right now the live Week 3 file is still the legacy summary format, so the generator:

- loads all records
- prints the record count and a sample record
- warns about missing canonical fields
- falls back to **one profiled row per record** because `extracted_facts[]` is not present

## Current Week 3 observations

From the live `outputs/week3/extractions.jsonl` file used by the generator:

- 50 records were loaded
- `confidence_score` stays within `0.0` to `1.0`
- observed confidence mean is `0.549294`
- current fields are:
  - `document_id`
  - `source_filename`
  - `strategy_used`
  - `confidence_score`
  - `escalation_triggered`
  - `escalation_reason`
  - `estimated_cost`
  - `processing_time_s`
  - `flagged_for_review`

## Lineage caveat

The current `outputs/week4/lineage_snapshots.jsonl` file is still a non-canonical dbt-style graph stored as a single JSON document.

The generator still loads it and injects lineage context, but it records that:

- no explicit Week 3 consumer nodes were found
- downstream blast-radius detail will improve once Week 4 is migrated to the canonical snapshot schema

## Local models

Your local Ollama models are noted, but **Phase 1 does not require model calls**. The generator is deterministic and does not invoke LLMs.
