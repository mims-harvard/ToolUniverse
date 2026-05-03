#!/usr/bin/env python3
"""
RCSB PDB Structure Search Example

Demonstrates how to use PDB_search_similar_structures to find similar
protein structures.
"""

import json

from tooluniverse import ToolUniverse

# Initialize ToolUniverse
tu = ToolUniverse()
# Load all tools (rcsb_search is included in default config)
tu.load_tools()

print("=" * 80)
print("RCSB PDB Structure Search Examples")
print("=" * 80)

# Example 1: Sequence-based similarity search
print("\n" + "=" * 80)
print("Example 1: Sequence-based Similarity Search")
print("=" * 80)
print("Searching for structures similar to a protein sequence...")

# Use a longer, well-known protein sequence (insulin)
sequence = (
    "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN"  # noqa: E501
)

result1 = tu.run(
    {
        "name": "PDB_search_similar_structures",
        "arguments": {
            "query": sequence,
            "search_type": "sequence",
            "similarity_threshold": 0.7,
            "max_results": 10,
        },
    }
)

print("\nResult:")
print("-" * 80)
if "error" in result1:
    print(f"Error: {result1['error']}")
elif "results" in result1:
    print(f"Found {result1.get('total_found', 0)} similar structures:")
    for i, res in enumerate(result1["results"][:5], 1):
        print(f"  {i}. PDB ID: {res.get('pdb_id')}, Rank: {res.get('rank')}")
else:
    print(json.dumps(result1, indent=2, ensure_ascii=False)[:500])

# Example 2: Structure-based similarity search
print("\n" + "=" * 80)
print("Example 2: Structure-based Similarity Search")
print("=" * 80)
print("Searching for structures similar to a known PDB structure...")

pdb_id = "1HHO"  # Hemoglobin structure (well-known, supports structure search)

result2 = tu.run(
    {
        "name": "PDB_search_similar_structures",
        "arguments": {
            "query": pdb_id,
            "search_type": "structure",
            "similarity_threshold": 0.7,
            "max_results": 10,
        },
    }
)

print("\nResult:")
print("-" * 80)
if "error" in result2:
    print(f"Error: {result2['error']}")
elif "results" in result2:
    print(f"Found {result2.get('total_found', 0)} similar structures:")
    for i, res in enumerate(result2["results"][:5], 1):
        print(f"  {i}. PDB ID: {res.get('pdb_id')}, Rank: {res.get('rank')}")
else:
    print(json.dumps(result2, indent=2, ensure_ascii=False)[:500])

# Example 3: Error handling - invalid PDB ID
print("\n" + "=" * 80)
print("Example 3: Error Handling - Invalid PDB ID")
print("=" * 80)

result3 = tu.run(
    {
        "name": "PDB_search_similar_structures",
        "arguments": {
            "query": "INVALID",
            "search_type": "structure",
        },
    }
)

print("\nResult:")
print("-" * 80)
if "error" in result3:
    print(f"Error (expected): {result3['error']}")
else:
    print(json.dumps(result3, indent=2, ensure_ascii=False)[:500])

# Example 4: Error handling - invalid sequence
print("\n" + "=" * 80)
print("Example 4: Error Handling - Invalid Sequence")
print("=" * 80)

result4 = tu.run(
    {
        "name": "PDB_search_similar_structures",
        "arguments": {
            "query": "SHORT",
            "search_type": "sequence",
        },
    }
)

print("\nResult:")
print("-" * 80)
if "error" in result4:
    print(f"Error (expected): {result4['error']}")
else:
    print(json.dumps(result4, indent=2, ensure_ascii=False)[:500])

# Example 5: Text-based search (find PDB IDs by name or keyword)
print("\n" + "=" * 80)
print("Example 5: Text-based Search (Find PDB IDs by Name)")
print("=" * 80)
print("Searching for PDB IDs by protein name or keyword...")

result5 = tu.run(
    {
        "name": "PDB_search_similar_structures",
        "arguments": {
            "query": "insulin",
            "search_type": "text",
            "max_results": 10,
        },
    }
)

print("\nResult:")
print("-" * 80)
if "error" in result5:
    print(f"Error: {result5['error']}")
elif "results" in result5:
    print(f"Found {result5.get('total_found', 0)} PDB structures:")
    for i, res in enumerate(result5["results"][:5], 1):
        print(f"  {i}. PDB ID: {res.get('pdb_id')}, Rank: {res.get('rank')}")
    if result5["results"]:
        print(
            "\n  Note: You can use these PDB IDs for structure "
            "similarity search"
        )
else:
    print(json.dumps(result5, indent=2, ensure_ascii=False)[:500])

# Example 6: Complete workflow - Text search -> Structure similarity search
print("\n" + "=" * 80)
print("Example 6: Complete Workflow - Text Search -> Similar Structures")
print("=" * 80)
print("Step 1: Find PDB ID by text search...")

text_result = tu.run(
    {
        "name": "PDB_search_similar_structures",
        "arguments": {
            "query": "insulin",
            "search_type": "text",
            "max_results": 5,
        },
    }
)

if "results" in text_result and text_result["results"]:
    first_pdb_id = text_result["results"][0]["pdb_id"]
    print(f"Found PDB ID: {first_pdb_id}")
    print("\nStep 2: Search for similar structures using the found PDB ID...")

    similar_result = tu.run(
        {
            "name": "PDB_search_similar_structures",
            "arguments": {
                "query": first_pdb_id,
                "search_type": "structure",
                "similarity_threshold": 0.7,
                "max_results": 10,
            },
        }
    )

    print("\nResult:")
    print("-" * 80)
    if "error" in similar_result:
        print(f"Error: {similar_result['error']}")
    elif "results" in similar_result:
        print(
            f"Found {similar_result.get('total_found', 0)} similar structures:"
        )
        for i, res in enumerate(similar_result["results"][:5], 1):
            print(
                f"  {i}. PDB ID: {res.get('pdb_id')}, "
                f"Rank: {res.get('rank')}"
            )
    else:
        print(json.dumps(similar_result, indent=2, ensure_ascii=False)[:500])
else:
    print("No PDB IDs found for text search")

print("\n" + "=" * 80)
print("Examples completed!")
print("=" * 80)
print(
    "\nNote: For real searches, use valid PDB IDs, protein sequences, "
    "or search text."
)
print("This tool is particularly useful for finding similar structures")
print("for antibodies, proteins, and other biologics that cannot be")
print(
    "searched using SMILES-based tools like "
    "ChEMBL_search_similar_molecules."
)
print(
    "\nText search allows you to find PDB IDs from drug names, "
    "protein names, or keywords, completing the workflow: "
    "drug name → PDB ID → similar structures."
)
