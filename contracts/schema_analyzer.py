from __future__ import annotations

import argparse
import copy
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import yaml

from registry_tools import get_field_subscriptions, load_registry


@dataclass
class SnapshotRef:
    path: Path
    payload: dict[str, Any]
    label: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SchemaEvolutionAnalyzer for producer-side compatibility and CI gate decisions."
    )
    parser.add_argument("--contract-id", default="week3-extractions")
    parser.add_argument("--snapshot-root", default="schema_snapshots/contracts")
    parser.add_argument("--registry", default="contract_registry/subscriptions.yaml")
    parser.add_argument("--previous", default=None)
    parser.add_argument("--current", default=None)
    parser.add_argument(
        "--simulate",
        default="rename_confidence_field",
        choices=["none", "rename_confidence_field", "confidence_scale_shift"],
    )
    parser.add_argument(
        "--compatibility-output",
        default="schema_snapshots/compatibility_report.json",
    )
    parser.add_argument(
        "--summary-output",
        default="schema_snapshots/evolution_summary.json",
    )
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write_yaml(path: Path, payload: dict[str, Any]) -> Path:
    ensure_parent(path)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=False, width=100),
        encoding="utf-8",
    )
    return path


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def dedupe_snapshot_paths(paths: list[Path]) -> list[Path]:
    seen_hashes: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in seen_hashes:
            continue
        seen_hashes.add(digest)
        unique.append(path)
    return unique


def discover_snapshots(contract_id: str, snapshot_root: Path) -> list[Path]:
    contract_dir = snapshot_root / contract_id
    if not contract_dir.exists():
        return []

    paths = [
        path
        for path in contract_dir.glob("*.yaml")
        if path.name.lower() != "latest.yaml"
    ]
    paths.sort(key=lambda item: item.name)
    unique = dedupe_snapshot_paths(paths)

    latest = contract_dir / "latest.yaml"
    if latest.exists():
        latest_unique = dedupe_snapshot_paths([latest])
        if latest_unique and all(
            hashlib.sha256(latest.read_bytes()).hexdigest()
            != hashlib.sha256(path.read_bytes()).hexdigest()
            for path in unique
        ):
            unique.append(latest)
    return unique


def resolve_previous_snapshot(args: argparse.Namespace) -> tuple[SnapshotRef | None, list[str]]:
    notes: list[str] = []
    if args.previous:
        path = Path(args.previous)
        if not path.exists():
            raise FileNotFoundError(f"Previous snapshot not found: {path}")
        return SnapshotRef(path=path, payload=load_yaml(path), label="explicit_previous"), notes

    discovered = discover_snapshots(args.contract_id, Path(args.snapshot_root))
    if not discovered:
        notes.append("No historical schema snapshots were found for the requested contract.")
        return None, notes

    previous_path = discovered[-1]
    if len(discovered) == 1:
        notes.append(
            "Only one unique historical snapshot was available, so it is being used as the producer-side 'previous' schema."
        )
    return SnapshotRef(path=previous_path, payload=load_yaml(previous_path), label="discovered_previous"), notes


def create_simulated_snapshot(
    previous: SnapshotRef,
    contract_id: str,
    simulation: str,
) -> SnapshotRef:
    simulated = copy.deepcopy(previous.payload)
    simulated.setdefault("observations", {})
    simulated["observations"]["generated_at"] = now_iso()
    simulated.setdefault("simulation", {})
    simulated["simulation"]["type"] = simulation
    simulated["simulation"]["source"] = str(previous.path).replace("\\", "/")

    schema = simulated.setdefault("schema", {})
    if simulation == "rename_confidence_field":
        if "fact_confidence" not in schema:
            raise KeyError("Could not simulate confidence rename because fact_confidence does not exist.")
        clause = schema.pop("fact_confidence")
        clause["description"] = (
            "Simulated renamed field for CI gate testing. This intentionally breaks consumers expecting fact_confidence."
        )
        reordered: dict[str, Any] = {}
        inserted = False
        for key, value in schema.items():
            if not inserted and key == "fact_page_ref":
                reordered["fact_confidence_score"] = clause
                inserted = True
            reordered[key] = value
        if not inserted:
            reordered["fact_confidence_score"] = clause
        simulated["schema"] = reordered
    elif simulation == "confidence_scale_shift":
        if "fact_confidence" not in schema:
            raise KeyError("Could not simulate confidence scale shift because fact_confidence does not exist.")
        schema["fact_confidence"]["minimum"] = 0.0
        schema["fact_confidence"]["maximum"] = 100.0
        schema["fact_confidence"]["description"] = (
            "Simulated confidence scale shift from 0.0-1.0 to 0-100 for CI gate testing."
        )

    out_path = Path("schema_snapshots") / "simulated" / contract_id / f"{simulation}.yaml"
    write_yaml(out_path, simulated)
    return SnapshotRef(path=out_path, payload=simulated, label="simulated_current")


