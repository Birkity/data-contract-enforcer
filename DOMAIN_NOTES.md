# DOMAIN_NOTES

## Purpose

This document explains the domain assumptions and architectural reasoning that drive the current Week 7 implementation after the updated challenge document, the updated Practitioner Manual, and the latest Week 3 and Week 4 output migrations.

The updated docs changed the center of gravity of the project. The most important shift is that contracts are no longer just schema descriptions. They are now part of an operational trust model:

- producers publish promises
- consumers decide how strictly to enforce them
- the registry names who is affected
- lineage explains how impact might propagate internally
- schema evolution protects consumers before a producer deploys a breaking change

## Current repository reality

The current repo contains these main upstream inputs:

- `outputs/week1/intent_records.jsonl`
- `outputs/week2/verdicts.jsonl`
- `outputs/week3/extractions.jsonl`
- `outputs/week4/lineage_snapshots.jsonl`
- `outputs/week5/events.jsonl`
- `outputs/traces/runs.jsonl`

The implemented system now covers:

- ContractGenerator
- ValidationRunner
- ViolationAttributor
- SchemaEvolutionAnalyzer
- AI Contract Extensions
- final Enforcer Report generation

Week 3 remains the clearest proving ground because it combines:

- nested extraction structure
- a semantically important confidence field
- enough volume for profiling, drift detection, and a real injected breaking-change test

Week 5 is also contract-ready and strengthens multi-interface coverage, but Week 3 still shows the architectural ideas most clearly.

## Three trust boundary tiers

The updated docs describe three practical trust-boundary tiers. In this repo, they map like this.

### Tier 1: registry plus lineage

This is the strongest model:

- the registry tells us who subscribed to a contract
- lineage helps explain how impact propagates inside systems we can see

This repo now partly reaches Tier 1 because:

- `contract_registry/subscriptions.yaml` exists and is used as the primary blast-radius source
- `outputs/week4/lineage_snapshots.jsonl` is now canonical JSONL with `nodes` and `edges`

But lineage enrichment is still weaker than registry reasoning for the Week 3 confidence case because the current Week 4 snapshots do not expose an explicit Week 3 consumer path.

### Tier 2: registry primary

This is the most realistic current operating mode for the Week 3 confidence violation in this repo.

Why:

- the registry explicitly names subscribers to `week3-extractions`
- the current Week 4 lineage snapshots are structurally correct, but they still do not model the Week 3 extraction interface directly

So the primary blast-radius answer is now correctly grounded in the registry first.

### Tier 3: weak lineage-only visibility

This is what the older implementation leaned on too heavily. It is the least reliable model because it tries to infer downstream impact from visible graph structure alone.

One of the main architectural corrections in this repo was moving away from that lineage-only mindset.

## Enforcement runs at the consumer boundary

The updated docs are explicit about this: enforcement is primarily a consumer-side decision.

In this repo that now means:

- ContractGenerator describes what consumers depend on at the interface boundary
- ValidationRunner enforces those expectations when a consumer reads a snapshot
- validation mode expresses how strict that consumer wants to be

That is more realistic than pretending producers can enforce every downstream runtime rule themselves.

## Validation mode strategy

The runner now supports three modes.

### AUDIT

- inspect and log
- never block

This is appropriate when a consumer wants visibility before adopting strict enforcement.

### WARN

- block on `CRITICAL`
- tolerate lower severities with warnings

This is appropriate when a consumer wants to stop clearly unsafe changes while still observing softer drift during contract adoption.

### ENFORCE

- block on `CRITICAL`
- block on `HIGH`

This is appropriate when the consumer depends on the contract strongly enough that severe failures should stop the flow.

For the current Week 3 confidence violation:

- `AUDIT` logs the failure and allows the run
- `WARN` blocks because the range break is `CRITICAL`
- `ENFORCE` blocks because the range break is `CRITICAL` and the drift break is `HIGH`

## Registry is now the primary blast-radius source

This is the biggest conceptual update in the repo.

Before the architecture migration, blast radius was inferred mainly from lineage. Now the first question is:

- who subscribed to this contract?

That is the right primary question because blast radius is fundamentally about downstream dependence, not just graph shape.

For the current Week 3 contract, the registry identifies these direct subscribers:

- `week4-brownfield-cartographer`
- `week7-contract-generator`
- `week7-validation-runner`

That is stronger than the previous lineage-only story because the current Week 4 snapshots still do not directly model the Week 3 extraction system.

## Lineage is enrichment, not ownership

Week 4 lineage still matters, but it now answers a different question:

- if impact exists, how might it propagate internally?

It does **not** answer the primary blast-radius question by itself anymore.

The current Week 4 file is now structurally correct for Week 7:

