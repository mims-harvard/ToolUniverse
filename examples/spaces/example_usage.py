#!/usr/bin/env python3
"""
Simple example: Loading and using Profile configurations

Usage:
    python examples/spaces/example_usage.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse import ToolUniverse  # noqa: E402


def main():
    """Simple example of loading and using a Profile configuration"""
    # Load Profile configuration
    tu = ToolUniverse()
    config = tu.load_profile("./examples/spaces/life-science.yaml")

    print(f"✅ Loaded: {config.get('name')}")
    print(f"   Tools available: {len(tu.all_tools)} tools")

    # Show some example tools
    print("\n   Example tools:")
    for tool in tu.all_tools[:5]:
        if isinstance(tool, dict):
            print(f"   - {tool.get('name')}")

    print("\n💡 Use tools with:")
    print("   tu.run_one_function({'name': 'tool_name', 'arguments': {...}})")


if __name__ == "__main__":
    main()
