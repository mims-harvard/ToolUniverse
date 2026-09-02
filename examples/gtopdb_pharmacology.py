#!/usr/bin/env python3
"""
GtoPdb Pharmacology Database Example

This example shows how to use the GtoPdb tool to query drug targets
and pharmacological information from the Guide to Pharmacology database.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.tooluniverse import ToolUniverse

def show_targets(result, limit):
    if result and result.get("status") == "success":
        data = result.get("data", [])
        print(f"Found {len(data)} drug targets")

        for i, target in enumerate(data[:limit], 1):
            name = target.get("name", "Unknown")
            target_id = target.get("targetId", "Unknown")
            target_type = target.get("type", "Unknown")
            print(f"   {i}. {name} ({target_type}) - ID {target_id}")
    else:
        print(f"Error: {result.get('error')}")

def main():
    # Initialize ToolUniverse
    tu = ToolUniverse()

    # Load tools first
    tu.load_tools()

    print("GtoPdb Pharmacology Database Examples")
    print("=" * 40)

    # Example 1: Search drug targets by name
    print("\n1. Searching drug targets by name")
    print("-" * 25)

    result = tu.run({"name": "GtoPdb_search_targets", "arguments": {
        "name": "dopamine"
    }})
    show_targets(result, 3)

    # Example 2: Restrict the search to one target type
    print("\n2. Restricting the search to one target type")
    print("-" * 30)

    result = tu.run({"name": "GtoPdb_search_targets", "arguments": {
        "name": "serotonin",
        "type": "GPCR"
    }})
    show_targets(result, 4)

    # Example 3: Exact lookup by HGNC gene symbol
    print("\n3. Exact lookup by gene symbol")
    print("-" * 30)

    result = tu.run({"name": "GtoPdb_search_targets", "arguments": {
        "gene_symbol": "HTR2A"
    }})
    show_targets(result, 3)

if __name__ == "__main__":
    main()
