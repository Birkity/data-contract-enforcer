from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from registry_tools import get_contract_subscriptions, load_registry


ALLOWED_TRACE_RUN_TYPES = {"llm", "chain", "tool", "retriever", "embedding"}
TOKEN_RE = re.compile(r"[a-z0-9]+")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run AI-specific contract extensions on Week 3, Week 2, and LangSmith trace artifacts."
    )
    parser.add_argument("--week3", default="outputs/week3/extractions.jsonl")
    parser.add_argument("--week2", default="outputs/week2/verdicts.jsonl")
    parser.add_argument("--traces", default="outputs/traces/runs.jsonl")
    parser.add_argument("--registry", default="contract_registry/subscriptions.yaml")
    parser.add_argument("--output", default="enforcer_report/ai_metrics.json")
    parser.add_argument("--violation-log", default="violation_log/violations.jsonl")
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def parse_iso(value: Any) -> datetime:
    text = str(value)
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def status_from_rate(rate: float, warn_threshold: float, fail_threshold: float) -> str:
    if rate > fail_threshold:
        return "FAIL"
    if rate > warn_threshold:
        return "WARN"
    return "PASS"


def severity_for_status(status: str) -> str:
    return {
        "PASS": "LOW",
        "WARN": "MEDIUM",
        "FAIL": "HIGH",
    }[status]


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def hashed_embedding(text: str, dimensions: int = 128) -> list[float]:
    vector = [0.0] * dimensions
    for token in tokenize(text):
        index = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16) % dimensions
        vector[index] += 1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def centroid(texts: list[str], dimensions: int = 128) -> list[float]:
    vectors = [hashed_embedding(text, dimensions) for text in texts if text]
    if not vectors:
        return [0.0] * dimensions
    accum = [0.0] * dimensions
    for vector in vectors:
        for index, value in enumerate(vector):
            accum[index] += value
    return [value / len(vectors) for value in accum]


def cosine_distance(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left)) or 1.0
    right_norm = math.sqrt(sum(b * b for b in right)) or 1.0
    similarity = numerator / (left_norm * right_norm)
    return max(0.0, min(1.0, 1.0 - similarity))


def top_shifted_tokens(left_texts: list[str], right_texts: list[str], limit: int = 8) -> list[str]:
    left_counts = Counter(token for text in left_texts for token in tokenize(text))
    right_counts = Counter(token for text in right_texts for token in tokenize(text))
    scored = []
    for token in set(left_counts) | set(right_counts):
        delta = abs(left_counts[token] - right_counts[token])
        if delta == 0:
            continue
        scored.append((delta, token))
    scored.sort(reverse=True)
    return [token for _, token in scored[:limit]]


