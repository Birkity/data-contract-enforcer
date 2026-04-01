# Data Contract Enforcer

This repository is currently focused on **Phase 0** of TRP Week 7: understanding the real shape of the upstream data before writing the contract engine itself.

## What is here right now

- Week 7 reference docs in markdown:
  - `TRP1 Challenge Week 7_ Data Contract Enforcer.md`
  - `TRP1 Practitioner Manual_ Data Contract Enforcer.md`
- Prior-week outputs under `outputs/`
- LangSmith trace export under `outputs/traces/runs.jsonl`
- Phase 0 deliverables:
  - `DOMAIN_NOTES.md`
  - `reports/phase_0.md`

## Current readiness summary

- `Week 1` is structurally close to the canonical Week 7 schema.
- `Week 2` is structurally close, but the record count is small.
- `Week 3` now meets the minimum volume requirement, but it still does not match the canonical extraction schema.
- `Week 4` now exists at the canonical filename, but the content is still not in the canonical JSONL snapshot shape.
- `Week 5` has enough volume, but the event envelope does not match the canonical Week 7 event schema.
- `LangSmith traces` are present and exceed the minimum count, but the exported trace schema still needs contract-aware normalization.

## Important Phase 0 conclusion

This repo is **not ready for a clean Phase 1 start yet**. The Week 7 manual says schema mismatches should be documented in `DOMAIN_NOTES.md` and handled with migration logic before proceeding. The biggest blockers are Week 3, Week 4, and Week 5 schema alignment.

## Files to read first

- `DOMAIN_NOTES.md`
- `reports/phase_0.md`
- `outputs/week1/intent_records.jsonl`
- `outputs/week2/verdicts.jsonl`
- `outputs/week3/extractions.jsonl`
- `outputs/week4/lineage_snapshots.jsonl`
- `outputs/week5/events.jsonl`
- `outputs/traces/runs.jsonl`

## Notes on traces

This repo includes a local helper, `export_langsmith_runs.py`, because the shell `langsmith export` command was not available in this environment. The helper was used to support trace export into `outputs/traces/runs.jsonl`.

## Next step after Phase 0

Before starting generator/runner code, create migration scripts for the non-canonical outputs and produce canonical Week 7 input views for:

- Week 3 extractions
- Week 4 lineage snapshots
- Week 5 events
