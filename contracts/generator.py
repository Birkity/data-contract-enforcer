from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from registry_tools import contact_summary, get_contract_subscriptions, infer_trust_tier, load_registry


UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Bitol-style data contract from a real JSONL dataset."
    )
    parser.add_argument("--source", required=True)
    parser.add_argument("--lineage", default="outputs/week4/lineage_snapshots.jsonl")
    parser.add_argument("--registry", default="contract_registry/subscriptions.yaml")
    parser.add_argument(
        "--output",
        default="generated_contracts",
        help="Directory for generated contracts, or an explicit .yaml output path.",
    )
    parser.add_argument("--snapshot-dir", default="schema_snapshots/contracts")
    parser.add_argument("--contract-id", default=None)
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8-sig") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def load_source_records(path: Path) -> list[dict[str, Any]]:
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


def make_dbt_output_filename(source_path: Path) -> str:
    return f"{source_path.parent.name}_{source_path.stem}_dbt.yml"


def make_model_name(source_path: Path) -> str:
    return f"{source_path.parent.name}_{source_path.stem}".replace("-", "_")


def make_contract_title(source_path: Path) -> str:
    if source_path.parent.name.lower() == "week3" and source_path.stem.lower() == "extractions":
        return "Week 3 Extractions Contract"
    if source_path.parent.name.lower() == "week5" and source_path.stem.lower() == "events":
        return "Week 5 Events Contract"
    return (
        f"{source_path.parent.name.replace('_', ' ').title()} "
        f"{source_path.stem.replace('_', ' ').title()} Contract"
    )


def make_contract_description(source_path: Path) -> str:
    dataset_label = f"{source_path.parent.name}/{source_path.stem}".replace("\\", "/")
    return (
        f"Generated from the live {dataset_label} JSONL output using profiling-based inference. "
        "The contract reflects the current serialized artifact present in the repository."
    )


def make_contract_usage(source_path: Path) -> str:
    return (
        "Internal inter-system data contract generated from the observed output snapshot at "
        f"{str(source_path).replace(chr(92), '/')}."
    )


def preview_record(record: dict[str, Any]) -> str:
    return json.dumps(record, indent=2, ensure_ascii=True)


