# DOMAIN_NOTES

## Phase 0 Scope

This document covers **Phase 0 only** for TRP Week 7: Data Contract Enforcer. I read the Week 7 challenge document and the Practitioner Manual first, then inspected the real files currently present under `outputs/`:

- `outputs/week1/intent_records.jsonl`
- `outputs/week2/verdicts.jsonl`
- `outputs/week3/extractions.jsonl`
- `outputs/week4/lineage_snapshot.jsonl`
- `outputs/week5/events.jsonl`
- `outputs/traces/runs.jsonl`

The biggest theme in my own data is not "missing data" so much as **schema drift across systems**. Week 1 and Week 2 are structurally close to the canonical Week 7 schemas. Week 3, Week 4, and Week 5 are not. That matters because the Week 7 manual is explicit: if the real outputs differ from the canonical schemas, I should document the gap and write migration scripts before moving into implementation.

## Current Reality vs Canonical Week 7 Inputs

- `Week 1` is the strongest match. I have 16 intent records. The top-level keys match the canonical schema: `intent_id`, `description`, `code_refs`, `governance_tags`, and `created_at`. A representative record references `.orchestration/active_intents.yaml` and `src/hooks/types.ts`, with `confidence` values in the 0.91 to 0.98 range.
- `Week 2` is structurally close as well. I have 3 verdict records with the expected top-level keys: `verdict_id`, `target_ref`, `rubric_id`, `rubric_version`, `scores`, `overall_verdict`, `overall_score`, `confidence`, and `evaluated_at`. The sample record is a real self-audit against the Week 2 Automaton Auditor rubric.
- `Week 3` is not in canonical extraction shape. I only have 25 records, which is below the manual's `>= 50` threshold, and the schema is record-level summary output: `document_id`, `source_filename`, `strategy_used`, `confidence_score`, `escalation_triggered`, `escalation_reason`, `estimated_cost`, `processing_time_s`, and `flagged_for_review`. It does **not** contain `extracted_facts[]`, `entities[]`, or a record-level `doc_id/source_path/source_hash/extracted_at` structure.
- `Week 4` is also not in canonical shape. The challenge doc expects `outputs/week4/lineage_snapshots.jsonl`, but my real file is `outputs/week4/lineage_snapshot.jsonl`. It is also not JSONL. It is a single JSON document with top-level keys `datasets`, `edges`, and `transformations`. This is still useful lineage evidence, but it does not match the canonical Week 7 snapshot schema.
- `Week 5` clears the volume threshold easily with 1198 event records, but the schema is a lean event-stream format: `stream_id`, `event_type`, `event_version`, `payload`, and `recorded_at`. The canonical Week 7 event contract expects richer event-sourcing metadata such as `event_id`, `aggregate_id`, `aggregate_type`, `sequence_number`, `metadata`, `schema_version`, and `occurred_at`.
- `LangSmith traces` are present and strong on volume: 153 records. They have consistent token arithmetic, but they are not a perfect canonical fit either. My trace export includes `run_type` values such as `prompt` and `parser`, while the challenge schema limits `run_type` to `llm`, `chain`, `tool`, `retriever`, or `embedding`.

That context matters for every answer below. In my case, the central Phase 0 job is not only understanding contracts in theory. It is understanding where my own systems already drift away from the contract model that Week 7 wants to enforce.

## 1. Backward-Compatible vs Breaking Schema Changes

In plain English, a **backward-compatible** change is one that lets existing consumers keep working without code changes. A **breaking** change is a change that either removes something a consumer needs, renames it, changes its type or meaning, or otherwise makes the old assumptions unsafe.

The easiest way to think about it is this:

- backward-compatible change: "old readers can safely ignore this"
- breaking change: "old readers will misread this, crash, or silently do the wrong thing"

### Three backward-compatible examples from my systems

#### Example 1: Week 3 adding optional review metadata

My real Week 3 records already contain fields such as `escalation_triggered`, `escalation_reason`, and `flagged_for_review`. If I started from a smaller Week 3 schema and later added those as optional fields while preserving the original extraction fields, that would be backward-compatible. A consumer that only needs extraction content could ignore the review metadata and keep working.

