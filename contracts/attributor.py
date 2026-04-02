import argparse
import json
import re
import subprocess
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from registry_tools import contact_summary, get_field_subscriptions, load_registry


TEXT_EXTENSIONS = {".py", ".yaml", ".yml", ".toml"}
IGNORED_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "data", ".refinery"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run ViolationAttributor against a validation failure report."
    )
    parser.add_argument(
        "--report",
        default="validation_reports/injected_violation.json",
        help="Path to the validation report that contains FAIL results.",
    )
    parser.add_argument(
        "--baseline-report",
        default="validation_reports/thursday_baseline.json",
        help="Optional baseline report for context.",
    )
    parser.add_argument(
        "--violation-log",
        default="violation_log/violations.jsonl",
        help="Path to the accumulated violation log JSONL.",
    )
    parser.add_argument(
        "--lineage",
        default="outputs/week4/lineage_snapshots.jsonl",
        help="Path to the Week 4 lineage snapshot.",
    )
    parser.add_argument(
        "--registry",
        default="contract_registry/subscriptions.yaml",
        help="Path to the contract registry subscriptions file.",
    )
    parser.add_argument(
        "--contract",
        default="generated_contracts/week3_extractions.yaml",
        help="Path to the generated contract YAML.",
    )
    parser.add_argument(
        "--output",
        default="violation_log/blame_chain.json",
        help="Path to the machine-readable blame chain output.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=14,
        help="Git recency window used for recent-commit context.",
    )
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def load_contract(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_lineage_snapshot(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if line.strip()]

    if lines:
        try:
            last = json.loads(lines[-1])
            if isinstance(last, dict):
                return last, "jsonl-last-line"
        except json.JSONDecodeError:
            pass

    payload = json.loads(text)
    if isinstance(payload, dict):
        return payload, "whole-file-json"
    if isinstance(payload, list) and payload and isinstance(payload[-1], dict):
        return payload[-1], "json-array-last-item"
    raise ValueError(f"Unsupported lineage snapshot format in {path}")


def find_git_root(start: Path) -> Path | None:
    current = start.resolve()
    while True:
        if (current / ".git").exists():
            return current
        if current.parent == current:
            return None
        current = current.parent


def infer_repo_roots_from_contract(contract: dict[str, Any], workspace_root: Path) -> list[Path]:
    servers = contract.get("servers", {})
    local_path = servers.get("local", {}).get("path")
    if not local_path:
        return []

    dataset_path = Path(local_path)
    if not dataset_path.is_absolute():
        dataset_path = workspace_root / dataset_path
    if not dataset_path.exists():
        return []

    rows = load_jsonl(dataset_path)
    roots: list[Path] = []
    for row in rows[:20]:
        source_path = row.get("source_path")
        if not source_path:
            continue
        source_file = Path(str(source_path))
        git_root = find_git_root(source_file.parent)
        if git_root is not None:
            roots.append(git_root)
    deduped: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root).lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(root)
    return deduped


def parse_system_id(contract: dict[str, Any], report: dict[str, Any]) -> str:
    contract_id = contract.get("id") or report.get("contract_id", "")
    normalized = str(contract_id).lower()
    if "week3" in normalized:
        return "week3-document-intelligence-refinery"
    if "week5" in normalized:
        return "week5-event-governance-ledger"
    return normalized or "unknown-system"


