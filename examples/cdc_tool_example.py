#!/usr/bin/env python3
"""
CDC Data Tools Example

This example demonstrates how to use the CDC Data.CDC.gov tools to:
1. Search for available datasets
2. Retrieve data from specific datasets
"""

from tooluniverse import ToolUniverse

# Initialize ToolUniverse and load tools
tu = ToolUniverse()
tu.load_tools()

print("=" * 80)
print("CDC Data Tools Example")
print("=" * 80)
print()

# Example 1: Search for datasets related to mortality
print("Example 1: Searching for mortality-related datasets")
print("-" * 80)
result = tu.run({
    "name": "cdc_data_search_datasets",
    "arguments": {
        "search_query": "mortality",
        "limit": 10
    }
})

if "error" in result:
    print(f"Error: {result['error']}")
else:
    data = result.get("data", [])
    print(f"Found {len(data)} datasets:")
    for idx, dataset in enumerate(data[:5], 1):
        print(f"  {idx}. ID: {dataset.get('id')}")
        print(f"      Name: {dataset.get('name', 'Unknown')[:60]}...")
        print(f"      Views: {dataset.get('viewCount', 0)}")
print()

# Example 2: Search for vaccination datasets
print("Example 2: Searching for vaccination datasets")
print("-" * 80)
result = tu.run({
    "name": "cdc_data_search_datasets",
    "arguments": {
        "search_query": "vaccination",
        "limit": 5
    }
})

if "error" in result:
    print(f"Error: {result['error']}")
else:
    data = result.get("data", [])
    print(f"Found {len(data)} vaccination datasets:")
    for idx, dataset in enumerate(data[:3], 1):
        print(f"  {idx}. {dataset.get('name', 'Unknown')[:70]}")
print()

# Example 3: Get data from a specific dataset
print("Example 3: Getting data from a specific dataset")
print("-" * 80)
# Use a dataset ID from the search results
result = tu.run({
    "name": "cdc_data_search_datasets",
    "arguments": {
        "search_query": "covid",
        "limit": 1
    }
})

if "error" not in result:
    datasets = result.get("data", [])
    if datasets:
        dataset_id = datasets[0].get("id")
        print(f"Fetching data from dataset: {dataset_id}")
        
        result = tu.run({
            "name": "cdc_data_get_dataset",
            "arguments": {
                "dataset_id": dataset_id,
                "limit": 5
            }
        })
        
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            data = result.get("data", {})
            rows = data.get("data", [])
            print(f"Retrieved {len(rows)} rows")
            if rows:
                print(f"Sample row keys: {list(rows[0].keys())[:5]}")
print()

# Example 4: Search without query (browse all datasets)
print("Example 4: Browsing recent datasets")
print("-" * 80)
result = tu.run({
    "name": "cdc_data_search_datasets",
    "arguments": {
        "limit": 10
    }
})

if "error" in result:
    print(f"Error: {result['error']}")
else:
    data = result.get("data", [])
    print(f"Found {len(data)} datasets (showing first 5):")
    for idx, dataset in enumerate(data[:5], 1):
        name = dataset.get("name", "Unknown")
        desc = dataset.get("description", "")[:100] if dataset.get("description") else "No description"
        print(f"  {idx}. {name}")
        print(f"      {desc}...")

print()
print("=" * 80)
print("Examples completed!")
print("=" * 80)

