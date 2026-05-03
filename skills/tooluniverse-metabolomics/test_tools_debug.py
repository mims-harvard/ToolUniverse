#!/usr/bin/env python3
"""
Debug script to test individual tools and identify issues
"""

from tooluniverse import ToolUniverse
import json

print("="*80)
print("METABOLOMICS TOOLS DEBUG TEST")
print("="*80)

# Initialize ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# Check which metabolomics tools are available
print("\n[1] Checking available metabolomics tools...")
print("-" * 80)

hmdb_tools = [name for name in tu.all_tool_dict.keys() if 'HMDB' in name]
metabolights_tools = [name for name in tu.all_tool_dict.keys() if 'metabolights' in name.lower()]
workbench_tools = [name for name in tu.all_tool_dict.keys() if 'Metabolomics' in name]
pubchem_tools = [name for name in tu.all_tool_dict.keys() if 'PubChem' in name]

print(f"\nHMDB tools ({len(hmdb_tools)}): {hmdb_tools}")
print(f"MetaboLights tools ({len(metabolights_tools)}): {metabolights_tools}")
print(f"Metabolomics Workbench tools ({len(workbench_tools)}): {workbench_tools}")
print(f"PubChem tools ({len(pubchem_tools)}): {pubchem_tools}")

# Test HMDB_search
print("\n" + "="*80)
print("[2] Testing HMDB_search with 'glucose'...")
print("-" * 80)
try:
    result = tu.tools.HMDB_search(operation="search", query="glucose")
    print(f"Result type: {type(result)}")
    print(f"Result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
    print(f"Result: {json.dumps(result, indent=2)[:500]}...")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test metabolights_list_studies
print("\n" + "="*80)
print("[3] Testing metabolights_list_studies...")
print("-" * 80)
try:
    result = tu.tools.metabolights_list_studies(size=3)
    print(f"Result type: {type(result)}")
    if isinstance(result, dict):
        print(f"Result keys: {result.keys()}")
        print(f"Result: {json.dumps(result, indent=2)[:500]}...")
    elif isinstance(result, list):
        print(f"List length: {len(result)}")
        print(f"First 3 items: {result[:3]}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test metabolights_get_study
print("\n" + "="*80)
print("[4] Testing metabolights_get_study with 'MTBLS1'...")
print("-" * 80)
try:
    result = tu.tools.metabolights_get_study(study_id="MTBLS1")
    print(f"Result type: {type(result)}")
    if isinstance(result, dict):
        print(f"Result keys: {result.keys()}")
        print(f"Result: {json.dumps(result, indent=2)[:500]}...")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test metabolights_search_studies
print("\n" + "="*80)
print("[5] Testing metabolights_search_studies with 'diabetes'...")
print("-" * 80)
try:
    result = tu.tools.metabolights_search_studies(query="diabetes")
    print(f"Result type: {type(result)}")
    if isinstance(result, dict):
        print(f"Result keys: {result.keys()}")
        data = result.get('data', [])
        print(f"Data type: {type(data)}")
        print(f"Data length: {len(data) if isinstance(data, list) else 'N/A'}")
        print(f"First 3 items: {data[:3] if isinstance(data, list) else data}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test PubChem
print("\n" + "="*80)
print("[6] Testing PubChem_get_CID_by_compound_name with 'glucose'...")
print("-" * 80)
try:
    result = tu.tools.PubChem_get_CID_by_compound_name(compound_name="glucose")
    print(f"Result type: {type(result)}")
    if isinstance(result, dict):
        print(f"Result keys: {result.keys()}")
        print(f"Result: {json.dumps(result, indent=2)[:500]}...")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("DEBUG TEST COMPLETE")
print("="*80)
