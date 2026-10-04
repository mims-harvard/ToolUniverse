#!/usr/bin/env python3
"""
Automatically find and test all tool configurations using test_new_tools.py

This script:
1. Scans src/tooluniverse/data/ for all JSON config files
2. Extracts unique tool name prefixes/patterns
3. Runs test_new_tools.py on each pattern
4. Aggregates results and generates a comprehensive report

Usage:
    python scripts/test_all_tools.py [--verbose] [--fail-fast] [--parallel]
    
Options:
    --verbose       Show detailed output for each test
    --fail-fast     Stop testing after first failure
    --parallel      Run tests in parallel (faster but less readable output)
    --output FILE   Save report to file (default: TOOL_TEST_REPORT.md)
    --json-output   Save atomic JSON progress (default: TOOL_TEST_RESULTS.json)
    --resume        Reuse completed categories when source/config still match
    --skip TOOLS    Skip specific tools (comma-separated, e.g., "agentic,finder,tool")
    --skip-pattern  Skip tools matching pattern (e.g., "agentic*" or "*discovery*")
    --skip-remote   Skip remote tools that require external servers
    --skip-mcp      Skip MCP tools that require MCP servers
"""

import argparse
import concurrent.futures
import fnmatch
import hashlib
import json
import signal
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# run_test_for_pattern spawns an independent subprocess per pattern (I/O-bound:
# mostly waiting on live HTTP calls), so a moderate thread pool speeds up
# --parallel substantially without hammering any single upstream API too hard.
DEFAULT_PARALLEL_WORKERS = 10

# 10 minutes per pattern. 5 was enough only while failures were cheap:
# fda_drug_labeling measured 255.89 s once its impossible examples were
# repaired, 85% of the old budget, so ordinary network variance tipped it
# into TIMEOUT -- which reads as a tool failure. Named once because three
# places reported the number and two of them still said five minutes.
PATTERN_TIMEOUT_SECONDS = 600

CHECKPOINT_SCHEMA_VERSION = 2
RESULT_STATES = (
    "passed",
    "failed",
    "schema_error",
    "no_tests",
    "skipped",
    "timeout",
    "error",
)
FAILURE_STATES = {"failed", "schema_error", "timeout", "error"}


def classify_result(result: Dict[str, Any]) -> str:
    """Return one unambiguous terminal state for a pattern result."""
    if result.get("timed_out"):
        return "timeout"
    if result.get("error"):
        return "error"
    if result.get("failed", 0) > 0:
        return "failed"
    if result.get("schema_invalid", 0) > 0:
        return "schema_error"
    if result.get("exit_code", 0) != 0:
        return "error"
    if result.get("tests_run", 0) == 0:
        # "no examples to run" and "every example needs a credential this
        # runner does not have" are different facts, and reporting the second
        # as the first is how 24 key-gated tools looked like a catalogue with
        # no tests. Neither is a failure.
        return "skipped" if result.get("skipped", 0) > 0 else "no_tests"
    if result.get("passed", 0) < result.get("tests_run", 0):
        return "error"
    return "passed"


def normalize_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Copy a result and attach its canonical state."""
    normalized = dict(result)
    normalized["state"] = classify_result(normalized)
    return normalized


def result_is_failure(result: Dict[str, Any]) -> bool:
    return normalize_result(result)["state"] in FAILURE_STATES


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_sweep_fingerprint(
    repo_root: Path,
    expected_patterns: List[str],
    config_patterns: Dict[str, List[Path]],
) -> str:
    """Hash the local inputs that determine a tool sweep's results."""
    input_paths = {
        repo_root / "pyproject.toml",
        repo_root / "scripts" / "test_all_tools.py",
        repo_root / "scripts" / "test_new_tools.py",
    }
    input_paths.update((repo_root / "src" / "tooluniverse").rglob("*.py"))
    for pattern in expected_patterns:
        input_paths.update(config_patterns.get(pattern, []))

    digest = hashlib.sha256()
    digest.update(
        json.dumps(expected_patterns, separators=(",", ":")).encode("utf-8")
    )
    for path in sorted(input_paths, key=lambda item: item.as_posix()):
        try:
            relative_path = path.relative_to(repo_root)
        except ValueError:
            relative_path = path
        digest.update(b"\0path\0")
        digest.update(relative_path.as_posix().encode("utf-8"))
        digest.update(b"\0content\0")
        if path.is_file():
            digest.update(path.read_bytes())
        else:
            digest.update(b"<missing>")
    return digest.hexdigest()


def write_checkpoint(
    output_path: Path,
    results: Dict[str, Dict[str, Any]],
    expected_patterns: List[str],
    sweep_fingerprint: str,
    started_at: str,
    complete: bool,
) -> None:
    """Atomically persist machine-readable progress after each category."""
    normalized_results = {
        pattern: normalize_result(result) for pattern, result in sorted(results.items())
    }
    status_counts = {state: 0 for state in RESULT_STATES}
    for result in normalized_results.values():
        status_counts[result["state"]] += 1

    payload = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "started_at": started_at,
        "updated_at": _utc_now(),
        "complete": complete,
        "expected_patterns": expected_patterns,
        "sweep_fingerprint": sweep_fingerprint,
        "completed_patterns": len(normalized_results),
        "status_counts": status_counts,
        "results": normalized_results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_name(f"{output_path.name}.tmp")
    temporary_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary_path.replace(output_path)