- valid JSONL
- one snapshot per line
- canonical top-level fields:
  - `snapshot_id`
  - `codebase_root`
  - `git_commit`
  - `nodes`
  - `edges`
  - `captured_at`

Current real Week 4 snapshot facts:

- `4` snapshots
- Week 7 consumer snapshot: `38` nodes, `19` edges
- Week 3 repo snapshot: `80` nodes, `47` edges
- jaffle-shop snapshot: `38` nodes, `30` edges
- Week 4 self-snapshot: `13` nodes, `7` edges

So the Week 4 problem is no longer format correctness or missing commit metadata. The remaining issue is coverage and relevance: the snapshots do not yet expose an explicit Week 3 extraction consumer path, and the current Week 7 consumer snapshot is still dominated by dynamic file-I/O observations rather than a clean contract-level dependency edge.

## Process failure vs technical failure

The updated docs push a useful distinction:

- a technical failure is when a field is wrong, missing, or semantically broken
- a process failure is when the organization has no clear subscriber, no owner, no validation mode, or no migration path

This repo now addresses both sides better than before.

### Technical failure example

The injected Week 3 confidence violation is a technical failure:

- `fact_confidence` was multiplied by `100`
- type checks still passed
- range and drift checks caught the semantic break

### Process failure example

The repo originally had no registry. That was not a bad data value problem. It was a dependency-governance problem. The migration fixed that by making subscribers, breaking fields, and validation modes explicit.

## Ownership and tradeoffs

The updated docs are strong on ownership thinking, and that maps well to this project.

### Producers own change safety

Producers should not silently introduce breaking changes. In the updated architecture, this is where SchemaEvolutionAnalyzer belongs.

In this repo that now means:

- contract snapshots are written on each generator run
- `contracts/schema_analyzer.py` compares snapshots
- a breaking producer-side change can now block deployment before consumers see it

### Consumers own runtime trust decisions

Consumers choose:

- whether they are in `AUDIT`
- whether they are in `WARN`
- whether they are in `ENFORCE`

That is why validation mode is attached to consumer-facing behavior rather than producer runtime behavior.

### Registry owns dependency visibility

The registry is where cross-system impact becomes explicit:

- fields consumed
- fields considered breaking
- expected validation mode
- contact owner

## Schema evolution as a producer-side CI gate

The updated docs frame SchemaEvolutionAnalyzer differently from ValidationRunner, and that distinction now exists in code as well.

That distinction matters:

- ValidationRunner asks: "should this consumer trust the data it just received?"
- SchemaEvolutionAnalyzer asks: "should this producer-side change be allowed to deploy?"

This repository now implements that producer-side gate in code:

- timestamped snapshots are written under `schema_snapshots/contracts/`
- `contracts/schema_analyzer.py` can diff snapshots
- a simulated rename of the confidence field is classified as breaking
- the current compatibility verdict is `FAIL`
- the analyzer emits producer next actions, not just a raw diff

## Why Week 3 confidence is still the right proving ground

The Week 3 confidence case remains the strongest demonstration of the system because it exposes the difference between structural correctness and semantic correctness.

Current real Week 3 facts:

- `50` extraction records
- `173` profiled rows after flattening
- `13` rows with extracted facts
- `29` rows with entities
- `136` fact-level confidence values
- clean confidence range: `0.55` to `0.9`
- clean confidence mean: `0.818015`

That makes Week 3 ideal for showing:

- profile-driven contract generation
- range enforcement
- drift detection
- registry-based blast radius
- git-backed attribution
- producer-side compatibility blocking

## Current limitations that still matter

The biggest remaining architectural weakness is still Week 4 lineage relevance, not Week 4 format.

The system is much stronger now because:

- the registry carries the primary blast-radius responsibility
- Week 4 lineage is now canonical JSONL

But lineage enrichment will become far better once the Week 4 graph includes an explicit Week 3 consumer path and complete source-repo metadata for every snapshot.

Another real limitation is trace quality:

- the Week 7 repo now keeps a cleaned contract-source trace file at `outputs/traces/runs.jsonl`
- the original raw export is preserved at `outputs/traces/runs_raw.jsonl`
- the consumer-boundary contract file at `outputs/traces/runs_contract_boundary.jsonl` now validates cleanly

The AI-side embedding metric is now in a stronger state as well:

- the metric uses real local Ollama embeddings when available
- the current result is `PASS`
- the persisted baseline now reflects the current Week 3 extraction slice

## Final note

The most important change in these notes is not a new field or a new check. It is a change in system thinking:

- contracts are not just schemas
- blast radius is not just graph traversal
- enforcement is not just pass/fail

The current Week 7 implementation now treats contracts as part of an operational trust model:

- producers publish
- consumers validate
- the registry declares who depends on what
- lineage explains propagation
- schema evolution blocks unsafe producer changes before release
- attribution helps teams act quickly when something breaks
