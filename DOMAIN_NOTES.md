# DOMAIN_NOTES

## Purpose

This document explains the domain assumptions and architectural reasoning that now drive the Week 7 implementation after the updated challenge document and Practitioner Manual.

It is no longer enough to describe schema fields and validation rules in isolation. The updated docs emphasize trust boundaries, ownership, blast radius, and operational behavior. These notes therefore focus on how this repository now thinks about those concepts using the real Week 1-5 artifacts already present here.

## Current repository reality

The current repo contains these main upstream inputs:

- `outputs/week1/intent_records.jsonl`
- `outputs/week2/verdicts.jsonl`
- `outputs/week3/extractions.jsonl`
- `outputs/week4/lineage_snapshots.jsonl`
- `outputs/week5/events.jsonl`
- `outputs/traces/runs.jsonl`

The most important interface for the implemented Phases 1-3 is still Week 3 because it combines:

- nested extraction structure
- a semantically important confidence field
- enough volume to support both profiling and drift detection

Week 5 is also now contract-ready and useful for multi-interface coverage, but Week 3 remains the clearest demonstration of why contracts matter in practice.

## Three trust boundary tiers

The updated docs describe three practical trust-boundary tiers. In this repo, they map like this.

### Tier 1: registry plus lineage

This is the ideal operating state:

- the registry tells us who subscribed to the contract
- lineage helps explain how impact propagates internally

The updated Week 3 contract now follows this model in structure, even though the lineage side is still weaker than the registry side.

### Tier 2: registry primary

This is the most realistic current state for the Week 3 confidence test in this repo.

Why:

- `contract_registry/subscriptions.yaml` now names explicit subscribers to `week3-extractions`
- the current Week 4 lineage file is still non-canonical and only partially useful for Week 3

So blast radius is now correctly grounded in the registry first.

### Tier 3: weak lineage-only visibility

This is what the older implementation leaned on too heavily. It is the least reliable state because it infers impact from graph structure without explicit subscription ownership.

The migration away from this tier is one of the main architectural corrections in the repo.

## Enforcement runs at the consumer boundary

The updated docs are explicit about this: enforcement is primarily a consumer-side decision.

In this repo that now means:

- ContractGenerator describes what consumers expect from Week 3 and Week 5 interfaces
- ValidationRunner enforces those expectations when a consumer reads a snapshot
- validation mode expresses how strict that consumer wants to be

This is more realistic than pretending producers can or should enforce every downstream rule at runtime.

## Validation mode strategy

The updated runner now supports three modes:

### AUDIT

- inspect and log
- never block

This is appropriate when a consumer wants visibility before adopting strict enforcement.

### WARN

- block only on `CRITICAL`
- warn on lower severities

This is appropriate when a consumer wants to stop clearly unsafe changes but tolerate softer drift while the contract matures.

### ENFORCE

- block on `CRITICAL`
- block on `HIGH`

This is appropriate when the consumer depends on the contract strongly enough that severe failures should stop the flow.

In the current Week 3 confidence violation:

- `AUDIT` logs the failure but allows the run
- `WARN` blocks because the range break is `CRITICAL`
- `ENFORCE` blocks because the range break is `CRITICAL` and the drift break is `HIGH`

## Registry is now the primary blast-radius source

This is the biggest conceptual update.

Before the migration, blast radius was inferred mainly from lineage. Now the first question is:

- who subscribed to this contract?

That is a better model because blast radius is fundamentally about downstream dependence, not just graph shape.

For the current Week 3 contract, the registry identifies these subscribers:

- `week4-brownfield-cartographer`
- `week7-contract-generator`
- `week7-validation-runner`

This is stronger than the previous lineage-only story because the current Week 4 file does not directly model the Week 3 extraction system.

## Lineage is enrichment, not ownership

Week 4 lineage still matters, but it now answers a different question:

- if impact exists, how might it propagate internally?

It does **not** answer the primary blast-radius question on its own anymore.

That distinction is especially important in this repo because the current Week 4 artifact is still a dbt-style whole-file graph with:

- `datasets`
- `edges`
- `transformations`

It is useful, but it is not a clean canonical Week 7 snapshot of the Week 3 extraction system.

## Process failure vs technical failure

The updated docs push a useful distinction:

- a technical failure is when a field is wrong, missing, or semantically broken
- a process failure is when the organization has no clear subscription, no owner, no validation mode, or no migration path

This repo now addresses both sides better than before.

### Technical failure example

The injected Week 3 confidence violation is a technical failure:

- `fact_confidence` was multiplied by `100`
- type checks still passed
- range and drift checks caught the semantic break

### Process failure example

The repo originally had no registry at all. That was not a bad data value problem. It was a dependency-governance problem. The migration fixes that by making subscribers explicit.

## Ownership and tradeoffs

The updated docs are strong on ownership thinking, and that maps well to this project.

### Producers own change safety

Producers should not silently introduce breaking changes. In the updated architecture, this is where schema evolution and CI gating belong, even though that phase is not implemented yet in this migration pass.

### Consumers own runtime trust decisions

Consumers choose:

- whether they are in `AUDIT`
- whether they are in `WARN`
- whether they are in `ENFORCE`

That is why validation mode is attached to consumer-facing behavior.

### Registry owns dependency visibility

The registry is now where cross-system impact becomes explicit:

- fields consumed
- fields considered breaking
- expected validation mode
- contact owner

## Schema evolution as a producer-side CI gate

The updated docs now frame SchemaEvolutionAnalyzer differently from ValidationRunner.

That distinction matters:

- ValidationRunner asks: "should this consumer trust the data it just received?"
- SchemaEvolutionAnalyzer asks: "should this producer-side change be allowed to deploy?"

This repository does not yet implement Phase 4 in code during this migration pass, but the generator now writes contract snapshots so that future producer-side schema comparison has real historical material to inspect.

## Why Week 3 confidence is still the right proving ground

The Week 3 confidence case remains the strongest demonstration of the system because it exposes the difference between structural correctness and semantic correctness.

Current real Week 3 facts:

- `50` extraction records
- `402` profiled rows after flattening
- `374` fact-level confidence values
- clean confidence range: `0.55` to `1.0`
- clean confidence mean: `0.8063636363636365`

That makes Week 3 ideal for showing:

- profile-driven contract generation
- range enforcement
- drift detection
- registry-based blast radius
- git-backed attribution

## Current limitation that still matters

The biggest remaining architectural weakness is still Week 4 lineage quality.

The system is much stronger now because the registry carries the primary blast-radius responsibility, but lineage enrichment will become far better once `outputs/week4/lineage_snapshots.jsonl` is migrated into the canonical Week 7 node/edge snapshot form.

## Final note

The most important change in these domain notes is not a new field or a new check. It is a change in system thinking:

- contracts are not just schemas
- blast radius is not just graph traversal
- enforcement is not just pass/fail

The updated Week 7 implementation now treats contracts as part of an operational trust model:

- producers publish
- consumers validate
- the registry declares who depends on what
- lineage explains propagation
- attribution helps teams act quickly when something breaks