#### Example 2: Week 5 adding extra payload detail without changing envelope fields

My Week 5 events already carry a `payload` object whose contents vary by `event_type`. Adding a new optional key inside `payload` for one event type, while preserving the event envelope, would usually be backward-compatible. For example, if `ApplicationSubmitted` later added an optional `broker_id`, older consumers that do not care about brokers could ignore it.

#### Example 3: LangSmith traces adding optional tags or child-run metadata

My trace export includes keys such as `tags`, `child_run_ids`, and `child_runs`. Adding more optional trace metadata of that kind is typically backward-compatible as long as the core fields such as `id`, `run_type`, `start_time`, `end_time`, `inputs`, and `outputs` still exist in the expected shape.

### Three breaking-change examples from my systems

#### Example 1: Week 3 changing confidence semantics

The challenge's own example is exactly right for my domain: changing extraction confidence from normalized float `0.0-1.0` to integer `0-100` is a breaking change. The column still "looks numeric," so it is especially dangerous because downstream logic may keep running while producing wrong results.

#### Example 2: Week 4 using a different lineage schema than the Week 7 contract expects

My real Week 4 lineage file uses `datasets`, `edges`, and `transformations`, while the canonical Week 7 input expects records with `snapshot_id`, `codebase_root`, `git_commit`, `nodes`, `edges`, and `captured_at`. That is not a harmless variation. A consumer written for the canonical snapshot format will not know how to interpret the current Week 4 structure without migration logic.

#### Example 3: Week 5 using `stream_id` instead of an event-sourcing aggregate contract

My real Week 5 events use `stream_id` and `event_version`, but the canonical Week 7 schema expects `aggregate_id`, `aggregate_type`, `sequence_number`, and `metadata`. That is breaking because the downstream contract logic cannot validate monotonic sequence numbers or aggregate-level ordering when those fields do not exist.

## 2. Week 3 Confidence Scale Failure

In the canonical Week 7 extraction schema, `extracted_facts[].confidence` is a float between `0.0` and `1.0`. That range matters because the downstream consumer is not just checking that the field is numeric. It is assuming a normalized probability-like scale.

If that field changes from `0.87` to `87`, the failure is subtle but severe:

1. the field still looks valid to a naive parser because it is still numeric
2. any threshold logic such as "only keep facts above 0.80" becomes meaningless
3. any mean, drift, or anomaly calculation becomes inflated by roughly two orders of magnitude
4. any downstream system that stores confidence as metadata will now propagate the wrong semantics

### How it propagates downstream into Week 4

The challenge doc frames Week 4 as a cartographer lineage system where Week 3 facts can become graph metadata. In that world, a broken Week 3 confidence scale would propagate into Week 4 in two ways:

- facts that should be "high confidence" on a normalized scale become absurdly high numeric values
- any ranking, filtering, or weighting logic that relies on confidence will over-trust those records

In my current repo there is an additional complication: my real Week 4 file is not yet the canonical Week 4 graph that consumes Week 3 extraction records. It is a dataset/transformation lineage document from a dbt-style environment. So the exact Week 3 to Week 4 propagation path is **not directly represented in the current artifacts**. That gap itself is important evidence for Phase 0: I cannot truthfully say the current Week 4 file already encodes the Week 3 extraction lineage the challenge assumes.

### Contract clause that should catch the failure

```yaml
apiVersion: bitol.io/v1
kind: DataContract
metadata:
  id: week3-extractions-confidence
  name: week3 extraction confidence guardrail
spec:
  dataProduct: outputs/week3/extractions.jsonl
  schema:
    type: object
    fields:
      - name: extracted_facts[].confidence
        type: float
        required: true
  quality:
    rules:
      - name: extracted_facts_confidence_range
        type: range
        field: extracted_facts[].confidence
        min: 0.0
        max: 1.0
        severity: critical
        description: Confidence must remain a normalized float in the 0.0-1.0 range.
```

