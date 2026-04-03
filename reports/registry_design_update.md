# Registry Design Update

## Why the registry is now primary

The updated Week 7 architecture changes the meaning of blast radius.

Under the older implementation, blast radius was inferred mainly from lineage. That was useful, but it made downstream impact depend too heavily on how complete the lineage graph happened to be.

The updated docs correct that by making the Contract Registry primary:

- if a consumer subscribed to a contract, that subscription is explicit evidence of dependency
- if a subscriber declared a field as breaking, that is explicit evidence of impact
- lineage still matters, but it is secondary and enrichment-oriented

This is a better operational model because blast radius becomes a process artifact, not just a graph traversal artifact.

## What was added

I created:

- `contract_registry/subscriptions.yaml`

This registry now serves as the first stop for downstream impact reasoning in the Week 7 implementation.

## How subscriptions were defined

I used two principles:

1. include the minimum doc-required interfaces
2. include the real Week 7 consumers already present in this repo

### Minimum interfaces included

- `week3-extractions -> week4-brownfield-cartographer`
- `week4-lineage-snapshots -> week7-violation-attributor`
- `week5-events -> week7-event-contract-consumer`
- `langsmith-trace-record -> week7-trace-contract-consumer`

### Real Week 7 consumers added

Because this repository already consumes Week 3 directly, I also registered:

- `week3-extractions -> week7-contract-generator`
- `week3-extractions -> week7-validation-runner`

That makes the registry reflect both the updated architecture and the actual implementation.

## Registry schema used

Each subscription includes:

- `contract_id`
- `subscriber_id`
- `fields_consumed`
- `breaking_fields`
- `validation_mode`
- `registered_at`
- `contact`

This matches the updated docs closely while staying readable and machine-usable.

## Why registry differs from lineage

The two artifacts answer different questions.

### Registry answers:

- who subscribed to this contract?
- which fields do they rely on?
- which fields do they consider breaking?
- what validation mode do they expect at their boundary?

### Lineage answers:

- once impact exists, how might it propagate internally?
- which upstream or downstream graph nodes are connected?
- what transformation paths make the dependency visible?

So in the updated model:

- registry tells me **who is affected**
- lineage helps explain **how the effect may propagate**

## How this affects attribution

Before this update, attribution could only say:

- there is a failing field
- there is a likely producer file
- lineage suggests some possible neighbors

After this update, attribution can now separate three distinct ideas:

1. **subscriber blast radius**
   - pulled from `contract_registry/subscriptions.yaml`
2. **lineage enrichment**
   - pulled from Week 4 lineage
3. **likely cause**
   - pulled from git and source code evidence

That separation is more honest and easier to defend.

## How this affects blast radius in practice

For the injected Week 3 confidence violation, registry-first blast radius now identifies three subscribers:

- `week4-brownfield-cartographer`
- `week7-contract-generator`
- `week7-validation-runner`

This is stronger than the older lineage-only result because the current Week 4 lineage file does not explicitly model the Week 3 extraction system. The registry therefore recovers real downstream visibility even when lineage is incomplete.

## Assumptions recorded explicitly

There is still some uncertainty in the registry:

- the updated docs describe some interfaces in Week 6 terms, while this repo is a Week 7 implementation
- the current Week 4 lineage artifact is canonical JSONL, but the available snapshots still do not expose a direct Week 3 consumer path, so the subscriber for that interface is modeled conservatively
- LangSmith is present as trace data but not yet used as a core Phase 1-3 enforcement target

Instead of hiding those gaps, the registry notes and the later update reports make the assumptions explicit.

## Outcome

The registry is now the authoritative blast-radius source for the updated Phase 1-3 implementation.

That means:

- contracts can name real subscribers
- validation reports can show who the contract matters to
- attribution can start from subscribed consumers before consulting lineage

This is the biggest architectural improvement in the migration.
