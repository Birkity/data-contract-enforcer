import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
HEX12_RE = re.compile(r"^[0-9a-f]{12}$", re.IGNORECASE)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Bitol-style contract YAML from real JSONL data."
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Path to the primary JSONL source file, for example outputs/week3/extractions.jsonl",
    )
    parser.add_argument(
        "--lineage",
        default="outputs/week4/lineage_snapshots.jsonl",
        help="Path to the Week 4 lineage snapshot file.",
    )
    parser.add_argument(
        "--output",
        default="generated_contracts",
        help="Output directory for the generated YAML contract.",
    )
    parser.add_argument(
        "--contract-id",
        default=None,
        help="Optional output contract slug. Defaults to '<parent>_<stem>'.",
    )
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def load_week3_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Source file not found: {path}")
    records = load_jsonl(path)
    if not records:
        raise ValueError(f"No records found in {path}")
    return records


def load_latest_lineage_snapshot(path: Path) -> tuple[dict[str, Any], str]:
    if not path.exists():
        raise FileNotFoundError(f"Lineage file not found: {path}")

    text = path.read_text(encoding="utf-8")
    non_empty_lines = [line for line in text.splitlines() if line.strip()]

    if non_empty_lines:
        try:
            last_record = json.loads(non_empty_lines[-1])
            if isinstance(last_record, dict):
                return last_record, "jsonl-last-line"
        except json.JSONDecodeError:
            pass

    payload = json.loads(text)
    if isinstance(payload, dict):
        return payload, "whole-file-json"
    if isinstance(payload, list) and payload and isinstance(payload[-1], dict):
        return payload[-1], "json-array-last-item"
    raise ValueError(f"Unsupported lineage file shape in {path}")


def make_contract_slug(source_path: Path, explicit_slug: str | None) -> str:
    if explicit_slug:
        return explicit_slug.strip()
    return f"{source_path.parent.name}_{source_path.stem}"


def preview_record(record: dict[str, Any]) -> str:
    return json.dumps(record, indent=2, ensure_ascii=True)


def inspect_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    first = records[0]
    warnings: list[str] = []
    observed_keys = list(first.keys())

    if not any("extracted_facts" in record for record in records):
        warnings.append(
            "The current Week 3 file does not contain extracted_facts[]. "
            "Profiling will fall back to one row per record instead of one row per fact."
        )

    canonical_markers = {"doc_id", "source_path", "source_hash", "extracted_facts", "entities"}
    missing_markers = sorted(marker for marker in canonical_markers if marker not in observed_keys)
    if missing_markers:
        warnings.append(
            "The current source uses a legacy summary schema and is missing canonical fields: "
            + ", ".join(missing_markers)
        )

    print(f"Loaded {len(records)} records.")
    print("Sample record:")
    print(preview_record(first))
    if warnings:
        print("Inspection warnings:")
        for warning in warnings:
            print(f"- {warning}")

    return {
        "record_count": len(records),
        "sample_record": first,
        "observed_keys": observed_keys,
        "warnings": warnings,
    }


def flatten_scalar_value(target: dict[str, Any], key: str, value: Any) -> None:
    if isinstance(value, dict):
        for nested_key, nested_value in value.items():
            flatten_scalar_value(target, f"{key}_{nested_key}", nested_value)
        return

    if isinstance(value, list):
        if not value:
            target[f"{key}_count"] = 0
            return
        if all(not isinstance(item, (dict, list)) for item in value):
            target[f"{key}_count"] = len(value)
            target[key] = "|".join(str(item) for item in value)
            return
        target[f"{key}_count"] = len(value)
        return

    target[key] = value


def choose_repeated_array_field(records: list[dict[str, Any]]) -> str | None:
    if any(isinstance(record.get("extracted_facts"), list) for record in records):
        return "extracted_facts"

    list_of_dict_candidates: dict[str, int] = {}
    for record in records:
        for key, value in record.items():
            if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
                list_of_dict_candidates[key] = list_of_dict_candidates.get(key, 0) + len(value)

    if not list_of_dict_candidates:
        return None

    return max(list_of_dict_candidates.items(), key=lambda item: item[1])[0]


def flatten_for_profile(records: list[dict[str, Any]]) -> tuple[pd.DataFrame, dict[str, Any]]:
    repeated_field = choose_repeated_array_field(records)
    rows: list[dict[str, Any]] = []

    for record in records:
        base: dict[str, Any] = {}
        for key, value in record.items():
            if key == repeated_field:
                continue
            flatten_scalar_value(base, key, value)

        if repeated_field:
            repeated_items = record.get(repeated_field) or [None]
            for item in repeated_items:
                row = dict(base)
                if isinstance(item, dict):
                    for nested_key, nested_value in item.items():
                        flatten_scalar_value(row, f"fact_{nested_key}", nested_value)
                elif item is not None:
                    row[f"fact_{repeated_field.rstrip('s')}"] = item
                rows.append(row)
        else:
            rows.append(base)

    df = pd.DataFrame(rows)
    metadata = {
        "flatten_mode": "exploded_repeated_items" if repeated_field else "record_level_fallback",
        "repeated_field": repeated_field,
        "profiled_row_count": len(df),
    }
    return df, metadata


