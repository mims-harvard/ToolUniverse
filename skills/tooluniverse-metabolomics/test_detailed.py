#!/usr/bin/env python3
"""
Detailed test to understand the actual response structures
"""

from tooluniverse import ToolUniverse
import json

tu = ToolUniverse()
tu.load_tools()

# Test 1: HMDB_search detailed
print("="*80)
print("TEST 1: HMDB_search response structure")
print("="*80)
result = tu.tools.HMDB_search(operation="search", query="glucose")
print(json.dumps(result, indent=2))

print("\n" + "="*80)
print("TEST 2: metabolights_get_study response structure")
print("="*80)
result = tu.tools.metabolights_get_study(study_id="MTBLS1")
print(json.dumps(result, indent=2)[:2000])

print("\n" + "="*80)
print("TEST 3: PubChem correct parameter")
print("="*80)
# Check tool config
tool = tu.all_tool_dict['PubChem_get_CID_by_compound_name']
print(f"Tool parameters: {tool.parameters}")
