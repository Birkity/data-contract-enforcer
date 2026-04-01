import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Bitol-style data contract from a real JSONL dataset."
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
        help="Optional contract id override. Defaults to '<parent>-<stem>'.",
    )
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    return f"{source_path.parent.name}-{source_path.stem}"


def make_output_filename(source_path: Path) -> str:
    return f"{source_path.parent.name}_{source_path.stem}.yaml"


def preview_record(record: dict[str, Any]) -> str:
    return json.dumps(record, indent=2, ensure_ascii=True)


def inspect_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    first = records[0]
    warnings: list[str] = []
    observed_keys = list(first.keys())

    canonical_markers = {"doc_id", "source_path", "source_hash", "extracted_facts", "entities"}
    missing_markers = sorted(marker for marker in canonical_markers if marker not in observed_keys)
    if missing_markers:
        warnings.append(
            "The current Week 3 file is missing canonical fields: " + ", ".join(missing_markers)
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
        target[f"{key}_count"] = len(value)
        if value and all(not isinstance(item, (dict, list)) for item in value):
            target[key] = "|".join(str(item) for item in value)
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


def render_sample_values(series: pd.Series, limit: int = 5) -> list[str]:
    samples: list[str] = []
    seen: set[str] = set()
    for value in series.dropna():
        rendered = str(value)
        if rendered in seen:
            continue
        seen.add(rendered)
        samples.append(rendered)
        if len(samples) >= limit:
            break
    return samples


def numeric_stats(series: pd.Series) -> dict[str, float]:
    clean = pd.to_numeric(series.dropna(), errors="coerce").dropna()
    if clean.empty:
        return {}
    return {
        "observed_min": round(float(clean.min()), 6),
        "observed_max": round(float(clean.max()), 6),
        "observed_mean": round(float(clean.mean()), 6),
        "observed_stddev": round(float(clean.std(ddof=1)) if len(clean) > 1 else 0.0, 6),
        "observed_p50": round(float(clean.quantile(0.50)), 6),
        "observed_p95": round(float(clean.quantile(0.95)), 6),
    }


def infer_logical_type(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_integer_dtype(series) and not pd.api.types.is_bool_dtype(series):
        return "integer"
    if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
        return "number"
    return "string"


def values_match(series: pd.Series, pattern: re.Pattern[str]) -> bool:
    values = [str(value) for value in series.dropna().tolist()]
    return bool(values) and all(pattern.match(value) for value in values)


def parse_datetime(value: Any) -> bool:
    if value is None:
        return False
    text = str(value)
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def unique_string_values(series: pd.Series, limit: int = 8) -> list[str] | None:
    values = [str(value) for value in series.dropna().unique().tolist()]
    if not values or len(values) > limit:
        return None
    return sorted(values)


def profile_column(series: pd.Series, column_name: str) -> dict[str, Any]:
    logical_type = infer_logical_type(series)
    profile: dict[str, Any] = {
        "dtype": logical_type,
        "null_fraction": round(float(series.isna().mean()), 6),
        "cardinality_estimate": int(series.dropna().nunique()),
        "sample_values": render_sample_values(series),
    }

    if logical_type in {"integer", "number"}:
        profile.update(numeric_stats(series))

    return profile


def describe_field(column_name: str) -> str:
    descriptions = {
        "doc_id": "Primary identifier for the extracted document record.",
        "source_path": "Original source path or URL for the document.",
        "source_hash": "SHA-256 content hash of the source document.",
        "entities_count": "Number of entities linked to the document record.",
        "extraction_model": "Extraction strategy or model label used to produce the record.",
        "processing_time_ms": "End-to-end extraction processing time in milliseconds.",
        "token_count_input": "Approximate input token count used by the extraction workflow.",
        "token_count_output": "Approximate output token count produced by the extraction workflow.",
        "extracted_at": "Timestamp when the extraction record was produced.",
        "fact_fact_id": "Primary identifier for the extracted fact.",
        "fact_text": "Plain-English extracted fact text.",
        "fact_entity_refs_count": "Number of entity references linked from the extracted fact.",
        "fact_entity_refs": "Entity identifiers referenced by the extracted fact.",
        "fact_confidence": "Confidence value for the extracted fact. This must remain in the 0.0-1.0 range.",
        "fact_page_ref": "Source page number associated with the extracted fact.",
        "fact_source_excerpt": "Supporting excerpt copied from the source document for the extracted fact.",
    }
    if column_name in descriptions:
        return descriptions[column_name]
    return f"Observed field for {column_name.replace('_', ' ')} in the source dataset."


def build_schema_clause(column_name: str, series: pd.Series) -> dict[str, Any]:
    profile = profile_column(series, column_name)
    clause: dict[str, Any] = {
        "type": profile["dtype"],
        "description": describe_field(column_name),
    }

    if profile["null_fraction"] == 0.0:
        clause["required"] = True

    if column_name.endswith("_id") and values_match(series, UUID_RE):
        clause["format"] = "uuid"

    if column_name.endswith("_at") and all(parse_datetime(value) for value in series.dropna().tolist()):
        clause["format"] = "date-time"

    if "confidence" in column_name:
        clause["minimum"] = 0.0
        clause["maximum"] = 1.0
        clause["description"] = "Confidence value for the extracted fact. This must remain in the 0.0-1.0 range."

    if column_name == "source_hash" and values_match(series, SHA256_RE):
        clause["pattern"] = "^[a-f0-9]{64}$"

    if profile["dtype"] == "string":
        enum_values = unique_string_values(series)
        if enum_values and column_name not in {"source_path", "source_hash", "fact_text", "fact_source_excerpt", "fact_entity_refs"}:
            clause["enum"] = enum_values

    ordered_profile: dict[str, Any] = {
        "dtype": profile["dtype"],
        "null_fraction": profile["null_fraction"],
        "cardinality_estimate": profile["cardinality_estimate"],
        "sample_values": profile["sample_values"],
    }
    for key in (
        "observed_min",
        "observed_max",
        "observed_mean",
        "observed_stddev",
        "observed_p50",
        "observed_p95",
    ):
        if key in profile:
            ordered_profile[key] = profile[key]
    clause["profile"] = ordered_profile
    return clause


def find_downstream_consumers(
    snapshot: dict[str, Any], snapshot_mode: str, source_fields: list[str]
) -> tuple[list[dict[str, Any]], list[str]]:
    downstream: list[dict[str, Any]] = []
    notes: list[str] = []

    if "nodes" in snapshot and "edges" in snapshot:
        node_map = {node.get("node_id"): node for node in snapshot.get("nodes", []) if node.get("node_id")}
        for edge in snapshot.get("edges", []):
            source = str(edge.get("source", ""))
            target = str(edge.get("target", ""))
            if "week3" in source.lower() or "extraction" in source.lower():
                node = node_map.get(target, {})
                downstream.append(
                    {
                        "id": target,
                        "label": node.get("label", target),
                        "relationship": edge.get("relationship", "CONSUMES"),
                        "fields_consumed": source_fields,
                    }
                )
        if not downstream:
            notes.append("Canonical lineage snapshot loaded, but no explicit Week 3 downstream consumers were found.")
        return downstream, notes

    if "datasets" in snapshot and "edges" in snapshot:
        notes.append(
            "Week 4 lineage is currently a dbt-style whole-file graph, not the canonical Week 7 node/edge snapshot."
        )
        notes.append(
            "No explicit consumer for the Week 3 extraction output was found in the current lineage file, so downstream blast radius is recorded as unknown."
        )
        return downstream, notes

    notes.append(
        f"Lineage snapshot was loaded in {snapshot_mode} mode, but its structure did not expose a direct Week 3 downstream mapping."
    )
    return downstream, notes


def build_contract(
    contract_id: str,
    source_path: Path,
    lineage_path: Path,
    inspection: dict[str, Any],
    df: pd.DataFrame,
    flatten_metadata: dict[str, Any],
    lineage_snapshot: dict[str, Any],
    lineage_mode: str,
) -> dict[str, Any]:
    schema_order = [
        "doc_id",
        "source_path",
        "source_hash",
        "entities_count",
        "extraction_model",
        "processing_time_ms",
        "token_count_input",
        "token_count_output",
        "extracted_at",
        "fact_fact_id",
        "fact_text",
        "fact_entity_refs_count",
        "fact_entity_refs",
        "fact_confidence",
        "fact_page_ref",
        "fact_source_excerpt",
    ]

    schema: dict[str, Any] = {}
    for column_name in schema_order:
        if column_name in df.columns:
            schema[column_name] = build_schema_clause(column_name, df[column_name])

    remaining = [column for column in df.columns if column not in schema]
    for column_name in remaining:
        schema[column_name] = build_schema_clause(column_name, df[column_name])

    downstream, lineage_notes = find_downstream_consumers(
        snapshot=lineage_snapshot,
        snapshot_mode=lineage_mode,
        source_fields=["doc_id", "extracted_facts"],
    )

    if source_path.parent.name.lower() == "week3" and source_path.stem.lower() == "extractions":
        title = "Week 3 Extractions Contract"
    else:
        title = (
            f"{source_path.parent.name.replace('_', ' ').title()} "
            f"{source_path.stem.replace('_', ' ').title()} Contract"
        )
    contract = {
        "kind": "DataContract",
        "apiVersion": "v3.0.0",
        "id": contract_id,
        "info": {
            "title": title,
            "version": "1.0.0",
            "owner": "week7-contract-generator",
            "description": (
                "Generated from the live Week 3 extraction output using profiling-based inference. "
                "The contract reflects the canonical JSONL file currently present in outputs/week3/extractions.jsonl."
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
            "limitations": "Lineage context reflects the current Week 4 snapshot shape and may be incomplete.",
        },
        "observations": {
            "generated_at": now_iso(),
            "record_count": inspection["record_count"],
            "profiled_row_count": flatten_metadata["profiled_row_count"],
            "flatten_mode": flatten_metadata["flatten_mode"],
            "repeated_field": flatten_metadata["repeated_field"],
            "observed_keys": inspection["observed_keys"],
            "warnings": inspection["warnings"],
        },
        "schema": schema,
        "lineage": {
            "source_snapshot": {
                "path": str(lineage_path).replace("\\", "/"),
                "load_mode": lineage_mode,
            },
            "downstream": downstream,
            "notes": lineage_notes,
        },
    }
    return contract


def ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_contract(output_dir: Path, filename: str, contract: dict[str, Any]) -> Path:
    ensure_output_dir(output_dir)
    output_path = output_dir / filename
    payload = yaml.safe_dump(contract, sort_keys=False, allow_unicode=False, width=100)
    output_path.write_text(payload, encoding="utf-8")
    return output_path


def quality_check(contract: dict[str, Any], output_path: Path) -> None:
    reloaded = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    schema = reloaded.get("schema", {})
    if not schema:
        raise ValueError("Generated contract has no schema block.")

    required_descriptions = [name for name, clause in schema.items() if not clause.get("description")]
    if required_descriptions:
        raise ValueError(f"Fields missing descriptions: {required_descriptions}")

    confidence_fields = [
        clause
        for name, clause in schema.items()
        if "confidence" in name
    ]
    if not confidence_fields:
        raise ValueError("Generated contract is missing a confidence clause.")

    for clause in confidence_fields:
        if clause.get("minimum") != 0.0 or clause.get("maximum") != 1.0:
            raise ValueError("Confidence clause does not enforce the 0.0-1.0 range.")

    if "lineage" not in reloaded:
        raise ValueError("Generated contract is missing lineage context.")


def main() -> int:
    args = parse_args()
    source_path = Path(args.source)
    lineage_path = Path(args.lineage)
    output_dir = Path(args.output)

    records = load_week3_records(source_path)
    inspection = inspect_records(records)
    df, flatten_metadata = flatten_for_profile(records)

    lineage_snapshot, lineage_mode = load_latest_lineage_snapshot(lineage_path)
    contract_id = make_contract_slug(source_path, args.contract_id)
    contract = build_contract(
        contract_id=contract_id,
        source_path=source_path,
        lineage_path=lineage_path,
        inspection=inspection,
        df=df,
        flatten_metadata=flatten_metadata,
        lineage_snapshot=lineage_snapshot,
        lineage_mode=lineage_mode,
    )
    output_path = write_contract(output_dir, make_output_filename(source_path), contract)
    quality_check(contract, output_path)

    print(f"Contract written to {output_path}")
    print("Contract quality check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