### Real measurement on my current Week 3 data

The Practitioner Manual asks me to compute:

```text
min, max, mean of extracted_facts[].confidence
```

I could not do that directly because my real Week 3 output does not currently contain `extracted_facts[]`. The canonical confidence field is missing entirely.

Observed result from the canonical path:

```text
extracted_facts[].confidence values found: 0
```

I did, however, measure the real record-level field that exists in my current Week 3 data, `confidence_score`, across 25 records:

```text
min=0.150 max=1.000 mean=0.664
```

This tells me two things:

1. my current Week 3 data does not already show the `0-100` scale failure
2. my current Week 3 output is still **not** in the schema the Week 7 contract system expects, so I need migration before the canonical contract can even run against the intended `extracted_facts[].confidence` path

## 3. How Blame Attribution Works

The basic idea of blame attribution is simple: once a contract fails, do not stop at "bad data happened." Walk the lineage graph backward until I can identify the transformation, file, and commit most likely to have introduced the break.

### How the traversal works in plain English

1. ValidationRunner identifies a failed clause on a specific dataset and field.
2. ViolationAttributor maps that failure to a node in the lineage graph.
3. It walks upstream through producer relationships until it reaches the transformations or source datasets that feed the broken field.
4. For each candidate transformation, it looks for the source file that created or modified the bad data.
5. It then queries git history for that file and ranks likely candidate commits.
6. Finally, it produces a blame chain with the upstream path, the likely commit, the author, and the downstream blast radius.

### What matters in my actual Week 4 lineage file

My current Week 4 file is not in the canonical `nodes[]` form. Instead, it has:

- `datasets`
- `edges`
- `transformations`

That means the real traversal in my repo would use those structures:

- `datasets` tell me which data entities exist
- `edges` tell me how they connect
- `transformations` tell me which SQL or code artifact performed the change

One real edge in my file is:

- `source.ecom.raw_customers -> sql:models/staging/stg_customers.sql` with `edge_type: CONSUMES`

One real transformation record is:

- `sql:models/marts/customers.sql`
- `source_file: models/marts/customers.sql`
- `source_datasets: ['model.stg_customers', 'model.orders']`
- `target_datasets: ['model.customers']`

So the blame process in my actual graph would look like this:

1. flag the violated downstream dataset or transformation output
2. inspect inbound edges to find the immediate producer
3. follow `source_datasets` recursively until the graph reaches the earliest relevant producer
4. use `source_file` and `line_range` from the responsible transformation as the git lookup target
5. run git history on that file to find the commits that most recently touched the transformation

### What nodes and edges matter

The important graph elements are not every node in the system. The important ones are:

- the failing dataset node
- the direct upstream transformation node
- the inbound producer edges
- the source datasets feeding that transformation
- the transformation's `source_file`

### How git history would be used

Once the traversal identifies a likely transformation file such as `models/marts/customers.sql`, the attributor would query git for:

- recent commits touching that file
- author and timestamp
- commit message
- exact diff on the relevant lines

The best candidate is the commit nearest to the violated transformation and closest in time to the appearance of the bad schema or bad values.

### What the final blame chain output should look like

```json
{
  "violation_id": "week3-confidence-range-failure",
  "failed_field": "extracted_facts[].confidence",
  "failing_dataset": "week3-extractions",
  "lineage_path": [
    "week3-extractions",
    "week4-lineage-node",
    "transformation:models/marts/customers.sql"
  ],
  "candidate_commits": [
    {
      "file": "models/marts/customers.sql",
      "commit": "abc123...",
      "author": "Engineer Name",
      "timestamp": "2026-03-30T10:12:00Z",
      "confidence": 0.91
    }
  ],
  "blast_radius": [
    "generated contract for week3 extractions",
    "validation reports",
    "downstream models depending on the broken field"
  ]
}
```

One more important Phase 0 observation: my current Week 4 file does not include the canonical top-level `git_commit` field. That means exact snapshot pinning is weaker than the challenge expects, and that should be documented before implementation starts.