def load_checkpoint(
    output_path: Path,
    expected_patterns: List[str],
    sweep_fingerprint: str,
) -> Dict[str, Dict[str, Any]]:
    """Load and validate results from a prior machine-readable checkpoint."""
    if not output_path.exists():
        return {}
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != CHECKPOINT_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported checkpoint schema: {payload.get('schema_version')!r}"
        )
    checkpoint_patterns = payload.get("expected_patterns")
    if checkpoint_patterns != expected_patterns:
        raise ValueError(
            "Checkpoint test scope does not match the current selected patterns"
        )
    if payload.get("sweep_fingerprint") != sweep_fingerprint:
        raise ValueError(
            "Checkpoint source/config fingerprint does not match the current tree"
        )
    results = payload.get("results")
    if not isinstance(results, dict):
        raise ValueError("Checkpoint field 'results' must be an object")

    validated = {}
    for pattern, result in results.items():
        if not isinstance(pattern, str) or not isinstance(result, dict):
            raise ValueError("Checkpoint results must map pattern names to objects")
        normalized = normalize_result(result)
        if result.get("state") != normalized["state"]:
            raise ValueError(f"Checkpoint state mismatch for pattern {pattern!r}")
        validated[pattern] = normalized
    return validated


# src/tooluniverse/remote/<slug>/ is a provider that needs its own server, so
# --skip-remote has to drop it. This used to be a hardcoded list of ten names
# and it drifted: 30 provider directories existed and 24 of them -- borzoi,
# celltypist, monocle3, scvi and the rest -- were still being tested. The tools
# are not loaded without their server, so each one failed with "Tool 'X' not
# found even after loading tools" and the weekly report counted 22 categories
# of phantom failures. Derived from the filesystem so it cannot drift again.
_EXTERNAL_SERVICE_PATTERNS = (
    "blast",  # NCBI BLAST API: submits a job to a queue, not a request/response
    "simbad",  # SIMBAD astronomical database API
    "uspto",  # USPTO Patent API, and uspto_downloader with it
    "depmap",  # the pattern name; the provider directory is depmap_24q2
)


def remote_tool_patterns() -> set:
    """Pattern names --skip-remote must drop: provider dirs plus the services."""
    patterns = set(_EXTERNAL_SERVICE_PATTERNS)
    remote_root = (
        Path(__file__).resolve().parents[1] / "src" / "tooluniverse" / "remote"
    )
    if remote_root.is_dir():
        patterns.update(
            entry.name
            for entry in remote_root.iterdir()
            if entry.is_dir() and not entry.name.startswith(("_", "."))
        )
    return patterns


def find_all_tool_configs(data_dir: Path) -> List[Path]:
    """Find all JSON configuration files."""
    json_files = list(data_dir.glob("*.json"))
    json_files.extend(data_dir.glob("**/*.json"))

    # Remove duplicates and sort
    json_files = sorted(set(json_files))

    # Filter out non-tool files if needed
    json_files = [f for f in json_files if not f.name.startswith('.')]

    # Skip broken_apis/ — those configs document non-functional upstream APIs
    # and the tools are not registered at runtime, so testing them produces
    # only false-positive "Tool not found" failures.
    json_files = [f for f in json_files if "broken_apis" not in f.parts]

    return json_files


def extract_tool_patterns(config_files: List[Path]) -> Dict[str, List[Path]]:
    """Extract tool name patterns from config files.
    
    Groups files by their base name pattern (e.g., 'fda', 'ncbi', 'cbioportal')
    """
    patterns = defaultdict(list)
    
    for config_file in config_files:
        # Get base name without extension
        base_name = config_file.stem
        
        # Extract pattern (typically the prefix before _tools).
        if '_tools' in base_name:
            pattern = base_name.replace('_tools', '')
        else:
            # Use the full stem for non-_tools files. Splitting on the first
            # underscore produced over-broad patterns: e.g. tool_page_index.json
            # and tool_discovery_agents.json both yielded "tool", and downstream
            # test_new_tools.py globs *tool* — which matches every *_tools.json
            # (500+ files) and times that "category" out on every run.
            pattern = base_name
        
        patterns[pattern].append(config_file)
    
    return patterns


def load_config_stats(config_file: Path) -> Dict[str, Any]:
    """Load basic statistics from a config file."""
    try:
        with open(config_file, 'r') as f:
            content = json.load(f)
        
        if isinstance(content, list):
            tools = content
        elif isinstance(content, dict):
            tools = [content]
        else:
            return {"error": "Invalid format"}
        
        tool_count = len(tools)
        example_count = sum(len(t.get("test_examples", [])) for t in tools)
        
        return {
            "tool_count": tool_count,
            "example_count": example_count,
            "tools": [t.get("name", "UNNAMED") for t in tools]
        }
    except Exception as e:
        return {"error": str(e)}


