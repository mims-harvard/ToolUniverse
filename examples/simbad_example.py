#!/usr/bin/env python3
"""
Example demonstrating the use of SIMBAD tools in ToolUniverse.

This script shows how to:
1. Query objects by name
2. Search by coordinates
3. Search by identifier patterns
4. Execute advanced ADQL queries
"""

from tooluniverse import ToolUniverse


def main():
    """Main function demonstrating SIMBAD tool usage."""
    
    # Initialize ToolUniverse
    print("Initializing ToolUniverse...")
    tu = ToolUniverse()
    tu.load_tools()
    
    print("\n" + "="*70)
    print("SIMBAD Tool Examples")
    print("="*70)
    
    # Example 1: Query by object name
    print("\n1. Query the Andromeda Galaxy (M31) by name:")
    print("-" * 70)
    
    result = tu.run_one_function({
        "name": "SIMBAD_query_object",
        "arguments": {
            "query_type": "object_name",
            "object_name": "M31",
            "output_format": "detailed"
        }
    })
    
    if result.get("success"):
        print(f"✓ Found {result['count']} object(s)")
        for obj in result["results"]:
            print(f"  - Name: {obj['main_id']}")
            print(f"    Coordinates: {obj['coordinates']}")
            print(f"    Type: {obj['object_type']}")
    else:
        print(f"✗ Error: {result.get('error')}")
    
    # Example 2: Query by coordinates
    print("\n2. Search for objects near Andromeda's coordinates:")
    print("-" * 70)
    
    result = tu.run_one_function({
        "name": "SIMBAD_query_object",
        "arguments": {
            "query_type": "coordinates",
            "ra": 10.68458,
            "dec": 41.26917,
            "radius": 5.0,
            "max_results": 5
        }
    })
    
    if result.get("success"):
        print(f"✓ Found {result['count']} object(s) within 5 arcminutes")
        for i, obj in enumerate(result["results"], 1):
            print(f"  {i}. {obj['main_id']} ({obj['object_type']})")
    else:
        print(f"✗ Error: {result.get('error')}")
    
    # Example 3: Query by identifier pattern
    print("\n3. Search for NGC objects starting with '10':")
    print("-" * 70)
    
    result = tu.run_one_function({
        "name": "SIMBAD_query_object",
        "arguments": {
            "query_type": "identifier",
            "identifier": "NGC 10*",
            "max_results": 5
        }
    })
    
    if result.get("success"):
        print(f"✓ Found {result['count']} object(s)")
        for obj in result["results"][:5]:
            print(f"  - {obj['main_id']}: {obj['object_type']}")
    else:
        print(f"✗ Error: {result.get('error')}")
    
    # Example 4: Query a famous star
    print("\n4. Get information about Sirius (brightest star):")
    print("-" * 70)
    
    result = tu.run_one_function({
        "name": "SIMBAD_query_object",
        "arguments": {
            "object_name": "Sirius",
            "output_format": "full"
        }
    })
    
    if result.get("success"):
        print(f"✓ Query successful")
        obj = result["results"][0]
        print(f"  - Main ID: {obj['main_id']}")
        print(f"  - Coordinates: {obj['coordinates']}")
        print(f"  - Object Type: {obj['object_type']}")
        if "spectral_type" in obj:
            print(f"  - Spectral Type: {obj['spectral_type']}")
        if "flux" in obj:
            print(f"  - Flux: {obj['flux']}")
    else:
        print(f"✗ Error: {result.get('error')}")
    
    # Example 5: Advanced ADQL query
    print("\n5. Advanced query: Find nearby stars using ADQL:")
    print("-" * 70)
    
    result = tu.run_one_function({
        "name": "SIMBAD_advanced_query",
        "arguments": {
            "adql_query": "SELECT TOP 5 main_id, ra, dec, otype FROM basic WHERE otype LIKE 'Star*' AND ra BETWEEN 0 AND 10",
            "max_results": 5,
            "format": "json"
        }
    })
    
    if result.get("success"):
        print(f"✓ ADQL query executed successfully")
        print(f"  Query: {result['query']}")
        if isinstance(result["results"], dict) and "data" in result["results"]:
            print(f"  Found {len(result['results']['data'])} results")
        else:
            print(f"  Results: {result['results']}")
    else:
        print(f"✗ Error: {result.get('error')}")
    
    print("\n" + "="*70)
    print("Examples completed!")
    print("="*70)


if __name__ == "__main__":
    main()
