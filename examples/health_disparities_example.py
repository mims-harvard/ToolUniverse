#!/usr/bin/env python3
"""
Health Disparities Tools Example

This example demonstrates how to use the health disparities tools to get
information about CDC Social Vulnerability Index (SVI) and County Health Rankings data.

Note: These data sources are primarily file-based (CSV downloads) rather than REST APIs.
The tools provide information and links to access the data.
"""

from tooluniverse import ToolUniverse

# Initialize ToolUniverse and load tools
tu = ToolUniverse()
tu.load_tools()

print("=" * 80)
print("Health Disparities Tools Example")
print("=" * 80)
print()

# Example 1: Get SVI information
print("Example 1: Getting CDC Social Vulnerability Index (SVI) information")
print("-" * 80)
result = tu.run({
    "name": "health_disparities_get_svi_info",
    "arguments": {
        "year": 2020,
        "geography": "county"
    }
})

if "error" in result:
    print(f"Error: {result['error']}")
else:
    data = result.get("data", {})
    sources = data.get("data_sources", [])
    print(f"Found {len(sources)} SVI data sources:")
    for source in sources:
        print(f"  Year: {source.get('year')}, Geography: {source.get('geography')}")
        print(f"  Download URL: {source.get('download_url')}")
    print(f"\nNote: {data.get('note', '')}")
print()

# Example 2: Get County Health Rankings information
print("Example 2: Getting County Health Rankings information")
print("-" * 80)
result = tu.run({
    "name": "health_disparities_get_county_rankings_info",
    "arguments": {
        "state": "CA"
    }
})

if "error" in result:
    print(f"Error: {result['error']}")
else:
    data = result.get("data", {})
    sources = data.get("data_sources", [])
    print(f"Found {len(sources)} data source(s):")
    for source in sources:
        print(f"  Year: {source.get('year')}, State: {source.get('state')}")
        print(f"  Access URL: {source.get('access_url')}")
    print(f"\nNote: {data.get('note', '')}")
print()

print("=" * 80)
print("Examples completed!")
print("=" * 80)
print()
print("Note: These tools provide information about data sources.")
print("Actual data may require downloading CSV files from the provided URLs.")