def resolve_current_snapshot(
    args: argparse.Namespace,
    previous: SnapshotRef | None,
) -> tuple[SnapshotRef | None, list[str]]:
    notes: list[str] = []
    if args.current:
        path = Path(args.current)
        if not path.exists():
            raise FileNotFoundError(f"Current snapshot not found: {path}")
        return SnapshotRef(path=path, payload=load_yaml(path), label="explicit_current"), notes

    if previous is None:
        notes.append("Current snapshot could not be resolved because no previous snapshot was available.")
        return None, notes

    if args.simulate != "none":
        notes.append(
            f"No explicit current snapshot was supplied, so a simulated '{args.simulate}' schema change was created for Phase 4 testing."
        )
        return create_simulated_snapshot(previous, args.contract_id, args.simulate), notes

    notes.append("No explicit current snapshot was supplied and simulation was disabled.")
    return None, notes


def schema_block(snapshot: SnapshotRef) -> dict[str, dict[str, Any]]:
    schema = snapshot.payload.get("schema", {})
    return schema if isinstance(schema, dict) else {}


def similarity_score(left_name: str, left_clause: dict[str, Any], right_name: str, right_clause: dict[str, Any]) -> float:
    name_score = SequenceMatcher(None, left_name, right_name).ratio()
    desc_score = SequenceMatcher(
        None,
        str(left_clause.get("description", "")),
        str(right_clause.get("description", "")),
    ).ratio()
    type_bonus = 0.2 if left_clause.get("type") == right_clause.get("type") else 0.0
    required_bonus = 0.1 if bool(left_clause.get("required")) == bool(right_clause.get("required")) else 0.0
    confidence_bonus = 0.15 if "confidence" in left_name and "confidence" in right_name else 0.0
    return name_score * 0.45 + desc_score * 0.1 + type_bonus + required_bonus + confidence_bonus


def detect_renames(
    previous_schema: dict[str, dict[str, Any]],
    current_schema: dict[str, dict[str, Any]],
    removed_fields: set[str],
    added_fields: set[str],
) -> list[tuple[str, str, float]]:
    pairs: list[tuple[str, str, float]] = []
    used_removed: set[str] = set()
    used_added: set[str] = set()

    scored_pairs: list[tuple[float, str, str]] = []
    for removed in removed_fields:
        for added in added_fields:
            score = similarity_score(removed, previous_schema[removed], added, current_schema[added])
            if score >= 0.7:
                scored_pairs.append((score, removed, added))

    for score, removed, added in sorted(scored_pairs, reverse=True):
        if removed in used_removed or added in used_added:
            continue
        used_removed.add(removed)
        used_added.add(added)
        pairs.append((removed, added, round(score, 3)))

    return pairs


def classify_range_change(field_name: str, old_clause: dict[str, Any], new_clause: dict[str, Any]) -> tuple[str, str]:
    old_min = old_clause.get("minimum")
    old_max = old_clause.get("maximum")
    new_min = new_clause.get("minimum")
    new_max = new_clause.get("maximum")

    if "confidence" in field_name and old_max == 1.0 and new_max and float(new_max) > 1.0:
        return "breaking", "confidence_scale_shift"

    if old_min is not None and new_min is not None and float(new_min) > float(old_min):
        return "breaking", "constraint_tightening"
    if old_max is not None and new_max is not None and float(new_max) < float(old_max):
        return "breaking", "constraint_tightening"

    return "backward-compatible", "constraint_relaxation"