def normalize_failures(report: dict[str, Any], contract: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    system_id = parse_system_id(contract, report)
    dataset_path = contract.get("servers", {}).get("local", {}).get("path")

    for result in report.get("results", []):
        if result.get("status") != "FAIL":
            continue
        failures.append(
            {
                "violation_id": str(uuid.uuid4()),
                "check_id": result.get("check_id"),
                "field": result.get("column_name"),
                "dataset_system": system_id,
                "dataset_path": dataset_path,
                "check_type": result.get("check_type"),
                "status": result.get("status"),
                "severity": result.get("severity"),
                "message": result.get("message"),
                "records_failing": result.get("records_failing"),
                "sample_failing": result.get("sample_failing", []),
                "detected_at": report.get("run_timestamp"),
            }
        )
    return failures


def load_violation_log(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return load_jsonl(path)


def normalize_lineage(snapshot: dict[str, Any], load_mode: str) -> dict[str, Any]:
    if "nodes" in snapshot and "edges" in snapshot:
        nodes = {
            node["node_id"]: {
                "id": node["node_id"],
                "type": node.get("type", "UNKNOWN"),
                "label": node.get("label", node["node_id"]),
                "metadata": node.get("metadata", {}),
            }
            for node in snapshot.get("nodes", [])
            if node.get("node_id")
        }
        return {
            "shape": "canonical",
            "load_mode": load_mode,
            "nodes": nodes,
            "edges": snapshot.get("edges", []),
        }

    if "datasets" in snapshot and "edges" in snapshot:
        nodes = {}
        for node_id, node in snapshot.get("datasets", {}).items():
            nodes[node_id] = {
                "id": node_id,
                "type": node.get("dataset_type", "dataset"),
                "label": node.get("name", node_id),
                "metadata": {"path": node.get("source_file"), "description": node.get("description")},
            }
        for transform_id, transform in snapshot.get("transformations", {}).items():
            nodes[transform_id] = {
                "id": transform_id,
                "type": transform.get("transformation_type", "transformation"),
                "label": transform_id,
                "metadata": {"path": transform.get("source_file")},
            }
        return {
            "shape": "dbt-whole-file",
            "load_mode": load_mode,
            "nodes": nodes,
            "edges": snapshot.get("edges", []),
        }

    return {
        "shape": "unknown",
        "load_mode": load_mode,
        "nodes": {},
        "edges": [],
    }


def seed_lineage_nodes(
    lineage: dict[str, Any], system_id: str, repo_roots: list[Path], failure_field: str
) -> tuple[list[str], list[str]]:
    notes: list[str] = []
    seeds: list[str] = []
    nodes = lineage.get("nodes", {})
    repo_tokens = set()
    for root in repo_roots:
        repo_tokens.update(token for token in re.split(r"[^a-z0-9]+", root.name.lower()) if token)

    field_tokens = set(token for token in failure_field.lower().split("_") if token and token != "fact")
    system_tokens = set(token for token in re.split(r"[^a-z0-9]+", system_id.lower()) if token)
    all_tokens = system_tokens | repo_tokens | field_tokens

    for node_id, node in nodes.items():
        haystack = " ".join(
            [
                node_id.lower(),
                str(node.get("label", "")).lower(),
                str(node.get("metadata", {}).get("path", "")).lower(),
            ]
        )
        if any(token and token in haystack for token in all_tokens):
            seeds.append(node_id)

    if not seeds:
        notes.append(
            "No explicit Week 3 or extraction-related nodes were found in the current Week 4 lineage snapshot."
        )
    return sorted(set(seeds)), notes


def traverse_lineage(lineage: dict[str, Any], seeds: list[str]) -> dict[str, Any]:
    if not seeds:
        return {
            "matched_nodes": [],
            "upstream_candidates": [],
            "downstream_nodes": [],
        }

    forward: dict[str, list[dict[str, Any]]] = defaultdict(list)
    backward: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in lineage.get("edges", []):
        source = edge.get("source")
        target = edge.get("target")
        if not source or not target:
            continue
        forward[source].append(edge)
        backward[target].append(edge)

    def bfs(start_nodes: list[str], adjacency: dict[str, list[dict[str, Any]]], direction: str) -> list[dict[str, Any]]:
        queue = [(node, 0) for node in start_nodes]
        seen = set(start_nodes)
        found: list[dict[str, Any]] = []
        while queue:
            current, distance = queue.pop(0)
            for edge in adjacency.get(current, []):
                next_node = edge["source"] if direction == "upstream" else edge["target"]
                if next_node in seen:
                    continue
                seen.add(next_node)
                queue.append((next_node, distance + 1))
                found.append(
                    {
                        "node_id": next_node,
                        "distance": distance + 1,
                        "relationship": edge.get("relationship") or edge.get("type") or "RELATED",
                        "metadata": edge.get("metadata", {}),
                    }
                )
        return found

    upstream = bfs(seeds, backward, "upstream")
    downstream = bfs(seeds, forward, "downstream")
    return {
        "matched_nodes": seeds,
        "upstream_candidates": upstream,
        "downstream_nodes": downstream,
    }


def run_git_command(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    command = ["git", "-c", f"safe.directory={repo_root.as_posix()}", "-C", str(repo_root), *args]
    return subprocess.run(command, capture_output=True, text=True, check=False)


def read_text_if_possible(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def scan_repo_for_candidates(repo_root: Path, failure_field: str, failure_message: str) -> list[dict[str, Any]]:
    field_tokens = [token for token in failure_field.lower().split("_") if token and token != "fact"]
    message_tokens = [
        token
        for token in re.split(r"[^a-z0-9]+", failure_message.lower())
        if token and token not in {"the", "and", "with", "from", "this", "that", "detected"}
    ]
    tokens = sorted(set(field_tokens + message_tokens))

    preferred_paths = [
        "src/agents/fact_table.py",
        "src/models/schemas.py",
        "src/strategies/base.py",
        "src/strategies/vision.py",
        "src/strategies/fast_text.py",
        "rubric/extraction_rules.yaml",
    ]

    candidates: list[dict[str, Any]] = []
    seen_paths: set[Path] = set()

    for rel_path in preferred_paths:
        full_path = repo_root / rel_path
        if full_path.exists():
            seen_paths.add(full_path)

    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        seen_paths.add(path)

    for path in seen_paths:
        rel_path = path.relative_to(repo_root)
        rel_str = rel_path.as_posix().lower()
        if rel_str.startswith("tests/"):
            continue
        if rel_str.endswith("readme.md"):
            continue
        content = read_text_if_possible(path)
        haystack = f"{rel_str}\n{content.lower()}"
        token_hits = sum(1 for token in tokens if token in haystack)
        if token_hits == 0 and str(rel_path).replace("\\", "/") not in preferred_paths:
            continue

        score = min(0.45, token_hits * 0.08)
        if "fact_table" in rel_str:
            score += 0.45
        if "schemas.py" in rel_str:
            score += 0.28
        if "/strategies/" in rel_str:
            score += 0.18
        if "extraction_rules" in rel_str:
            score += 0.14
        if "confidence" in content.lower():
            score += 0.15
        if "[0, 1]" in content or "ge=0.0, le=1.0" in content or "0.0, le=1.0" in content:
            score += 0.1
        if "fact_tables" in content:
            score += 0.1

        if score <= 0.15:
            continue

        candidates.append(
            {
                "path": rel_path.as_posix(),
                "score": round(min(score, 1.0), 3),
                "token_hits": token_hits,
            }
        )

    candidates.sort(key=lambda item: (item["score"], item["token_hits"]), reverse=True)
    return candidates[:5]


def relevant_line_ranges(path: Path, failure_field: str) -> list[tuple[int, int]]:
    content = read_text_if_possible(path)
    lines = content.splitlines()
    if not lines:
        return []

    patterns = []
    if "confidence" in failure_field:
        patterns.extend(
            [
                "_confidence_for_method",
                "confidence: float = Field",
                "confidence_score",
                "min_confidence",
                "ge=0.0, le=1.0",
                "confidence=",
                "confidence",
            ]
        )
    else:
        patterns.extend(token for token in failure_field.split("_") if token and token != "fact")

    matches = [index + 1 for index, line in enumerate(lines) if any(pattern in line for pattern in patterns)]
    if not matches:
        return [(1, min(len(lines), 20))]

    ranges: list[tuple[int, int]] = []
    start = matches[0]
    prev = matches[0]
    for line_no in matches[1:]:
        if line_no - prev <= 3:
            prev = line_no
            continue
        ranges.append((max(1, start - 1), min(len(lines), prev + 1)))
        start = line_no
        prev = line_no
    ranges.append((max(1, start - 1), min(len(lines), prev + 1)))
    return ranges[:3]


def parse_blame_output(stdout: str) -> list[dict[str, Any]]:
    commits: dict[str, dict[str, Any]] = {}
    current_hash: str | None = None

    for raw_line in stdout.splitlines():
        line = raw_line.rstrip("\n")
        if not line:
            continue
        if re.match(r"^[0-9a-f]{40}\s", line):
            current_hash = line.split()[0]
            commits.setdefault(
                current_hash,
                {
                    "commit_hash": current_hash,
                    "author_name": None,
                    "author_email": None,
                    "commit_timestamp": None,
                    "commit_message": None,
                    "line_hits": 0,
                },
            )
            commits[current_hash]["line_hits"] += 1
            continue
        if current_hash is None:
            continue
        if line.startswith("author "):
            commits[current_hash]["author_name"] = line.removeprefix("author ").strip()
        elif line.startswith("author-mail "):
            commits[current_hash]["author_email"] = line.removeprefix("author-mail ").strip("<>")
        elif line.startswith("author-time "):
            timestamp = int(line.removeprefix("author-time ").strip())
            commits[current_hash]["commit_timestamp"] = datetime.fromtimestamp(
                timestamp, tz=timezone.utc
            ).isoformat()
        elif line.startswith("summary "):
            commits[current_hash]["commit_message"] = line.removeprefix("summary ").strip()

    return sorted(commits.values(), key=lambda item: item["line_hits"], reverse=True)


def get_recent_commits(repo_root: Path, rel_path: str, days: int) -> list[dict[str, Any]]:
    result = run_git_command(
        repo_root,
        [
            "log",
            "--follow",
            f"--since={days} days ago",
            "--format=%H|%an|%ae|%ai|%s",
            "--",
            rel_path,
        ],
    )
    commits: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        if "|" not in line:
            continue
        commit_hash, author_name, author_email, timestamp, message = line.split("|", 4)
        commits.append(
            {
                "commit_hash": commit_hash,
                "author_name": author_name,
                "author_email": author_email,
                "commit_timestamp": timestamp.strip(),
                "commit_message": message.strip(),
            }
        )
    return commits


def get_line_blame(repo_root: Path, rel_path: str, ranges: list[tuple[int, int]]) -> list[dict[str, Any]]:
    aggregated: Counter[str] = Counter()
    details: dict[str, dict[str, Any]] = {}

    for start, end in ranges:
        result = run_git_command(
            repo_root,
            ["blame", "-L", f"{start},{end}", "--porcelain", "--", rel_path],
        )
        blamed = parse_blame_output(result.stdout)
        for commit in blamed:
            commit_hash = commit["commit_hash"]
            aggregated[commit_hash] += commit["line_hits"]
            details.setdefault(commit_hash, commit)

    output: list[dict[str, Any]] = []
    for commit_hash, line_hits in aggregated.most_common():
        commit = dict(details[commit_hash])
        commit["line_hits"] = line_hits
        output.append(commit)
    return output


def infer_file_rationale(rel_path: str) -> str:
    if rel_path.endswith("src/agents/fact_table.py"):
        return "This file assigns and persists fact-level confidence values for extracted facts."
    if rel_path.endswith("src/models/schemas.py"):
        return "This file defines the Week 3 fact schema and enforces the confidence field as a 0.0-1.0 float."
    if rel_path.endswith("src/strategies/base.py"):
        return "This file defines the base extraction confidence contract used by Week 3 strategies."
    if rel_path.endswith("src/strategies/vision.py"):
        return "This file sets concrete confidence values for one extraction strategy."
    if rel_path.endswith("src/strategies/fast_text.py"):
        return "This file computes a confidence score for the fast-text extraction strategy."
    if rel_path.endswith("rubric/extraction_rules.yaml"):
        return "This configuration file defines confidence thresholds used for escalation and review."
    return "This file matched the failing field and message tokens and appears related to the producer-side logic."


def score_candidates(
    failures: list[dict[str, Any]],
    repo_root: Path,
    candidate_files: list[dict[str, Any]],
    days: int,
) -> dict[str, list[dict[str, Any]]]:
    scored: dict[str, list[dict[str, Any]]] = {}

    for failure in failures:
        ranked: list[dict[str, Any]] = []
        for candidate in candidate_files:
            rel_path = candidate["path"]
            full_path = repo_root / rel_path
            ranges = relevant_line_ranges(full_path, failure["field"])
            blamed = get_line_blame(repo_root, rel_path, ranges)
            recent = get_recent_commits(repo_root, rel_path, days)

            primary = blamed[0] if blamed else (recent[0] if recent else None)
            if primary is None:
                continue

            confidence_score = (candidate["score"] * 0.55)
            confidence_score += 0.2 if blamed else 0.0
            confidence_score += 0.08 if recent else 0.0
            if rel_path.endswith("src/agents/fact_table.py"):
                confidence_score += 0.08
            elif rel_path.endswith("src/models/schemas.py"):
                confidence_score += 0.05
            elif rel_path.endswith("src/strategies/base.py"):
                confidence_score += 0.03
            elif rel_path.endswith("rubric/extraction_rules.yaml"):
                confidence_score -= 0.04
            confidence_score += min(0.08, (blamed[0]["line_hits"] * 0.005)) if blamed else 0.0

            ranked.append(
                {
                    "file_path": rel_path,
                    "repo_root": str(repo_root),
                    "commit_hash": primary.get("commit_hash"),
                    "author": primary.get("author_name"),
                    "author_email": primary.get("author_email"),
                    "commit_timestamp": primary.get("commit_timestamp"),
                    "commit_message": primary.get("commit_message"),
                    "confidence_score": round(max(0.0, min(confidence_score, 0.99)), 3),
                    "path_relevance": candidate["score"],
                    "lineage_distance": 0,
                    "rationale": infer_file_rationale(rel_path),
                    "recent_commit_count": len(recent),
                    "line_blame_hits": blamed[0]["line_hits"] if blamed else 0,
                }
            )

        ranked.sort(
            key=lambda item: (
                item["confidence_score"],
                item["line_blame_hits"],
                item["recent_commit_count"],
            ),
            reverse=True,
        )
        for index, item in enumerate(ranked, start=1):
            item["rank"] = index
        scored[failure["check_id"]] = ranked[:5]
    return scored


def build_registry_blast_radius(
    registry_payload: dict[str, Any], contract_id: str, failing_field: str
) -> dict[str, Any]:
    matching, contract_subscriptions = get_field_subscriptions(
        registry_payload, contract_id, failing_field
    )
    subscriptions = matching or contract_subscriptions
    matched_on_field = bool(matching)

    impacted_subscribers = []
    for subscription in subscriptions:
        impacted_subscribers.append(
            {
                "subscriber_id": subscription.get("subscriber_id"),
                "fields_consumed": subscription.get("fields_consumed", []),
                "breaking_fields": subscription.get("breaking_fields", []),
                "validation_mode": subscription.get("validation_mode", "AUDIT"),
                "registered_at": subscription.get("registered_at"),
                "contact": subscription.get("contact"),
                "contact_summary": contact_summary(subscription.get("contact")),
                "match_type": "field_match" if matched_on_field else "contract_fallback",
            }
        )

    if impacted_subscribers:
        summary = (
            "Blast radius derived from contract registry subscribers that explicitly consume the failing field."
            if matched_on_field
            else "Blast radius derived from contract registry subscribers for the contract, even though the failing field was not explicitly declared."
        )
        confidence = "high" if matched_on_field else "medium"
    else:
        summary = (
            "No registry subscriptions were found for this contract. Blast radius cannot be established from the registry alone."
        )
        confidence = "low"

    return {
        "source": "contract_registry",
        "subscriber_count": len(impacted_subscribers),
        "matched_on_field": matched_on_field,
        "subscribers": impacted_subscribers,
        "summary": summary,
        "confidence": confidence,
    }


def build_lineage_enrichment(lineage_walk: dict[str, Any], lineage: dict[str, Any]) -> dict[str, Any]:
    downstream_nodes = [node["node_id"] for node in lineage_walk.get("downstream_nodes", [])]
    upstream_nodes = [node["node_id"] for node in lineage_walk.get("upstream_candidates", [])]
    notes = list(lineage_walk.get("notes", []))

    if downstream_nodes:
        summary = "Lineage traversal found downstream enrichment nodes that may reflect transitive propagation."
        confidence = "medium"
    else:
        shape = lineage.get("shape")
        if shape == "dbt-whole-file":
            summary = (
                "The current Week 4 lineage snapshot is a dbt-style graph and does not expose an explicit Week 3 consumer path, so lineage enrichment is partial."
            )
        else:
            summary = "No downstream lineage enrichment nodes were identified from the current snapshot."
        confidence = "low"

    return {
        "source": "week4_lineage_enrichment",
        "matched_nodes": lineage_walk.get("matched_nodes", []),
        "upstream_candidates": upstream_nodes,
        "downstream_nodes": downstream_nodes,
        "summary": summary,
        "confidence": confidence,
        "notes": notes,
    }


def build_output(
    report_path: Path,
    contract_path: Path,
    registry_path: Path,
    lineage_path: Path,
    normalized_failures: list[dict[str, Any]],
    candidate_map: dict[str, list[dict[str, Any]]],
    registry_blast_radius: dict[str, Any],
    lineage: dict[str, Any],
    lineage_enrichment: dict[str, Any],
    repo_roots: list[Path],
    violation_log_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    attributions = []
    for failure in normalized_failures:
        matching_log_entries = [
            row for row in violation_log_rows if row.get("check_id") == failure["check_id"]
        ]
        attributions.append(
            {
                "violation_id": failure["violation_id"],
                "check_id": failure["check_id"],
                "detected_at": failure["detected_at"],
                "field": failure["field"],
                "producer_system": failure["dataset_system"],
                "dataset_path": failure["dataset_path"],
                "status": failure["status"],
                "severity": failure["severity"],
                "message": failure["message"],
                "records_failing": failure["records_failing"],
                "sample_failing": failure["sample_failing"],
                "matching_violation_log_entries": len(matching_log_entries),
                "candidate_files": [item["file_path"] for item in candidate_map.get(failure["check_id"], [])],
                "blame_chain": candidate_map.get(failure["check_id"], []),
                "blast_radius": {
                    "primary": registry_blast_radius,
                    "enrichment": lineage_enrichment,
                },
                "lineage_context": {
                    "lineage_shape": lineage["shape"],
                    "load_mode": lineage["load_mode"],
                },
            }
        )

    return {
        "generated_at": now_iso(),
        "architecture_mode": {
            "blast_radius_primary_source": "contract_registry",
            "lineage_role": "enrichment_only",
            "enforcement_boundary": "consumer",
        },
        "source_report": str(report_path),
        "contract_path": str(contract_path),
        "registry_path": str(registry_path),
        "lineage_path": str(lineage_path),
        "repo_roots": [str(root) for root in repo_roots],
        "violation_log_entry_count": len(violation_log_rows),
        "attributions": attributions,
    }


def write_output(path: Path, payload: dict[str, Any]) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def main() -> int:
    args = parse_args()
    workspace_root = Path.cwd()
    report_path = Path(args.report)
    violation_log_path = Path(args.violation_log)
    lineage_path = Path(args.lineage)
    registry_path = Path(args.registry)
    contract_path = Path(args.contract)
    output_path = Path(args.output)

    report = load_json(report_path)
    contract = load_contract(contract_path)
    registry_payload = load_registry(registry_path)
    violation_log_rows = load_violation_log(violation_log_path)
    lineage_snapshot, lineage_mode = load_lineage_snapshot(lineage_path)
    lineage = normalize_lineage(lineage_snapshot, lineage_mode)

    normalized_failures = normalize_failures(report, contract)
    if not normalized_failures:
        raise SystemExit("No FAIL results were found in the supplied validation report.")

    repo_roots = infer_repo_roots_from_contract(contract, workspace_root)
    if not repo_roots:
        raise SystemExit("Could not infer any upstream git repository roots from the contract dataset.")

    seeds, seed_notes = seed_lineage_nodes(
        lineage=lineage,
        system_id=normalized_failures[0]["dataset_system"],
        repo_roots=repo_roots,
        failure_field=normalized_failures[0]["field"],
    )
    lineage_walk = traverse_lineage(lineage, seeds)
    if seed_notes:
        lineage_walk["notes"] = seed_notes

    repo_root = repo_roots[0]
    candidate_files = scan_repo_for_candidates(
        repo_root=repo_root,
        failure_field=normalized_failures[0]["field"],
        failure_message=normalized_failures[0]["message"],
    )
    candidate_map = score_candidates(
        failures=normalized_failures,
        repo_root=repo_root,
        candidate_files=candidate_files,
        days=args.days,
    )
    registry_blast_radius = build_registry_blast_radius(
        registry_payload=registry_payload,
        contract_id=contract.get("id", contract_path.stem),
        failing_field=normalized_failures[0]["field"],
    )
    lineage_enrichment = build_lineage_enrichment(lineage_walk, lineage)
    payload = build_output(
        report_path=report_path,
        contract_path=contract_path,
        registry_path=registry_path,
        lineage_path=lineage_path,
        normalized_failures=normalized_failures,
        candidate_map=candidate_map,
        registry_blast_radius=registry_blast_radius,
        lineage=lineage,
        lineage_enrichment=lineage_enrichment,
        repo_roots=repo_roots,
        violation_log_rows=violation_log_rows,
    )
    write_output(output_path, payload)

    summary = {
        "attributed_failures": len(payload["attributions"]),
        "top_file": payload["attributions"][0]["blame_chain"][0]["file_path"]
        if payload["attributions"] and payload["attributions"][0]["blame_chain"]
        else None,
        "registry_subscribers": len(payload["attributions"][0]["blast_radius"]["primary"]["subscribers"])
        if payload["attributions"]
        else 0,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