def compute_embedding_drift(week3_rows: list[dict[str, Any]]) -> dict[str, Any]:
    documents = sorted(
        week3_rows,
        key=lambda row: parse_iso(row.get("extracted_at") or now_iso()),
    )
    fact_texts: list[tuple[str, str]] = []
    for row in documents:
        extracted_at = str(row.get("extracted_at") or "")
        for fact in row.get("extracted_facts", []):
            text = fact.get("text")
            if text:
                fact_texts.append((extracted_at, text))

    ordered_texts = [text for _, text in fact_texts]
    midpoint = max(len(ordered_texts) // 2, 1)
    baseline_texts = ordered_texts[:midpoint]
    current_texts = ordered_texts[midpoint:] or ordered_texts[:midpoint]

    drift_score = cosine_distance(centroid(baseline_texts), centroid(current_texts))
    status = status_from_rate(drift_score, warn_threshold=0.18, fail_threshold=0.35)
    return {
        "status": status,
        "severity": severity_for_status(status),
        "metric": "embedding_drift_score",
        "value": round(drift_score, 6),
        "baseline_size": len(baseline_texts),
        "current_size": len(current_texts),
        "thresholds": {"warn_above": 0.18, "fail_above": 0.35},
        "summary": "Deterministic lexical embedding drift between early and late Week 3 fact text windows.",
        "top_shifted_tokens": top_shifted_tokens(baseline_texts, current_texts),
        "notes": [
            "This uses a local hashed-token embedding surrogate so the metric is reproducible without external model calls."
        ],
    }


def validate_prompt_family(inputs: dict[str, Any]) -> tuple[bool, str]:
    if {"document_id", "page", "section", "text"} <= set(inputs):
        valid = (
            isinstance(inputs.get("document_id"), str)
            and bool(inputs.get("document_id").strip())
            and isinstance(inputs.get("page"), int)
            and inputs.get("page") >= 1
            and isinstance(inputs.get("section"), str)
            and isinstance(inputs.get("text"), str)
            and len(inputs.get("text").strip()) >= 20
        )
        return valid, "document_page_text"

    if {"numeric_dense", "section_text", "section_title"} <= set(inputs):
        valid = (
            isinstance(inputs.get("section_title"), str)
            and bool(inputs.get("section_title").strip())
            and isinstance(inputs.get("section_text"), str)
            and len(inputs.get("section_text").strip()) >= 20
            and isinstance(inputs.get("numeric_dense"), (bool, int))
        )
        return valid, "section_prompt"

    if {"format_json", "prompt", "prompt_chars", "system", "system_chars", "task"} <= set(inputs):
        valid = (
            isinstance(inputs.get("task"), str)
            and bool(inputs.get("task").strip())
            and isinstance(inputs.get("prompt"), str)
            and len(inputs.get("prompt").strip()) >= 20
            and isinstance(inputs.get("system"), str)
            and len(inputs.get("system").strip()) >= 10
            and isinstance(inputs.get("prompt_chars"), int)
            and inputs.get("prompt_chars") >= len(inputs.get("prompt", "")) * 0.5
            and isinstance(inputs.get("system_chars"), int)
            and inputs.get("system_chars") >= len(inputs.get("system", "")) * 0.5
            and isinstance(inputs.get("format_json"), bool)
        )
        return valid, "task_prompt"

    return False, "unrecognized_prompt_shape"


def compute_prompt_input_validation(trace_rows: list[dict[str, Any]]) -> dict[str, Any]:
    prompt_rows = [row for row in trace_rows if row.get("run_type") == "prompt"]
    failures: list[dict[str, Any]] = []
    family_counts = Counter()
    for row in prompt_rows:
        valid, family = validate_prompt_family(row.get("inputs") or {})
        family_counts[family] += 1
        if not valid:
            failures.append(
                {
                    "run_id": row.get("id"),
                    "family": family,
                    "input_keys": sorted((row.get("inputs") or {}).keys()),
                }
            )

    rate = len(failures) / max(len(prompt_rows), 1)
    status = status_from_rate(rate, warn_threshold=0.02, fail_threshold=0.08)
    return {
        "status": status,
        "severity": severity_for_status(status),
        "metric": "prompt_input_schema_violation_rate",
        "value": round(rate, 6),
        "checked_runs": len(prompt_rows),
        "failing_runs": len(failures),
        "thresholds": {"warn_above": 0.02, "fail_above": 0.08},
        "prompt_families": dict(sorted(family_counts.items())),
        "sample_failures": failures[:5],
        "summary": "Trace prompt inputs were validated against the observed structured prompt families in the LangSmith export.",
    }


def verdict_schema_valid(row: dict[str, Any]) -> tuple[bool, list[str]]:
    problems: list[str] = []
    required = {
        "verdict_id",
        "target_ref",
        "rubric_id",
        "rubric_version",
        "scores",
        "overall_verdict",
        "overall_score",
        "confidence",
        "evaluated_at",
    }
    for field in required:
        if field not in row or row.get(field) is None:
            problems.append(f"missing:{field}")

    if row.get("overall_verdict") not in {"PASS", "FAIL", "WARN"}:
        problems.append("invalid:overall_verdict")

    try:
        confidence = float(row.get("confidence"))
        if confidence < 0.0 or confidence > 1.0:
            problems.append("range:confidence")
    except (TypeError, ValueError):
        problems.append("type:confidence")

    scores = row.get("scores")
    if not isinstance(scores, dict) or not scores:
        problems.append("type:scores")
    else:
        for dimension, payload in scores.items():
            if not isinstance(payload, dict):
                problems.append(f"type:scores.{dimension}")
                continue
            if "score" not in payload or "evidence" not in payload or "notes" not in payload:
                problems.append(f"shape:scores.{dimension}")

    return (not problems), problems


def compute_llm_output_schema_validation(verdict_rows: list[dict[str, Any]]) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    for row in verdict_rows:
        valid, problems = verdict_schema_valid(row)
        if not valid:
            failures.append({"verdict_id": row.get("verdict_id"), "problems": problems})

    rate = len(failures) / max(len(verdict_rows), 1)
    status = status_from_rate(rate, warn_threshold=0.02, fail_threshold=0.08)
    verdict_mix = Counter(str(row.get("overall_verdict")) for row in verdict_rows)
    return {
        "status": status,
        "severity": severity_for_status(status),
        "metric": "llm_output_schema_violation_rate",
        "value": round(rate, 6),
        "checked_rows": len(verdict_rows),
        "failing_rows": len(failures),
        "thresholds": {"warn_above": 0.02, "fail_above": 0.08},
        "verdict_mix": dict(sorted(verdict_mix.items())),
        "sample_failures": failures[:5],
        "summary": "Week 2 verdict records were checked for stable structured LLM output envelopes.",
    }


def compute_trace_contract_risk(trace_rows: list[dict[str, Any]], registry_payload: dict[str, Any]) -> dict[str, Any]:
    invalid_run_types = [
        row.get("run_type") for row in trace_rows if row.get("run_type") not in ALLOWED_TRACE_RUN_TYPES
    ]
    duration_failures = []
    token_failures = []
    for row in trace_rows:
        try:
            start = parse_iso(row.get("start_time"))
            end = parse_iso(row.get("end_time"))
            if end <= start:
                duration_failures.append(row.get("id"))
        except Exception:
            duration_failures.append(row.get("id"))

        prompt_tokens = int(row.get("prompt_tokens") or 0)
        completion_tokens = int(row.get("completion_tokens") or 0)
        total_tokens = int(row.get("total_tokens") or 0)
        if total_tokens < prompt_tokens + completion_tokens:
            token_failures.append(row.get("id"))

    run_type_rate = len(invalid_run_types) / max(len(trace_rows), 1)
    status = status_from_rate(run_type_rate, warn_threshold=0.05, fail_threshold=0.12)
    subscribers = get_contract_subscriptions(registry_payload, "langsmith-trace-record")
    return {
        "status": status,
        "severity": severity_for_status(status),
        "metric": "trace_contract_violation_rate",
        "value": round(run_type_rate, 6),
        "checked_rows": len(trace_rows),
        "invalid_run_type_rows": len(invalid_run_types),
        "thresholds": {"warn_above": 0.05, "fail_above": 0.12},
        "allowed_run_types": sorted(ALLOWED_TRACE_RUN_TYPES),
        "observed_invalid_run_types": dict(sorted(Counter(invalid_run_types).items())),
        "duration_failures": len(duration_failures),
        "token_failures": len(token_failures),
        "subscriber_count": len(subscribers),
        "summary": "LangSmith trace telemetry was checked against the documented Week 7 trace contract expectations.",
    }


def worst_status(metrics: list[dict[str, Any]]) -> str:
    ordering = {"PASS": 0, "WARN": 1, "FAIL": 2}
    return max(metrics, key=lambda item: ordering[item["status"]])["status"]


def append_ai_findings(
    violation_log_path: Path,
    trace_path: Path,
    trace_rows: list[dict[str, Any]],
    ai_metrics: dict[str, Any],
) -> None:
    ensure_parent(violation_log_path)
    report_id = str(uuid.uuid4())
    run_timestamp = ai_metrics["generated_at"]
    snapshot_id = hashlib.sha256(trace_path.read_bytes()).hexdigest()

    metrics = ai_metrics.get("checks", {})
    trace_metric = metrics.get("trace_contract_risk")
    if trace_metric and trace_metric.get("status") in {"WARN", "FAIL"}:
        entry = {
            "report_id": report_id,
            "contract_id": "langsmith-trace-record",
            "snapshot_id": snapshot_id,
            "run_timestamp": run_timestamp,
            "validation_mode": "AUDIT",
            "field": "run_type",
            "check_type": "enum",
            "status": trace_metric["status"],
            "severity": trace_metric["severity"],
            "action": "WARN",
            "blocking": False,
            "message": "Observed trace run types include values outside the documented Week 7 trace enum.",
            "sample_values": list((trace_metric.get("observed_invalid_run_types") or {}).keys())[:5],
            "records_failing": trace_metric.get("invalid_run_type_rows", 0),
            "records_total": len(trace_rows),
            "failing_percent": round((trace_metric.get("invalid_run_type_rows", 0) / max(len(trace_rows), 1)) * 100.0, 2),
            "check_id": "langsmith-trace-record.run_type.enum",
            "source_component": "ai_extensions",
            "evidence_kind": "real_observed_violation",
        }
        with violation_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")


def build_ai_metrics(
    week3_rows: list[dict[str, Any]],
    verdict_rows: list[dict[str, Any]],
    trace_rows: list[dict[str, Any]],
    registry_payload: dict[str, Any],
) -> dict[str, Any]:
    embedding = compute_embedding_drift(week3_rows)
    prompt_validation = compute_prompt_input_validation(trace_rows)
    llm_output = compute_llm_output_schema_validation(verdict_rows)
    trace_risk = compute_trace_contract_risk(trace_rows, registry_payload)
    checks = {
        "embedding_drift": embedding,
        "prompt_input_schema_validation": prompt_validation,
        "llm_output_schema_validation": llm_output,
        "trace_contract_risk": trace_risk,
    }
    overall = worst_status(list(checks.values()))
    recommendations = []
    if trace_risk["status"] != "PASS":
        recommendations.append(
            "Normalize LangSmith run_type values or adapt the trace export so only the documented enum values reach the contract boundary."
        )
    if embedding["status"] != "PASS":
        recommendations.append(
            "Re-baseline embedding-style fact-text centroids before promoting the current extraction slice to a stricter enforcement tier."
        )
    if prompt_validation["status"] != "PASS":
        recommendations.append(
            "Standardize prompt input payload shapes so trace consumers do not need to branch on undocumented prompt families."
        )
    if llm_output["status"] != "PASS":
        recommendations.append(
            "Tighten Week 2 verdict serialization and rerun the schema check before treating verdicts as a stable AI output contract."
        )
    if not recommendations:
        recommendations.append(
            "AI-specific contract metrics are stable on the current artifacts; keep tracing and schema snapshots in place as the next safety layer."
        )

    return {
        "generated_at": now_iso(),
        "architecture_context": {
            "enforcement_boundary": "consumer",
            "blast_radius_primary_source": "contract_registry",
            "lineage_role": "enrichment_only",
        },
        "checks": checks,
        "overall_status": overall,
        "summary": {
            "week3_fact_count": sum(len(row.get("extracted_facts", [])) for row in week3_rows),
            "week2_verdict_count": len(verdict_rows),
            "trace_row_count": len(trace_rows),
            "registered_trace_consumers": len(
                get_contract_subscriptions(registry_payload, "langsmith-trace-record")
            ),
        },
        "recommendations": recommendations,
    }


def main() -> int:
    args = parse_args()
    week3_rows = load_jsonl(Path(args.week3))
    verdict_rows = load_jsonl(Path(args.week2))
    trace_rows = load_jsonl(Path(args.traces))
    registry_payload = load_registry(Path(args.registry))

    payload = build_ai_metrics(week3_rows, verdict_rows, trace_rows, registry_payload)
    output_path = Path(args.output)
    ensure_parent(output_path)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    append_ai_findings(Path(args.violation_log), Path(args.traces), trace_rows, payload)

    print(
        json.dumps(
            {
                "overall_status": payload["overall_status"],
                "embedding_drift": payload["checks"]["embedding_drift"]["value"],
                "prompt_input_schema_violation_rate": payload["checks"]["prompt_input_schema_validation"]["value"],
                "llm_output_schema_violation_rate": payload["checks"]["llm_output_schema_validation"]["value"],
                "trace_contract_violation_rate": payload["checks"]["trace_contract_risk"]["value"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