def classify_enum_change(old_values: list[Any], new_values: list[Any]) -> tuple[str, str]:
    old_set = set(str(value) for value in old_values)
    new_set = set(str(value) for value in new_values)
    if old_set.issubset(new_set):
        return "backward-compatible", "enum_widened"
    return "breaking", "enum_changed"


def impact_for_change(
    registry_payload: dict[str, Any],
    contract_id: str,
    field_name: str,
    classification: str,
) -> dict[str, Any]:
    matching, contract_subscriptions = get_field_subscriptions(registry_payload, contract_id, field_name)
    subscribers = matching or contract_subscriptions

    affected = []
    for subscription in subscribers:
        affected.append(
            {
                "subscriber_id": subscription.get("subscriber_id"),
                "fields_consumed": subscription.get("fields_consumed", []),
                "breaking_fields": subscription.get("breaking_fields", []),
                "validation_mode": subscription.get("validation_mode", "AUDIT"),
                "contact": subscription.get("contact"),
                "match_type": "field_match" if matching else "contract_fallback",
            }
        )

    if classification == "breaking" and matching:
        impact_level = "HIGH"
    elif classification == "breaking" and subscribers:
        impact_level = "MEDIUM"
    elif classification == "breaking":
        impact_level = "LOW"
    elif subscribers:
        impact_level = "LOW"
    else:
        impact_level = "NONE"

    return {
        "affected_consumers": affected,
        "impact_level": impact_level,
        "requires_registry_update": classification == "breaking",
        "matched_field_subscriptions": bool(matching),
    }