def run_test_for_pattern(
    pattern: str, 
    repo_root: Path, 
    verbose: bool = False,
    fail_fast: bool = False
) -> Dict[str, Any]:
    """Run test_new_tools.py for a specific pattern."""
    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "test_new_tools.py"),
        pattern
    ]
    
    if verbose:
        cmd.append("-v")
    if fail_fast:
        cmd.append("--fail-fast")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=repo_root,
            # 10 minutes per pattern. 5 was enough only while failures were
            # cheap: fda_drug_labeling's 156 tests fit inside 300 s because 27
            # of them died instantly on a NOT_FOUND from an impossible example
            # query. With those examples repaired the tests fetch real label
            # sections, and the category measured 255.89 s -- 85% of the old
            # budget -- so normal network variance tipped it into TIMEOUT,
            # which reads as a tool failure and is worse signal than before.
            timeout=PATTERN_TIMEOUT_SECONDS,
        )
        
        # Parse output to extract statistics
        output = result.stdout
        stats = parse_test_output(output)
        stats["exit_code"] = result.returncode
        stats["raw_output"] = output
        stats["stderr"] = result.stderr

        # A negative return code is a signal, and a runner reports that as
        # "incomplete or invalid test output" because the process died before
        # printing its summary. The xml category was killed by the OOM killer
        # on every sweep -- 120 GB of RSS, exit 137 -- and the report said only
        # that its output was unparseable, which reads like a formatting bug.
        if result.returncode is not None and result.returncode < 0:
            signal_number = -result.returncode
            name = signal.Signals(signal_number).name if signal_number in {
                member.value for member in signal.Signals
            } else f"signal {signal_number}"
            hint = (
                " The usual cause is the OOM killer; check the category's "
                "memory use before reading this as a test failure."
                if signal_number == signal.SIGKILL
                else ""
            )
            stats["error"] = f"Killed by {name}.{hint}"

        return normalize_result(stats)

    except subprocess.TimeoutExpired:
        return normalize_result(
            {
                "error": f"Timeout after {PATTERN_TIMEOUT_SECONDS // 60} minutes",
                "timed_out": True,
                "exit_code": -1,
            }
        )
    except Exception as e:
        return normalize_result({"error": str(e), "exit_code": -1})


def _format_result_status(result: Dict[str, Any]) -> str:
    """One-line human-readable status for a single pattern's test result."""
    state = normalize_result(result)["state"]
    if state == "timeout":
        return f"TIMEOUT: exceeded {PATTERN_TIMEOUT_SECONDS // 60} minutes"
    if state == "error":
        return f"ERROR: {result.get('error', 'incomplete or invalid test output')}"
    if state == "failed":
        return f"FAILED: {result['failed']} test failure(s)"
    if state == "schema_error":
        return f"SCHEMA ERROR: {result['schema_invalid']} invalid result(s)"
    if state == "no_tests":
        return "NO TESTS: category has no executable examples"
    if state == "skipped":
        skipped = result.get("skipped", 0)
        reasons = []
        local_input = result.get("skipped_local_input", 0)
        long_running = result.get("skipped_long_running", 0)
        if local_input:
            reasons.append(f"{local_input} need an input file the caller supplies")
        if long_running:
            reasons.append(f"{long_running} poll an upstream job for longer than "
                           "this budget")
        credential = skipped - local_input - long_running
        if credential > 0:
            reasons.append(
                f"{credential} need a credential this run does not have"
            )
        if len(reasons) == 1:
            return f"SKIPPED: {skipped} tool(s) {reasons[0].split(' ', 1)[1]}"
        return f"SKIPPED: {skipped} tool(s) -- " + ", ".join(reasons)
    return f"PASSED: {result.get('tests_run', 0)} test(s)"


