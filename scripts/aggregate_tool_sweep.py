#!/usr/bin/env python3
"""Aggregate sharded tool-sweep checkpoints into one audited result."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
RESULT_STATES = (
    "passed",
    "failed",
    "schema_error",
    "no_tests",
    "timeout",
    "error",
)
FAILURE_STATES = {"failed", "schema_error", "timeout", "error"}


def load_checkpoint(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"{path}: unsupported schema version")
    if not isinstance(payload.get("results"), dict):
        raise ValueError(f"{path}: results must be an object")
    if not isinstance(payload.get("expected_patterns"), list):
        raise ValueError(f"{path}: expected_patterns must be an array")
    for pattern, result in payload["results"].items():
        if not isinstance(result, dict) or result.get("state") not in RESULT_STATES:
            raise ValueError(f"{path}: invalid result state for {pattern!r}")
    return payload


def aggregate_checkpoints(
    checkpoint_paths: list[Path], expected_shards: int
) -> dict[str, Any]:
    """Merge checkpoints and retain all completeness/duplication failures."""
    if expected_shards < 1:
        raise ValueError("expected_shards must be at least 1")

    errors: list[str] = []
    shards: list[dict[str, Any]] = []
    results: dict[str, dict[str, Any]] = {}
    expected_patterns: set[str] = set()
    shard_indices: set[int] = set()

    if len(checkpoint_paths) != expected_shards:
        errors.append(
            f"Expected {expected_shards} shard checkpoint(s), found "
            f"{len(checkpoint_paths)}"
        )

    for path in sorted(checkpoint_paths):
        try:
            payload = load_checkpoint(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(str(exc))
            continue

        run = payload.get("run") or {}
        shard_index = run.get("shard_index")
        shard_count = run.get("shard_count")
        if not isinstance(shard_index, int) or not isinstance(shard_count, int):
            errors.append(f"{path}: missing integer shard metadata")
        else:
            if shard_count != expected_shards:
                errors.append(
                    f"{path}: shard_count={shard_count}, expected {expected_shards}"
                )
            if shard_index in shard_indices:
                errors.append(f"{path}: duplicate shard_index {shard_index}")
            if shard_index < 0 or shard_index >= expected_shards:
                errors.append(f"{path}: shard_index {shard_index} is out of range")
            shard_indices.add(shard_index)

        for pattern in payload["expected_patterns"]:
            if not isinstance(pattern, str):
                errors.append(f"{path}: expected pattern names must be strings")
                continue
            if pattern in expected_patterns:
                errors.append(f"{path}: duplicate expected pattern {pattern!r}")
            expected_patterns.add(pattern)

        for pattern, result in payload["results"].items():
            if pattern in results:
                errors.append(f"{path}: duplicate completed pattern {pattern!r}")
            else:
                results[pattern] = result

        if not payload.get("complete"):
            errors.append(f"{path}: shard did not complete")
        shards.append(
            {
                "path": str(path),
                "shard_index": shard_index,
                "complete": bool(payload.get("complete")),
                "completed_patterns": len(payload["results"]),
                "expected_patterns": len(payload["expected_patterns"]),
            }
        )

    missing_patterns = sorted(expected_patterns - set(results))
    unexpected_patterns = sorted(set(results) - expected_patterns)
    if missing_patterns:
        errors.append(f"Missing {len(missing_patterns)} expected pattern result(s)")
    if unexpected_patterns:
        errors.append(f"Found {len(unexpected_patterns)} unexpected pattern result(s)")
    missing_shard_indices = sorted(set(range(expected_shards)) - shard_indices)
    if missing_shard_indices:
        errors.append(f"Missing shard index(es): {missing_shard_indices}")

    status_counts = {state: 0 for state in RESULT_STATES}
    for result in results.values():
        status_counts[result["state"]] += 1

    complete = not errors and set(results) == expected_patterns
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "complete": complete,
        "expected_shards": expected_shards,
        "received_shards": len(shards),
        "shards": sorted(shards, key=lambda shard: shard["shard_index"] or 0),
        "expected_patterns": sorted(expected_patterns),
        "completed_patterns": len(results),
        "missing_patterns": missing_patterns,
        "unexpected_patterns": unexpected_patterns,
        "status_counts": status_counts,
        "errors": errors,
        "results": dict(sorted(results.items())),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    results = payload["results"]
    total_tests = sum(result.get("tests_run", 0) for result in results.values())
    total_passed = sum(result.get("passed", 0) for result in results.values())
    lines = [
        "# Weekly Tool Health Check",
        "",
        f"- Complete: **{'yes' if payload['complete'] else 'no'}**",
        f"- Shards received: **{payload['received_shards']}/{payload['expected_shards']}**",
        f"- Categories completed: **{payload['completed_patterns']}**",
        f"- Test examples executed: **{total_tests}**",
        f"- Test examples passed: **{total_passed}**",
        "",
        "## Category States",
        "",
        "| State | Count |",
        "|---|---:|",
    ]
    for state in RESULT_STATES:
        lines.append(f"| `{state}` | {payload['status_counts'][state]} |")

    if payload["errors"]:
        lines.extend(["", "## Aggregation Problems", ""])
        lines.extend(f"- {error}" for error in payload["errors"])

    baseline = payload.get("baseline")
    if baseline:
        new_failures = baseline["new_failures"]
        known_failures = baseline["known_failures"]
        recovered = baseline["recovered"]
        if new_failures:
            lines.extend(["", f"## New Failing Categories ({len(new_failures)})", ""])
            lines.append(", ".join(f"`{pattern}`" for pattern in new_failures))
        if known_failures:
            lines.extend(
                ["", f"## Known Failing Categories ({len(known_failures)})", ""]
            )
            lines.append(", ".join(f"`{pattern}`" for pattern in known_failures))
        if recovered:
            lines.extend(
                ["", f"## Baseline Categories That Passed ({len(recovered)})", ""]
            )
            lines.append(", ".join(f"`{pattern}`" for pattern in recovered))

    attention = {
        state: sorted(
            pattern
            for pattern, result in results.items()
            if result.get("state") == state
        )
        for state in RESULT_STATES
        if state != "passed"
    }
    for state, patterns in attention.items():
        if patterns:
            lines.extend(
                ["", f"## {state.replace('_', ' ').title()} ({len(patterns)})", ""]
            )
            lines.append(", ".join(f"`{pattern}`" for pattern in patterns))

    return "\n".join(lines) + "\n"


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f"{path.name}.tmp")
    temporary_path.write_text(content, encoding="utf-8")
    temporary_path.replace(path)


def add_baseline_comparison(payload: dict[str, Any], baseline_path: Path) -> None:
    baseline = {
        line.split("#", 1)[0].strip()
        for line in baseline_path.read_text(encoding="utf-8").splitlines()
        if line.split("#", 1)[0].strip()
    }
    failing = {
        pattern
        for pattern, result in payload["results"].items()
        if result.get("state") in FAILURE_STATES
    }
    payload["baseline"] = {
        "new_failures": sorted(failing - baseline),
        "known_failures": sorted(failing & baseline),
        "recovered": sorted((baseline & set(payload["expected_patterns"])) - failing),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoints", nargs="*", type=Path)
    parser.add_argument("--expected-shards", type=int, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()

    existing_paths = [path for path in args.checkpoints if path.is_file()]
    payload = aggregate_checkpoints(existing_paths, args.expected_shards)
    if args.baseline and args.baseline.is_file():
        add_baseline_comparison(payload, args.baseline)
    write_text_atomic(
        args.json_output,
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
    )
    write_text_atomic(args.markdown_output, render_markdown(payload))

    failed = any(
        result.get("state") in FAILURE_STATES for result in payload["results"].values()
    )
    return 0 if payload["complete"] and not failed else 1


if __name__ == "__main__":
    sys.exit(main())
