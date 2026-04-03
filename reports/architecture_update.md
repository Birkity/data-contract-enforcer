# Architecture Update

## Plain-English architecture

The updated Week 7 architecture can be explained in one sentence:

**producers publish data, consumers enforce contracts at their own boundary, the registry tells us who depends on what, lineage helps explain propagation, and attribution helps us find likely causes when a contract fails**

That is a more operationally realistic design than treating lineage alone as the whole system.

## Producer

A producer is the system that emits a dataset or event stream.

Examples in this repo:

- Week 3 produces `outputs/week3/extractions.jsonl`
- Week 5 produces `outputs/week5/events.jsonl`
- LangSmith produces `outputs/traces/runs.jsonl`

The producer's job is not to enforce every downstream contract at runtime. Its job is to publish data and avoid introducing breaking changes without coordination.

## Consumer

A consumer is the system that reads a contract-governed interface and decides whether the data is acceptable for its own purpose.

Examples in this repo:

- Week 4 consumes Week 3 extraction outputs
- Week 7 ContractGenerator consumes Week 3 and Week 5 outputs
- Week 7 ValidationRunner consumes generated contracts plus the live data snapshots
- Week 7 ViolationAttributor consumes validation failures, registry information, lineage enrichment, and git history

This is why the updated docs say enforcement lives at the consumer boundary.

## Contract

A contract describes what a consumer expects from an interface.

In this repo, the generated contracts now express:

- structural expectations
- semantic rules like confidence ranges
- registry subscribers
- lineage enrichment notes
- trust-boundary information

The contract is therefore not just a schema file. It is a machine-readable agreement about what downstream systems are relying on.

## Registry

The Contract Registry is now the primary source of blast radius.

This matters because blast radius is fundamentally about dependency ownership:

- who subscribed to the contract?
- which fields do they rely on?
- what do they consider breaking?
- how strictly do they validate?

Lineage can suggest propagation, but a subscription explicitly states business dependency. That is why the registry is primary in the updated design.

## Validation

Validation is where the contract becomes operational.

The updated runner now supports three modes:

- `AUDIT`
- `WARN`
- `ENFORCE`

These modes turn the same technical checks into different operational decisions. That is important because the same contract can be used in:

- visibility mode
- cautious rollout mode
- strict blocking mode

So validation is not only about pass/fail. It is about how a consumer wants to react.

## Attribution

Attribution begins after validation fails.

The updated Phase 3 flow is:

1. read the failed validation result
2. look up subscribed consumers in the registry
3. consult lineage for enrichment only
4. inspect producer-side source code and git history
5. rank likely files and commits

This is stronger than the older lineage-first design because it distinguishes:

- downstream dependency
- transitive propagation
- likely code-level cause

## Schema evolution

The updated docs also clarify the role of schema evolution:

- ValidationRunner is consumer-side runtime or batch enforcement
- SchemaEvolutionAnalyzer is producer-side CI or pre-deploy protection

That distinction is useful because it separates:

- "should this producer change be allowed to ship?"
from
- "should this consumer trust the data it just received?"

In this migration pass, that Phase 4 producer-side role is documented but not implemented yet by user scope.

## Blast radius

Blast radius now has two layers.

### Primary layer

Registry subscribers:

- explicit
- declared
- operationally meaningful

### Secondary layer

Lineage enrichment:

- useful for internal graph context
- useful for transitive propagation
- less authoritative when incomplete

This is the core design correction applied in the codebase.

## Three trust boundary tiers

The updated docs describe a tiered trust-boundary model. In practice, this repo now reflects it like this:

### Tier 1: registry plus lineage

Used where both are available.

This is now the intended operating model for Week 3 contracts in this repo, even though the lineage portion is still partial.

### Tier 2: registry primary

Used when the consumer has an explicit subscription but lineage is weak or incomplete.

This is the practical reality of the current Week 3 confidence failure case.

### Tier 3: lineage-only fallback or weak visibility

This is the least desirable state because it relies on inferred relationships rather than explicit subscriptions.

The old implementation leaned too far in this direction. The migration corrects that.

## Business and user perspective

From a business perspective, the updated architecture improves three things:

1. **clearer responsibility**
   - consumers choose how strict they want to be
2. **clearer impact**
   - blast radius names actual subscribed dependents
3. **clearer triage**
   - failures can be traced from contract to consumer impact to likely producer-side cause

That is why the architecture is more useful now, even though the code changes themselves are fairly focused.

## Current limitation

The biggest remaining limitation is still Week 4 lineage quality.

The updated system is already much better because the registry carries the primary blast-radius load, but the repo will become stronger still once the Week 4 lineage snapshot is migrated into the canonical node/edge form described by the updated docs.
