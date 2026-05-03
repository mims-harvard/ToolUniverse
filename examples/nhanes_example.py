#!/usr/bin/env python3
"""
NHANES Tools Example

This example demonstrates how to use the NHANES tools to get information
about available NHANES datasets.

Note: NHANES data is typically available as downloadable files (SAS, XPT formats)
rather than REST APIs. The tools provide information and links to access the data.
"""

from tooluniverse import ToolUniverse

# Initialize ToolUniverse and load tools
tu = ToolUniverse()
tu.load_tools()

print("=" * 80)
print("NHANES Tools Example")
print("=" * 80)
print()

# Example 1: Get dataset information
print("Example 1: Getting NHANES dataset information")
print("-" * 80)
result = tu.run({
    "name": "nhanes_get_dataset_info",
    "arguments": {
        "year": "2017-2018",
        "component": "Demographics"
    }
})

if "error" in result:
    print(f"Error: {result['error']}")
else:
    data = result.get("data", {})
    datasets = data.get("datasets", [])
    print(f"Found {len(datasets)} datasets:")
    for ds in datasets[:5]:
        print(f"  - {ds.get('name')}")
        print(f"    Download: {ds.get('download_url')}")
    print(f"\nNote: {data.get('note', '')}")
print()

# Example 2: Search for datasets
print("Example 2: Searching for NHANES datasets")
print("-" * 80)
result = tu.run({
    "name": "nhanes_search_datasets",
    "arguments": {
        "search_term": "glucose",
        "limit": 5
    }
})

if "error" in result:
    print(f"Error: {result['error']}")
else:
    data = result.get("data", {})
    datasets = data.get("datasets", [])
    print(f"Found {len(datasets)} matching datasets:")
    for ds in datasets:
        print(f"  - {ds.get('name')}")
        print(f"    Year: {ds.get('year')}")
        print(f"    URL: {ds.get('download_url')}")
print()

print("=" * 80)
print("Examples completed!")
print("=" * 80)
print()
print("Note: NHANES data files are in SAS/XPT format.")
print("Visit the download URLs to access datasets. Files may require conversion tools.")