def build_change(
    contract_id: str,
    registry_payload: dict[str, Any],
    change_type: str,
    field_name: str,
    classification: str,
    rationale: str,
    previous_value: Any,
    current_value: Any,
    consumer_lookup_field: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    impact = impact_for_change(
        registry_payload,
        contract_id,
        consumer_lookup_field or field_name,
        classification,
    )
    payload = {
        "change_type": change_type,
        "field": field_name,
        "classification": classification,
        "rationale": rationale,
        "previous_value": previous_value,
        "current_value": current_value,
        **impact,
    }
    if extra:
        payload.update(extra)
    return payload


def compare_schemas(
    contract_id: str,
    previous_schema: dict[str, dict[str, Any]],
    current_schema: dict[str, dict[str, Any]],
    registry_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []

    previous_fields = set(previous_schema)
    current_fields = set(current_schema)
    removed_fields = previous_fields - current_fields
    added_fields = current_fields - previous_fields

    rename_pairs = detect_renames(previous_schema, current_schema, removed_fields, added_fields)
    for removed, added, score in rename_pairs:
        removed_fields.discard(removed)
        added_fields.discard(added)
        changes.append(
            build_change(
                contract_id=contract_id,
                registry_payload=registry_payload,
                change_type="field_renamed",
                field_name=f"{removed} -> {added}",
                classification="breaking",
                rationale="Field rename is breaking because existing consumers depend on the previous field path.",
                previous_value=removed,
                current_value=added,
                consumer_lookup_field=removed,
                extra={"rename_confidence": score},
            )
        )

    for field_name in sorted(removed_fields):
        changes.append(
            build_change(
                contract_id=contract_id,
                registry_payload=registry_payload,
                change_type="field_removed",
                field_name=field_name,
                classification="breaking",
                rationale="Field removal is breaking because downstream consumers may still read this field.",
                previous_value=previous_schema[field_name],
                current_value=None,
            )
        )

    for field_name in sorted(added_fields):
        changes.append(
            build_change(
                contract_id=contract_id,
                registry_payload=registry_payload,
                change_type="field_added",
                field_name=field_name,
                classification="backward-compatible",
                rationale="Additive field introduction is treated as backward-compatible by default in this CI gate.",
                previous_value=None,
                current_value=current_schema[field_name],
            )
        )

    for field_name in sorted(previous_fields & current_fields):
        old_clause = previous_schema[field_name]
        new_clause = current_schema[field_name]

        if old_clause.get("type") != new_clause.get("type"):
            changes.append(
                build_change(
                    contract_id,
                    registry_payload,
                    "type_changed",
                    field_name,
                    "breaking",
                    "Type changes are breaking because consumers parse the field according to the old type.",
                    old_clause.get("type"),
                    new_clause.get("type"),
                )
            )

        old_required = bool(old_clause.get("required"))
        new_required = bool(new_clause.get("required"))
        if old_required != new_required:
            classification = "breaking" if not old_required and new_required else "backward-compatible"
            rationale = (
                "Nullability tightened from optional to required, which is breaking for compatibility."
                if classification == "breaking"
                else "Nullability was relaxed from required to optional, which is backward-compatible."
            )
            changes.append(
                build_change(
                    contract_id,
                    registry_payload,
                    "nullability_changed",
                    field_name,
                    classification,
                    rationale,
                    {"required": old_required},
                    {"required": new_required},
                )
            )

        old_enum = old_clause.get("enum")
        new_enum = new_clause.get("enum")
        if old_enum != new_enum and (old_enum is not None or new_enum is not None):
            classification, reason = classify_enum_change(old_enum or [], new_enum or [])
            rationale = (
                "Enum widened, so previous values remain valid and the change is backward-compatible."
                if classification == "backward-compatible"
                else "Enum changed in a restrictive way, so existing consumers may reject new values."
            )
            changes.append(
                build_change(
                    contract_id,
                    registry_payload,
                    "enum_changed",
                    field_name,
                    classification,
                    rationale,
                    old_enum,
                    new_enum,
                    extra={"enum_change_kind": reason},
                )
            )

        old_min = old_clause.get("minimum")
        old_max = old_clause.get("maximum")
        new_min = new_clause.get("minimum")
        new_max = new_clause.get("maximum")
        if (old_min, old_max) != (new_min, new_max) and any(
            value is not None for value in (old_min, old_max, new_min, new_max)
        ):
            classification, reason = classify_range_change(field_name, old_clause, new_clause)
            rationale = {
                "confidence_scale_shift": "Confidence changed from a normalized 0.0-1.0 range to a different scale, which is a breaking semantic shift.",
                "constraint_tightening": "Range constraints tightened, so previously valid values may now fail.",
                "constraint_relaxation": "Range constraints relaxed, so the change is backward-compatible.",
            }[reason]
            changes.append(
                build_change(
                    contract_id,
                    registry_payload,
                    "range_changed",
                    field_name,
                    classification,
                    rationale,
                    {"minimum": old_min, "maximum": old_max},
                    {"minimum": new_min, "maximum": new_max},
                    extra={"range_change_kind": reason},
                )
            )

    return changes


def overall_decision(changes: list[dict[str, Any]]) -> tuple[str, str]:
    breaking_with_consumers = [
        change
        for change in changes
        if change["classification"] == "breaking" and change["affected_consumers"]
    ]
    breaking_without_consumers = [
        change
        for change in changes
        if change["classification"] == "breaking" and not change["affected_consumers"]
    ]

    if breaking_with_consumers:
        return (
            "FAIL",
            "Breaking change detected for fields that active registered consumers depend on. Deployment should be blocked.",
        )
    if breaking_without_consumers:
        return (
            "WARN",
            "Breaking change detected, but no active subscribers were matched. Deployment is risky and should require review.",
        )
    return ("PASS", "Only backward-compatible changes were detected. Deployment may proceed.")


def recommend_next_actions(changes: list[dict[str, Any]], decision: str) -> list[str]:
    actions: list[str] = []
    if decision == "FAIL":
        actions.append("Block producer deployment until impacted consumers have a migration plan.")
        actions.append("Update contract_registry/subscriptions.yaml with any new field names, aliases, or migration notes before release.")
        actions.append("Publish a compatibility notice to affected subscribers and regenerate the contract snapshot after the schema fix or migration.")
    elif decision == "WARN":
        actions.append("Require producer review before deployment because a risky change was detected without an active subscriber match.")
        actions.append("Confirm whether the changed field should be added to registry breaking_fields for future blast-radius visibility.")
    else:
        actions.append("Deployment may proceed, but publish the new snapshot and keep registry metadata current.")

    if any(change.get("change_type") == "field_renamed" for change in changes):
        actions.append("Prefer deprecating the old field with an alias period before removing or renaming it outright.")

    if any(change.get("change_type") == "range_changed" for change in changes):
        actions.append("Re-establish downstream numeric baselines after the producer-side schema change is accepted.")

    deduped: list[str] = []
    seen: set[str] = set()
    for action in actions:
        if action in seen:
            continue
        seen.add(action)
        deduped.append(action)
    return deduped


def build_reports(
    contract_id: str,
    previous: SnapshotRef,
    current: SnapshotRef,
    changes: list[dict[str, Any]],
    notes: list[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    decision, recommendation = overall_decision(changes)
    next_actions = recommend_next_actions(changes, decision)
    impacted_consumers = sorted(
        {
            consumer["subscriber_id"]
            for change in changes
            for consumer in change.get("affected_consumers", [])
            if consumer.get("subscriber_id")
        }
    )
    breaking = [change for change in changes if change["classification"] == "breaking"]
    compatible = [change for change in changes if change["classification"] != "breaking"]

    compatibility_report = {
        "generated_at": now_iso(),
        "role": "producer_side_ci_gate",
        "contract_id": contract_id,
        "previous_snapshot": str(previous.path).replace("\\", "/"),
        "current_snapshot": str(current.path).replace("\\", "/"),
        "decision": decision,
        "recommendation": recommendation,
        "lineage_role": "optional_enrichment_only",
        "registry_role": "primary_impact_source",
        "notes": notes,
        "producer_next_actions": next_actions,
        "changes": changes,
    }

    evolution_summary = {
        "generated_at": now_iso(),
        "contract_id": contract_id,
        "total_changes": len(changes),
        "breaking_changes": len(breaking),
        "backward_compatible_changes": len(compatible),
        "impacted_systems": impacted_consumers,
        "decision": decision,
        "ci_gate_blocking": decision == "FAIL",
        "recommendation": recommendation,
        "producer_next_actions": next_actions,
    }
    return compatibility_report, evolution_summary


def main() -> int:
    args = parse_args()
    registry_payload = load_registry(Path(args.registry))

    previous, previous_notes = resolve_previous_snapshot(args)
    current, current_notes = resolve_current_snapshot(args, previous)
    notes = previous_notes + current_notes

    if previous is None or current is None:
        compatibility_report = {
            "generated_at": now_iso(),
            "role": "producer_side_ci_gate",
            "contract_id": args.contract_id,
            "decision": "WARN",
            "recommendation": "Not enough snapshots were available to compute a schema diff.",
            "notes": notes,
            "producer_next_actions": [
                "Capture at least two contract snapshots before relying on CI compatibility enforcement.",
                "Regenerate the contract after the next producer-side schema change so the analyzer has comparison history.",
            ],
            "changes": [],
        }
        evolution_summary = {
            "generated_at": now_iso(),
            "contract_id": args.contract_id,
            "total_changes": 0,
            "breaking_changes": 0,
            "backward_compatible_changes": 0,
            "impacted_systems": [],
            "decision": "WARN",
            "ci_gate_blocking": False,
            "recommendation": "Capture at least two snapshots or supply explicit previous/current inputs.",
            "producer_next_actions": [
                "Capture at least two contract snapshots or provide explicit previous/current files to the analyzer.",
            ],
        }
        write_json(Path(args.compatibility_output), compatibility_report)
        write_json(Path(args.summary_output), evolution_summary)
        print(json.dumps({"decision": "WARN", "changes": 0}, indent=2))
        return 0

    changes = compare_schemas(
        contract_id=args.contract_id,
        previous_schema=schema_block(previous),
        current_schema=schema_block(current),
        registry_payload=registry_payload,
    )
    compatibility_report, evolution_summary = build_reports(
        contract_id=args.contract_id,
        previous=previous,
        current=current,
        changes=changes,
        notes=notes,
    )
    write_json(Path(args.compatibility_output), compatibility_report)
    write_json(Path(args.summary_output), evolution_summary)
    print(
        json.dumps(
            {
                "decision": evolution_summary["decision"],
                "total_changes": evolution_summary["total_changes"],
                "breaking_changes": evolution_summary["breaking_changes"],
                "impacted_systems": evolution_summary["impacted_systems"],
            },
            indent=2,
        )
    )
    return 2 if evolution_summary["ci_gate_blocking"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