## 4. LangSmith Trace Contract

My trace export has 153 records. It is strong enough to analyze, but it already shows why trace contracts matter:

- token arithmetic is clean: `prompt_tokens + completion_tokens = total_tokens` for all 153 records
- run types are **not** fully canonical: I have `prompt` and `parser` in addition to `llm`, `chain`, and `tool`
- `total_cost` is null in all 153 records

That means a good trace contract must check structure, behavior, and AI-specific expectations, not just field existence.

```yaml
apiVersion: bitol.io/v1
kind: DataContract
metadata:
  id: langsmith-trace-record
  name: langsmith trace record contract
spec:
  dataProduct: outputs/traces/runs.jsonl
  schema:
    type: object
    fields:
      - name: id
        type: string
        required: true
      - name: run_type
        type: string
        required: true
      - name: start_time
        type: datetime
        required: true
      - name: end_time
        type: datetime
        required: true
      - name: inputs
        type: object
        required: true
      - name: outputs
        type: object
        required: false
  quality:
    rules:
      - name: trace_run_type_enum
        type: accepted_values
        field: run_type
        values: [llm, chain, tool, retriever, embedding]
        severity: major
        description: Run type must use the canonical Week 7 enum.
      - name: trace_end_after_start
        type: expression
        field: end_time
        expression: end_time > start_time
        severity: critical
        description: Trace end_time must be later than start_time.
      - name: trace_token_arithmetic
        type: expression
        field: total_tokens
        expression: total_tokens = prompt_tokens + completion_tokens
        severity: major
        description: Token accounting must reconcile exactly.
      - name: llm_runs_have_payload
        type: conditional_required
        when: run_type = llm
        required_fields: [inputs, outputs]
        severity: major
        description: LLM runs must capture the prompt input and the model output unless an error is present.
```

On my current data, that contract would be useful immediately:

- the token arithmetic clause should pass
- the run type enum clause would currently fail for the `prompt` and `parser` records
- a cost-based clause would need care because `total_cost` is entirely missing in my export

## 5. Why Contract Systems Fail in Production

The most common failure mode is not "the contract was never written." It is that the contract was written once, approved, and then quietly became stale while the system kept evolving.

That failure mode is visible in my own repo right now:

- Week 3 output drifted into a record-summary schema that no longer matches the canonical extraction contract
- Week 4 lineage exists, but in a different structure and file name than the Week 7 architecture expects
- Week 5 events are rich and numerous, but they do not expose the canonical event-sourcing envelope that Week 7 wants to validate

This is exactly how contract systems fail in real teams. Nobody wakes up intending to break the contract. The system changes locally, the consumers keep assuming the old shape, and the mismatch becomes normal until a downstream failure finally exposes it.

Contracts become stale for three reasons:

1. they are written by hand and never regenerated from live data
2. they are disconnected from lineage, so nobody knows who owns the break
3. they only check structure, while the real failure is semantic or statistical

The Week 7 architecture is good because it addresses all three:

- `ContractGenerator` generates contracts from live outputs rather than relying only on memory
- `ValidationRunner` turns assumptions into executable checks
- `ViolationAttributor` connects failures to lineage and git history, which makes ownership actionable
- `SchemaEvolutionAnalyzer` treats change as a first-class problem instead of pretending schemas are static
- `AI Contract Extensions` cover the parts standard data contracts miss, especially traces, prompt inputs, and structured outputs

In other words, this architecture does not prevent drift by wishing it away. It prevents drift by making contracts observable, testable, attributable, and refreshable.

My practical conclusion for this project is simple: before I start Phase 1, I should not pretend that my real outputs already fit the canonical schemas. The honest and technically correct path is:

1. document the schema gaps
2. create migration logic for Week 3, Week 4, and Week 5
3. preserve the original raw outputs as evidence
4. generate contracts from the migrated canonical views rather than from the mismatched raw shapes

That is the cleanest way to keep the rest of Week 7 grounded in my real systems instead of in an idealized version of them.
