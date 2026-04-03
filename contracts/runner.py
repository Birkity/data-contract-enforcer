import argparse
import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from generator import flatten_for_profile, load_jsonl
from registry_tools import get_contract_subscriptions, load_registry


UUID_RE = re.compile(r"^[0-9a-f-]{36}$", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run ValidationRunner against a contract YAML and a JSONL snapshot."
    )
    parser.add_argument("--contract", required=True, help="Path to the contract YAML file.")
    parser.add_argument("--data", required=True, help="Path to the JSONL data snapshot.")
    parser.add_argument("--output", required=True, help="Path to the output validation report JSON.")
    parser.add_argument(
        "--mode",
        default="AUDIT",
        choices=["AUDIT", "WARN", "ENFORCE"],
        help="Consumer-boundary validation mode.",
    )
    parser.add_argument(
        "--registry",
        default="contract_registry/subscriptions.yaml",
        help="Path to the contract registry subscriptions file.",
    )
    parser.add_argument(
        "--baselines",
        default="schema_snapshots/baselines.json",
        help="Path to baseline statistics JSON.",
    )
    parser.add_argument(
        "--violation-log",
        default="violation_log/violations.jsonl",
        help="Path to the violation log JSONL file.",
    )
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_contract(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_records(path: Path) -> list[dict[str, Any]]:
    return load_jsonl(path)


def load_dataframe(path: Path) -> tuple[list[dict[str, Any]], pd.DataFrame, dict[str, Any]]:
    records = load_records(path)
    df, flatten_metadata = flatten_for_profile(records)
    return records, df, flatten_metadata


def load_baselines(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"written_at": None, "columns": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"written_at": None, "columns": {}}
    return {"written_at": payload.get("written_at"), "columns": payload.get("columns", {})}


def write_baselines(path: Path, df: pd.DataFrame) -> None:
    numeric_columns = {}
    for column in df.columns:
        series = df[column]
        if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
            clean = pd.to_numeric(series, errors="coerce").dropna()
            if clean.empty:
                continue
            numeric_columns[column] = {
                "mean": float(clean.mean()),
                "stddev": float(clean.std(ddof=1)) if len(clean) > 1 else 0.0,
            }

    payload = {"written_at": now_iso(), "columns": numeric_columns}
    ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_result(
    check_id: str,
    column_name: str,
    check_type: str,
    status: str,
    actual_value: str,
    expected: str,
    severity: str,
    records_failing: int,
    sample_failing: list[Any],
    message: str,
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "column_name": column_name,
        "check_type": check_type,
        "status": status,
        "actual_value": actual_value,
        "expected": expected,
        "severity": severity,
        "records_failing": records_failing,
        "sample_failing": [str(value) for value in sample_failing[:5]],
        "message": message,
    }


def blocking_for_mode(mode: str, status: str, severity: str) -> bool:
    normalized_mode = mode.upper()
    if status in {"PASS", "WARN"}:
        return False
    if normalized_mode == "AUDIT":
        return False
    if normalized_mode == "WARN":
        return severity == "CRITICAL"
    return severity in {"CRITICAL", "HIGH"}


def action_for_result(mode: str, status: str, severity: str) -> str:
    if status == "PASS":
        return "ALLOW"
    if blocking_for_mode(mode, status, severity):
        return "BLOCK"
    if status == "WARN" or severity in {"MEDIUM", "HIGH", "CRITICAL"}:
        return "WARN"
    return "LOG"


def missing_column_result(contract_id: str, column_name: str, check_type: str) -> dict[str, Any]:
    return build_result(
        check_id=f"{contract_id}.{column_name}.{check_type}",
        column_name=column_name,
        check_type=check_type,
        status="ERROR",
        actual_value="column missing",
        expected="column present",
        severity="CRITICAL",
        records_failing=0,
        sample_failing=[],
        message=f"Column {column_name} does not exist in the flattened data snapshot.",
    )


def is_expected_type(series: pd.Series, expected_type: str) -> bool:
    if expected_type == "number":
        return pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)
    if expected_type == "integer":
        return pd.api.types.is_integer_dtype(series) and not pd.api.types.is_bool_dtype(series)
    if expected_type == "boolean":
        return pd.api.types.is_bool_dtype(series)
    if expected_type == "string":
        return (
            pd.api.types.is_string_dtype(series)
            or series.dtype == "object"
            or pd.api.types.is_object_dtype(series)
        )
    return True