def is_boolean_dtype(dtype_str: str) -> bool:
    return dtype_str == "bool"


def is_integer_dtype(dtype_str: str) -> bool:
    return dtype_str.startswith("int") or dtype_str.startswith("Int")


def is_numeric_dtype(series: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)


def sample_values(series: pd.Series, limit: int = 5) -> list[str]:
    seen: set[str] = set()
    samples: list[str] = []
    for value in series.dropna():
        rendered = str(value)
        if rendered in seen:
            continue
        seen.add(rendered)
        samples.append(rendered)
        if len(samples) >= limit:
            break
    return samples


def full_unique_values(series: pd.Series, limit: int = 10) -> list[str] | None:
    values = [str(value) for value in pd.Series(series.dropna().unique()).tolist()]
    if not values or len(values) > limit:
        return None
    return values


def numeric_stats(series: pd.Series) -> dict[str, float]:
    clean = pd.to_numeric(series.dropna(), errors="coerce").dropna()
    if clean.empty:
        return {}
    return {
        "min": float(clean.min()),
        "max": float(clean.max()),
        "mean": float(clean.mean()),
        "stddev": float(clean.std(ddof=1)) if len(clean) > 1 else 0.0,
        "p50": float(clean.quantile(0.50)),
        "p95": float(clean.quantile(0.95)),
    }


def values_match(series: pd.Series, pattern: re.Pattern[str]) -> bool:
    values = [str(value) for value in series.dropna().tolist()]
    return bool(values) and all(pattern.match(value) for value in values)


def profile_column(series: pd.Series, column_name: str) -> dict[str, Any]:
    profile: dict[str, Any] = {
        "name": column_name,
        "dtype": str(series.dtype),
        "null_fraction": float(series.isna().mean()),
        "cardinality_estimate": int(series.dropna().nunique()),
        "sample_values": sample_values(series),
        "non_null_count": int(series.notna().sum()),
        "is_unique": bool(series.isna().sum() == 0 and series.nunique(dropna=True) == len(series)),
    }

    if is_numeric_dtype(series):
        profile["stats"] = numeric_stats(series)

    safe_enum = full_unique_values(series)
    if safe_enum is not None and not is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
        profile["enum_values"] = safe_enum

    if values_match(series, UUID_RE):
        profile["pattern_hint"] = "uuid"
    elif values_match(series, SHA256_RE):
        profile["pattern_hint"] = "sha256"
    elif values_match(series, HEX12_RE):
        profile["pattern_hint"] = "hex12"

    return profile


