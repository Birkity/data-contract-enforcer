from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "version": 1,
            "subscriptions": [],
            "notes": [f"Registry file not found at {path}."],
        }

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if isinstance(payload, list):
        return {"version": 1, "subscriptions": payload, "notes": []}

    if not isinstance(payload, dict):
        return {
            "version": 1,
            "subscriptions": [],
            "notes": [f"Registry file at {path} could not be interpreted as a mapping."],
        }

    subscriptions = payload.get("subscriptions", [])
    if not isinstance(subscriptions, list):
        subscriptions = []

    normalized = dict(payload)
    normalized["subscriptions"] = subscriptions
    normalized.setdefault("notes", [])
    return normalized


def get_contract_subscriptions(registry_payload: dict[str, Any], contract_id: str) -> list[dict[str, Any]]:
    subscriptions = registry_payload.get("subscriptions", [])
    return [
        subscription
        for subscription in subscriptions
        if str(subscription.get("contract_id", "")).strip().lower() == contract_id.strip().lower()
    ]


def normalize_field_name(field_name: str) -> str:
    lowered = str(field_name).strip().lower()
    lowered = lowered.replace("[]", "")
    lowered = re.sub(r"[^a-z0-9]+", "_", lowered)
    lowered = re.sub(r"_+", "_", lowered).strip("_")
    return lowered


def field_aliases(field_name: str) -> set[str]:
    normalized = normalize_field_name(field_name)
    aliases = {normalized}

    if normalized.startswith("extracted_facts_"):
        aliases.add(normalized.replace("extracted_facts_", "fact_", 1))
    if normalized.startswith("fact_"):
        aliases.add(normalized.replace("fact_", "extracted_facts_", 1))

    if normalized.startswith("metadata_"):
        aliases.add(normalized)

    return aliases


def breaking_field_names(subscription: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for item in subscription.get("breaking_fields", []):
        if isinstance(item, dict):
            field_name = item.get("field")
            if field_name:
                names.append(str(field_name))
        elif item:
            names.append(str(item))
    return names


def subscription_matches_field(subscription: dict[str, Any], failing_field: str) -> bool:
    failing_aliases = field_aliases(failing_field)

    for field_name in breaking_field_names(subscription):
        if field_aliases(field_name) & failing_aliases:
            return True

    for field_name in subscription.get("fields_consumed", []):
        if field_aliases(field_name) & failing_aliases:
            return True

    return False


def get_field_subscriptions(
    registry_payload: dict[str, Any], contract_id: str, failing_field: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    contract_subscriptions = get_contract_subscriptions(registry_payload, contract_id)
    matching = [
        subscription
        for subscription in contract_subscriptions
        if subscription_matches_field(subscription, failing_field)
    ]
    return matching, contract_subscriptions


def contact_summary(contact: Any) -> str:
    if isinstance(contact, str):
        return contact
    if isinstance(contact, dict):
        owner = contact.get("owner")
        email = contact.get("email")
        role = contact.get("role")
        parts = [part for part in (owner, role, email) if part]
        return " | ".join(parts)
    return str(contact) if contact is not None else ""


def infer_trust_tier(has_registry: bool, has_lineage: bool) -> str:
    if has_registry and has_lineage:
        return "tier_1_registry_plus_lineage"
    if has_registry:
        return "tier_2_registry_primary"
    return "tier_3_lineage_only_fallback"
