# Phase 4 Report

## Scope

This report documents the implementation of the updated **SchemaEvolutionAnalyzer** for TRP Week 7.

Created component:

- `contracts/schema_analyzer.py`

Generated artifacts:

- `schema_snapshots/compatibility_report.json`
- `schema_snapshots/evolution_summary.json`

Test artifact:

- `schema_snapshots/simulated/week3-extractions/rename_confidence_field.yaml`

## 1. Role of SchemaEvolutionAnalyzer

The updated docs make a very important distinction:

- **ValidationRunner** is a consumer-side enforcement tool
- **SchemaEvolutionAnalyzer** is a producer-side CI / pre-deployment gate

That means this analyzer is not asking:

> “Should this consumer accept the data it just received?”

Instead, it is asking:

> “Can the producer safely release this schema change at all?”

That is why the output is a compatibility verdict and a deployment recommendation, not a runtime validation report.

## 2. Architecture alignment

The implementation now follows the updated architecture in three important ways.

### Producer-side gate

The analyzer compares schema snapshots before release and produces a CI-style verdict:

- `PASS`
- `WARN`
- `FAIL`

### Registry-first impact analysis

The analyzer uses:

- `contract_registry/subscriptions.yaml`

as the primary source of impact.

For each changed field, it checks:

- which consumers subscribed to the contract
- which consumers explicitly listed the field as breaking
- which validation modes those consumers use

### Lineage is optional enrichment only

I did not make lineage the primary source of impact here.

That is intentional and correct under the updated docs. The current Week 4 lineage file is canonical now, but it still does not expose a direct Week 3 consumer path, so treating lineage as secondary is both architecturally correct and practically safer.

## 3. Implementation details

### Snapshot loading

The analyzer loads:

- previous snapshot
- current snapshot

from `schema_snapshots/contracts/<contract-id>/`

In this repo, only one unique historical Week 3 snapshot existed:

- `schema_snapshots/contracts/week3-extractions/20260402T104355Z.yaml`

So the analyzer records that limitation explicitly.

### Diff logic

The diff engine detects:

- field added
- field removed
- field renamed
- type changed
- enum changed
- range changed
- nullability changed

Rename detection uses a simple similarity heuristic:

- field name similarity
- description similarity
- type match
- required/optional match
- a small bonus for confidence-related names

This keeps the logic explainable rather than black-box.

### Classification rules

Backward-compatible examples in the implementation:

- additive field introduction
- enum widening
- relaxed nullability
- relaxed range constraint

Breaking examples in the implementation:

- field removed
- field renamed
- type changed
- enum restriction
- nullability tightening
- range tightening
- confidence scale shift from `0.0-1.0` to something larger

### Decision rules

Overall CI gate behavior is:

- `FAIL`
  - breaking change with affected registered consumers
- `WARN`
  - breaking change but no affected registered consumers
- `PASS`
  - only backward-compatible changes

This matches the updated docs closely and stays easy to reason about.

## 4. Test case used

I simulated a breaking schema change on the Week 3 contract:

- renamed `fact_confidence` -> `fact_confidence_score`

Why this is a good test:

- it is clearly breaking for downstream consumers that expect the old field
- the registry already identifies `extracted_facts[].confidence` as a breaking field
- it tests both diff classification and registry impact logic

The analyzer wrote the simulated current snapshot to:

- `schema_snapshots/simulated/week3-extractions/rename_confidence_field.yaml`

## 5. Results

### Compatibility report

Output:

- `schema_snapshots/compatibility_report.json`

Observed result:

- decision: `FAIL`
- total changes: `1`
- change type: `field_renamed`
- classification: `breaking`
- impact level: `HIGH`
- `requires_registry_update: true`

### Evolution summary

Output:

- `schema_snapshots/evolution_summary.json`

Observed result:

- total changes: `1`
- breaking changes: `1`
- backward-compatible changes: `0`
- impacted systems:
  - `week4-brownfield-cartographer`
  - `week7-contract-generator`
  - `week7-validation-runner`
- CI gate blocking: `true`

## 6. Impacted consumers

The registry identified these affected consumers for the renamed confidence field:

- `week4-brownfield-cartographer`
- `week7-contract-generator`
- `week7-validation-runner`

This is exactly the kind of impact analysis the updated docs want: consumer-aware, registry-first, and suitable for blocking deployment before the bad schema ships.

## 7. Limitations

### Only one unique historical snapshot existed

The analyzer had to use the one current Week 3 snapshot as the "previous" version and create a simulated current version for the test.

That is acceptable for this phase, but it is still a real limitation.

### Registry assumptions remain documented

The registry is now real and used correctly, but some subscriber relationships are still Week 7 equivalents of the Week 6-style consumer model described in the docs.

That is documented rather than hidden.

### Lineage enrichment was intentionally not used as the primary impact source

This is not a bug. It is the correct updated architecture.

## 8. Key insight

This phase proves why producer-side schema analysis matters.

If the producer waits until consumer ingestion time to discover a breaking rename, the damage is already downstream. A CI gate changes that timing. It catches the problem before release, names the affected subscribers, and gives the team a concrete reason to block deploy until the registry, migration plan, or schema change is fixed.

That is the difference between reactive contract enforcement and preventive contract governance.
