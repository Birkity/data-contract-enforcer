# Phase 2 Update

## Scope of this update

This report documents the Phase 2 migration to the updated Week 7 operating model.

Updated component:

- `contracts/runner.py`

Regenerated artifacts:

- `validation_reports/thursday_baseline.json`
- `validation_reports/injected_violation_audit.json`
- `validation_reports/injected_violation_warn.json`
- `validation_reports/injected_violation.json`
- `violation_log/violations.jsonl`
- `schema_snapshots/baselines.json`

## 1. Old vs new behavior

### Previously

The runner already performed:

- structural checks
- statistical checks
- baseline drift logic
- structured report writing
- violation logging

But it had a single behavioral model. It validated and logged, but it did not explicitly express how a consumer boundary should react.

### Now

The runner still performs the same checks, but it now supports:

- `AUDIT`
- `WARN`
- `ENFORCE`

Each result now carries:

- `validation_mode`
- `action`
- `blocking`

The top-level report now includes:

- `validation_mode`
- `decision`
- `blocking`
- `architecture_context`
- `registry_subscribers`

## 2. New mode design

### AUDIT

- run all checks
- log all non-pass results
- never block

Use case:

- learning mode
- visibility-first monitoring
- early adoption where contracts are not yet allowed to stop traffic

### WARN

- block only on `CRITICAL`
- warn on lower severities

Use case:

- mixed-trust environments where hard breakage must stop, but softer drift should remain visible without causing downtime

### ENFORCE

- block on `CRITICAL`
- block on `HIGH`
- allow lower-severity issues through with warning/log semantics

Use case:

- mature consumer boundaries where contract integrity is part of release or runtime safety

## 3. Severity to action mapping

This implementation now uses the following practical mapping:

- `PASS` -> `ALLOW`
- `WARN` -> `WARN`
- `FAIL` / `ERROR` in `AUDIT` -> `WARN` or `LOG`, never block
- `CRITICAL` in `WARN` -> `BLOCK`
- `CRITICAL` or `HIGH` in `ENFORCE` -> `BLOCK`

This makes mode behavior understandable without overcomplicating the runner.

## 4. Example runs

### Clean baseline in AUDIT mode

Command used:

```powershell
.\.venv\Scripts\python.exe contracts/runner.py --contract generated_contracts/week3_extractions.yaml --data outputs/week3/extractions.jsonl --output validation_reports/thursday_baseline.json --registry contract_registry/subscriptions.yaml --mode AUDIT
```

Observed result:

- decision: `ALLOW_WITH_AUDIT_TRAIL`
- blocking: `false`
- total checks: `30`
- passed: `30`
- failed: `0`

### Injected violation in AUDIT mode

Command used:

```powershell
.\.venv\Scripts\python.exe contracts/runner.py --contract generated_contracts/week3_extractions.yaml --data outputs/week3/extractions_violated.jsonl --output validation_reports/injected_violation_audit.json --registry contract_registry/subscriptions.yaml --mode AUDIT
```

Observed result:

- decision: `ALLOW_WITH_AUDIT_TRAIL`
- blocking: `false`
- total checks: `37`
- failed: `2`

### Injected violation in WARN mode

Observed result:

- decision: `BLOCK`
- blocking: `true`
- the run blocks because the range failure is `CRITICAL`

### Injected violation in ENFORCE mode

Observed result:

- decision: `BLOCK`
- blocking: `true`
- the run blocks because the range failure is `CRITICAL` and the drift failure is `HIGH`

## 5. Whether the injected confidence violation is caught in each mode

Yes. It is caught in every mode.

### AUDIT

- caught
- logged
- not blocked

### WARN

- caught
- blocked because the range check is `CRITICAL`

### ENFORCE

- caught
- blocked because the range check is `CRITICAL` and the drift check is `HIGH`

## 6. What the injected violation still proves

The injected test remains strong under the new docs because it is still a semantic failure:

- the field remains numeric
- naive type checks still pass
- only contract-aware range and drift checks expose the problem

The two failing checks remain:

- `week3-extractions.fact_confidence.range`
- `week3-extractions.fact_confidence.drift`

## 7. Risks and edge cases

- `WARN` mode currently blocks on a single `CRITICAL` failure, which is faithful to the updated prompt but may be stricter than some teams expect operationally.
- Baseline creation still happens only when `schema_snapshots/baselines.json` is empty or reset.
- The violation log now contains richer mode/action semantics, but rerunning different modes on the same violated file will naturally add multiple entries for the same root problem.

## 8. Result

Phase 2 now matches the updated operational model:

- consumer-boundary enforcement is explicit
- report outputs show mode-aware decisions
- severity now has an operational consequence
- the confidence-scale breaking change is caught and interpreted differently depending on mode
