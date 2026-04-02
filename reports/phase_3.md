# Phase 3 Report

## Plain-English summary

The ViolationAttributor is the part of Week 7 that turns a failed contract check into an explainable blame chain.

The challenge and manual require it to:

- read a real validation failure
- use the Week 4 lineage graph as a required dependency
- trace the failure back to the most likely upstream producer side
- use git history to identify plausible causing commits, files, and authors
- describe downstream blast radius where possible

In this repo, the injected confidence-scale violation from Phase 2 is a good test because it is a real structured failure with a clear producer system: the Week 3 Document Intelligence Refinery.

The important constraint is that the current Week 4 lineage file is now canonical Week 7 JSONL, but the available snapshots still do not expose an explicit Week 3 consumer path. That means attribution is still useful, but some lineage-based enrichment results remain partial and must be reported honestly.

## 1. Requirements from the docs

From the Week 7 challenge document and the Practitioner Manual, the ViolationAttributor is expected to do four things:

- read a real `FAIL` result from Phase 2
- use the Week 4 lineage graph as a required dependency
- identify likely upstream producer files and commits using git history and blame
- describe blast radius so the failure can be communicated as downstream risk, not just a broken check

The challenge document is explicit that attribution starts from the failing schema element, traverses lineage upstream with breadth-first search, then runs git history and targeted line blame on the files it finds.

The expected blame-chain output must contain:

- the failing check
- a ranked blame chain
- file path
- commit hash
- author
- timestamp
- commit message
- confidence score
- blast radius

Why Week 4 lineage is essential:

- without lineage, a failure is only a local data-quality event
- with lineage, the same failure becomes an explainable system event: what produced it, and what else depends on it
- the manual also says blast radius should come from contract lineage context when available

Inputs I used in this phase:

- `validation_reports/injected_violation.json`
- `validation_reports/thursday_baseline.json` as reference context only
- `violation_log/violations.jsonl`
- `outputs/week4/lineage_snapshots.jsonl`
- `generated_contracts/week3_extractions.yaml`
- local git history from `E:\10 Academy\Week 3\document-intelligence-refinery`

The current violation log contains `4` entries total, and `2` of them match each of the two injected failure check ids because Phase 2 was rerun without cleanup.

## 2. Architecture and logic used

I created:

- `contracts/attributor.py`
- `violation_log/blame_chain.json`

The attributor logic is intentionally simple and explainable.

### Failure normalization

The script loads the validation report and keeps only results with `status == "FAIL"`.

It also loads `violation_log/violations.jsonl` and records how many existing log entries already match each failing `check_id`.

Each normalized failure includes:

- `check_id`
- `field`
- `dataset_system`
- `dataset_path`
- `check_type`
- `severity`
- `message`
- `records_failing`
- `detected_at`

For this repo, both failures map cleanly back to:

- `week3-document-intelligence-refinery`

because the contract id and failing fields clearly belong to the Week 3 extraction output.

### Producer-system mapping

The attributor does not guess the producer repo from thin air.

Instead, it:

1. loads the contract YAML
2. reads the contract's local dataset path
3. opens the Week 3 extraction rows
4. inspects the real `source_path` values
5. walks upward from those paths until it finds a `.git` directory

That resolved to one real upstream repo root:

- `E:\10 Academy\Week 3\document-intelligence-refinery`

### Lineage traversal

The attributor loads the Week 4 lineage snapshot and normalizes it into a node/edge structure.

It supports:

- canonical Week 7 `nodes[]` and `edges[]`
- the earlier repo shape with `datasets`, `transformations`, and `edges`, which was later migrated into canonical Week 7 snapshots

Traversal logic:

1. try to seed lineage nodes using system tokens like `week3`, `document`, `refinery`, and `extraction`
2. if seed nodes are found, run breadth-first traversal upstream and downstream
3. if no nodes match, keep the result partial and report that honestly

In this repo, the current Week 4 snapshots are canonical but still unrelated to the Week 3 extraction system, so no explicit Week 3 nodes were found.

That means lineage was still used, but it produced:

- `matched_nodes: []`
- `upstream_candidates: []`
- low-confidence blast radius

### Git history integration

For the producer repo, the attributor scans code and config files for confidence-related matches and ranks candidate files.

The scoring is explainable:

- path relevance first
- field/message token hits second
- line-level blame evidence next
- recent git activity as supporting context

