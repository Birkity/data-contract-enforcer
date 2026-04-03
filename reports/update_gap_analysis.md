# Update Gap Analysis

## Purpose

This report captures the gap analysis I performed after re-reading the updated Week 7 challenge document, the updated Practitioner Manual, the existing reports in `reports/`, and the live implementation artifacts already present in this repository.

The goal of this migration pass is intentionally limited to the implementation already built through roughly Phase 3. The updated docs also strengthen Phase 4, but this pass focuses on bringing Phase 0 through Phase 3 into architectural compliance.

## 1. Summary of the updated doc changes

The updated docs make six architecture corrections that materially affect this repo:

1. Enforcement is now described as a **consumer-boundary activity**, not a producer-side one.
2. The **Contract Registry** is now the primary source of blast radius.
3. **Lineage still matters**, but it is now an enrichment layer rather than the main blast-radius source.
4. ValidationRunner must support explicit operating modes:
   - `AUDIT`
   - `WARN`
   - `ENFORCE`
5. SchemaEvolutionAnalyzer is reframed as a **producer-side CI / pre-deploy gate**.
6. Reports and architecture explanations must reflect the new **trust-boundary tier model** and distinguish process failure from technical failure.

## 2. Outdated assumptions in the current project before this migration

### Old assumption 1: lineage was the main blast-radius source

This was the biggest mismatch.

Before the migration:

- `contracts/generator.py` only injected lineage context
- `contracts/attributor.py` built blast radius from contract lineage or direct lineage traversal
- the older reports described Week 4 lineage as the required dependency and the main downstream impact source

That is no longer correct under the updated docs.

### Old assumption 2: ValidationRunner only needed one operating style

Before the migration:

- `contracts/runner.py` had no `--mode`
- all validation output behaved like an audit pass that logged results but had no explicit block/allow semantics

The updated docs make mode behavior part of the architecture, not just a CLI nicety.

### Old assumption 3: registry was optional or implicit

Before the migration:

- there was no `contract_registry/subscriptions.yaml`
- contracts did not identify real registered subscribers
- blast radius had no authoritative subscription source

Under the updated docs, that is now a first-class gap.

### Old assumption 4: old reports could still stand as architecture explanations

The existing reports were useful historically, but several of them became outdated:

- `reports/phase_1.md` still framed lineage as the downstream context for contracts
- `reports/phase_2.md` described a runner with no mode semantics
- `reports/phase_3.md` treated lineage as the main blast-radius dependency
- `DOMAIN_NOTES.md` still emphasized lineage-first reasoning and older Phase 0 schema gaps

## 3. Existing reports reviewed and what changed

### `reports/phase_0.md`

What still holds:

- it correctly captured the original readiness issues
- it correctly identified schema migration pressure on Week 3, Week 4, and Week 5

What became outdated:

- it predates the new registry-first architecture
- it does not frame enforcement at the consumer boundary

### `reports/phase_1.md`

What still holds:

- it correctly describes fact-level flattening and profile-driven contract generation

What became outdated:

- it describes lineage injection as the main downstream context
- it does not mention registry subscribers
- it does not mention contract snapshots as part of generator output

### `reports/phase_2.md`

What still holds:

- structural and statistical validation design was already sound
- the injected confidence violation remained a strong test case

What became outdated:

- there was no validation mode model
- the report did not connect runner behavior to consumer-boundary enforcement

### `reports/phase_3.md`

What still holds:

- git-backed attribution logic was already useful
- the injected confidence violation remained a valid attribution test

What became outdated:

- blast radius was lineage-first
- registry subscribers were not represented at all
- the report treated Week 4 lineage as the required source rather than enrichment

### `DOMAIN_NOTES.md`

What still holds:

- it still captured real schema mismatch evidence and Week 3 confidence risk

What became outdated:

- it did not reflect the trust-boundary tier model
- it did not describe registry as the primary blast-radius source
- it did not explain validation modes or the producer-side CI role of schema evolution clearly enough

## 4. Implementation gaps found during re-audit

### Already matched or mostly matched

- profiling-based contract generation from real data
- dbt-compatible contract counterparts
- structural validation and statistical drift logic
- injected violation testing
- git-backed candidate attribution

### Partially matched

- generator already produced readable contracts, but they were lineage-centric
- runner already emitted structured reports, but without operational modes
- attributor already used git and lineage, but with the wrong blast-radius priority

### Missing or needing redesign

- contract registry did not exist
- generator did not inject registry context
- generator did not write contract snapshots for later schema evolution analysis
- runner did not expose `AUDIT`, `WARN`, `ENFORCE`
- violation entries did not include mode/action/blocking semantics
- attributor did not query registry first

## 5. Artifact gaps found

Missing before migration:

- `contract_registry/subscriptions.yaml`
- registry-aware contract metadata
- mode-aware validation reports
- registry-first blame-chain structure
- explicit update reports explaining the migration

Stale before migration:

- generated contracts still implied lineage-first blast radius
- validation reports had no mode semantics
- blame chain output had no registry section

## 6. Report and documentation gaps

The repo needed new documentation in addition to code changes:

- a gap analysis report
- a registry design update
- phase-specific update reports for Phases 1, 2, and 3
- a new architecture explanation written in plain English
- an artifact regeneration log
- a final migration summary

## 7. Migration plan used

I used the following migration plan:

1. Add a first-class contract registry with minimum required subscriptions plus the actual Week 7 consumers already present in this repo.
2. Update ContractGenerator to inject:
   - registry subscribers as the primary blast-radius source
   - lineage as enrichment only
   - contract snapshots for future schema evolution work
3. Update ValidationRunner to support:
   - `AUDIT`
   - `WARN`
   - `ENFORCE`
   and reflect those modes in reports and violation logs.
4. Update ViolationAttributor to split attribution into:
   - registry-first blast radius
   - lineage enrichment
   - git-backed likely cause
5. Regenerate contracts, snapshots, validation outputs, and blame-chain artifacts.
6. Rewrite architecture-facing documentation so the repo tells the updated story accurately.

## 8. Scope boundary for this migration

The updated docs also strengthen Phase 4 by reframing SchemaEvolutionAnalyzer as a producer-side CI gate. That is an important change, but it is intentionally **not implemented in this migration pass** because the user asked me to focus on updating the repository through Phase 3 only.

That means:

- Phase 4 is now documented as a future architectural requirement
- Phase 0 through Phase 3 are the only components brought fully into alignment in this pass
