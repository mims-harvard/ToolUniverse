#!/usr/bin/env python3
"""
Test ToolUniverse tools using their defined test_examples and return_schema.

This script validates:
- Tool execution success (no errors)
- 404 error detection (tracks separately)
- Schema validation against return_schema
- Clear reporting of failures

Usage:
    python scripts/test_new_tools.py [pattern] [--fail-fast] [--verbose]

Examples:
    python scripts/test_new_tools.py          # Test ALL tools
    python scripts/test_new_tools.py fda      # Test only tools matching "fda"
    python scripts/test_new_tools.py hpa -v   # Test "hpa" tools with verbose output
    python scripts/test_new_tools.py cbioportal  # Test cBioPortal tools
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure we can import the package in a src/ layout checkout.
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))
sys.path.insert(0, str(repo_root))

from tooluniverse import ToolUniverse  # noqa: E402

try:
    from jsonschema import validate, ValidationError

    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    print(
        "⚠️  jsonschema not available. Schema validation will be skipped. "
        "Install with: pip install jsonschema"
    )


def load_all_tool_configs(
    data_dir: Path, pattern: str = None
) -> List[Tuple[Path, List[Dict]]]:
    """Load tool configurations matching the pattern."""
    configs = []
    search_pattern = f"*{pattern}*" if pattern else "*"
    files = list(data_dir.glob(f"**/{search_pattern}.json"))

    # Fallback: If no files found matching pattern, maybe it's a tool name?
    # Try loading ALL files and letting the tool name filter handle it.
    if not files and pattern:
        print(
            f"⚠️  No files matched '{search_pattern}'. Scanning all files to filter "
            f"by tool name '{pattern}'..."
        )
        files = list(data_dir.glob("**/*.json"))

    # Filter out known non-tool files or problematic ones if necessary
    # files = [f for f in files if "boltz" not in f.name] # Example exclusion if needed

    # Skip broken_apis/ — those configs document non-functional upstream APIs
    # and the tools are not registered at runtime, so testing them produces
    # only false-positive "Tool not found" failures.
    files = [f for f in files if "broken_apis" not in f.parts]

    print(f"🔍 Found {len(files)} config files matching '{search_pattern}'")

    for file_path in files:
        try:
            with open(file_path, "r") as f:
                content = json.load(f)
                if isinstance(content, list):
                    configs.append((file_path, content))
                elif isinstance(content, dict):
                    configs.append((file_path, [content]))
        except Exception as e:
            print(f"⚠️  Error loading {file_path.name}: {e}")

    return configs


def validate_against_schema(
    data: Any, schema: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    """Validate data against JSON schema."""
    if not JSONSCHEMA_AVAILABLE or not schema:
        return True, None

    # Skip validation if schema is explicitly null (some tools might still have this if not fixed)
    if schema.get("type") == "null":
        return True, None  # Treat as valid if we can't validate it

    try:
        validate(instance=data, schema=schema)
        return True, None
    except ValidationError as e:
        # Create a concise error message
        path = "->".join(str(p) for p in e.absolute_path) or "root"
        return False, f"At {path}: {e.message}"
    except Exception as e:
        return False, str(e)


def _schema_describes_envelope(schema: Dict[str, Any]) -> bool:
    """Heuristic: schema describes the {status,data,error,metadata} envelope.

    Many tool configs declare return_schema at the envelope level (top-level
    properties include 'data' or 'status'). For those, validating the
    unwrapped result.get('data') against the schema always fails ("Schema
    Mismatch: At root: ..."). Detect that style and validate the full result
    instead. Inner-data schemas (no 'data'/'status' at top) keep the
    historical unwrapped behaviour.

    Looking for 'error' alone is NOT enough — many inner-data schemas pair an
    inner array with a {'error': str} error wrapper but still describe the
    inner data shape, not the envelope.
    """
    if not isinstance(schema, dict):
        return False
    branches = schema.get("oneOf") or schema.get("anyOf") or [schema]
    for br in branches:
        if not isinstance(br, dict):
            continue
        props = br.get("properties") or {}
        if "data" in props or "status" in props:
            return True
    return False


def format_result(val: Any, max_len: int = 100) -> str:
    """Format result for display."""
    s = str(val)
    if len(s) > max_len:
        return s[:max_len] + "..."
    return s


def check_for_404_error(result: Any) -> bool:
    """Check if result contains a 404 error."""
    if isinstance(result, dict):
        error = result.get("error", "")
        if "404" in str(error):
            return True
    return False


def run_tests(
    tu: ToolUniverse, configs: List[Tuple[Path, List[Dict]]], args
) -> Dict[str, Any]:
    stats = {
        "files": 0,
        "tools": 0,
        "tests": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "schema_valid": 0,
        "schema_invalid": 0,
        "errors_404": 0,
        "errors_other": 0,
    }

    start_time = time.time()

    for file_path, tools in configs:
        stats["files"] += 1
        if args.verbose:
            print(f"\n📂 {file_path.name}")

        for tool in tools:
            name = tool.get("name")
            if not name:
                continue

            # Name filter logic (if pattern matches tool name directly)
            if (
                args.pattern
                and args.pattern.lower() not in name.lower()
                and args.pattern.lower() not in file_path.name.lower()
            ):
                continue

            stats["tools"] += 1
            examples = tool.get("test_examples", [])
            schema = tool.get("return_schema")

            # Skip tools that require user-supplied local files (no fixture
            # we can ship covers the realistic use case). Tools that declare
            # `requires_local_input: true` are still loadable and runnable;
            # the harness just can't exercise them without real input data.
            if tool.get("requires_local_input"):
                if args.verbose:
                    print(
                        f"  ⏭️  {name}: Skipped (requires user-supplied local input file)"
                    )
                stats["skipped"] += 1
                continue

            # Check if tool requires API keys that are not available
            required_keys = tool.get("required_api_keys", [])
            if required_keys:
                missing_keys = [key for key in required_keys if not os.getenv(key)]
                if missing_keys:
                    if args.verbose:
                        print(
                            f"  ⏭️  {name}: Skipped (missing API keys: {', '.join(missing_keys)})"
                        )
                    stats["skipped"] += 1
                    continue

            # Skip LLM-backed AgenticTool/SmolAgent tools if no LLM provider env
            # is set. Otherwise they show as "Schema Mismatch: None is not of
            # type object" once the provider call fails silently inside the agent.
            if tool.get("type") in (
                "AgenticTool",
                "SmolAgent",
                "SmolAgentTool",
                "ToolFinderLLM",
                "ToolFinderEmbedding",
                "ComposeTool",
                "EmbeddingDatabase",
            ):
                # Gemini fallback fails AgenticTool callers with
                # 'JSON mode not supported here' — agentic framework requires
                # structured-output support. Only count JSON-mode providers.
                providers = (
                    "OPENAI_API_KEY",
                    "AZURE_OPENAI_API_KEY",
                    "OPENROUTER_API_KEY",
                    "ANTHROPIC_API_KEY",
                    "BEDROCK_ACCESS_KEY_ID",
                )
                # Even if a key env is present, the actual key may be
                # invalid/expired (e.g. AZURE_OPENAI_API_KEY 401s). The
                # AgenticTool init prints those errors but the call still
                # returns None, failing schema validation. Require an opt-in
                # env LLM_PROVIDER_WORKING=1 to actually run these tests.
                if not os.getenv("LLM_PROVIDER_WORKING") or not any(
                    os.getenv(pk) for pk in providers
                ):
                    if args.verbose:
                        print(
                            f"  ⏭️  {name}: Skipped (set LLM_PROVIDER_WORKING=1 to run AgenticTool tests)"
                        )
                    stats["skipped"] += 1
                    continue

            if not examples:
                if args.verbose:
                    print(f"  ⏭️  {name}: No test examples")
                stats["skipped"] += 1
                continue

            if args.verbose:
                print(f"  Testing {name} ({len(examples)} examples)...")

            for idx, inputs in enumerate(examples):
                stats["tests"] += 1

                # Check for placeholders
                if any("example_string" in str(v) for v in inputs.values()):
                    print(f"  ⚠️  {name} Example {idx + 1}: Contains placeholder input")

                try:
                    # Execute
                    # Note: ToolUniverse.run_one_function expects specific dict format
                    result = tu.run_one_function({"name": name, "arguments": inputs})

                    # Check for 404 errors first
                    if check_for_404_error(result):
                        stats["failed"] += 1
                        stats["errors_404"] += 1
                        error = result.get("error", "Unknown 404 error")
                        print(f"    ❌ {name} Ex {idx + 1}: 404 ERROR - {error}")
                        if args.fail_fast:
                            print("Stopping due to --fail-fast")
                            return stats
                        continue

                    # ToolUniverse generic wrapper often returns dict with success/data/error
                    # or status/data/error (new style)
                    # But some specific tools might return raw data.
                    # Let's standardize interpretation.

                    success = False
                    data = None
                    error = None

                    if isinstance(result, dict):
                        # Check for status field (new API style)
                        if "status" in result:
                            success = result["status"] == "success"
                            data = result.get("data")
                            error = result.get("error")
                        # Check for success field (old style)
                        elif "success" in result:
                            success = result["success"]
                            if success:
                                data = result.get("data")
                            else:
                                error = result.get("error")
                        else:
                            # No status/success field, assume raw data
                            success = True
                            data = result
                    else:
                        # Assume raw return means success
                        success = True
                        data = result

                    if success:
                        stats["passed"] += 1
                        # Validate Schema: envelope-style schemas describe the
                        # whole {status,data,...} return; inner-data schemas
                        # describe only the data payload. Pick the right target.
                        validation_target = (
                            result if _schema_describes_envelope(schema) else data
                        )
                        is_valid, schema_err = validate_against_schema(
                            validation_target, schema
                        )
                        if is_valid:
                            stats["schema_valid"] += 1
                            if args.verbose:
                                print(f"    ✅ Ex {idx + 1}: Passed")
                        else:
                            stats["schema_invalid"] += 1
                            print(
                                f"    ⚠️  {name} Ex {idx + 1}: Schema Mismatch: {schema_err}"
                            )
                            if args.verbose:
                                print(f"       Data: {format_result(data)}")

                    else:
                        stats["failed"] += 1
                        stats["errors_other"] += 1
                        print(f"    ❌ {name} Ex {idx + 1}: Failed - {error}")
                        if args.fail_fast:
                            print("Stopping due to --fail-fast")
                            return stats

                except Exception as e:
                    stats["failed"] += 1
                    stats["errors_other"] += 1
                    print(f"    🔥 {name} Ex {idx + 1}: Exception - {e}")
                    if args.fail_fast:
                        return stats

    duration = time.time() - start_time
    stats["duration"] = duration
    return stats


def main():
    parser = argparse.ArgumentParser(description="Test ToolUniverse tools.")
    parser.add_argument(
        "pattern",
        nargs="?",
        help="Filter tools by filename or tool name pattern (e.g. 'fda')",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show passed tests detailed output",
    )
    parser.add_argument(
        "--fail-fast", action="store_true", help="Stop after first failure"
    )
    parser.add_argument(
        "--dir",
        default="src/tooluniverse/data",
        help="Directory containing tool JSONs",
    )

    args = parser.parse_args()

    # Setup paths
    repo_root = Path(__file__).parent.parent
    data_dir = repo_root / args.dir

    if not data_dir.exists():
        print(f"Error: Data directory not found at {data_dir}")
        sys.exit(1)

    # Load ToolUniverse
    print("Initializing ToolUniverse...")
    try:
        tu = ToolUniverse()
        tu.load_tools()
        print(f"Loaded {len(tu.tools)} tools into registry.")
    except Exception as e:
        print(f"Failed to load ToolUniverse: {e}")
        sys.exit(1)

    # Load Configs
    configs = load_all_tool_configs(data_dir, args.pattern)
    if not configs:
        print("No matching configuration files found.")
        sys.exit(0)

    # Run Tests
    print(f"Running tests on {len(configs)} files...")
    stats = run_tests(tu, configs, args)

    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print(f"Files Scanned:    {stats['files']}")
    print(f"Tools Tested:     {stats['tools']}")
    print(f"Tests Run:        {stats['tests']}")
    if stats["tests"]:
        pct = stats["passed"] / stats["tests"] * 100
        print(f"Passed:           {stats['passed']} ({pct:.1f}%)")
    else:
        print("Passed: 0")
    print(f"Failed:           {stats['failed']}")
    if stats["errors_404"] > 0:
        print(f"  └─ 404 Errors:  {stats['errors_404']}")
    if stats["errors_other"] > 0:
        print(f"  └─ Other Errors: {stats['errors_other']}")
    print(f"Skipped:          {stats['skipped']}")
    print("-" * 30)
    print(f"Schema Valid:     {stats['schema_valid']}")
    print(f"Schema Invalid:   {stats['schema_invalid']}")
    print(f"Duration:         {stats['duration']:.2f}s")
    print("=" * 50)

    if stats["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
