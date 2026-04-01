# Phase 1 Report

## Scope

This report covers **TRP Week 7 Phase 1 only**.

Implemented:

- `contracts/generator.py`
- `generated_contracts/week3_extractions.yaml`

Not implemented in this phase:

- ValidationRunner
- blame attribution
- schema evolution snapshots and diffing
- later AI-specific enforcement

## Goal

Build a working ContractGenerator that uses **real data** to infer a readable contract instead of hardcoding a schema by hand.

The primary input for this phase was:

- `outputs/week3/extractions.jsonl`

The required lineage input was:

- `outputs/week4/lineage_snapshots.jsonl`

## Implementation methodology

### 1. Load and inspect the live Week 3 data

The generator starts by loading the Week 3 JSONL file record by record.

It prints:

- the number of records loaded
- a sample record from the file

It also performs a light schema sanity check.

This is important because the current Week 3 file in this repo is **not** the canonical Week 7 extraction schema. Instead of failing immediately, the generator records warnings and continues with a profile-driven fallback path.

Observed live Week 3 keys:

- `document_id`
- `source_filename`
- `strategy_used`
- `confidence_score`
- `escalation_triggered`
- `escalation_reason`
- `estimated_cost`
- `processing_time_s`
- `flagged_for_review`

Missing canonical Week 7 extraction keys:

- `doc_id`
- `source_path`
- `source_hash`
- `extracted_facts`
- `entities`
- `extraction_model`
- `processing_time_ms`
- `token_count`
- `extracted_at`

### 2. Flatten data for profiling

The generator supports two shapes:

- canonical nested records with `extracted_facts[]`
- legacy flat records with only scalar fields

Flattening strategy:

- if `extracted_facts[]` exists, explode it and create one profiling row per fact
- preserve base document-level fields in every exploded row
- prefix nested fact fields with `fact_`
- flatten nested dictionaries into underscore-separated field names

For the current live data, `extracted_facts[]` does **not** exist.

So the generator used a deliberate fallback:

- one profiling row per source record
- base scalar fields preserved as-is
- warnings written into the generated contract so the limitation is visible

### 3. Profile each column with pandas

For every column, the generator computes:

- dtype
- null fraction
- cardinality estimate
- sample values
- numeric stats when applicable:
  - min
  - max
  - mean
  - stddev
  - p50
  - p95

The generator stores this profile in memory first, then uses it to build the YAML contract.

### 4. Translate profiles into contract clauses

The generator does not hardcode the live Week 3 schema.

Instead, it derives field clauses from the profile:

- non-null columns become `required: true`
- numeric confidence fields get:
  - `type: number`
  - `minimum: 0.0`
  - `maximum: 1.0`
  - a breaking-change description
- safe low-cardinality strings become enums
- string IDs get patterns when the observed values support them
- every field receives a human-readable description
- every field includes a compact `profile` block so the contract is understandable without reopening pandas output

One important real-data decision:

- `document_id` ends with `_id`, but the observed values are **not UUIDs**
- they match a 12-character hex pattern instead
- the generator therefore emits `pattern: ^[a-f0-9]{12}$` rather than a false `format: uuid`

That keeps the contract faithful to the real file instead of generating a misleading rule.

### 5. Inject lineage context from Week 4

The generator loads the latest lineage payload from:

- `outputs/week4/lineage_snapshots.jsonl`

It supports both:

- a proper JSONL snapshot file
- the current single-document JSON fallback that exists in this repo

Because the current lineage file is still a dbt-style graph with:

- `datasets`
- `transformations`
- `edges`

and no explicit Week 3 extraction nodes, the generator records:

- snapshot format
- dataset / transformation / edge counts
- an empty downstream consumer list
- explicit notes explaining why the lineage link is currently weak

This was intentional. I did not invent downstream consumers that do not exist in the source lineage file.

### 6. Write and quality-check the YAML

The generator writes:

- `generated_contracts/week3_extractions.yaml`

Then it reopens the file and verifies:

- the YAML parses correctly
- a schema section exists
- the confidence rule is present and uses the `0.0` to `1.0` range
- field descriptions are present
- a lineage section exists

## Generated contract outcome

The generator completed successfully on the live data and produced:

- `generated_contracts/week3_extractions.yaml`

The contract includes:

- 9 profiled schema fields
- a valid confidence range clause on `confidence_score`
- enums for safe categorical fields such as `strategy_used` and `estimated_cost`
- a lineage section grounded in the real Week 4 file
- warnings about the current legacy Week 3 shape

## Key profiling results

From the live Week 3 input used during generation:

- record count: `50`
- profiling row count: `50`
- flatten mode: `record_level_fallback`

Confidence:

- min: `0.0`
- max: `1.0`
- mean: `0.549294`
- p95: `1.0`

Processing time:

- min: `0.0071`
- max: `279.256`
- mean: `27.084928`

Categorical distributions:

- `strategy_used`: `layout_aware=25`, `ocr_heavy=15`, `vision_augmented=10`
- `estimated_cost`: `medium=25`, `high=25`
- `escalation_triggered`: `False=38`, `True=12`
- `flagged_for_review`: `False=31`, `True=19`

## Anomalies found

### Legacy Week 3 shape

The biggest anomaly is structural:

- the live file is not the canonical nested extraction schema
- there is no `extracted_facts[]`
- there is no `entities[]`

That means the generator could not produce a fact-level contract yet. It produced the strongest honest record-level contract possible from the actual data.

### Non-UUID document IDs

`document_id` looks like an ID field semantically, but the observed values are 12-character hexadecimal strings rather than UUIDs.

This matters because blindly forcing `format: uuid` would create a false contract.

### Duplicate document IDs

There are:

- 50 rows
- 40 unique `document_id` values

So the current live file contains repeated document IDs. Because of that, the generator correctly did **not** mark `document_id` as unique.

### Weak lineage coupling

The current Week 4 lineage file is useful as graph evidence, but it does not contain explicit Week 3 extraction consumers.

The generator therefore injected lineage carefully and transparently instead of inventing downstream nodes.

## Assumptions made

### Assumption 1

If `extracted_facts[]` exists in future inputs, it is the preferred repeated structure and should be exploded into one row per fact.

### Assumption 2

If the input remains in the current legacy shape, one record per row is the safest fallback for profiling and contract generation.

### Assumption 3

The current Week 4 lineage file should be treated as valid lineage context input even though it is not yet in canonical Week 7 snapshot format.

### Assumption 4

Phase 1 should remain deterministic. Your available local Ollama models were not used because this phase does not require LLM inference.

## Why this approach was chosen

The main design goal was honesty.

This generator does not pretend the current Week 3 data is already canonical. It profiles what is truly present, emits a useful contract immediately, and preserves the evidence needed for later migration work.

That gives you a working Phase 1 deliverable now without hiding the upstream schema gaps that still matter for later phases.