def run_all_patterns(
    patterns: List[str],
    repo_root: Path,
    verbose: bool = False,
    fail_fast: bool = False,
    parallel: bool = False,
    max_workers: int = DEFAULT_PARALLEL_WORKERS,
    initial_results: Optional[Dict[str, Dict[str, Any]]] = None,
    on_result: Optional[Callable[[str, Dict[str, Dict[str, Any]]], None]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Run run_test_for_pattern for every pattern, sequentially or in parallel.

    Returns a dict of pattern -> result, in the same shape either way.
    Progress is printed as each result becomes available; in parallel mode
    that's completion order, not pattern order, since patterns run
    concurrently.

    --fail-fast semantics under --parallel: patterns already running when a
    failure is detected are allowed to finish (they're independent
    subprocesses already in flight), but no further not-yet-started patterns
    are submitted. This is the closest parallel analogue to the sequential
    "stop after first failure" behavior.
    """
    total = len(patterns)
    results = {
        pattern: normalize_result(result)
        for pattern, result in (initial_results or {}).items()
    }
    pending_patterns = [pattern for pattern in patterns if pattern not in results]

    if not parallel:
        for pattern in pending_patterns:
            i = len(results) + 1
            print(f"[{i}/{total}] Testing {pattern}...", end=" ", flush=True)
            result = normalize_result(
                run_test_for_pattern(
                    pattern, repo_root, verbose=verbose, fail_fast=fail_fast
                )
            )
            results[pattern] = result
            if on_result:
                on_result(pattern, results)
            print(_format_result_status(result))
            if fail_fast and result_is_failure(result):
                print("\n⚠️  Stopping due to --fail-fast")
                break
        return results

    workers = max(1, min(max_workers, len(pending_patterns))) if pending_patterns else 1
    print(
        f"⚡ Running {len(pending_patterns)} pending pattern(s) in parallel "
        f"(workers={workers}, total={total})"
    )
    print()

    stop_requested = False
    completed = len(results)
    if not pending_patterns:
        return results
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_pattern = {
            executor.submit(
                run_test_for_pattern, pattern, repo_root, verbose, fail_fast
            ): pattern
            for pattern in pending_patterns
        }
        for future in concurrent.futures.as_completed(future_to_pattern):
            pattern = future_to_pattern[future]
            if future.cancelled():
                # Cancelled while still queued (fail-fast) -- never ran, so
                # it's simply omitted from results rather than recorded as
                # a failure.
                continue
            completed += 1
            result = normalize_result(future.result())
            results[pattern] = result
            if on_result:
                on_result(pattern, results)
            print(f"[{completed}/{total}] {pattern}: {_format_result_status(result)}", flush=True)

            if fail_fast and result_is_failure(result) and not stop_requested:
                stop_requested = True
                print("\n⚠️  --fail-fast: not starting any remaining not-yet-started patterns "
                      "(already-running patterns will still finish)")
                for f in future_to_pattern:
                    f.cancel()

    return results


# Signals that a category's failures came from load rather than from the tool.
#
# The 2026-10-03 sweep ran 10 workers against live APIs and reported 90
# non-passing categories. Roughly 120 of the individual test failures were
# self-inflicted: ensembl_sequence failed twice in the parallel sweep and
# passed 4/4 run alone, and enrichr failed with "'str' object has no attribute"
# in parallel and passed alone. That error reads exactly like a code defect,
# which is the problem -- the report could not tell "this tool is broken" from
# "we overloaded its upstream", so a third of its contents had to be re-checked
# by hand before any of it could be trusted.
_CONTENTION_MARKERS = (
    "429",
    "too many requests",
    "rate limit",
    "500",
    "502",
    "503",
    "504",
    "internal server error",
    "service unavailable",
    "bad gateway",
    "timed out",
    "timeout",
    "connection reset",
    "connection aborted",
    "remote end closed",
    "response ended prematurely",
    # Ensembl answers a throttled request with no usable status, and the tool
    # surfaces that as "HTTP error: unknown".
    "http error: unknown",
)


def looks_contended(result: Dict[str, Any]) -> bool:
    """True when a non-passing result's messages all point at load.

    Only the failure lines are read. A category that also reports a schema
    mismatch or a 404 is left alone: re-running it serially would cost minutes
    and change nothing.
    """
    if not result_is_failure(result):
        return False
    if normalize_result(result)["state"] == "timeout":
        return True

    output = result.get("raw_output") or ""
    messages = [
        line.lower()
        for line in output.splitlines()
        if "\u274c" in line or "Failed -" in line
    ]
    if not messages:
        # No per-test message at all: the subprocess died before printing one,
        # which a serial re-run can distinguish from a tool defect.
        return bool(result.get("error"))
    # One contended-looking failure is enough. Requiring all of them meant a
    # category with 28 load failures and one real defect never got re-run, so
    # its 28 lines of noise stayed in the report next to the one line worth
    # reading. A re-run costs one serial subprocess and says which it was.
    return any(
        marker in message
        for message in messages
        for marker in _CONTENTION_MARKERS
    )


def retry_contended_patterns(
    results: Dict[str, Dict[str, Any]],
    repo_root: Path,
    verbose: bool = False,
    on_result: Optional[Callable[[str, Dict[str, Dict[str, Any]]], None]] = None,
) -> Dict[str, str]:
    """Re-run load-shaped failures one at a time; keep the better result.

    Returns pattern -> "state before -> state after" for the ones that changed.
    """
    candidates = [
        pattern
        for pattern, result in sorted(results.items())
        if looks_contended(result)
    ]
    if not candidates:
        return {}

    print()
    print(
        f"🔁 Re-running {len(candidates)} category/categories serially: their "
        "failures all look like upstream load, which the parallel pass causes"
    )
    changed: Dict[str, str] = {}
    for index, pattern in enumerate(candidates, start=1):
        before = normalize_result(results[pattern])["state"]
        retried = normalize_result(
            run_test_for_pattern(pattern, repo_root, verbose=verbose)
        )
        after = retried["state"]
        # Only a pass replaces the original. "not a failure any more" was too
        # loose: a serial re-run that reports no_tests or skipped would then
        # overwrite a real failure with an absence, which is worse signal than
        # the failure was. A category that fails serially too keeps the
        # evidence it first produced.
        if after == "passed" or (
            after == "skipped" and before in {"failed", "schema_error"}
        ):
            retried["retried_serially"] = True
            results[pattern] = retried
            changed[pattern] = f"{before} -> {after}"
            verdict = f"{after} (was {before} under load)"
        else:
            results[pattern].setdefault("retried_serially", True)
            verdict = f"still {after}"
        if on_result:
            on_result(pattern, results)
        print(f"   [{index}/{len(candidates)}] {pattern}: {verdict}", flush=True)
    return changed


# Maps a label found in test output to the stats key it populates.
# All values are parsed as int except "Duration" which is float.
_OUTPUT_LABELS: List[Tuple[str, str]] = [
    ("Tools Tested:", "tools_tested"),
    ("Tests Run:", "tests_run"),
    ("Passed:", "passed"),
    ("Failed:", "failed"),
    ("404 Errors:", "errors_404"),
    ("Other Errors:", "errors_other"),
    ("Schema Valid:", "schema_valid"),
    ("Schema Invalid:", "schema_invalid"),
    # Parsed so a category whose every tool was skipped for a missing
    # credential can be told apart from one that ships no examples.
    ("Skipped:", "skipped"),
    ("Skipped local input:", "skipped_local_input"),
    ("Skipped long running:", "skipped_long_running"),
]


def parse_test_output(output: str) -> Dict[str, Any]:
    """Parse test output to extract statistics."""
    stats: Dict[str, Any] = {key: 0 for _, key in _OUTPUT_LABELS}
    stats["duration"] = 0.0

    for line in output.split('\n'):
        line = line.strip()

        for label, key in _OUTPUT_LABELS:
            if label in line:
                try:
                    # Take the first token after the colon (handles "Passed: 12 (100.0%)")
                    stats[key] = int(line.split(':')[1].strip().split()[0])
                except (ValueError, IndexError):
                    pass
                break
        else:
            # Duration is a float with a trailing 's'
            if "Duration:" in line:
                try:
                    stats["duration"] = float(line.split(':')[1].strip().rstrip('s'))
                except (ValueError, IndexError):
                    pass

    return stats


def generate_report(
    results: Dict[str, Dict[str, Any]],
    config_patterns: Dict[str, List[Path]],
    total_duration: float,
    output_file: str = "TOOL_TEST_REPORT.md",
    skipped_tools: set = None
) -> str:
    """Generate a markdown report of all test results."""
    if skipped_tools is None:
        skipped_tools = set()
    
    # Calculate totals
    total_tools = sum(r.get("tools_tested", 0) for r in results.values())
    total_tests = sum(r.get("tests_run", 0) for r in results.values())
    total_passed = sum(r.get("passed", 0) for r in results.values())
    total_failed = sum(r.get("failed", 0) for r in results.values())
    total_404 = sum(r.get("errors_404", 0) for r in results.values())
    total_other_errors = sum(r.get("errors_other", 0) for r in results.values())
    total_schema_valid = sum(r.get("schema_valid", 0) for r in results.values())
    total_schema_invalid = sum(r.get("schema_invalid", 0) for r in results.values())
    normalized_results = {
        pattern: normalize_result(result) for pattern, result in results.items()
    }
    state_counts = {state: 0 for state in RESULT_STATES}
    for result in normalized_results.values():
        state_counts[result["state"]] += 1
    
    pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    lines = []
    lines.append("# ToolUniverse - Comprehensive Tool Test Report")
    lines.append("")
    lines.append(f"**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Total Duration**: {total_duration:.2f}s")
    
    if skipped_tools:
        skipped_list = ", ".join(sorted(skipped_tools))
        lines.append(f"**Skipped**: {len(skipped_tools)} tool(s) - {skipped_list}")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(f"- **Tool Categories Tested**: {len(results)}")
    lines.append(f"- **Total Tools**: {total_tools}")
    lines.append(f"- **Total Test Examples**: {total_tests}")
    lines.append(f"- **Pass Rate**: {pass_rate:.1f}%")
    lines.append("")
    lines.append("### Overall Statistics")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("|--------|-------|")
    lines.append(f"| ✅ Passed | {total_passed} ({pass_rate:.1f}%) |")
    lines.append(f"| ❌ Failed | {total_failed} |")
    lines.append(f"| 🔍 404 Errors | {total_404} |")
    lines.append(f"| ⚠️  Other Errors | {total_other_errors} |")
    lines.append(f"| ✓ Schema Valid | {total_schema_valid} |")
    lines.append(f"| ✗ Schema Invalid | {total_schema_invalid} |")
    for state in RESULT_STATES:
        lines.append(f"| Categories: {state} | {state_counts[state]} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Results by Tool Category")
    lines.append("")
    
    # Sort by category name
    for pattern in sorted(results.keys()):
        result = normalized_results[pattern]
        config_files = config_patterns.get(pattern, [])
        
        state = result["state"]
        lines.append(f"### {state.upper()} - {pattern}")
        lines.append("")
        lines.append(f"**Config Files**: {', '.join(f.name for f in config_files)}")
        lines.append(f"**Status**: {state}")
        lines.append("")
        
        if result.get("error"):
            lines.append(f"**Error**: {result['error']}")
            lines.append("")
        else:
            tools_tested = result.get("tools_tested", 0)
            tests_run = result.get("tests_run", 0)
            passed = result.get("passed", 0)
            failed = result.get("failed", 0)
            
            pattern_pass_rate = (passed / tests_run * 100) if tests_run > 0 else 0
            
            lines.append("| Metric | Value |")
            lines.append("|--------|-------|")
            lines.append(f"| Tools | {tools_tested} |")
            lines.append(f"| Tests | {tests_run} |")
            lines.append(f"| Passed | {passed} ({pattern_pass_rate:.1f}%) |")
            lines.append(f"| Failed | {failed} |")
            
            if result.get("errors_404", 0) > 0:
                lines.append(f"| 404 Errors | {result['errors_404']} |")
            if result.get("errors_other", 0) > 0:
                lines.append(f"| Other Errors | {result['errors_other']} |")
            
            lines.append(f"| Schema Valid | {result.get('schema_valid', 0)} |")
            lines.append(f"| Schema Invalid | {result.get('schema_invalid', 0)} |")
            lines.append(f"| Duration | {result.get('duration', 0):.2f}s |")
            lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append("## Issues Requiring Attention")
    lines.append("")
    
    # List failures
    issues_found = False

    patterns_without_tests = [
        pattern
        for pattern, result in normalized_results.items()
        if result["state"] == "no_tests"
    ]
    if patterns_without_tests:
        issues_found = True
        lines.append("### Categories Without Executable Tests")
        lines.append("")
        for pattern in sorted(patterns_without_tests):
            lines.append(f"- **{pattern}**")
        lines.append("")

    patterns_with_runtime_errors = [
        pattern
        for pattern, result in normalized_results.items()
        if result["state"] in {"timeout", "error"}
    ]
    if patterns_with_runtime_errors:
        issues_found = True
        lines.append("### Incomplete Category Runs")
        lines.append("")
        for pattern in sorted(patterns_with_runtime_errors):
            result = normalized_results[pattern]
            detail = result.get("error", result["state"])
            lines.append(f"- **{pattern}** ({result['state']}): {detail}")
        lines.append("")
    
    # 404 Errors
    patterns_with_404 = [p for p, r in results.items() if r.get("errors_404", 0) > 0]
    if patterns_with_404:
        issues_found = True
        lines.append("### 🔍 404 Errors Detected")
        lines.append("")
        lines.append("These tools are returning 404 errors (API endpoints may have changed):")
        lines.append("")
        for pattern in sorted(patterns_with_404):
            count = results[pattern]["errors_404"]
            lines.append(f"- **{pattern}**: {count} 404 error(s)")
        lines.append("")
    
    # Schema Mismatches
    patterns_with_schema_issues = [
        p for p, r in results.items() 
        if r.get("schema_invalid", 0) > 0
    ]
    if patterns_with_schema_issues:
        issues_found = True
        lines.append("### ⚠️  Schema Validation Issues")
        lines.append("")
        lines.append("These tools have schema mismatches:")
        lines.append("")
        for pattern in sorted(patterns_with_schema_issues):
            count = results[pattern]["schema_invalid"]
            lines.append(f"- **{pattern}**: {count} schema mismatch(es)")
        lines.append("")
    
    # Other Failures
    patterns_with_failures = [
        p for p, r in results.items() 
        if r.get("failed", 0) > 0 and not r.get("errors_404", 0)
    ]
    if patterns_with_failures:
        issues_found = True
        lines.append("### ❌ Other Failures")
        lines.append("")
        lines.append("These tools have other failures:")
        lines.append("")
        for pattern in sorted(patterns_with_failures):
            count = results[pattern]["failed"]
            lines.append(f"- **{pattern}**: {count} failure(s)")
        lines.append("")
    
    if not issues_found:
        lines.append("✨ **No issues found!** All tools are working correctly.")
        lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append("## Next Steps")
    lines.append("")
    
    if patterns_with_404:
        lines.append("1. **Fix 404 Errors**: Review API documentation for tools with 404 errors")
        lines.append("   - Check if API endpoints have changed")
        lines.append("   - Update tool configurations accordingly")
        lines.append("")
    
    if patterns_with_schema_issues:
        lines.append("2. **Fix Schema Mismatches**: Update return_schema definitions")
        lines.append("   - Review actual API responses")
        lines.append("   - Update JSON schemas to match current API")
        lines.append("")
    
    if patterns_with_failures:
        lines.append("3. **Investigate Failures**: Review error messages and fix issues")
        lines.append("   - Check API keys and authentication")
        lines.append("   - Verify network connectivity")
        lines.append("   - Review error messages in detail")
        lines.append("")
    
    if not issues_found:
        lines.append("✅ All tools validated successfully! No action needed.")
        lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append(f"**Report Generated**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("**Command**: `python scripts/test_all_tools.py`")
    
    report = "\n".join(lines)
    
    # Write to file
    repo_root = Path(__file__).parent.parent
    output_path = repo_root / output_file
    with open(output_path, 'w') as f:
        f.write(report)
    
    return str(output_path)


def select_shard(patterns, spec):
    """Return the slice of `patterns` belonging to shard `spec` ("I/N").

    Strided, not contiguous: consecutive patterns often share an upstream host,
    so a contiguous block would concentrate one API's outage in one shard and
    leave the others looking healthy. Striding also keeps every shard's slice
    stable as long as the pattern list is sorted.

    Raises ValueError on a malformed or out-of-range spec.
    """
    try:
        index_str, count_str = str(spec).split("/", 1)
        shard_index, shard_count = int(index_str), int(count_str)
    except ValueError:
        raise ValueError(f"--shard must look like I/N, got {spec!r}") from None
    if shard_count < 1 or not (0 <= shard_index < shard_count):
        raise ValueError(f"--shard out of range: {spec!r}")
    return sorted(patterns)[shard_index::shard_count], shard_index, shard_count


def main():
    parser = argparse.ArgumentParser(
        description="Test all ToolUniverse tool configurations"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed output"
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop after first failure"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help=f"Run tests in parallel across patterns (up to {DEFAULT_PARALLEL_WORKERS} workers)"
    )
    parser.add_argument(
        "--no-retry",
        action="store_true",
        help=(
            "Do not re-run load-shaped failures serially after a --parallel "
            "pass. The retry exists because 10 workers against live APIs "
            "produce 429s and timeouts that read exactly like tool defects"
        ),
    )
    parser.add_argument(
        "--output",
        default="TOOL_TEST_REPORT.md",
        help="Output report filename"
    )
    parser.add_argument(
        "--json-output",
        default="TOOL_TEST_RESULTS.json",
        help="Machine-readable checkpoint filename",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse completed categories when source/config still match --json-output",
    )
    parser.add_argument(
        "--pattern",
        help="Test only specific pattern (e.g., 'fda', 'cbioportal')"
    )
    parser.add_argument(
        "--skip",
        help="Skip specific tools (comma-separated, e.g., 'agentic,finder,tool')"
    )
    parser.add_argument(
        "--skip-pattern",
        help="Skip tools matching wildcard pattern (e.g., 'agentic*' or '*discovery*')"
    )
    parser.add_argument(
        "--shard",
        help=(
            "Run only one slice of the patterns, as I/N (e.g. '0/8'). Patterns are "
            "sorted then strided, so slices are stable across runs and each covers "
            "the whole alphabet rather than one contiguous block."
        ),
    )
    parser.add_argument(
        "--skip-remote",
        action="store_true",
        help="Skip remote tools that require external servers"
    )
    parser.add_argument(
        "--skip-mcp",
        action="store_true",
        help="Skip MCP (Model Context Protocol) tools that require MCP servers"
    )
    
    args = parser.parse_args()
    
    # Setup paths
    repo_root = Path(__file__).parent.parent
    data_dir = repo_root / "src" / "tooluniverse" / "data"
    
    if not data_dir.exists():
        print(f"❌ Error: Data directory not found at {data_dir}")
        sys.exit(1)
    
    print("=" * 70)
    print("ToolUniverse - Comprehensive Tool Testing")
    print("=" * 70)
    print()
    
    # Find all config files
    print("🔍 Scanning for tool configurations...")
    config_files = find_all_tool_configs(data_dir)
    print(f"✅ Found {len(config_files)} configuration files")
    
    # Extract patterns
    print("📊 Analyzing tool patterns...")
    config_patterns = extract_tool_patterns(config_files)
    
    # Build skip list
    skip_tools = set()
    if args.skip:
        skip_tools.update(tool.strip() for tool in args.skip.split(','))
        print(f"📝 Skipping tools: {', '.join(sorted(skip_tools))}")
    
    # Skip remote tools if requested
    if args.skip_remote:
        skip_tools.update(remote_tool_patterns())
        print(
            "🌐 Skipping remote tools (require external servers): "
            f"{len(remote_tool_patterns())} pattern(s)"
        )
    
    # Skip MCP tools if requested
    if args.skip_mcp:
        mcp_tools = ['boltz_mcp_loader', 'mcp_client_example', 'mcpautoloadertool']
        skip_tools.update(mcp_tools)
        print(f"🔌 Skipping MCP tools (require MCP servers): {', '.join(sorted(mcp_tools))}")
    
    # Apply skip pattern
    if args.skip_pattern:
        pattern_to_skip = args.skip_pattern.strip()
        tools_to_skip = [
            tool for tool in config_patterns.keys()
            if fnmatch.fnmatch(tool, pattern_to_skip)
        ]
        skip_tools.update(tools_to_skip)
        if tools_to_skip:
            print(f"📝 Skipping tools matching '{pattern_to_skip}': {', '.join(sorted(tools_to_skip))}")
    
    # Filter by pattern if specified
    if args.pattern:
        filtered = {
            k: v for k, v in config_patterns.items() 
            if args.pattern.lower() in k.lower()
        }
        if not filtered:
            print(f"❌ No patterns found matching '{args.pattern}'")
            sys.exit(1)
        config_patterns = filtered
        print(f"✅ Filtered to {len(config_patterns)} pattern(s) matching '{args.pattern}'")
    
    # Apply skip list
    if skip_tools:
        before_count = len(config_patterns)
        config_patterns = {
            k: v for k, v in config_patterns.items()
            if k not in skip_tools
        }
        skipped_count = before_count - len(config_patterns)
        if skipped_count > 0:
            print(f"⏭️  Skipped {skipped_count} tool(s)")
        if before_count and not config_patterns:
            # Everything asked for was on the skip list. Nothing failed, so
            # exiting non-zero would report a deliberate exclusion as a
            # problem -- `--pattern borzoi --skip-remote` is a reasonable thing
            # to type and the answer is "that one needs its own server".
            print(
                f"⏭️  Every pattern matched was on the skip list "
                f"({skipped_count} skipped); nothing to test"
            )
            sys.exit(0)

    if not config_patterns:
        print("❌ No tools remaining after filtering")
        sys.exit(1)
    
    # Sharding. The weekly sweep is one long job, and losing the runner discards
    # everything it had done -- 10 of 12 consecutive weekly runs ended that way,
    # one of them after 636 of 638 categories. Splitting the sweep across jobs
    # bounds both the blast radius of an eviction and the memory a single job
    # holds.
    selected = sorted(config_patterns.keys())
    if args.shard:
        try:
            selected, shard_index, shard_count = select_shard(selected, args.shard)
        except ValueError as exc:
            print(f"❌ {exc}")
            sys.exit(2)
        print(f"🔀 Shard {shard_index + 1}/{shard_count}: {len(selected)} of "
              f"{len(config_patterns)} patterns")

    print(f"✅ Found {len(selected)} unique tool patterns to test")
    print()
    print("🧪 Running tests...")
    print()
    
    # Run tests for each pattern
    start_time = time.time()
    started_at = _utc_now()
    expected_patterns = sorted(config_patterns.keys())
    sweep_fingerprint = compute_sweep_fingerprint(
        repo_root, expected_patterns, config_patterns
    )
    checkpoint_path = Path(args.json_output)
    if not checkpoint_path.is_absolute():
        checkpoint_path = repo_root / checkpoint_path

    resumed_results: Dict[str, Dict[str, Any]] = {}
    if args.resume:
        try:
            checkpoint_results = load_checkpoint(
                checkpoint_path, expected_patterns, sweep_fingerprint
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"❌ Cannot resume from {checkpoint_path}: {exc}")
            sys.exit(1)
        resumed_results = {
            pattern: result
            for pattern, result in checkpoint_results.items()
            if pattern in config_patterns
        }
        print(f"Resuming with {len(resumed_results)} completed pattern(s)")

    write_checkpoint(
        checkpoint_path,
        resumed_results,
        expected_patterns,
        sweep_fingerprint,
        started_at,
        complete=False,
    )

    def save_progress(
        _pattern: str, current_results: Dict[str, Dict[str, Any]]
    ) -> None:
        write_checkpoint(
            checkpoint_path,
            current_results,
            expected_patterns,
            sweep_fingerprint,
            started_at,
            complete=False,
        )

    results = run_all_patterns(
        selected,
        repo_root,
        verbose=args.verbose,
        fail_fast=args.fail_fast,
        parallel=args.parallel,
        initial_results=resumed_results,
        on_result=save_progress,
    )

    # A category that only fails under load is not a broken tool, and the
    # report cannot tell the difference from the parallel pass alone.
    retried = {}
    if args.parallel and not args.no_retry:
        retried = retry_contended_patterns(
            results, repo_root, verbose=args.verbose, on_result=save_progress
        )
        if retried:
            print()
            print(
                f"🔁 {len(retried)} category/categories passed on their own, so "
                "the parallel pass was the cause:"
            )
            for pattern, transition in sorted(retried.items()):
                print(f"   {pattern}: {transition}")

    total_duration = time.time() - start_time
    # Completeness is judged against `selected` (this invocation's assigned
    # scope), not `expected_patterns` (the full unsharded universe): under
    # --shard, results only ever cover this shard's slice, and comparing
    # against the full set would report every successful shard as incomplete.
    # The two are identical when --shard is not used.
    checkpoint_complete = set(results) == set(selected)
    write_checkpoint(
        checkpoint_path,
        results,
        expected_patterns,
        sweep_fingerprint,
        started_at,
        complete=checkpoint_complete,
    )
    
    print()
    print("=" * 70)
    print("Generating report...")
    
    # Generate report
    report_path = generate_report(
        results, 
        config_patterns, 
        total_duration,
        args.output,
        skip_tools
    )
    
    print(f"✅ Report saved to: {report_path}")
    print(f"✅ JSON checkpoint saved to: {checkpoint_path}")
    print()
    
    # Print summary
    total_tests = sum(r.get("tests_run", 0) for r in results.values())
    total_passed = sum(r.get("passed", 0) for r in results.values())
    total_failed = sum(r.get("failed", 0) for r in results.values())
    normalized_results = [normalize_result(result) for result in results.values()]
    state_counts = {state: 0 for state in RESULT_STATES}
    for result in normalized_results:
        state_counts[result["state"]] += 1
    
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Patterns Tested:  {len(results)}")
    print(f"Total Tests:      {total_tests}")
    print(f"Passed:           {total_passed}")
    print(f"Failed:           {total_failed}")
    print(
        "Category states:  "
        + ", ".join(f"{state}={state_counts[state]}" for state in RESULT_STATES)
    )
    print(f"Duration:         {total_duration:.2f}s")
    if skip_tools:
        print(f"Skipped:          {len(skip_tools)} tool(s)")
    print("=" * 70)
    
    # Runtime, assertion, and schema failures are unsuccessful. A no-test
    # category is reported as a coverage gap without turning a health canary
    # into a runtime failure.
    failed_categories = [
        result for result in normalized_results if result["state"] in FAILURE_STATES
    ]
    if failed_categories or not checkpoint_complete:
        sys.exit(1)
    if state_counts["no_tests"]:
        print("\nSweep completed with categories that have no executable tests.")
    else:
        print("\n✨ All tests passed!")
    sys.exit(0)


if __name__ == "__main__":
    main()
