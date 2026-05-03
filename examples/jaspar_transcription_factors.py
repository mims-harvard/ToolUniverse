#!/usr/bin/env python3
"""
JASPAR Transcription Factor Analysis Example

This example shows how to use the JASPAR tool to query transcription factor
binding site matrices for important regulatory proteins.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.tooluniverse import ToolUniverse

def main():
    # Initialize ToolUniverse
    tu = ToolUniverse()
    
    # Load tools first
    tu.load_tools()
    
    print("🧬 JASPAR Transcription Factor Analysis Examples")
    print("=" * 55)
    
    # Example 1: Query p53 transcription factor matrices
    print("\n1. Querying p53 transcription factor matrices")
    print("-" * 45)
    
    result = tu.run({"name": "JASPAR_get_transcription_factors", "arguments": {
        "collection": "CORE",
        "limit": 5
    }})
    
    if result and result.get("status") == "success":
        data = result.get("data", {})
        results = data.get("results", [])
        print(f"✅ Found {len(results)} transcription factor matrices")
        
        for i, tf in enumerate(results[:3], 1):
            name = tf.get("name", "Unknown")
            tf_id = tf.get("matrix_id", "Unknown")
            print(f"   {i}. {name} (ID: {tf_id})")
    else:
        print(f"❌ Error: {result.get('error')}")
    
    # Example 2: Query specific transcription factors
    print("\n2. Querying specific transcription factors")
    print("-" * 40)
    
    result = tu.run({"name": "JASPAR_get_transcription_factors", "arguments": {
        "collection": "CORE",
        "limit": 8
    }})
    
    if result and result.get("status") == "success":
        data = result.get("data", {})
        results = data.get("results", [])
        print(f"✅ Found {len(results)} transcription factor matrices")
        
        # Show different types of transcription factors
        for i, tf in enumerate(results[:4], 1):
            name = tf.get("name", "Unknown")
            tf_id = tf.get("matrix_id", "Unknown")
            species = tf.get("species", ["Unknown"])[0] if tf.get("species") else "Unknown"
            print(f"   {i}. {name} ({species}) - {tf_id}")
    else:
        print(f"❌ Error: {result.get('error')}")
    
    # Example 3: Query transcription factors by species
    print("\n3. Querying transcription factors by species")
    print("-" * 40)
    
    result = tu.run({"name": "JASPAR_get_transcription_factors", "arguments": {
        "collection": "CORE",
        "limit": 6
    }})
    
    if result and result.get("status") == "success":
        data = result.get("data", {})
        results = data.get("results", [])
        print(f"✅ Found {len(results)} transcription factor matrices")
        
        # Group by species
        species_count = {}
        for tf in results:
            species = tf.get("species", ["Unknown"])[0] if tf.get("species") else "Unknown"
            species_count[species] = species_count.get(species, 0) + 1
        
        print("   Species distribution:")
        for species, count in list(species_count.items())[:3]:
            print(f"     • {species}: {count} matrices")

if __name__ == "__main__":
    main()
