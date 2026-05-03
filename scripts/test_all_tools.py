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
    --skip TOOLS    Skip specific tools (comma-separated, e.g., "agentic,finder,tool")
    --skip-pattern  Skip tools matching pattern (e.g., "agentic*" or "*discovery*")
    --skip-remote   Skip remote tools that require external servers
    --skip-mcp      Skip MCP tools that require MCP servers
"""

import argparse
import fnmatch
import json
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Any


def find_all_tool_configs(data_dir: Path) -> List[Path]:
    """Find all JSON configuration files."""
    json_files = list(data_dir.glob("*.json"))
    json_files.extend(data_dir.glob("**/*.json"))
    
    # Remove duplicates and sort
    json_files = sorted(set(json_files))
    
    # Filter out non-tool files if needed
    json_files = [f for f in json_files if not f.name.startswith('.')]
    
    return json_files


def extract_tool_patterns(config_files: List[Path]) -> Dict[str, List[Path]]:
    """Extract tool name patterns from config files.
    
    Groups files by their base name pattern (e.g., 'fda', 'ncbi', 'cbioportal')
    """
    patterns = defaultdict(list)
    
    for config_file in config_files:
        # Get base name without extension
        base_name = config_file.stem
        
        # Extract pattern (typically prefix before _tools or first underscore)
        if '_tools' in base_name:
            pattern = base_name.replace('_tools', '')
        elif '_' in base_name:
            pattern = base_name.split('_')[0]
        else:
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
        
        return stats
        
    except subprocess.TimeoutExpired:
        return {
            "error": "Timeout after 5 minutes",
            "exit_code": -1
        }
    except Exception as e:
        return {
            "error": str(e),
            "exit_code": -1
        }


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
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Results by Tool Category")
    lines.append("")
    
    # Sort by category name
    for pattern in sorted(results.keys()):
        result = results[pattern]
        config_files = config_patterns.get(pattern, [])
        
        # Determine status emoji
        if result.get("error"):
            status = "🔥"
        elif result.get("failed", 0) > 0:
            status = "❌"
        elif result.get("schema_invalid", 0) > 0:
            status = "⚠️"
        else:
            status = "✅"
        
        lines.append(f"### {status} {pattern}")
        lines.append("")
        lines.append(f"**Config Files**: {', '.join(f.name for f in config_files)}")
        lines.append("")
        
        if result.get("error"):
            lines.append(f"**Status**: ERROR")
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
        help="Run tests in parallel (experimental)"
    )
    parser.add_argument(
        "--output",
        default="TOOL_TEST_REPORT.md",
        help="Output report filename"
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
    results = {}
    start_time = time.time()
    
    for i, pattern in enumerate(sorted(config_patterns.keys()), 1):
        print(f"[{i}/{len(config_patterns)}] Testing {pattern}...", end=" ", flush=True)
        
        result = run_test_for_pattern(
            pattern, 
            repo_root, 
            verbose=args.verbose,
            fail_fast=args.fail_fast
        )
        
        results[pattern] = result
        
        # Print quick status
        if result.get("error"):
            print(f"🔥 ERROR: {result['error']}")
        elif result.get("failed", 0) > 0:
            print(f"❌ {result['failed']} failures")
            if args.fail_fast:
                print("\n⚠️  Stopping due to --fail-fast")
                break
        elif result.get("schema_invalid", 0) > 0:
            print(f"⚠️  {result['schema_invalid']} schema issues")
        else:
            tests = result.get("tests_run", 0)
            print(f"✅ {tests} tests passed")
    
    total_duration = time.time() - start_time
    
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
    print()
    
    # Print summary
    total_tests = sum(r.get("tests_run", 0) for r in results.values())
    total_passed = sum(r.get("passed", 0) for r in results.values())
    total_failed = sum(r.get("failed", 0) for r in results.values())
    
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Patterns Tested:  {len(results)}")
    print(f"Total Tests:      {total_tests}")
    print(f"Passed:           {total_passed}")
    print(f"Failed:           {total_failed}")
    print(f"Duration:         {total_duration:.2f}s")
    if skip_tools:
        print(f"Skipped:          {len(skip_tools)} tool(s)")
    print("=" * 70)
    
    # Exit with error if any tests failed
    if total_failed > 0:
        sys.exit(1)
    else:
        print("\n✨ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
