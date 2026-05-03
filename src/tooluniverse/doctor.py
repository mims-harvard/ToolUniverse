#!/usr/bin/env python3
"""ToolUniverse health checker."""


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
    print(f"✅ Available: {health['available']}")
    print(f"❌ Unavailable: {health['unavailable']}\n")

    if health["unavailable"] == 0:
        print("🎉 All tools loaded successfully!")
        return 0

    print("⚠️  Unavailable tools:\n")

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
        print(f"   pip install {' '.join(sorted(packages))}")

    return 0


if __name__ == "__main__":
    exit(main())
