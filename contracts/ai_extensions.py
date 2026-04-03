from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import urllib.error
import urllib.request
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from registry_tools import get_contract_subscriptions, load_registry


ALLOWED_TRACE_RUN_TYPES = {"llm", "chain", "tool", "retriever", "embedding"}
INTERNAL_TRACE_RUN_TYPES = {
    "prompt": {"run_type": "chain", "reason": "prompt_helper_span"},
    "parser": {"run_type": "tool", "reason": "parser_helper_span"},
}
DEFAULT_CANONICAL_TRACE_OUTPUT = "outputs/traces/runs_contract_boundary.jsonl"
DEFAULT_EMBEDDING_BASELINE = "schema_snapshots/ai/embedding_baseline.json"
EMBEDDING_MODEL_HINTS = ("embed", "embedding", "nomic-embed", "mxbai-embed")
TOKEN_RE = re.compile(r"[a-z0-9]+")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run AI-specific contract extensions on Week 3, Week 2, and LangSmith trace artifacts."
    )
    parser.add_argument("--week3", default="outputs/week3/extractions.jsonl")
    parser.add_argument("--week2", default="outputs/week2/verdicts.jsonl")
    parser.add_argument("--traces", default="outputs/traces/runs.jsonl")
    parser.add_argument("--canonical-traces-output", default=DEFAULT_CANONICAL_TRACE_OUTPUT)
    parser.add_argument("--embedding-baseline", default=DEFAULT_EMBEDDING_BASELINE)
    parser.add_argument("--refresh-embedding-baseline", action="store_true")
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
    with path.open(encoding="utf-8-sig") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


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


def extract_fact_texts(week3_rows: list[dict[str, Any]]) -> list[str]:
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

    return [text for _, text in fact_texts]


