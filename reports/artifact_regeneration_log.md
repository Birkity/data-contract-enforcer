# Artifact Regeneration Log

## Purpose

This log records which artifacts were regenerated during the update from the older Phase 0-3 implementation to the registry-first, consumer-boundary architecture described in the updated docs.

## 1. Contracts and schema outputs

### Regenerated

- `generated_contracts/week3_extractions.yaml`
- `generated_contracts/week3_extractions_dbt.yml`
- `generated_contracts/week5_events.yaml`
- `generated_contracts/week5_events_dbt.yml`

### Why

- contracts needed registry context
- contracts needed updated implementation-model metadata
- lineage needed to be reframed as enrichment only
- dbt counterparts needed to remain aligned with regenerated Bitol contracts

### What changed

- added registry-first blast-radius context
- added contract snapshots
- updated contract metadata from lineage-first to registry-first

## 2. Contract snapshots

### Generated

- `schema_snapshots/contracts/week3-extractions/latest.yaml`
- `schema_snapshots/contracts/week3-extractions/20260402T104355Z.yaml`
- `schema_snapshots/contracts/week5-events/latest.yaml`
- `schema_snapshots/contracts/week5-events/20260402T104355Z.yaml`

### Why

- updated docs say generator should still write snapshots
- later schema-evolution work needs durable contract history

### Status

- new artifacts

## 3. Validation artifacts

### Regenerated

- `validation_reports/thursday_baseline.json`
- `validation_reports/injected_violation_audit.json`
- `validation_reports/injected_violation_warn.json`
- `validation_reports/injected_violation.json`
- `schema_snapshots/baselines.json`
- `violation_log/violations.jsonl`

### Why

- runner needed new mode semantics
- reports needed decision/blocking metadata
- violation log needed mode/action/blocking fields
- baseline was refreshed so the new reports were built from a clean updated state

### What changed

- validation reports now include:
  - `validation_mode`
  - `decision`
  - `blocking`
  - `architecture_context`
  - `registry_subscribers`

## 4. Attribution artifacts

### Regenerated

- `violation_log/blame_chain.json`

### Why

- attribution needed to move from lineage-first blast radius to registry-first blast radius

### What changed

- blame chain now separates:
  - primary registry blast radius
  - lineage enrichment
  - git-backed likely cause

## 5. Preserved backups

To avoid silently losing the prior generated state while still refreshing the live artifacts, I preserved:

- `schema_snapshots/baselines_pre_update_backup.json`
- `violation_log/violations_pre_update_backup.jsonl`

These were kept only for comparison and migration traceability.

## 6. Artifacts kept without regeneration

These were kept as-is because they were still valid inputs rather than stale generated outputs:

- `outputs/week3/extractions.jsonl`
- `outputs/week3/extractions_violated.jsonl`
- `outputs/week4/lineage_snapshots.jsonl`
- `outputs/week5/events.jsonl`

## 7. Artifacts deprecated conceptually

The older generated artifacts are no longer wrong as files, but their old interpretation is deprecated:

- lineage-only blast-radius assumptions in old contracts
- mode-less validation semantics in old runner outputs
- lineage-first blast radius in the old blame-chain interpretation

## 8. Summary

This regeneration pass replaced the Phase 1-3 generated artifacts that were semantically stale under the updated docs, while preserving lightweight comparison backups where that improved traceability.
