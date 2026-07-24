#!/usr/bin/env python3
"""ToolUniverse health checker."""

import sys


def _report_optional_dependencies(tool_configs) -> bool:
    """Print the optional-dependency section. Returns True if everything is installed.

    Loading a tool only registers its config; tools backed by an optional
    dependency group stay listed as "available" but fail when run. Report those
    groups so a partial install is not mistaken for a complete one.
    """
    try:
        from .extras import runtime_readiness

        readiness = runtime_readiness(tool_configs)
    except Exception as exc:  # never let diagnostics break the health check
        print(f"⚠️  Could not check optional dependencies: {exc}\n")
        return True

    if readiness["ready"]:
        return True

    gaps = readiness["missing_extras"]
    affected = readiness["affected_tools"]
    print(f"⚠️  {len(gaps)} optional dependency group(s) not installed:\n")
    for extra, packages in gaps.items():
        count = affected.get(extra)
        scope = (
            f"up to {count} tool(s) may not run"
            if count
            else "no currently-loaded tool needs it"
        )
        print(f"  📦 [{extra}] — {scope}")
        print(f"     Missing: {', '.join(packages)}")
        print(f"     Fix: pip install 'tooluniverse[{extra}]'")
        print()

    print(
        "   Note: tool counts above are an upper bound — a few tools use these\n"
        "   packages only as an enhancement and still work without them.\n"
    )
    return False


def main() -> int:
    """Run ToolUniverse health checks and print a diagnostic report."""
    print("🔍 Checking ToolUniverse health...\n")

    try:
        from tooluniverse import ToolUniverse

        tu = ToolUniverse()
        # Load tools to get actual tool counts
        tu.load_tools()
        health = tu.get_tool_health()
    except Exception as e:
        print(f"❌ Failed to initialize ToolUniverse: {e}")
        return 1

    print(f"📊 Total tools: {health['total']}")
    print(f"✅ Config loaded: {health['available']}")
    print(f"❌ Failed to load: {health['unavailable']}\n")

    if health["unavailable"]:
        print("⚠️  Tools that failed to load:\n")

        packages = set()
        for tool_name in health["unavailable_list"]:
            details = health["details"].get(tool_name, {})
            print(f"  ❌ {tool_name}")
            print(f"     Error: {details.get('error', 'Unknown')[:80]}")
            if details.get("missing_package"):
                pkg = details["missing_package"]
                print(f"     Fix: pip install {pkg}")
                packages.add(pkg)
            print()

        if packages:
            print("💡 Bulk fix command:")
            print(f"   pip install {' '.join(sorted(packages))}\n")

    deps_ok = _report_optional_dependencies(getattr(tu, "all_tools", None))

    if not health["unavailable"] and deps_ok:
        print("🎉 All tools loaded and every optional dependency group is installed!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
