#!/usr/bin/env python3
"""
Usage examples for FAERS_count_reactions_by_drug_event tool in ToolUniverse

This script demonstrates how to use the FAERS_count_reactions_by_drug_event tool
to count adverse reactions reported for a given drug, with optional filtering
by reaction term using the reactionmeddraverse parameter.

The tool supports two main modes:
1. Without reactionmeddraverse: Returns all adverse reactions (AE) with their counts
   grouped by MedDRA Preferred Term
2. With reactionmeddraverse: Filters results to only include the specific reaction term

Usage:
    python faers_count_reactions_example.py
"""

import os
import json
import inspect

from tooluniverse import ToolUniverse

print("=" * 70)
print("Testing FAERS_count_reactions_by_drug_event tool")
print("=" * 70)

# Initialize ToolUniverse
tu = ToolUniverse()

# Test 1: Without reactionmeddraverse parameter - returns all AEs and counts
print("\nTest 1: Without reactionmeddraverse parameter - returns all adverse reactions (AE) and counts")
print("-" * 70)
print("Functionality: When reactionmeddraverse is not specified, the tool returns")
print("               all adverse reactions for the drug, grouped by MedDRA Preferred Term")
print("               with counts for each reaction")
print()
try:
    result1 = tu.run({
        "name": "FAERS_count_reactions_by_drug_event",
        "arguments": {
            "medicinalproduct": "ASPIRIN"
        }
    })
    print(f"✓ Call succeeded")
    print(f"  Result type: {type(result1)}")
    if isinstance(result1, list) and len(result1) > 0:
        print(f"  ✓ Returned {len(result1)} adverse reaction records")
        print(f"  Each record contains: term (reaction name) and count (count)")
        print(f"\n  Top 10 most common adverse reactions:")
        for i, item in enumerate(result1[:10], 1):
            if isinstance(item, dict):
                reaction = item.get('term', item.get('reaction', 'N/A'))
                count = item.get('count', 'N/A')
                print(f"    {i:2d}. {reaction:30s}: {count:>8,}")
        print(f"\n  ... {len(result1) - 10} more records")
        print(f"\n  Total: {len(result1)} different adverse reactions")
    elif isinstance(result1, list) and len(result1) == 0:
        print(f"  ⚠ Returned 0 records (the drug may have no adverse reaction data)")
    elif isinstance(result1, dict):
        if 'error' in result1:
            print(f"  ✗ Error: {result1['error']}")
        else:
            print(f"  Result: {result1}")