def profile_dataframe(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    return {column: profile_column(df[column], column) for column in df.columns}


def infer_contract_type(profile: dict[str, Any]) -> str:
    dtype_str = profile["dtype"]
    if is_boolean_dtype(dtype_str):
        return "boolean"
    if is_integer_dtype(dtype_str):
        return "integer"
    if "float" in dtype_str:
        return "number"
    return "string"


def human_readable_dtype(profile: dict[str, Any]) -> str:
    dtype_str = profile["dtype"]
    if is_boolean_dtype(dtype_str):
        return "boolean"
    if is_integer_dtype(dtype_str):
        return "integer"
    if "float" in dtype_str:
        return "number"
    return "string"


def humanize_field_name(name: str) -> str:
    return name.replace("_", " ")


def field_description(name: str, profile: dict[str, Any]) -> str:
    mapping = {
        "document_id": "Identifier emitted by the current Week 3 pipeline for the processed document.",
        "source_filename": "Original source filename for the processed document.",
        "strategy_used": "Extraction strategy selected by the Week 3 pipeline for this document.",
        "confidence_score": (
            "Document-level confidence score for the current extraction output. "
            "This must remain a 0.0-1.0 numeric value; changing it to 0-100 is a breaking change."
        ),
        "escalation_triggered": "Whether the document was escalated for additional handling.",
        "escalation_reason": "Recorded reason for escalation when escalation was triggered.",
        "estimated_cost": "Cost tier assigned to the extraction run.",
        "processing_time_s": "Observed processing time in seconds for the extraction run.",
        "flagged_for_review": "Whether the pipeline flagged the document for manual review.",
        "doc_id": "Primary identifier for the extracted document record.",
        "source_path": "Original source path or URL for the document.",
        "source_hash": "Content hash of the source document.",
    }
    if name in mapping:
        return mapping[name]

    if name.endswith("_id"):
        return f"Identifier for {humanize_field_name(name[:-3])}."
    if name.endswith("_at"):
        return f"Timestamp for {humanize_field_name(name[:-3])}."
    if "confidence" in name:
        return (
            f"Confidence value for {humanize_field_name(name)}. "
            "This must remain in the 0.0-1.0 range."
        )
    if profile["dtype"] == "bool":
        return f"Boolean flag for {humanize_field_name(name)}."
    return f"Observed field for {humanize_field_name(name)} in the source dataset."


def build_profile_block(profile: dict[str, Any]) -> dict[str, Any]:
    block: dict[str, Any] = {
        "dtype": human_readable_dtype(profile),
        "null_fraction": round(profile["null_fraction"], 6),
        "cardinality_estimate": profile["cardinality_estimate"],
    }
    if profile["sample_values"]:
        block["sample_values"] = profile["sample_values"]
    if "stats" in profile and profile["stats"]:
        stats = profile["stats"]
        block["observed_min"] = round(stats["min"], 6)
        block["observed_max"] = round(stats["max"], 6)
        block["observed_mean"] = round(stats["mean"], 6)
        block["observed_stddev"] = round(stats["stddev"], 6)
        block["observed_p50"] = round(stats["p50"], 6)
        block["observed_p95"] = round(stats["p95"], 6)
    return block


def build_field_clause(profile: dict[str, Any]) -> dict[str, Any]:
    name = profile["name"]
    clause: dict[str, Any] = {"type": infer_contract_type(profile)}

    if profile["null_fraction"] == 0.0:
        clause["required"] = True

    if profile["is_unique"]:
        clause["unique"] = True

    if "confidence" in name and clause["type"] in {"number", "integer"}:
        clause["minimum"] = 0.0
        clause["maximum"] = 1.0

    if name.endswith("_id"):
        if profile.get("pattern_hint") == "uuid":
            clause["format"] = "uuid"
        elif profile.get("pattern_hint") == "hex12":
            clause["pattern"] = "^[a-f0-9]{12}$"

    if name.endswith("_at"):
        clause["format"] = "date-time"

    if profile.get("pattern_hint") == "sha256":
        clause["pattern"] = "^[a-f0-9]{64}$"

    enum_values = profile.get("enum_values")
    if enum_values and len(enum_values) == profile["cardinality_estimate"]:
        clause["enum"] = enum_values

    clause["description"] = field_description(name, profile)
    clause["profile"] = build_profile_block(profile)
    return clause


def build_quality_checks(
    profiles: dict[str, dict[str, Any]], contract_label: str
) -> dict[str, Any]:
    checks: list[str] = ["row_count >= 1"]

    for name, profile in profiles.items():
        if profile["null_fraction"] == 0.0:
            checks.append(f"missing_count({name}) = 0")
        if profile["is_unique"]:
            checks.append(f"duplicate_count({name}) = 0")
        if "confidence" in name and "stats" in profile:
            checks.append(f"min({name}) >= 0.0")
            checks.append(f"max({name}) <= 1.0")

    return {
        "type": "SodaChecks",
        "specification": {f"checks for {contract_label}": checks},
    }


def derive_lineage_consumers(
    snapshot: dict[str, Any], observed_fields: list[str]
) -> tuple[list[dict[str, Any]], list[str], dict[str, int]]:
    edges = snapshot.get("edges", [])
    summary = {
        "dataset_count": len(snapshot.get("datasets", []))
        if isinstance(snapshot.get("datasets"), list)
        else len(snapshot.get("datasets", {})),
        "transformation_count": len(snapshot.get("transformations", []))
        if isinstance(snapshot.get("transformations"), list)
        else len(snapshot.get("transformations", {})),
        "edge_count": len(edges) if isinstance(edges, list) else 0,
    }

    query_tokens = {field.lower() for field in observed_fields}
    query_tokens.update({"week3", "document_id", "doc_id", "confidence_score"})

    downstream: list[dict[str, Any]] = []
    notes: list[str] = []
    seen_ids: set[str] = set()

    if isinstance(edges, list):
        for edge in edges:
            source_text = str(edge.get("source", "")).lower()
            target_text = str(edge.get("target", "")).lower()
            if not any(token in source_text or token in target_text for token in query_tokens):
                continue
            target_id = str(edge.get("target"))
            if target_id in seen_ids:
                continue
            seen_ids.add(target_id)
            downstream.append(
                {
                    "id": target_id,
                    "fields_consumed": observed_fields[: min(3, len(observed_fields))],
                }
            )

    if not downstream:
        notes.append(
            "No explicit Week 3 consumer nodes were found in the provided Week 4 lineage snapshot."
        )
        notes.append(
            "The latest lineage file is a dbt-style graph with datasets, transformations, and edges, "
            "so blast-radius details will become stronger after Week 4 is migrated to the canonical snapshot schema."
        )

    return downstream, notes, summary


def build_contract(
    source_path: Path,
    lineage_path: Path,
    contract_slug: str,
    records: list[dict[str, Any]],
    inspection: dict[str, Any],
    df: pd.DataFrame,
    flatten_metadata: dict[str, Any],
    profiles: dict[str, dict[str, Any]],
    lineage_snapshot: dict[str, Any],
    lineage_mode: str,
) -> dict[str, Any]:
    schema: dict[str, Any] = {}
    for name in df.columns:
        schema[name] = build_field_clause(profiles[name])

    downstream, lineage_notes, lineage_summary = derive_lineage_consumers(
        lineage_snapshot, list(df.columns)
    )

    limitations: list[str] = []
    if inspection["warnings"]:
        limitations.extend(inspection["warnings"])
    if flatten_metadata["flatten_mode"] == "record_level_fallback":
        limitations.append(
            "This contract was generated from record-level summary rows because extracted_facts[] was not present in the live Week 3 file."
        )

    return {
        "kind": "DataContract",
        "apiVersion": "v3.0.0",
        "id": contract_slug.replace("_", "-"),
        "info": {
            "title": "Week 3 Extractions Contract",
            "version": "1.0.0",
            "owner": "week7-contract-generator",
            "description": (
                "Generated from the live Week 3 extraction output using profiling-based inference. "
                "The contract reflects the real source file currently present in outputs/week3/extractions.jsonl."
            ),
        },
        "servers": {
            "local": {
                "type": "local",
                "path": str(source_path).replace("\\", "/"),
                "format": "jsonl",
            }
        },
        "terms": {
            "usage": "Internal inter-system data contract generated from observed Week 3 output.",
            "limitations": (
                "Generated from the current live Week 3 export, which still uses a legacy summary schema."
                if limitations
                else "No additional limitations recorded."
            ),
        },
        "observations": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "record_count": len(records),
            "profiled_row_count": flatten_metadata["profiled_row_count"],
            "flatten_mode": flatten_metadata["flatten_mode"],
            "repeated_field": flatten_metadata["repeated_field"],
            "observed_keys": inspection["observed_keys"],
            "warnings": limitations,
        },
        "schema": schema,
        "quality": build_quality_checks(profiles, contract_slug),
        "lineage": {
            "source_snapshot": str(lineage_path).replace("\\", "/"),
            "snapshot_format": lineage_mode,
            "snapshot_summary": lineage_summary,
            "upstream": [],
            "downstream": downstream,
            "notes": lineage_notes,
        },
    }


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=False)


