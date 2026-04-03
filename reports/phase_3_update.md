# Phase 3 Update

## Scope of this update

This report documents the Phase 3 migration to the updated Week 7 attribution architecture.

Updated component:

- `contracts/attributor.py`

Regenerated artifact:

- `violation_log/blame_chain.json`

## 1. What changed from the old attribution design

### Previously

Attribution already did useful work:

- normalized failed validation results
- inferred the producer repository from real source paths
- ranked source files with git log and git blame
- used Week 4 lineage to infer blast radius

The problem was architectural, not functional:

- lineage was being treated as the primary blast-radius source

### Now

Attribution is split into three explicit layers:

1. **registry-first blast radius**
2. **lineage enrichment**
3. **git-backed likely cause**

That matches the updated docs much better.

## 2. How registry-first blast radius now works

The attributor now loads:

- `contract_registry/subscriptions.yaml`

For each failing field, it:

1. identifies the contract id from the generated contract
2. queries the registry for subscribers to that contract
3. prefers subscribers whose `fields_consumed` or `breaking_fields` explicitly match the failing field
4. falls back to contract-level subscribers if no field-level match exists

The registry output is now written as the `primary` blast-radius source in the blame-chain artifact.

For the injected Week 3 confidence failure, this now surfaces three subscribed consumers:

- `week4-brownfield-cartographer`
- `week7-contract-generator`
- `week7-validation-runner`

That is much stronger than the old lineage-only blast radius because it reflects explicit dependency declarations.

## 3. How lineage is now used

Lineage is still loaded and normalized from:

- `outputs/week4/lineage_snapshots.jsonl`

But it is now used as:

- `enrichment`
- transitive context
- internal propagation evidence when available

It is no longer the main answer to "who is affected?"

That is important in this repo because the current Week 4 lineage file is now canonical JSONL, but the available snapshots still do not model the Week 3 extraction system directly.

## 4. Test results on the injected violation

The attributor was rerun against:

- `validation_reports/injected_violation.json`

Results:

- `2` failures attributed
- top file: `src/agents/fact_table.py`
- registry subscribers identified: `3`

The top producer-side candidate remains:

- file: `src/agents/fact_table.py`
- commit: `033135cc46c7b8889cb8bf4f6607f940469bed5b`
- author: `Birkity`
- rationale: this file directly assigns and persists fact-level confidence values

That means the code-side cause story remained stable, while the blast-radius story improved.

## 5. What blast radius looks like now

The blame-chain output now clearly separates:

### Primary blast radius

From the registry:

- who subscribed
- what fields they consume
- what they marked as breaking
- what validation mode they expect

### Enrichment blast radius

From lineage:

- matched nodes
- upstream candidates
- downstream enrichment nodes
- lineage confidence and notes

This is the right separation for the updated docs.

## 6. Limitations and confidence level

### What is now strong

- producer-side file ranking
- git-backed blame evidence
- explicit subscribed-consumer blast radius

### What is still weak

- transitive lineage enrichment is still weak because the current Week 4 snapshots do not expose a direct Week 3 consumer path
- blast radius beyond registered consumers remains conservative
- some subscriber entries are Week 7 equivalents of the Week 6-style consumer boundary described in the docs, so they are documented assumptions rather than hidden facts

## 7. Result

Phase 3 is now aligned with the updated architecture:

- registry tells the system who is affected
- lineage only enriches the story
- git evidence still identifies likely cause

This is the most important conceptual fix in the migration because it changes attribution from graph-first reasoning to subscription-first reasoning.
