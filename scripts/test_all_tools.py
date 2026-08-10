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

CHECKPOINT_SCHEMA_VERSION = 2
RESULT_STATES = (
    "passed",
    "failed",
    "schema_error",
    "no_tests",
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
        return "no_tests"
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
            timeout=300  # 5 minute timeout per pattern
        )
        
        # Parse output to extract statistics
        output = result.stdout
        stats = parse_test_output(output)
        stats["exit_code"] = result.returncode
        stats["raw_output"] = output
        stats["stderr"] = result.stderr
        
        return normalize_result(stats)
        
    except subprocess.TimeoutExpired:
        return normalize_result(
            {
                "error": "Timeout after 5 minutes",
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
        return "TIMEOUT: exceeded 5 minutes"
    if state == "error":
        return f"ERROR: {result.get('error', 'incomplete or invalid test output')}"
    if state == "failed":
        return f"FAILED: {result['failed']} test failure(s)"
    if state == "schema_error":
        return f"SCHEMA ERROR: {result['schema_invalid']} invalid result(s)"
    if state == "no_tests":
        return "NO TESTS: category has no executable examples"
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
        remote_tools = [
            'boltz', 'depmap', 'expert_feedback', 'immune_compass', 
            'pinnacle', 'transcriptformer', 'uspto_downloader',
            # Add external API services that require remote servers
            'blast',  # NCBI BLAST API
            'simbad',  # SIMBAD astronomical database API
            'uspto',  # USPTO Patent API (in addition to uspto_downloader)
        ]
        skip_tools.update(remote_tools)
        print(f"🌐 Skipping remote tools (require external servers): {', '.join(sorted(remote_tools))}")
    
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
    
    if not config_patterns:
        print("❌ No tools remaining after filtering")
        sys.exit(1)
    
    print(f"✅ Found {len(config_patterns)} unique tool patterns to test")
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
        expected_patterns,
        repo_root,
        verbose=args.verbose,
        fail_fast=args.fail_fast,
        parallel=args.parallel,
        initial_results=resumed_results,
        on_result=save_progress,
    )

    total_duration = time.time() - start_time
    checkpoint_complete = set(results) == set(expected_patterns)
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