For each candidate file it runs:

- `git log --follow --since="14 days ago" --format=... -- <file>`
- targeted `git blame --porcelain` on line ranges that match the failing field

This is important because the recent commit list alone would bias too heavily toward unrelated late changes, while line-level blame points at the logic that actually defines confidence behavior.

### Ranking and confidence

The final ranking uses:

- file relevance score
- whether the file had line-level blame matches
- whether it had recent commits
- a small direct bonus for obvious producer files like `src/agents/fact_table.py`

This produced a ranked blame chain instead of a single brittle guess.

## 3. Test case used

I used the injected Phase 2 violation from:

- `validation_reports/injected_violation.json`

This is a strong test because:

- it is a real structured `FAIL` report, not a fabricated example
- the failing field is clear: `fact_confidence`
- the violation type is meaningful: confidence changed from `0.0-1.0` to `0-100`
- the producer side is expected to be Week 3, so the attribution should be easy to sanity-check

The two failing checks were:

- `week3-extractions.fact_confidence.range`
- `week3-extractions.fact_confidence.drift`

## 4. Results

The attributor ran successfully and wrote:

- `violation_log/blame_chain.json`

It attributed both failing checks to the Week 3 producer side.

### Top blame-chain result

Top candidate for both failures:

- file: `src/agents/fact_table.py`
- repo: `E:\10 Academy\Week 3\document-intelligence-refinery`
- commit: `033135cc46c7b8889cb8bf4f6607f940469bed5b`
- author: `Birkity <birkity.yishak.m@gmail.com>`
- timestamp: `2026-03-07T15:06:52+00:00`
- message: `feat: Add centralized configuration and OCR extraction strategy`
- confidence score: `0.942`

Why this ranked first:

- it directly assigns and persists fact-level confidence values
- it contains the `_confidence_for_method` logic
- line-level blame on the relevant confidence block pointed at this commit

### Other strong candidates

Second candidate:

- `src/models/schemas.py`
- same commit
- confidence score: `0.719`

Reason:

- this file defines the fact schema and explicitly constrains confidence to `0.0-1.0`

Third candidate:

- `src/strategies/vision.py`
- same commit
- confidence score: `0.718`

Reason:

- this file sets concrete confidence values for one extraction strategy

### Blast radius summary

The current Week 4 lineage file did not expose a real downstream consumer for the Week 3 extraction dataset.

So the computed blast radius is:

- `affected_nodes: []`
- `affected_pipelines: []`
- lineage confidence: `low`

Plain-English interpretation:

- the known producer side is clear
- the known downstream impact from the current Week 4 graph is not
- practical risk still exists for any unseen consumer of `outputs/week3/extractions.jsonl`, including downstream monitoring or agent systems that rely on fact confidence

This is partial attribution, not fake precision, which is the right tradeoff here.

## 5. Limitations and uncertainty

The biggest limitation is not git. It is lineage quality.

### Limitation 1: Week 4 lineage is not modeling Week 3

The current Week 4 snapshots are canonical but represent different systems. They do not contain explicit Week 3 extraction nodes.

Impact:

- upstream producer mapping had to rely on contract metadata and real source paths
- blast radius could not be grounded in explicit downstream nodes

### Limitation 2: the top commit is plausible, not proven causal

The attributor identifies the most plausible commit touching the confidence-producing logic. It does not prove that the injected violation literally came from that commit, because in this demo the violation was injected in the Week 7 repo for testing.

Impact:

- this is a defensible blame candidate, not courtroom-level proof

### Limitation 3: no line numbers are currently written into the blame-chain output

I used targeted line blame internally, but the output currently records the file and commit rather than a fully materialized `line_start/line_end` span.

Impact:

- attribution is strong enough for this phase
- it can still be improved in a later polish pass

### Limitation 4: downstream blast radius is conservative

Because lineage matching failed, the blast radius is intentionally narrow and low-confidence.

That is the correct behavior for this repo state, but it means this phase will look stronger after Week 4 lineage migration.

## 6. Key insight

This phase proves that Week 7 can do more than say "a check failed."

It can now say:

- which producer system the violation belongs to
- which files most likely define the failing behavior
- which commit most plausibly last changed that behavior
- how certain the system is
- where the blast-radius analysis is strong, and where the lineage input is too weak

That is the real value of the ViolationAttributor: turning a contract failure into a triage path a human can act on.