def inspect_records(records: list[dict[str, Any]], source_path: Path) -> dict[str, Any]:
    first = records[0]
    warnings: list[str] = []
    observed_keys = list(first.keys())

    canonical_markers: set[str] = set()
    if source_path.parent.name.lower() == "week3" and source_path.stem.lower() == "extractions":
        canonical_markers = {"doc_id", "source_path", "source_hash", "extracted_facts", "entities"}
    elif source_path.parent.name.lower() == "week5" and source_path.stem.lower() == "events":
        canonical_markers = {
            "event_id",
            "event_type",
            "aggregate_id",
            "aggregate_type",
            "sequence_number",
            "payload",
            "metadata",
            "schema_version",
            "occurred_at",
            "recorded_at",
        }

    missing_markers = sorted(marker for marker in canonical_markers if marker not in observed_keys)
    if missing_markers:
        warnings.append(
            "The current source file is missing canonical fields: " + ", ".join(missing_markers)
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
        "event_id": "Primary identifier for the event record.",
        "event_type": "Business event type emitted by the event-sourcing platform.",
        "aggregate_id": "Identifier for the aggregate instance the event belongs to.",
        "aggregate_type": "Aggregate class or domain entity name for the event stream.",
        "sequence_number": "Monotonic sequence number within the aggregate stream.",
        "schema_version": "Version of the payload schema used to serialize the event.",
        "occurred_at": "Business timestamp when the event occurred.",
        "recorded_at": "Persistence timestamp when the event was stored.",
        "metadata_causation_id": "Identifier of the event or command that triggered this event.",
        "metadata_correlation_id": "Correlation identifier used to tie related events together.",
        "metadata_user_id": "User or system principal associated with the event.",
        "metadata_source_service": "Service or subsystem that emitted the event.",
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
    snapshot: dict[str, Any],
    snapshot_mode: str,
    source_fields: list[str],
    source_terms: list[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    downstream: list[dict[str, Any]] = []
    notes: list[str] = []

    if "nodes" in snapshot and "edges" in snapshot:
        node_map = {}
        for node in snapshot.get("nodes", []):
            node_id = node.get("node_id") or node.get("id")
            if not node_id:
                continue
            node_map[str(node_id)] = node
        for edge in snapshot.get("edges", []):
            source = str(edge.get("source", ""))
            target = str(edge.get("target", ""))
            source_text = source.lower()
            if any(term in source_text for term in source_terms):
                node = node_map.get(target, {})
                downstream.append(
                    {
                        "id": target,
                        "label": node.get("label") or node.get("name") or target,
                        "relationship": edge.get("relationship") or edge.get("edge_type") or "CONSUMES",
                        "fields_consumed": source_fields,
                    }
                )
        if not downstream:
            notes.append(
                "Canonical lineage snapshot loaded, but no explicit downstream consumers were found for the current source dataset."
            )
        return downstream, notes

    if "datasets" in snapshot and "edges" in snapshot:
        notes.append(
            "Week 4 lineage is currently a dbt-style whole-file graph, not the canonical Week 7 node/edge snapshot."
        )
        notes.append(
            "No explicit consumer for the current source dataset was found in the current lineage file, so lineage enrichment is partial."
        )
        return downstream, notes

    notes.append(
        f"Lineage snapshot was loaded in {snapshot_mode} mode, but its structure did not expose a direct downstream mapping for the current source dataset."
    )
    return downstream, notes


def make_source_fields(source_path: Path) -> list[str]:
    if source_path.parent.name.lower() == "week3" and source_path.stem.lower() == "extractions":
        return ["doc_id", "extracted_facts", "extracted_facts[].confidence"]
    if source_path.parent.name.lower() == "week5" and source_path.stem.lower() == "events":
        return ["event_id", "event_type", "payload", "occurred_at"]
    return ["record_id"]


def make_source_terms(source_path: Path) -> list[str]:
    terms = {source_path.parent.name.lower(), source_path.stem.lower()}
    if source_path.parent.name.lower() == "week3":
        terms.update({"week3", "extraction", "document-refinery"})
    if source_path.parent.name.lower() == "week5":
        terms.update({"week5", "event", "ledger"})
    return sorted(terms)


def ordered_columns_for_dataset(source_path: Path) -> list[str]:
    if source_path.parent.name.lower() == "week3" and source_path.stem.lower() == "extractions":
        return [
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
    if source_path.parent.name.lower() == "week5" and source_path.stem.lower() == "events":
        return [
            "event_id",
            "event_type",
            "aggregate_id",
            "aggregate_type",
            "sequence_number",
            "schema_version",
            "occurred_at",
            "recorded_at",
            "metadata_causation_id",
            "metadata_correlation_id",
            "metadata_user_id",
            "metadata_source_service",
        ]
    return []


def build_registry_context(
    contract_id: str,
    registry_path: Path,
    registry_payload: dict[str, Any],
) -> dict[str, Any]:
    subscriptions = []
    for subscription in get_contract_subscriptions(registry_payload, contract_id):
        subscriptions.append(
            {
                "subscriber_id": subscription.get("subscriber_id"),
                "fields_consumed": subscription.get("fields_consumed", []),
                "breaking_fields": subscription.get("breaking_fields", []),
                "validation_mode": subscription.get("validation_mode", "AUDIT"),
                "registered_at": subscription.get("registered_at"),
                "contact": subscription.get("contact"),
                "contact_summary": contact_summary(subscription.get("contact")),
            }
        )

    notes: list[str] = []
    if subscriptions:
        notes.append("Registry subscriptions are the primary source of blast-radius reasoning for this contract.")
    else:
        notes.append("No registry subscriptions were found for this contract. Blast radius falls back to lineage only.")

    registry_notes = registry_payload.get("notes", [])
    if isinstance(registry_notes, list):
        notes.extend(str(note) for note in registry_notes if note)

    return {
        "role": "primary_blast_radius_source",
        "path": str(registry_path).replace("\\", "/"),
        "subscriber_count": len(subscriptions),
        "subscriptions": subscriptions,
        "notes": notes,
    }


def build_contract(
    contract_id: str,
    source_path: Path,
    lineage_path: Path,
    registry_path: Path,
    inspection: dict[str, Any],
    df: pd.DataFrame,
    flatten_metadata: dict[str, Any],
    lineage_snapshot: dict[str, Any],
    lineage_mode: str,
    registry_payload: dict[str, Any],
) -> dict[str, Any]:
    schema_order = ordered_columns_for_dataset(source_path)

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
        source_fields=make_source_fields(source_path),
        source_terms=make_source_terms(source_path),
    )
    registry_context = build_registry_context(contract_id, registry_path, registry_payload)
    trust_tier = infer_trust_tier(
        has_registry=registry_context["subscriber_count"] > 0,
        has_lineage=bool(downstream or lineage_notes),
    )

    return {
        "kind": "DataContract",
        "apiVersion": "v3.0.0",
        "id": contract_id,
        "info": {
            "title": make_contract_title(source_path),
            "version": "1.1.0",
            "owner": "week7-contract-generator",
            "description": make_contract_description(source_path),
        },
        "servers": {
            "local": {
                "type": "local",
                "path": str(source_path).replace("\\", "/"),
                "format": "jsonl",
            }
        },
        "terms": {
            "usage": make_contract_usage(source_path),
            "limitations": "Registry subscribers are authoritative for blast radius; lineage remains enrichment-only and may be incomplete.",
        },
        "implementation_model": {
            "enforcement_boundary": "consumer",
            "blast_radius_primary_source": "contract_registry",
            "lineage_role": "enrichment_only",
            "trust_boundary_tier": trust_tier,
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
        "registry": registry_context,
        "lineage": {
            "role": "enrichment_only",
            "source_snapshot": {
                "path": str(lineage_path).replace("\\", "/"),
                "load_mode": lineage_mode,
            },
            "downstream_enrichment": downstream,
            "notes": lineage_notes,
        },
    }


def ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_yaml(path: Path, payload: dict[str, Any]) -> Path:
    ensure_output_dir(path.parent)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=False, width=100),
        encoding="utf-8",
    )
    return path


def write_contract(output_dir: Path, filename: str, contract: dict[str, Any]) -> Path:
    ensure_output_dir(output_dir)
    return write_yaml(output_dir / filename, contract)


def resolve_output_paths(output_arg: Path, source_path: Path) -> tuple[Path, Path]:
    if output_arg.suffix.lower() in {".yaml", ".yml"}:
        contract_path = output_arg
        dbt_name = make_dbt_output_filename(source_path)
        dbt_path = output_arg.with_name(dbt_name)
        return contract_path, dbt_path

    contract_path = output_arg / make_output_filename(source_path)
    dbt_path = output_arg / make_dbt_output_filename(source_path)
    return contract_path, dbt_path


def write_contract_snapshot(snapshot_dir: Path, contract_id: str, contract: dict[str, Any]) -> dict[str, str]:
    slug = timestamp_slug()
    contract_dir = snapshot_dir / contract_id
    timestamped_path = write_yaml(contract_dir / f"{slug}.yaml", contract)
    latest_path = write_yaml(contract_dir / "latest.yaml", contract)
    return {
        "timestamped": str(timestamped_path).replace("\\", "/"),
        "latest": str(latest_path).replace("\\", "/"),
    }


def build_dbt_tests(column_name: str, clause: dict[str, Any], contract: dict[str, Any]) -> list[Any]:
    tests: list[Any] = []

    if clause.get("required") is True:
        tests.append("not_null")

    profile = clause.get("profile", {})
    observations = contract.get("observations", {})
    profiled_row_count = observations.get("profiled_row_count", 0)
    cardinality_estimate = profile.get("cardinality_estimate")
    null_fraction = profile.get("null_fraction")
    if (
        column_name.endswith("_id")
        and cardinality_estimate
        and profiled_row_count
        and cardinality_estimate == profiled_row_count
        and null_fraction == 0.0
    ):
        tests.append("unique")

    if clause.get("enum"):
        tests.append({"accepted_values": {"values": clause["enum"]}})

    if clause.get("minimum") is not None or clause.get("maximum") is not None:
        range_payload: dict[str, Any] = {}
        if clause.get("minimum") is not None:
            range_payload["min_value"] = clause["minimum"]
        if clause.get("maximum") is not None:
            range_payload["max_value"] = clause["maximum"]
        tests.append({"dbt_expectations.expect_column_values_to_be_between": range_payload})

    if clause.get("pattern"):
        tests.append(
            {
                "dbt_expectations.expect_column_values_to_match_regex": {
                    "regex": clause["pattern"]
                }
            }
        )

    if clause.get("format") == "uuid":
        tests.append(
            {
                "dbt_expectations.expect_column_values_to_match_regex": {
                    "regex": "^[0-9a-fA-F-]{36}$"
                }
            }
        )

    if clause.get("format") == "date-time":
        tests.append(
            {
                "dbt_expectations.expect_column_values_to_match_regex": {
                    "regex": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T"
                }
            }
        )

    return tests


def build_dbt_counterpart(contract: dict[str, Any], source_path: Path) -> dict[str, Any]:
    model_name = make_model_name(source_path)
    columns: list[dict[str, Any]] = []

    for column_name, clause in contract.get("schema", {}).items():
        column_payload: dict[str, Any] = {
            "name": column_name,
            "description": clause.get("description", ""),
        }
        tests = build_dbt_tests(column_name, clause, contract)
        if tests:
            column_payload["tests"] = tests
        columns.append(column_payload)

    return {
        "version": 2,
        "models": [
            {
                "name": model_name,
                "description": (
                    f"dbt-compatible counterpart for generated contract {contract.get('id')} "
                    f"built from {str(source_path).replace(chr(92), '/')}."
                ),
                "meta": {
                    "generated_from_contract": contract.get("id"),
                    "generated_at": contract.get("observations", {}).get("generated_at"),
                    "source_path": str(source_path).replace("\\", "/"),
                    "blast_radius_primary_source": "contract_registry",
                    "registry_subscribers": [
                        subscription.get("subscriber_id")
                        for subscription in contract.get("registry", {}).get("subscriptions", [])
                    ],
                    "lineage_notes": contract.get("lineage", {}).get("notes", []),
                },
                "columns": columns,
            }
        ],
    }


def write_dbt_counterpart(output_dir: Path, filename: str, dbt_contract: dict[str, Any]) -> Path:
    ensure_output_dir(output_dir)
    return write_yaml(output_dir / filename, dbt_contract)


def quality_check(contract: dict[str, Any], output_path: Path) -> None:
    reloaded = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    schema = reloaded.get("schema", {})
    if not schema:
        raise ValueError("Generated contract has no schema block.")

    required_descriptions = [name for name, clause in schema.items() if not clause.get("description")]
    if required_descriptions:
        raise ValueError(f"Fields missing descriptions: {required_descriptions}")

    confidence_fields = [clause for name, clause in schema.items() if "confidence" in name]
    if not confidence_fields:
        raise ValueError("Generated contract is missing a confidence clause.")

    for clause in confidence_fields:
        if clause.get("minimum") != 0.0 or clause.get("maximum") != 1.0:
            raise ValueError("Confidence clause does not enforce the 0.0-1.0 range.")

    registry = reloaded.get("registry", {})
    if registry.get("role") != "primary_blast_radius_source":
        raise ValueError("Generated contract is missing registry-first blast-radius context.")

    lineage = reloaded.get("lineage", {})
    if lineage.get("role") != "enrichment_only":
        raise ValueError("Generated contract must mark lineage as enrichment only.")


def quality_check_dbt(dbt_output_path: Path) -> None:
    reloaded = yaml.safe_load(dbt_output_path.read_text(encoding="utf-8"))
    if reloaded.get("version") != 2:
        raise ValueError("Generated dbt counterpart is missing version: 2.")

    models = reloaded.get("models", [])
    if not models:
        raise ValueError("Generated dbt counterpart has no models block.")

    columns = models[0].get("columns", [])
    if not columns:
        raise ValueError("Generated dbt counterpart has no column definitions.")

    if not any("tests" in column for column in columns):
        raise ValueError("Generated dbt counterpart has no tests.")

    confidence_columns = [column for column in columns if "confidence" in column.get("name", "")]
    for column in confidence_columns:
        tests = column.get("tests", [])
        has_range = any(
            isinstance(test, dict) and "dbt_expectations.expect_column_values_to_be_between" in test
            for test in tests
        )
        if not has_range:
            raise ValueError("Confidence column in dbt counterpart is missing a range test.")


def main() -> int:
    args = parse_args()
    source_path = Path(args.source)
    lineage_path = Path(args.lineage)
    registry_path = Path(args.registry)
    output_arg = Path(args.output)
    snapshot_dir = Path(args.snapshot_dir)

    records = load_source_records(source_path)
    inspection = inspect_records(records, source_path)
    df, flatten_metadata = flatten_for_profile(records)

    lineage_snapshot, lineage_mode = load_latest_lineage_snapshot(lineage_path)
    registry_payload = load_registry(registry_path)
    contract_id = make_contract_slug(source_path, args.contract_id)
    contract = build_contract(
        contract_id=contract_id,
        source_path=source_path,
        lineage_path=lineage_path,
        registry_path=registry_path,
        inspection=inspection,
        df=df,
        flatten_metadata=flatten_metadata,
        lineage_snapshot=lineage_snapshot,
        lineage_mode=lineage_mode,
        registry_payload=registry_payload,
    )
    snapshot_paths = write_contract_snapshot(snapshot_dir, contract_id, contract)
    contract["observations"]["snapshot_paths"] = snapshot_paths
    output_path, dbt_output_path = resolve_output_paths(output_arg, source_path)
    output_path = write_yaml(output_path, contract)
    quality_check(contract, output_path)
    write_yaml(dbt_output_path, build_dbt_counterpart(contract, source_path))
    quality_check_dbt(dbt_output_path)

    print(f"Contract written to {output_path}")
    print(f"dbt counterpart written to {dbt_output_path}")
    print(f"Snapshot written to {snapshot_paths['timestamped']}")
    print("Contract quality check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
