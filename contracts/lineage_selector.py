from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def find_git_root(start: Path) -> Path | None:
    current = start.resolve()
    while True:
        if (current / ".git").exists():
            return current
        if current.parent == current:
            return None
        current = current.parent


def infer_repo_roots_from_records(records: list[dict[str, Any]], sample_size: int = 20) -> list[Path]:
    roots: list[Path] = []
    for row in records[:sample_size]:
        source_path = row.get("source_path")
        if not source_path:
            continue
        source_file = Path(str(source_path))
        start_path = source_file.parent if source_file.suffix else source_file
        if not start_path.exists():
            continue
        git_root = find_git_root(start_path)
        if git_root is not None:
            roots.append(git_root)

    deduped: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(root.resolve())
    return deduped


def load_preferred_lineage_snapshot(
    path: Path,
    preferred_roots: list[Path] | None = None,
) -> tuple[dict[str, Any], str]:
    if not path.exists():
        raise FileNotFoundError(f"Lineage file not found: {path}")

    candidates, load_mode = _load_snapshot_candidates(path)
    snapshot, selection_mode = _select_snapshot(candidates, preferred_roots or [])
    return snapshot, f"{load_mode}:{selection_mode}"


def load_lineage_snapshots(path: Path) -> tuple[list[dict[str, Any]], str]:
    if not path.exists():
        raise FileNotFoundError(f"Lineage file not found: {path}")
    return _load_snapshot_candidates(path)


def _load_snapshot_candidates(path: Path) -> tuple[list[dict[str, Any]], str]:
    text = path.read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if line.strip()]

    jsonl_records: list[dict[str, Any]] = []
    if lines:
        for line in lines:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                jsonl_records = []
                break
            if isinstance(payload, dict):
                jsonl_records.append(payload)
        if jsonl_records:
            return jsonl_records, "jsonl"

    payload = json.loads(text)
    if isinstance(payload, dict):
        return [payload], "whole-file-json"
    if isinstance(payload, list):
        records = [item for item in payload if isinstance(item, dict)]
        if records:
            return records, "json-array"
    raise ValueError(f"Unsupported lineage file shape in {path}")


def _select_snapshot(
    candidates: list[dict[str, Any]],
    preferred_roots: list[Path],
) -> tuple[dict[str, Any], str]:
    if not candidates:
        raise ValueError("No lineage snapshots were available for selection.")

    normalized_roots = [str(root.resolve()).lower() for root in preferred_roots]
    root_names = [root.name.lower() for root in preferred_roots]
    best_score = -1
    best_snapshot = candidates[-1]

    for snapshot in candidates:
        score = _score_snapshot(snapshot, normalized_roots, root_names)
        if score > best_score:
            best_score = score
            best_snapshot = snapshot

    if best_score > 0:
        return best_snapshot, "matched-root"
    return candidates[-1], "fallback-last"


def _score_snapshot(snapshot: dict[str, Any], normalized_roots: list[str], root_names: list[str]) -> int:
    if not normalized_roots and not root_names:
        return 0

    codebase_root = str(snapshot.get("codebase_root") or "").lower()
    score = 0
    for root in normalized_roots:
        if codebase_root == root:
            score = max(score, 100)
        elif codebase_root.startswith(root):
            score = max(score, 90)

    haystacks = [codebase_root]
    for node in snapshot.get("nodes", []) or []:
        metadata = node.get("metadata", {}) or {}
        haystacks.append(str(node.get("id") or ""))
        haystacks.append(str(node.get("name") or ""))
        haystacks.append(str(node.get("source_file") or ""))
        haystacks.append(str(metadata.get("source_file") or ""))
        haystacks.append(str(metadata.get("source_file_abs") or ""))
        haystacks.append(str(metadata.get("codebase_root") or ""))
        haystacks.append(str(metadata.get("repo_name") or ""))

    combined = " ".join(part.lower() for part in haystacks if part)
    for root in normalized_roots:
        if root and root in combined:
            score = max(score, 80)
    for name in root_names:
        if name and name in combined:
            score = max(score, 70)
    return score
