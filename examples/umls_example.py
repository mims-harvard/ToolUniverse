#!/usr/bin/env python3
"""
UMLS Tools Example

This example demonstrates how to use UMLS tools to access medical terminology data.
Note: These tools require a free UMLS API key. Register at https://uts.nlm.nih.gov/uts/

To run this example:
    export UMLS_API_KEY='your_key'
    python3 examples/umls_example.py

Or with PYTHONPATH:
    PYTHONPATH=src python3 examples/umls_example.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from tooluniverse import ToolUniverse
except ImportError:
    print("Error: Could not import ToolUniverse.")
    print("Make sure you're running from the project root or have installed the package.")
    print("Try: PYTHONPATH=src python3 examples/umls_example.py")
    sys.exit(1)

# Check for API key
if not os.getenv("UMLS_API_KEY"):
    print("=" * 80)
    print("WARNING: UMLS_API_KEY environment variable not set!")
    print("=" * 80)
    print("UMLS tools require a free API key.")
    print("Register for free at: https://uts.nlm.nih.gov/uts/")
    print("Then set: export UMLS_API_KEY='your_api_key_here'")
    print("=" * 80)
    print()

# Initialize ToolUniverse and load tools
tu = ToolUniverse()
tu.load_tools()

print("=" * 80)
print("UMLS Tools Example")
print("=" * 80)
print()

# Example 1: Search UMLS concepts
print("Example 1: Search UMLS for 'diabetes'")
print("-" * 80)
result = tu.run({
    "name": "umls_search_concepts",
    "arguments": {
        "query": "diabetes",
        "pageSize": 5
    }
})

if "error" in result:
    print(f"Error: {result['error']}")
else:
    data = result.get("data", {})
    result_obj = data.get("result", {})
    results = result_obj.get("results", [])
    print(f"Found {len(results)} concepts:")
    for idx, concept in enumerate(results[:5], 1):
        print(f"  {idx}. CUI: {concept.get('ui')}, "
              f"Name: {concept.get('name')}, "
              f"Source: {concept.get('rootSource')}")
print()

# Example 2: Get concept details
print("Example 2: Get details for CUI C0004096 (Asthma)")
print("-" * 80)
result = tu.run({
    "name": "umls_get_concept_details",
    "arguments": {
        "cui": "C0004096"
    }
})

if "error" in result:
    print(f"Error: {result['error']}")
else:
    data = result.get("data", {})
    result_obj = data.get("result", {})
    print(f"CUI: {result_obj.get('ui')}")
    print(f"Name: {result_obj.get('name')}")
    if "definition" in result_obj:
        print(f"Definition: {result_obj.get('definition')[:200]}...")
print()

# Example 3: Search ICD-10 codes
print("Example 3: Search ICD-10 codes for 'asthma'")
print("-" * 80)
result = tu.run({
    "name": "icd_search_codes",
    "arguments": {
        "query": "asthma",
        "version": "ICD10CM",
        "pageSize": 5
    }
})

if "error" in result:
    print(f"Error: {result['error']}")
else:
    data = result.get("data", {})
    result_obj = data.get("result", {})
    results = result_obj.get("results", [])
    print(f"Found {len(results)} ICD-10 codes:")
    for idx, code in enumerate(results[:5], 1):
        print(f"  {idx}. Code: {code.get('ui')}, "
              f"Name: {code.get('name')}")
print()

# Example 4: Search SNOMED CT concepts
print("Example 4: Search SNOMED CT for 'diabetes mellitus'")
print("-" * 80)
result = tu.run({
    "name": "snomed_search_concepts",
    "arguments": {
        "query": "diabetes mellitus",
        "pageSize": 5
    }
})

if "error" in result:
    print(f"Error: {result['error']}")
else:
    data = result.get("data", {})
    result_obj = data.get("result", {})
    results = result_obj.get("results", [])
    print(f"Found {len(results)} SNOMED CT concepts:")
    for idx, concept in enumerate(results[:5], 1):
        print(f"  {idx}. Code: {concept.get('ui')}, "
              f"Name: {concept.get('name')}")
print()

# Example 5: Search LOINC codes
print("Example 5: Search LOINC codes for 'glucose'")
print("-" * 80)
result = tu.run({
    "name": "loinc_search_codes",
    "arguments": {
        "query": "glucose",
        "pageSize": 5
    }
})

if "error" in result:
    print(f"Error: {result['error']}")
else:
    data = result.get("data", {})
    result_obj = data.get("result", {})
    results = result_obj.get("results", [])
    print(f"Found {len(results)} LOINC codes:")
    for idx, code in enumerate(results[:5], 1):
        print(f"  {idx}. Code: {code.get('ui')}, "
              f"Name: {code.get('name')}")
print()

print("=" * 80)
print("Examples completed!")
print("=" * 80)
print("\nNote: UMLS tools require a free API key.")
print("Register at: https://uts.nlm.nih.gov/uts/")
print("Set environment variable: export UMLS_API_KEY='your_key'")