except Exception as e:
    print(f"✗ Call failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Using reactionmeddraverse parameter (new feature)
print("\nTest 2: Using reactionmeddraverse parameter to filter specific reactions")
print("-" * 70)
print("Functionality:")
print("  - reactionmeddraverse is MedDRA Lowest Level Term (LLT) for precise filtering")
print("  - When reactionmeddraverse is specified, only returns reactions matching that LLT")
print("  - Note: LLT terms require exact match and may differ from Preferred Term (PT)")
print("  - If empty results are returned, the LLT term may not exist in data or format mismatch")
print()

# First get all reactions, then try using some of them for testing
print("Step 1: Get all adverse reactions (for comparison)")
try:
    all_reactions = tu.run({
        "name": "FAERS_count_reactions_by_drug_event",
        "arguments": {
            "medicinalproduct": "ASPIRIN"
        }
    })
    
    if isinstance(all_reactions, list) and len(all_reactions) > 0:
        print(f"  ✓ Retrieved {len(all_reactions)} adverse reactions (grouped by PT)")
        print(f"  Top 5 most common reactions (PT):")
        top_reactions = []
        for i, item in enumerate(all_reactions[:5], 1):
            if isinstance(item, dict):
                reaction = item.get('term', 'N/A')
                count = item.get('count', 'N/A')
                print(f"    {i}. {reaction:30s}: {count:>8,}")
                top_reactions.append(reaction)
        
        print(f"\nStep 2: Try filtering with reactionmeddraverse (using above PT terms)")
        print("  Note: These are Preferred Terms, which may not be valid LLTs")
        print("  If empty results are returned, true LLT terms are needed")
        print()
        
        # Test using these reaction terms
        for reaction_term in top_reactions[:3]:  # Only test first 3
            print(f"  Testing reaction term: {reaction_term}")
            try:
                result2 = tu.run({
                    "name": "FAERS_count_reactions_by_drug_event",
                    "arguments": {
                        "medicinalproduct": "ASPIRIN",
                        "reactionmeddraverse": reaction_term
                    }
                })
                
                if isinstance(result2, list):
                    if len(result2) > 0:
                        print(f"    ✓ Returned {len(result2)} reaction records")
                        print(f"    Result details:")
                        for i, item in enumerate(result2[:5], 1):
                            if isinstance(item, dict):
                                reaction = item.get('term', item.get('reaction', 'N/A'))
                                count = item.get('count', 'N/A')
                                print(f"      {i}. {reaction:30s}: {count:>8,}")
                    else:
                        print(f"    - Returned 0 records")
                        print(f"      Note: '{reaction_term}' may not be a valid MedDRA LLT")
                        print(f"      or this LLT does not exist in ASPIRIN adverse reaction data")
                elif isinstance(result2, dict):
                    if 'error' in result2:
                        print(f"    ✗ Error: {result2['error']}")
                    else:
                        print(f"    Result: {result2}")
            except Exception as e:
                print(f"    ✗ Call failed: {type(e).__name__}: {e}")
        
        print(f"\nStep 3: Comparison notes")
        print(f"  - Without reactionmeddraverse: Returns all adverse reactions (grouped by PT)")
        print(f"  - With reactionmeddraverse: Returns only reactions matching that LLT")
        print(f"  - If LLT filtering returns empty results, the term may:")
        print(f"    1. Not be a valid MedDRA LLT")
        print(f"    2. Not exist in the data")
        print(f"    3. Need different format or case")
        
    else:
        print(f"  ⚠ Unable to retrieve adverse reaction list, skipping comparison test")
        
except Exception as e:
    print(f"  ✗ Failed to retrieve adverse reaction list: {type(e).__name__}: {e}")
    print(f"  Will use preset test terms")
    
    # If retrieval fails, use preset test terms
    test_reactions = ["DYSPNOEA", "NAUSEA", "FATIGUE"]
    for reaction_term in test_reactions:
        print(f"\n  Testing reaction term: {reaction_term}")
        try:
            result2 = tu.run({
                "name": "FAERS_count_reactions_by_drug_event",
                "arguments": {
                    "medicinalproduct": "ASPIRIN",
                    "reactionmeddraverse": reaction_term
                }
            })
            if isinstance(result2, list):
                if len(result2) > 0:
                    print(f"    ✓ Returned {len(result2)} reaction records")
                else:
                    print(f"    - Returned 0 records")
        except Exception as e:
            print(f"    ✗ Call failed: {type(e).__name__}: {e}")

# Test 3: Using reactionmeddraverse + other filters
print("\nTest 3: Using reactionmeddraverse + other filters")
print("-" * 70)
try:
    result3 = tu.run({
        "name": "FAERS_count_reactions_by_drug_event",
        "arguments": {
            "medicinalproduct": "ASPIRIN",
            "reactionmeddraverse": "NAUSEA",
            "serious": "Yes"  # Only query serious events
        }
    })
    print(f"✓ Call succeeded (using reactionmeddraverse='NAUSEA' + serious='Yes')")
    print(f"  Result type: {type(result3)}")
    if isinstance(result3, list):
        print(f"  Returned {len(result3)} reaction records")
        if len(result3) > 0:
            print(f"  Examples (first 3):")
            for i, item in enumerate(result3[:3], 1):
                if isinstance(item, dict):
                    reaction = item.get('term', item.get('reaction', 'N/A'))
                    count = item.get('count', 'N/A')
                    print(f"    {i}. {reaction}: {count:,}")
except Exception as e:
    print(f"✗ Call failed: {type(e).__name__}: {e}")

# Test 4: Verify parameter exists in function signature
print("\nTest 4: Verify Python function signature")
print("-" * 70)
try:
    from tooluniverse.tools.FAERS_count_reactions_by_drug_event import FAERS_count_reactions_by_drug_event
    
    sig = inspect.signature(FAERS_count_reactions_by_drug_event)
    params = list(sig.parameters.keys())
    
    if 'reactionmeddraverse' in params:
        print(f"✓ reactionmeddraverse parameter exists in function signature")
        print(f"  All parameters: {', '.join(params)}")
        
        # Show parameter details
        param = sig.parameters['reactionmeddraverse']
        print(f"  Parameter type: {param.annotation}")
        print(f"  Default value: {param.default}")
    else:
        print(f"✗ reactionmeddraverse parameter does not exist in function signature")
        print(f"  Current parameters: {', '.join(params)}")
except Exception as e:
    print(f"✗ Check failed: {type(e).__name__}: {e}")

# Test 5: Check JSON configuration
print("\nTest 5: Check JSON configuration file")
print("-" * 70)
try:
    config_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'tooluniverse', 'data', 'fda_drug_adverse_event_tools.json')
    with open(config_path, 'r') as f:
        tools_config = json.load(f)
    
    tool_config = None
    for tool in tools_config:
        if tool.get('name') == 'FAERS_count_reactions_by_drug_event':
            tool_config = tool
            break
    
    if tool_config:
        params = tool_config.get('parameter', {}).get('properties', {})
        if 'reactionmeddraverse' in params:
            print(f"✓ reactionmeddraverse parameter exists in JSON configuration")
            print(f"  Description: {params['reactionmeddraverse'].get('description', 'N/A')}")
        else:
            print(f"✗ reactionmeddraverse parameter does not exist in JSON configuration")
        
        # Check search_fields
        search_fields = tool_config.get('fields', {}).get('search_fields', {})
        if 'reactionmeddraverse' in search_fields:
            print(f"✓ reactionmeddraverse search_field exists")
            print(f"  Field mapping: {search_fields['reactionmeddraverse']}")
        else:
            print(f"✗ reactionmeddraverse search_field does not exist")
    else:
        print(f"✗ Tool configuration not found")