def extract_fact_text_windows(week3_rows: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    ordered_texts = extract_fact_texts(week3_rows)
    midpoint = max(len(ordered_texts) // 2, 1)
    baseline_texts = ordered_texts[:midpoint]
    current_texts = ordered_texts[midpoint:] or ordered_texts[:midpoint]
    return baseline_texts, current_texts


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


def average_vectors(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    accum = [0.0] * len(vectors[0])
    for vector in vectors:
        for index, value in enumerate(vector):
            accum[index] += value
    return [value / len(vectors) for value in accum]


def top_shifted_tokens(left_texts: list[str], right_texts: list[str], limit: int = 8) -> list[str]:
    left_counts = Counter(token for text in left_texts for token in tokenize(text))
    right_counts = Counter(token for text in right_texts for token in tokenize(text))
    return top_shifted_tokens_from_counts(left_counts, right_counts, limit=limit)


def top_shifted_tokens_from_counts(
    left_counts: Counter[str],
    right_counts: Counter[str],
    limit: int = 8,
) -> list[str]:
    scored = []
    for token in set(left_counts) | set(right_counts):
        delta = abs(left_counts[token] - right_counts[token])
        if delta == 0:
            continue
        scored.append((delta, token))
    scored.sort(reverse=True)
    return [token for _, token in scored[:limit]]


def token_count_map(texts: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(token for text in texts for token in tokenize(text)).items()))


def post_json(url: str, payload: dict[str, Any], timeout: int = 30) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_json(url: str, timeout: int = 10) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_ollama_base_url(raw_url: str | None) -> str | None:
    if not raw_url:
        return None
    cleaned = raw_url.strip().rstrip("/")
    if cleaned.endswith("/v1"):
        cleaned = cleaned[:-3]
    return cleaned.rstrip("/")


def discover_embedding_base_url(trace_rows: list[dict[str, Any]]) -> str | None:
    env_candidates = [
        os.getenv("OLLAMA_BASE_URL"),
        os.getenv("OLLAMA_HOST"),
        os.getenv("OPENAI_BASE_URL"),
    ]
    for candidate in env_candidates:
        normalized = normalize_ollama_base_url(candidate)
        if normalized:
            return normalized

    for row in trace_rows:
        metadata = ((row.get("extra") or {}).get("metadata") or {})
        for key in ("ollama_base_url", "base_url"):
            normalized = normalize_ollama_base_url(metadata.get(key))
            if normalized:
                return normalized
        inputs = row.get("inputs") or {}
        normalized = normalize_ollama_base_url(inputs.get("base_url"))
        if normalized:
            return normalized
    return None


def discover_embedding_model(base_url: str | None) -> tuple[str | None, str | None]:
    env_model = os.getenv("OLLAMA_EMBED_MODEL") or os.getenv("OLLAMA_EMBEDDING_MODEL")
    if env_model:
        return env_model, None
    if not base_url:
        return None, "No Ollama-compatible base URL was discovered in the environment or trace metadata."

    try:
        payload = fetch_json(f"{base_url}/api/tags")
    except Exception as exc:  # pragma: no cover - exercised in live env
        return None, f"Could not query local embedding provider at {base_url}: {exc}"

    names = [
        str(model.get("name") or "")
        for model in payload.get("models", [])
        if isinstance(model, dict)
    ]
    for name in names:
        lowered = name.lower()
        if any(hint in lowered for hint in EMBEDDING_MODEL_HINTS):
            return name, None
    if names:
        return None, (
            "No embedding-capable Ollama model was installed. "
            f"Available models: {', '.join(names)}"
        )
    return None, "No models were reported by the local Ollama provider."


def fetch_ollama_embeddings(
    base_url: str,
    model: str,
    texts: list[str],
    batch_size: int = 24,
) -> list[list[float]]:
    vectors: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        payload = {"model": model, "input": batch}
        response = post_json(f"{base_url}/api/embed", payload, timeout=60)
        batch_vectors = response.get("embeddings")
        if not isinstance(batch_vectors, list):
            raise ValueError("Embedding response did not include an 'embeddings' list.")
        vectors.extend(batch_vectors)
    if len(vectors) != len(texts):
        raise ValueError(
            f"Expected {len(texts)} embeddings but provider returned {len(vectors)}."
        )
    return vectors


def build_embedding_representation(
    texts: list[str],
    trace_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    metric_source = "deterministic_lexical_surrogate"
    provider = "local-hash"
    model = "hashed-token-centroid"
    fallback_reason = None

    base_url = discover_embedding_base_url(trace_rows)
    embed_model, model_reason = discover_embedding_model(base_url)
    if embed_model and base_url:
        try:
            vectors = fetch_ollama_embeddings(base_url, embed_model, texts)
            centroid_vector = average_vectors(vectors)
            metric_source = "ollama_embeddings"
            provider = base_url
            model = embed_model
        except Exception as exc:  # pragma: no cover - depends on local runtime
            centroid_vector = centroid(texts)
            fallback_reason = (
                f"Embedding provider was discovered but the embedding request failed: {exc}"
            )
    else:
        centroid_vector = centroid(texts)
        fallback_reason = model_reason

    return {
        "centroid": centroid_vector,
        "metric_source": metric_source,
        "provider": provider,
        "model": model,
        "fallback_reason": fallback_reason,
        "text_count": len(texts),
        "token_counts": token_count_map(texts),
    }


def persist_embedding_baseline(
    path: Path,
    representation: dict[str, Any],
    *,
    baseline_action: str,
) -> dict[str, Any]:
    payload = {
        "generated_at": now_iso(),
        "baseline_action": baseline_action,
        "metric_source": representation["metric_source"],
        "provider": representation["provider"],
        "model": representation["model"],
        "fallback_reason": representation["fallback_reason"],
        "text_count": representation["text_count"],
        "token_counts": representation["token_counts"],
        "centroid": representation["centroid"],
    }
    write_json(path, payload)
    return payload


def compute_embedding_drift(
    week3_rows: list[dict[str, Any]],
    trace_rows: list[dict[str, Any]],
    baseline_path: Path,
    *,
    refresh_baseline: bool = False,
) -> dict[str, Any]:
    current_texts = extract_fact_texts(week3_rows)
    current_representation = build_embedding_representation(current_texts, trace_rows)
    baseline_payload = load_json(baseline_path)

    baseline_action = "used_existing"
    if refresh_baseline or not baseline_payload:
        baseline_action = "refreshed" if refresh_baseline and baseline_payload else "created"
        baseline_payload = persist_embedding_baseline(
            baseline_path,
            current_representation,
            baseline_action=baseline_action,
        )
        drift_score = 0.0
    else:
        baseline_vector = baseline_payload.get("centroid") or []
        current_vector = current_representation["centroid"]
        if not baseline_vector or len(baseline_vector) != len(current_vector):
            baseline_action = "recreated_due_to_shape_mismatch"
            baseline_payload = persist_embedding_baseline(
                baseline_path,
                current_representation,
                baseline_action=baseline_action,
            )
            drift_score = 0.0
        else:
            drift_score = cosine_distance(baseline_vector, current_vector)

    status = status_from_rate(drift_score, warn_threshold=0.18, fail_threshold=0.35)
    notes = []
    if current_representation["metric_source"] == "ollama_embeddings":
        notes.append(
            "This metric used a real local embedding provider, so the drift score reflects semantic similarity rather than token hashing alone."
        )
    else:
        notes.append(
            "This metric used a deterministic local hashed-token embedding surrogate because no usable embedding provider was available."
        )
    if current_representation["fallback_reason"]:
        notes.append(current_representation["fallback_reason"])
    if baseline_action in {"created", "refreshed", "recreated_due_to_shape_mismatch"}:
        notes.append(
            f"Embedding baseline was {baseline_action.replace('_', ' ')} from the current Week 3 extraction slice before evaluating drift."
        )

    return {
        "status": status,
        "severity": severity_for_status(status),
        "metric": "embedding_drift_score",
        "value": round(drift_score, 6),
        "baseline_size": int(baseline_payload.get("text_count") or 0),
        "current_size": len(current_texts),
        "metric_source": current_representation["metric_source"],
        "provider": current_representation["provider"],
        "model": current_representation["model"],
        "fallback_reason": current_representation["fallback_reason"],
        "baseline_action": baseline_action,
        "baseline_generated_at": baseline_payload.get("generated_at"),
        "baseline_path": str(baseline_path).replace("\\", "/"),
        "thresholds": {"warn_above": 0.18, "fail_above": 0.35},
        "summary": (
            "Semantic drift between the current Week 3 fact text slice and the persisted embedding baseline."
            if current_representation["metric_source"] == "ollama_embeddings"
            else "Deterministic lexical embedding drift between the current Week 3 fact text slice and the persisted embedding baseline."
        ),
        "top_shifted_tokens": top_shifted_tokens_from_counts(
            Counter(baseline_payload.get("token_counts") or {}),
            Counter(current_representation["token_counts"]),
        ),
        "notes": notes,
    }


def canonicalize_trace_rows(trace_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    canonical_rows: list[dict[str, Any]] = []
    normalized_rows: list[dict[str, Any]] = []
    for row in trace_rows:
        raw_run_type = str(row.get("run_type") or "").strip()
        normalized = dict(row)
        metadata = dict(((normalized.get("extra") or {}).get("metadata") or {}))
        if raw_run_type in INTERNAL_TRACE_RUN_TYPES:
            normalization = INTERNAL_TRACE_RUN_TYPES[raw_run_type]
            metadata["original_run_type"] = raw_run_type
            metadata["span_role"] = normalization["reason"]
            normalized["run_type"] = normalization["run_type"]
            normalized_rows.append(
                {
                    "id": row.get("id"),
                    "name": row.get("name"),
                    "raw_run_type": raw_run_type,
                    "normalized_run_type": normalization["run_type"],
                    "reason": normalization["reason"],
                }
            )
        else:
            metadata.setdefault("original_run_type", raw_run_type)
        normalized.setdefault("extra", {})
        normalized["extra"] = dict(normalized["extra"])
        normalized["extra"]["metadata"] = metadata
        normalized.setdefault("run_type", raw_run_type)
        canonical_rows.append(normalized)

    return canonical_rows, {
        "raw_row_count": len(trace_rows),
        "canonical_row_count": len(canonical_rows),
        "normalized_helper_rows": len(normalized_rows),
        "normalized_helper_run_types": dict(
            sorted(Counter(item["raw_run_type"] for item in normalized_rows).items())
        ),
        "normalized_samples": normalized_rows[:10],
        "summary": (
            "Internal helper spans were normalized to documented contract run types while preserving the original raw run_type in metadata."
        ),
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
    prompt_rows = []
    for row in trace_rows:
        metadata = ((row.get("extra") or {}).get("metadata") or {})
        if row.get("run_type") == "prompt" or metadata.get("original_run_type") == "prompt":
            prompt_rows.append(row)
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


def compute_trace_contract_risk(
    raw_trace_rows: list[dict[str, Any]],
    canonical_trace_rows: list[dict[str, Any]],
    normalization_summary: dict[str, Any],
    registry_payload: dict[str, Any],
) -> dict[str, Any]:
    invalid_run_types = [
        row.get("run_type")
        for row in canonical_trace_rows
        if row.get("run_type") not in ALLOWED_TRACE_RUN_TYPES
    ]
    duration_failures = []
    token_failures = []
    for row in canonical_trace_rows:
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

    run_type_rate = len(invalid_run_types) / max(len(canonical_trace_rows), 1)
    status = status_from_rate(run_type_rate, warn_threshold=0.05, fail_threshold=0.12)
    subscribers = get_contract_subscriptions(registry_payload, "langsmith-trace-record")
    return {
        "status": status,
        "severity": severity_for_status(status),
        "metric": "trace_contract_violation_rate",
        "value": round(run_type_rate, 6),
        "raw_checked_rows": len(raw_trace_rows),
        "checked_rows": len(canonical_trace_rows),
        "invalid_run_type_rows": len(invalid_run_types),
        "thresholds": {"warn_above": 0.05, "fail_above": 0.12},
        "allowed_run_types": sorted(ALLOWED_TRACE_RUN_TYPES),
        "observed_invalid_run_types": dict(sorted(Counter(invalid_run_types).items())),
        "normalization": normalization_summary,
        "duration_failures": len(duration_failures),
        "token_failures": len(token_failures),
        "subscriber_count": len(subscribers),
        "summary": (
            "LangSmith trace telemetry was normalized at the consumer boundary and then checked against the documented Week 7 trace contract expectations."
        ),
    }


def worst_status(metrics: list[dict[str, Any]]) -> str:
    ordering = {"PASS": 0, "WARN": 1, "FAIL": 2}
    return max(metrics, key=lambda item: ordering[item["status"]])["status"]


def append_ai_findings(
    violation_log_path: Path,
    trace_boundary_path: Path,
    canonical_trace_rows: list[dict[str, Any]],
    ai_metrics: dict[str, Any],
) -> None:
    ensure_parent(violation_log_path)
    report_id = str(uuid.uuid4())
    run_timestamp = ai_metrics["generated_at"]
    snapshot_id = hashlib.sha256(trace_boundary_path.read_bytes()).hexdigest()

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
            "records_total": len(canonical_trace_rows),
            "failing_percent": round(
                (trace_metric.get("invalid_run_type_rows", 0) / max(len(canonical_trace_rows), 1)) * 100.0,
                2,
            ),
            "check_id": "langsmith-trace-record.run_type.enum",
            "source_component": "ai_extensions",
            "evidence_kind": "real_observed_violation",
        }
        with violation_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")


def build_ai_metrics(
    week3_rows: list[dict[str, Any]],
    verdict_rows: list[dict[str, Any]],
    raw_trace_rows: list[dict[str, Any]],
    canonical_trace_rows: list[dict[str, Any]],
    normalization_summary: dict[str, Any],
    registry_payload: dict[str, Any],
    embedding_baseline_path: Path,
    *,
    refresh_embedding_baseline: bool = False,
) -> dict[str, Any]:
    embedding = compute_embedding_drift(
        week3_rows,
        raw_trace_rows,
        embedding_baseline_path,
        refresh_baseline=refresh_embedding_baseline,
    )
    prompt_validation = compute_prompt_input_validation(raw_trace_rows)
    llm_output = compute_llm_output_schema_validation(verdict_rows)
    trace_risk = compute_trace_contract_risk(
        raw_trace_rows,
        canonical_trace_rows,
        normalization_summary,
        registry_payload,
    )
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
            "trace_row_count_raw": len(raw_trace_rows),
            "trace_row_count_canonical": len(canonical_trace_rows),
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
    raw_trace_rows = load_jsonl(Path(args.traces))
    canonical_trace_rows, normalization_summary = canonicalize_trace_rows(raw_trace_rows)
    canonical_trace_path = Path(args.canonical_traces_output)
    write_jsonl(canonical_trace_path, canonical_trace_rows)
    registry_payload = load_registry(Path(args.registry))
    embedding_baseline_path = Path(args.embedding_baseline)

    payload = build_ai_metrics(
        week3_rows,
        verdict_rows,
        raw_trace_rows,
        canonical_trace_rows,
        normalization_summary,
        registry_payload,
        embedding_baseline_path,
        refresh_embedding_baseline=args.refresh_embedding_baseline,
    )
    output_path = Path(args.output)
    ensure_parent(output_path)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    append_ai_findings(
        Path(args.violation_log),
        canonical_trace_path,
        canonical_trace_rows,
        payload,
    )

    print(
        json.dumps(
            {
                "overall_status": payload["overall_status"],
                "embedding_drift": payload["checks"]["embedding_drift"]["value"],
                "prompt_input_schema_violation_rate": payload["checks"]["prompt_input_schema_validation"]["value"],
                "llm_output_schema_violation_rate": payload["checks"]["llm_output_schema_validation"]["value"],
                "trace_contract_violation_rate": payload["checks"]["trace_contract_risk"]["value"],
                "canonical_trace_rows": len(canonical_trace_rows),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
