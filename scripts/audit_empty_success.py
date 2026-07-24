#!/usr/bin/env python3
"""
Audit tools for "silent empty success" — a tool that returns
``{"status": "success", ...}`` while carrying no actual content.

This is the failure mode behind issue #264: OpenTargets changed its disease IDs,
the stale ``test_examples`` started resolving to nothing, and the tools reported
an empty success instead of an error. Nobody noticed until a user filed a bug.

The audit runs each tool's ``test_examples`` and flags any that succeed with
effectively-empty data, so stale examples and silently-failing tools surface in
CI / a scheduled job instead of in a user's workflow.

It is intentionally STRICTER than the runtime guard in ``GraphQLTool.run``: the
runtime guard only errors when the top-level entity is null (so a legitimate
0-hit search still succeeds), whereas this audit flags *any* empty-content
success for a human to review.

Usage:
    python3 scripts/audit_empty_success.py --type OpenTarget
    python3 scripts/audit_empty_success.py --pattern disease_target_score
    python3 scripts/audit_empty_success.py            # every tool (slow)

Exit code is non-zero if any tool is flagged, so it can gate a CI job.
"""

import argparse
import json
import sys
from pathlib import Path

# src/ layout import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from tooluniverse import ToolUniverse  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "src" / "tooluniverse" / "data"


def is_effectively_empty(value) -> bool:
    """True when value carries no real content (recursively).

    None, "", [], {} are empty; a dict/list is empty when every member is;
    any non-empty scalar (number, non-empty string, bool) is content.
    """
    if value is None or value == "" or value == [] or value == {}:
        return True
    if isinstance(value, dict):
        return all(is_effectively_empty(v) for v in value.values())
    if isinstance(value, list):
        return all(is_effectively_empty(v) for v in value)
    return False  # a real scalar


def load_configs(pattern=None, type_filter=None):
    """Yield (tool_name, config) for tools matching the filters."""
    for file_path in sorted(DATA_DIR.glob("**/*.json")):
        if "broken_apis" in file_path.parts:
            continue
        try:
            content = json.load(open(file_path))
        except Exception:
            continue
        tools = content if isinstance(content, list) else [content]
        for t in tools:
            if not isinstance(t, dict) or "name" not in t:
                continue
            if type_filter and t.get("type") != type_filter:
                continue
            if pattern and pattern not in t["name"]:
                continue
            yield t["name"], t


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--type", dest="type_filter", help="filter by tool config type")
    ap.add_argument("--pattern", help="substring filter on tool name")
    ap.add_argument(
        "--limit", type=int, default=0, help="max tools to test (0 = no limit)"
    )
    args = ap.parse_args()

    configs = list(load_configs(args.pattern, args.type_filter))
    if args.limit:
        configs = configs[: args.limit]
    if not configs:
        print("No tools matched the filters.")
        return 0

    tu = ToolUniverse()
    tu.load_tools()

    empty, broken, ok, no_example = [], [], 0, 0
    print(f"Auditing {len(configs)} tool(s) — do their test_examples return content?\n")

    for name, cfg in configs:
        examples = cfg.get("test_examples", [])
        if not examples:
            no_example += 1
            continue
        for i, example in enumerate(examples, 1):
            try:
                result = tu.run_one_function({"name": name, "arguments": example})
            except Exception as e:
                broken.append((name, i, f"{type(e).__name__}: {e}"))
                print(f"  BROKEN {name} ex{i}: raised {type(e).__name__}: {e}")
                continue
            status = result.get("status") if isinstance(result, dict) else None
            data = result.get("data") if isinstance(result, dict) else result
            if status == "success" and is_effectively_empty(data):
                # The dangerous one: looks fine, carries nothing. Invisible without
                # this audit -- exactly the issue #264 failure mode.
                empty.append((name, i, example))
                print(f"  EMPTY  {name} ex{i}: success but empty data  args={example}")
            elif status == "error":
                broken.append((name, i, result.get("error", "")))
                err = str(result.get("error", ""))[:120]
                print(f"  BROKEN {name} ex{i}: error on its own example -- {err}")
            else:
                ok += 1

    print(
        f"\nSummary: {len(empty)} empty-success, {len(broken)} broken-example, "
        f"{ok} ok, {no_example} without examples."
    )
    if empty:
        print("\nSilent empty success (stale example or silent failure):")
        for name, i, _ in empty:
            print(f"  - {name} (example {i})")
    if broken:
        print("\nBroken examples (tool errors on its own documented example):")
        for name, i, _ in broken:
            print(f"  - {name} (example {i})")
    return 1 if (empty or broken) else 0


if __name__ == "__main__":
    raise SystemExit(main())
