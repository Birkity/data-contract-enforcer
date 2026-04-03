# Phase 1 Update

## Scope of this update

This report documents the migration of Phase 1 to the updated Week 7 architecture.

Updated component:

- `contracts/generator.py`

Regenerated artifacts:

- `generated_contracts/week3_extractions.yaml`
- `generated_contracts/week3_extractions_dbt.yml`
- `generated_contracts/week5_events.yaml`
- `generated_contracts/week5_events_dbt.yml`
- `schema_snapshots/contracts/week3-extractions/latest.yaml`
- `schema_snapshots/contracts/week5-events/latest.yaml`
- timestamped contract snapshots under `schema_snapshots/contracts/`

## 1. What changed from the prior implementation

### Previously

The generator already:

- read real JSONL data
- flattened nested records
- profiled columns with pandas
- generated Bitol-style YAML
- exported dbt-compatible counterparts

But it still treated lineage as the main downstream context.

### Now

The generator still does all of the above, but it now also:

- loads `contract_registry/subscriptions.yaml`
- injects registry subscribers into the contract
- marks registry as the **primary blast-radius source**
- marks lineage as **enrichment only**
- writes contract snapshots for future schema evolution analysis

This is an architectural change, not just a formatting change.

## 2. How generator now incorporates registry and lineage

The new contract structure explicitly separates the two.

### Registry section

The generated contract now includes a `registry` block with:

- registry path
- subscriber count
- subscriber details
- validation modes
- breaking-field declarations
- notes explaining that registry is authoritative for blast radius

### Lineage section

The generated contract still includes lineage, but now as:

- `role: enrichment_only`
- `downstream_enrichment`
- lineage notes

That wording matters because it prevents the contract from implying that lineage alone defines blast radius.

### Implementation model section

The contract now also includes an `implementation_model` block that makes the new architecture explicit:

- `enforcement_boundary: consumer`
- `blast_radius_primary_source: contract_registry`
- `lineage_role: enrichment_only`
- `trust_boundary_tier: tier_1_registry_plus_lineage`

## 3. Contracts regenerated

### Week 3

Regenerated:

- `generated_contracts/week3_extractions.yaml`
- `generated_contracts/week3_extractions_dbt.yml`

Observed shape:

- `50` document records
- `173` profiled rows after exploding `extracted_facts[]`
- `136` fact-level confidence values

Important contract facts:

- `fact_confidence` still enforces `0.0` to `1.0`
- registry now lists three Week 3 subscribers
- snapshot paths are recorded in the contract observations block

### Week 5

Regenerated:

- `generated_contracts/week5_events.yaml`
- `generated_contracts/week5_events_dbt.yml`

Important contract facts:

- registry context is now included there too
- Week 5 no longer looks like an isolated secondary artifact
- the contract now reflects a consumer-facing event interface rather than just a profiled schema dump

## 4. Output structure differences

The biggest semantic differences are:

- new `implementation_model` block
- new `registry` block
- lineage renamed and reframed as enrichment
- snapshot metadata written into `observations.snapshot_paths`

The dbt outputs were also regenerated so their metadata now aligns with the registry-first model.

## 5. Contract snapshots

The updated docs say the generator should still write snapshots. I implemented that by writing:

- `schema_snapshots/contracts/<contract-id>/latest.yaml`
- timestamped copies per generation run

This snapshot discipline now feeds the implemented SchemaEvolutionAnalyzer.

## 6. Unresolved assumptions

- Week 4 lineage is now canonical JSONL, but the available snapshots still do not expose an explicit Week 3 consumer path, so lineage enrichment remains partial.
- The registry contains both doc-required interfaces and Week 7 equivalents that reflect the current repo structure.
- Phase 1 now writes the snapshot material that the implemented analyzer consumes.

## 7. Result

Phase 1 is now aligned with the updated architecture:

- contracts are still profile-driven and readable
- dbt counterparts still exist
- registry is now primary for blast radius
- lineage is present, but no longer overstated