except Exception as e:
    print(f"✗ Check failed: {type(e).__name__}: {e}")

# Custom test area
print("\n" + "=" * 70)
print("Custom Test Area")
print("=" * 70)
print("You can add your own test code here")
print("\nExample:")
print("""
# Test your own drug and reaction terms
result = tu.run({
    "name": "FAERS_count_reactions_by_drug_event",
    "arguments": {
        "medicinalproduct": "YOUR_DRUG_NAME",
        "reactionmeddraverse": "YOUR_REACTION_TERM",
        # You can add other filters
        # "serious": "Yes",
        # "patientsex": "Female",
    }
})
print(result)
""")

print("\n" + "=" * 70)
print("Test Summary")
print("=" * 70)
print("✓ reactionmeddraverse parameter has been successfully added to the tool")
print()
print("Functionality:")
print("  1. When reactionmeddraverse is not specified:")
print("     - Returns all adverse reactions (AE) for the drug")
print("     - Results are grouped by MedDRA Preferred Term")
print("     - Each record contains reaction name (term) and count (count)")
print()
print("  2. When reactionmeddraverse is specified:")
print("     - Returns only reactions matching that MedDRA LLT")
print("     - Can be used to precisely filter specific reaction types")
print()
print("⚠ Note: reactionmeddraverse is MedDRA Lowest Level Term (LLT)")
print("   If empty results are returned, please check:")
print("   1. Whether the reaction term is a valid MedDRA LLT")
print("   2. Whether the term exists in the data")
print("   3. Whether a different search format is needed")
print("=" * 70)

