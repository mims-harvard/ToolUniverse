#!/usr/bin/env python3
"""
WHO GHO (Global Health Observatory) Tools Example

This example demonstrates how to use the two essential WHO GHO tools:
1. who_gho_query_health_data - Answer health questions using natural language
2. who_gho_get_data - Get health data when you know the indicator code

To run this example:
    python3 examples/who_gho_example.py

Or with PYTHONPATH:
    PYTHONPATH=src python3 examples/who_gho_example.py
"""

import sys
import os
import json

from tooluniverse import ToolUniverse


# Initialize ToolUniverse and load tools
tu = ToolUniverse()
tu.load_tools()

print("=" * 80)
print("WHO GHO Tools Example")
print("=" * 80)
print()

# Example 1: Natural language query
print("Example 1: who_gho_query_health_data")
print("Query: 'smoking rate in USA 2020'")
print("-" * 80)
result = tu.run({
    "name": "who_gho_query_health_data",
    "arguments": {
        "query": "smoking rate in USA 2020"
    }
})
print(json.dumps(result, indent=2))
print()

# Example 2: Direct data retrieval
print("Example 2: who_gho_get_data")
print("Indicator: Adult_curr_cig_smoking, Country: USA, Year: 2020")
print("-" * 80)
result = tu.run({
    "name": "who_gho_get_data",
    "arguments": {
        "indicator_code": "Adult_curr_cig_smoking",
        "country_code": "USA",
        "year": 2020,
        "top": 3
    }
})
print(json.dumps(result, indent=2))
print()

# Example 3: Natural language query without year
print("Example 3: who_gho_query_health_data")
print("Query: 'diabetes prevalence in China'")
print("-" * 80)
result = tu.run({
    "name": "who_gho_query_health_data",
    "arguments": {
        "query": "diabetes prevalence in China"
    }
})
print(json.dumps(result, indent=2))
print()

print("=" * 80)
print("Examples completed!")
print("=" * 80)
