# Phase 1 Report

## Scope

This report covers **TRP Week 7 Phase 1 only**:

- `contracts/generator.py`
- `generated_contracts/week3_extractions.yaml`

This phase does **not** implement:

- validation
- violation injection
- attribution
- schema evolution analysis
- AI-assisted enforcement

## What I used

I rebuilt Phase 1 against the current real inputs:

- `outputs/week3/extractions.jsonl`
- `outputs/week4/lineage_snapshots.jsonl`

The Week 3 file is now in canonical Week 7-style shape with:

- `doc_id`
- `source_path`
- `source_hash`
- `extracted_facts`
- `entities`
- `extraction_model`
- `processing_time_ms`
- `token_count`
- `extracted_at`

The Week 4 lineage file has since been migrated to canonical JSONL, but at the time of the original Phase 1 run lineage enrichment was still limited. The generator now records the current limitation honestly: the snapshots are canonical, but they still do not expose an explicit Week 3 consumer path.

## What I implemented

I recreated:

- `contracts/generator.py`

The generator does the following:

1. Loads the Week 3 JSONL file
2. Prints the record count and one sample record
3. Flattens nested structures for profiling
4. Explodes `extracted_facts[]` so profiling happens at fact level
5. Preserves document-level fields like `doc_id`, `source_path`, and token counts on every flattened row
6. Profiles each observed column with pandas
7. Converts the profiles into a readable Bitol-style YAML contract
8. Loads the Week 4 lineage file and injects downstream lineage context or honest lineage notes
9. Runs a quality check before finishing

## Flattening methodology

The most important design choice in this phase is flattening.

Why:

- the contract needs to reason about fact-level confidence
- confidence lives inside `extracted_facts[]`
- a record-level profile would hide the distribution and null behavior of real fact rows

How:

- the generator identifies `extracted_facts` as the repeated field
- one output row is created per extracted fact
- base document fields are copied onto each flattened fact row
- nested dictionaries are flattened with prefixes such as:
  - `token_count_input`
  - `token_count_output`
  - `fact_fact_id`
  - `fact_confidence`
  - `fact_page_ref`
  - `fact_source_excerpt`
- list fields become count fields, and scalar lists are also joined into a pipe-delimited string when useful

Result:

- `50` source extraction records
- `402` profiled rows after flattening

## Profiling methodology

For each column, the generator computes:

- logical dtype
- null fraction
- cardinality estimate
- sample values
- numeric distribution statistics when the field is numeric

Numeric fields include:

- `entities_count`
- `processing_time_ms`
- `token_count_input`
- `token_count_output`
- `fact_entity_refs_count`
- `fact_confidence`
- `fact_page_ref`

The generator stores:

- `observed_min`
- `observed_max`
- `observed_mean`
- `observed_stddev`
- `observed_p50`
- `observed_p95`

## Contract generation logic

The YAML clause generation is profile-driven rather than hardcoded to one static schema file.

Rules implemented:

- `null_fraction == 0.0` becomes `required: true`
- numeric columns become `type: integer` or `type: number`
- `_id` fields become `format: uuid` only when the observed values really match UUID format
- `_at` fields become `format: date-time` only when the values parse cleanly
- `source_hash` becomes a 64-hex regex pattern when the observed values support it
- fields containing `confidence` get:
  - `minimum: 0.0`
  - `maximum: 1.0`
  - a description that explicitly calls the range out as meaningful
- low-cardinality string enums are only emitted when the coverage is small and safe

This kept the contract readable and honest to the real data instead of forcing brittle schema claims.

## Generated contract summary

The generator wrote:

- `generated_contracts/week3_extractions.yaml`

Key contract observations:

- contract id: `week3-extractions`
- record count: `50`
- profiled row count: `402`
- repeated field: `extracted_facts`
- no structural warnings were needed for the Week 3 input

Important generated clauses include:

- `doc_id`
  - required
  - UUID-formatted
- `source_hash`
  - required
  - constrained by SHA-256 regex
- `extracted_at`
  - required
  - date-time formatted
- `fact_confidence`
  - numeric
  - constrained to `0.0` through `1.0`
- `processing_time_ms`
  - required integer with observed runtime statistics

## Real profiling results

From the current Week 3 file:

- extraction records: `50`
- fact rows with confidence: `374`
- fact confidence min: `0.55`
- fact confidence max: `1.0`
- fact confidence mean: `0.8063636363636363`

Other useful observations:

- `doc_id` is valid UUID format
- `source_hash` values match SHA-256 shape
- `processing_time_ms` ranges from `7` to `279256`
- some extraction rows contain no facts, so a small share of flattened rows have null fact-level fields

## Lineage injection

The generator loads:

- `outputs/week4/lineage_snapshots.jsonl`

What happened:

- the file successfully loaded as `whole-file-json`
- it exposes a dbt-style structure with `datasets` and `edges`
- it does not expose a direct canonical Week 3 downstream mapping

So the contract records:

- `downstream: []`
- a note explaining that the current lineage source is not yet the canonical Week 7 snapshot shape
- a note explaining that downstream blast radius is currently unknown from this file alone

This is intentional. I did not invent downstream consumers that are not present in the real lineage file.

## Quality check

After generation, I reopened the YAML and checked that:

- a schema block exists
- every field has a description
- confidence clauses enforce `0.0` to `1.0`
- lineage context exists

The generator completed successfully and printed:

- `Contract quality check passed.`

## Assumptions

- the current canonical Week 3 file is the source of truth for Phase 1
- fact-level profiling is more useful than record-level profiling for this dataset
- the current Week 4 lineage file is authoritative even though it is not yet in canonical Week 7 shape
- local Ollama models are not required for this deterministic generation step

## Limitations

- lineage injection is limited by the current Week 4 file shape
- the generator profiles only what is present in the real data, so sparse fields are described conservatively
- some document-level fields are repeated across flattened fact rows by design

## Why this implementation is a good fit

This rebuild keeps Phase 1 aligned with the real project state:

- it uses the migrated canonical Week 3 data
- it profiles confidence where confidence actually lives
- it produces a readable contract instead of a raw statistical dump
- it carries forward lineage context without pretending the current Week 4 graph is richer than it is