def quality_check_contract(path: Path) -> list[str]:
    warnings: list[str] = []
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    schema = payload.get("schema", {})
    if not schema:
        raise ValueError("Generated contract is missing a schema section.")

    confidence_fields = [
        (name, clause)
        for name, clause in schema.items()
        if "confidence" in name and isinstance(clause, dict)
    ]
    if not confidence_fields:
        warnings.append("No confidence field was present in the generated contract.")
    else:
        for name, clause in confidence_fields:
            if clause.get("minimum") != 0.0 or clause.get("maximum") != 1.0:
                raise ValueError(
                    f"Confidence clause for {name} is missing the required 0.0-1.0 range."
                )

    for name, clause in schema.items():
        if not clause.get("description"):
            warnings.append(f"{name} is missing a human-readable description.")

    if not payload.get("lineage"):
        warnings.append("Lineage section is missing.")

    return warnings


def main() -> int:
    args = parse_args()
    source_path = Path(args.source)
    lineage_path = Path(args.lineage)
    output_dir = Path(args.output)
    contract_slug = make_contract_slug(source_path, args.contract_id)
    output_path = output_dir / f"{contract_slug}.yaml"

    records = load_week3_records(source_path)
    inspection = inspect_records(records)
    df, flatten_metadata = flatten_for_profile(records)
    profiles = profile_dataframe(df)
    lineage_snapshot, lineage_mode = load_latest_lineage_snapshot(lineage_path)

    contract = build_contract(
        source_path=source_path,
        lineage_path=lineage_path,
        contract_slug=contract_slug,
        records=records,
        inspection=inspection,
        df=df,
        flatten_metadata=flatten_metadata,
        profiles=profiles,
        lineage_snapshot=lineage_snapshot,
        lineage_mode=lineage_mode,
    )
    write_yaml(output_path, contract)

    print(f"Wrote contract to {output_path}")
    warnings = quality_check_contract(output_path)
    if warnings:
        print("Contract quality warnings:")
        for warning in warnings:
            print(f"- {warning}")
    else:
        print("Contract quality check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
