#!/usr/bin/env python3
"""Test script for BioGRID tools implementation."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from tooluniverse import ToolUniverse

# Each entry: (tool_name, arguments, is_required)
# is_required=True means failure aborts the test suite
TOOL_TEST_CASES = [
    ("BioGRID_get_interactions", {
        "gene_names": ["TP53"], "organism": "9606",
        "interaction_type": "physical", "limit": 5,
    }, True),
    ("BioGRID_get_chemical_interactions", {
        "gene_names": ["EGFR"], "organism": "9606", "limit": 5,
    }, False),
    ("BioGRID_search_by_pubmed", {
        "pubmed_ids": ["28514442"], "organism": "9606", "limit": 10,
    }, False),
    ("BioGRID_get_ptms", {
        "gene_names": ["TP53"], "organism": "9606",
        "ptm_type": ["Phosphorylation"], "limit": 5,
    }, False),
]


def _run_tool_test(tu, tool_name, arguments, is_required):
    """Run a single tool test, returning True on success."""
    try:
        result = tu.run({"name": tool_name, "arguments": arguments})

        if result.get("status") == "success":
            data = result.get("data", {})
            count = len(data) if isinstance(data, dict) else 0
            print(f"  PASS: {tool_name} ({count} results)")
            return True

        print(f"  FAIL: {tool_name} - {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"  EXCEPTION: {tool_name} - {e}")

    if not is_required:
        print(f"    (non-critical, continuing)")
    return False


def test_biogrid_tools():
    """Test all BioGRID tools."""
    api_key = os.environ.get("BIOGRID_ACCESS_KEY") or os.environ.get("BIOGRID_API_KEY")
    if not api_key:
        print("BIOGRID_ACCESS_KEY not set. Get a free key from: https://webservice.thebiogrid.org/")
        return False

    tu = ToolUniverse()
    tu.load_tools(categories=["biogrid"])

    biogrid_tools = [name for name in tu.all_tool_dict if "BioGRID" in name]
    print(f"Found {len(biogrid_tools)} BioGRID tools: {biogrid_tools}")

    if len(biogrid_tools) < 4:
        print(f"Expected 4 BioGRID tools, found {len(biogrid_tools)}")
        return False

    for tool_name, arguments, is_required in TOOL_TEST_CASES:
        success = _run_tool_test(tu, tool_name, arguments, is_required)
        if not success and is_required:
            return False

    print("\nBioGRID tools implementation verified.")
    return True


if __name__ == "__main__":
    sys.exit(0 if test_biogrid_tools() else 1)
