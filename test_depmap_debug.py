#!/usr/bin/env python3
"""Debug DepMap tool failures reported in TEST_REPORT_CRISPR.md"""

from tooluniverse import ToolUniverse
import json

# Initialize ToolUniverse
tu = ToolUniverse()
tu.load_tools()

print("=" * 80)
print("DEPMAP TOOLS DEBUG TEST")
print("=" * 80)

# Test 1: DepMap_search_genes (most critical)
print("\n1. Testing DepMap_search_genes with 'KRAS'")
print("-" * 80)
try:
    result = tu.tools.DepMap_search_genes(query="KRAS")
    print(f"Status: {result.get('status')}")
    print(f"Result: {json.dumps(result, indent=2)}")
except Exception as e:
    print(f"ERROR: {e}")

# Test 2: DepMap_get_gene_dependencies
print("\n\n2. Testing DepMap_get_gene_dependencies with 'EGFR'")
print("-" * 80)
try:
    result = tu.tools.DepMap_get_gene_dependencies(gene_symbol="EGFR")
    print(f"Status: {result.get('status')}")
    print(f"Result: {json.dumps(result, indent=2)}")
except Exception as e:
    print(f"ERROR: {e}")

# Test 3: DepMap_get_cell_lines
print("\n\n3. Testing DepMap_get_cell_lines (Lung)")
print("-" * 80)
try:
    result = tu.tools.DepMap_get_cell_lines(tissue="Lung", page_size=5)
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        data = result.get('data', {})
        print(f"Count: {data.get('count')}")
        print(f"Cell lines: {[cl.get('model_name') for cl in data.get('cell_lines', [])]}")
    else:
        print(f"Error: {result.get('error')}")
except Exception as e:
    print(f"ERROR: {e}")

# Test 4: Direct API test (bypass ToolUniverse)
print("\n\n4. Direct API Test (bypassing ToolUniverse)")
print("-" * 80)
import requests
try:
    response = requests.get(
        "https://api.cellmodelpassports.sanger.ac.uk/genes",
        params={"sort": "symbol", "page[size]": 5},
        timeout=10
    )
    print(f"HTTP Status: {response.status_code}")
    print(f"Response sample: {response.text[:500]}")
except Exception as e:
    print(f"ERROR: {e}")

print("\n" + "=" * 80)
print("DEBUG TEST COMPLETE")
print("=" * 80)