def parse_datetime(value: Any) -> bool:
    if value is None:
        return False
    text = str(value)
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def structural_checks(
    contract_id: str, df: pd.DataFrame, schema: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for column_name, clause in schema.items():
        if column_name not in df.columns:
            applicable = any(
                key in clause for key in ("required", "type", "enum", "format", "pattern")
            )
            if applicable:
                if clause.get("required"):
                    results.append(missing_column_result(contract_id, column_name, "required"))
                if clause.get("type"):
                    results.append(missing_column_result(contract_id, column_name, "type"))
                if clause.get("enum"):
                    results.append(missing_column_result(contract_id, column_name, "enum"))
                if clause.get("format"):
                    results.append(missing_column_result(contract_id, column_name, clause["format"]))
                if clause.get("pattern"):
                    results.append(missing_column_result(contract_id, column_name, "pattern"))
            continue

        series = df[column_name]

        if clause.get("required") is True:
            failing_mask = series.isna()
            failing_count = int(failing_mask.sum())
            status = "PASS" if failing_count == 0 else "FAIL"
            results.append(
                build_result(
                    check_id=f"{contract_id}.{column_name}.required",
                    column_name=column_name,
                    check_type="required",
                    status=status,
                    actual_value=f"missing={failing_count}",
                    expected="missing=0",
                    severity="LOW" if status == "PASS" else "CRITICAL",
                    records_failing=failing_count,
                    sample_failing=series[failing_mask].tolist(),
                    message=(
                        f"{column_name} is fully populated."
                        if status == "PASS"
                        else f"{column_name} has nulls but is required."
                    ),
                )
            )

        if clause.get("type"):
            matches = is_expected_type(series, clause["type"])
            results.append(
                build_result(
                    check_id=f"{contract_id}.{column_name}.type",
                    column_name=column_name,
                    check_type="type",
                    status="PASS" if matches else "FAIL",
                    actual_value=str(series.dtype),
                    expected=clause["type"],
                    severity="LOW" if matches else "CRITICAL",
                    records_failing=0 if matches else int(series.notna().sum()),
                    sample_failing=[] if matches else series.dropna().astype(str).head(5).tolist(),
                    message=(
                        f"{column_name} matches expected type {clause['type']}."
                        if matches
                        else f"{column_name} dtype {series.dtype} does not match expected {clause['type']}."
                    ),
                )
            )

        if clause.get("enum"):
            allowed = set(str(value) for value in clause["enum"])
            normalized = series.dropna().astype(str)
            failing_values = normalized[~normalized.isin(allowed)]
            failing_count = int(len(failing_values))
            status = "PASS" if failing_count == 0 else "FAIL"
            results.append(
                build_result(
                    check_id=f"{contract_id}.{column_name}.enum",
                    column_name=column_name,
                    check_type="enum",
                    status=status,
                    actual_value=f"nonconforming={failing_count}",
                    expected=f"subset_of={sorted(allowed)}",
                    severity="LOW" if status == "PASS" else "CRITICAL",
                    records_failing=failing_count,
                    sample_failing=failing_values.head(5).tolist(),
                    message=(
                        f"{column_name} only contains allowed enum values."
                        if status == "PASS"
                        else f"{column_name} contains values outside the allowed enum."
                    ),
                )
            )

        if clause.get("format") == "uuid":
            normalized = series.dropna().astype(str)
            failing_values = normalized[~normalized.str.match(UUID_RE)]
            failing_count = int(len(failing_values))
            status = "PASS" if failing_count == 0 else "FAIL"
            results.append(
                build_result(
                    check_id=f"{contract_id}.{column_name}.uuid",
                    column_name=column_name,
                    check_type="format",
                    status=status,
                    actual_value=f"invalid_uuid={failing_count}",
                    expected="^[0-9a-f-]{36}$",
                    severity="LOW" if status == "PASS" else "CRITICAL",
                    records_failing=failing_count,
                    sample_failing=failing_values.head(5).tolist(),
                    message=(
                        f"{column_name} matches the UUID format."
                        if status == "PASS"
                        else f"{column_name} contains values that do not match the UUID format."
                    ),
                )
            )

        if clause.get("format") == "date-time":
            normalized = series.dropna()
            failing_values = [value for value in normalized.tolist() if not parse_datetime(value)]
            failing_count = len(failing_values)
            status = "PASS" if failing_count == 0 else "FAIL"
            results.append(
                build_result(
                    check_id=f"{contract_id}.{column_name}.datetime",
                    column_name=column_name,
                    check_type="format",
                    status=status,
                    actual_value=f"unparseable={failing_count}",
                    expected="ISO-8601 date-time",
                    severity="LOW" if status == "PASS" else "CRITICAL",
                    records_failing=failing_count,
                    sample_failing=failing_values[:5],
                    message=(
                        f"{column_name} parses as ISO-8601 date-time."
                        if status == "PASS"
                        else f"{column_name} contains values that do not parse as ISO-8601 date-time."
                    ),
                )
            )

        if clause.get("pattern"):
            regex = re.compile(clause["pattern"])
            normalized = series.dropna().astype(str)
            failing_values = normalized[~normalized.str.match(regex)]
            failing_count = int(len(failing_values))
            status = "PASS" if failing_count == 0 else "FAIL"
            results.append(
                build_result(
                    check_id=f"{contract_id}.{column_name}.pattern",
                    column_name=column_name,
                    check_type="pattern",
                    status=status,
                    actual_value=f"pattern_failures={failing_count}",
                    expected=clause["pattern"],
                    severity="LOW" if status == "PASS" else "CRITICAL",
                    records_failing=failing_count,
                    sample_failing=failing_values.head(5).tolist(),
                    message=(
                        f"{column_name} matches the expected pattern."
                        if status == "PASS"
                        else f"{column_name} contains values that do not match the expected pattern."
                    ),
                )
            )

    return results


def statistical_checks(
    contract_id: str,
    df: pd.DataFrame,
    schema: dict[str, dict[str, Any]],
    baselines: dict[str, Any],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    baseline_columns = baselines.get("columns", {})

    for column_name, clause in schema.items():
        if column_name not in df.columns:
            if "minimum" in clause or "maximum" in clause:
                results.append(missing_column_result(contract_id, column_name, "range"))
            if column_name in baseline_columns:
                results.append(missing_column_result(contract_id, column_name, "drift"))
            continue

        series = df[column_name]
        numeric_series = pd.to_numeric(series, errors="coerce")
        has_numeric = numeric_series.notna().any()

        if ("minimum" in clause or "maximum" in clause) and not has_numeric:
            results.append(
                build_result(
                    check_id=f"{contract_id}.{column_name}.range",
                    column_name=column_name,
                    check_type="range",
                    status="ERROR",
                    actual_value="non-numeric column",
                    expected="numeric values for range check",
                    severity="CRITICAL",
                    records_failing=int(series.notna().sum()),
                    sample_failing=series.dropna().astype(str).head(5).tolist(),
                    message=f"{column_name} is not numeric, so the range check could not run.",
                )
            )
        elif "minimum" in clause or "maximum" in clause:
            clean = numeric_series.dropna()
            current_min = float(clean.min())
            current_max = float(clean.max())
            lower_bound = clause.get("minimum")
            upper_bound = clause.get("maximum")

            failing_mask = pd.Series(False, index=series.index)
            if lower_bound is not None:
                failing_mask = failing_mask | (numeric_series < float(lower_bound))
            if upper_bound is not None:
                failing_mask = failing_mask | (numeric_series > float(upper_bound))

            failing_values = series[failing_mask].tolist()
            failing_count = int(failing_mask.sum())
            status = "PASS" if failing_count == 0 else "FAIL"
            results.append(
                build_result(
                    check_id=f"{contract_id}.{column_name}.range",
                    column_name=column_name,
                    check_type="range",
                    status=status,
                    actual_value=f"min={current_min}, max={current_max}",
                    expected=f"min>={lower_bound}, max<={upper_bound}",
                    severity="LOW" if status == "PASS" else "CRITICAL",
                    records_failing=failing_count,
                    sample_failing=failing_values[:5],
                    message=(
                        f"{column_name} stays within the configured range."
                        if status == "PASS"
                        else f"{column_name} is outside the configured range. Breaking change detected."
                    ),
                )
            )

        if column_name not in baseline_columns:
            continue

        if not has_numeric:
            results.append(
                build_result(
                    check_id=f"{contract_id}.{column_name}.drift",
                    column_name=column_name,
                    check_type="drift",
                    status="ERROR",
                    actual_value="non-numeric column",
                    expected="numeric values for drift check",
                    severity="CRITICAL",
                    records_failing=int(series.notna().sum()),
                    sample_failing=series.dropna().astype(str).head(5).tolist(),
                    message=f"{column_name} is not numeric, so drift could not be measured.",
                )
            )
            continue

        clean = numeric_series.dropna()
        current_mean = float(clean.mean())
        baseline_mean = float(baseline_columns[column_name].get("mean", 0.0))
        baseline_stddev = float(baseline_columns[column_name].get("stddev", 0.0))
        z_score = abs(current_mean - baseline_mean) / max(baseline_stddev, 1e-9)

        if z_score > 3:
            status = "FAIL"
            severity = "HIGH"
            message = f"{column_name} mean drifted {z_score:.1f} stddev from baseline."
        elif z_score > 2:
            status = "WARN"
            severity = "MEDIUM"
            message = f"{column_name} mean within warning range ({z_score:.1f} stddev)."
        else:
            status = "PASS"
            severity = "LOW"
            message = f"{column_name} remains within the established baseline."

        results.append(
            build_result(
                check_id=f"{contract_id}.{column_name}.drift",
                column_name=column_name,
                check_type="drift",
                status=status,
                actual_value=f"mean={current_mean}, z_score={round(z_score, 2)}",
                expected=f"baseline_mean={baseline_mean}, baseline_stddev={baseline_stddev}",
                severity=severity,
                records_failing=0 if status == "PASS" else int(clean.shape[0]),
                sample_failing=[],
                message=message,
            )
        )

    return results


def decorate_results_for_mode(mode: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    decorated: list[dict[str, Any]] = []
    for result in results:
        enriched = dict(result)
        enriched["validation_mode"] = mode.upper()
        enriched["action"] = action_for_result(mode, result["status"], result["severity"])
        enriched["blocking"] = blocking_for_mode(mode, result["status"], result["severity"])
        decorated.append(enriched)
    return decorated


def attach_result_statistics(results: list[dict[str, Any]], total_rows: int) -> list[dict[str, Any]]:
    enriched_results: list[dict[str, Any]] = []
    denominator = max(total_rows, 1)
    for result in results:
        enriched = dict(result)
        failing_fraction = float(result.get("records_failing", 0)) / denominator
        enriched["records_total"] = total_rows
        enriched["failing_fraction"] = round(failing_fraction, 6)
        enriched["failing_percent"] = round(failing_fraction * 100.0, 2)
        enriched_results.append(enriched)
    return enriched_results


def append_violations(
    path: Path,
    report_id: str,
    contract_id: str,
    snapshot_id: str,
    run_timestamp: str,
    validation_mode: str,
    results: list[dict[str, Any]],
) -> None:
    ensure_parent(path)
    with path.open("a", encoding="utf-8") as handle:
        for result in results:
            if result["status"] == "PASS":
                continue
            violation_entry = {
                "report_id": report_id,
                "contract_id": contract_id,
                "snapshot_id": snapshot_id,
                "run_timestamp": run_timestamp,
                "validation_mode": validation_mode,
                "field": result["column_name"],
                "check_type": result["check_type"],
                "status": result["status"],
                "severity": result["severity"],
                "action": result.get("action"),
                "blocking": result.get("blocking", False),
                "message": result["message"],
                "sample_values": result["sample_failing"],
                "records_failing": result["records_failing"],
                "records_total": result.get("records_total"),
                "failing_percent": result.get("failing_percent"),
                "check_id": result["check_id"],
            }
            handle.write(json.dumps(violation_entry) + "\n")


def summarize_statuses(results: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "passed": sum(1 for result in results if result["status"] == "PASS"),
        "failed": sum(1 for result in results if result["status"] == "FAIL"),
        "warned": sum(1 for result in results if result["status"] == "WARN"),
        "errored": sum(1 for result in results if result["status"] == "ERROR"),
        "blocked": sum(1 for result in results if result.get("blocking")),
    }


def build_report(
    contract_id: str,
    data_path: Path,
    mode: str,
    registry_subscriptions: list[dict[str, Any]],
    row_count: int,
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    report_id = str(uuid.uuid4())
    snapshot_id = sha256_file(data_path)
    run_timestamp = now_iso()
    counts = summarize_statuses(results)
    blocking = any(result.get("blocking") for result in results)
    if mode.upper() == "AUDIT":
        decision = "ALLOW_WITH_AUDIT_TRAIL"
    elif blocking:
        decision = "BLOCK"
    elif counts["warned"] or counts["failed"] or counts["errored"]:
        decision = "ALLOW_WITH_WARNINGS"
    else:
        decision = "ALLOW"
    return {
        "report_id": report_id,
        "contract_id": contract_id,
        "snapshot_id": snapshot_id,
        "run_timestamp": run_timestamp,
        "validation_mode": mode.upper(),
        "blocking": blocking,
        "decision": decision,
        "profiled_row_count": row_count,
        "total_checks": len(results),
        "passed": counts["passed"],
        "failed": counts["failed"],
        "warned": counts["warned"],
        "errored": counts["errored"],
        "blocked": counts["blocked"],
        "architecture_context": {
            "enforcement_boundary": "consumer",
            "blast_radius_primary_source": "contract_registry",
            "lineage_role": "enrichment_only",
        },
        "registry_subscribers": registry_subscriptions,
        "results": results,
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")


def main() -> int:
    args = parse_args()
    contract_path = Path(args.contract)
    data_path = Path(args.data)
    output_path = Path(args.output)
    registry_path = Path(args.registry)
    baselines_path = Path(args.baselines)
    violation_log_path = Path(args.violation_log)

    contract = load_contract(contract_path)
    _, df, _ = load_dataframe(data_path)
    schema = contract.get("schema", {})
    contract_id = contract.get("id", contract_path.stem)
    registry_payload = load_registry(registry_path)
    registry_subscriptions = get_contract_subscriptions(registry_payload, contract_id)

    baselines = load_baselines(baselines_path)

    results: list[dict[str, Any]] = []
    try:
        results.extend(structural_checks(contract_id, df, schema))
        results.extend(statistical_checks(contract_id, df, schema, baselines))
    except Exception as exc:
        results.append(
            build_result(
                check_id=f"{contract_id}.runner.execution",
                column_name="__runner__",
                check_type="execution",
                status="ERROR",
                actual_value=type(exc).__name__,
                expected="runner completed without crashing",
                severity="CRITICAL",
                records_failing=0,
                sample_failing=[],
                message=f"ValidationRunner caught an unexpected error but stayed alive: {exc}",
            )
        )

    results = attach_result_statistics(results, int(len(df)))
    results = decorate_results_for_mode(args.mode, results)
    report = build_report(
        contract_id,
        data_path,
        args.mode,
        registry_subscriptions,
        int(len(df)),
        results,
    )
    write_report(output_path, report)
    append_violations(
        path=violation_log_path,
        report_id=report["report_id"],
        contract_id=report["contract_id"],
        snapshot_id=report["snapshot_id"],
        run_timestamp=report["run_timestamp"],
        validation_mode=report["validation_mode"],
        results=results,
    )

    if baselines.get("written_at") is None or not baselines.get("columns"):
        write_baselines(baselines_path, df)

    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "report_id",
                    "validation_mode",
                    "decision",
                    "blocking",
                    "total_checks",
                    "passed",
                    "failed",
                    "warned",
                    "errored",
                )
            },
            indent=2,
        )
    )
    return 2 if report["blocking"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
