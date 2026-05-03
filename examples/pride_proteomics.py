#!/usr/bin/env python3
"""
PRIDE Proteomics Database Example

This example shows how to use the PRIDE tool to search for proteomics
experiments and datasets from the PRIDE database.
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
    
    print("🧪 PRIDE Proteomics Database Examples")
    print("=" * 40)
    
    # Example 1: Search for cancer proteomics studies
    print("\n1. Searching for cancer proteomics studies")
    print("-" * 40)
    
    result = tu.run({"name": "PRIDE_search_proteomics", "arguments": {
        "query": "cancer",
        "page_size": 5
    }})
    
    if result and result.get("status") == "success":
        data = result.get("data", [])
        print(f"✅ Found {len(data)} proteomics experiments")
        
        for i, exp in enumerate(data[:3], 1):
            title = exp.get("title", "Unknown")
            accession = exp.get("accession", "Unknown")
            print(f"   {i}. {accession}: {title[:80]}...")
    else:
        print(f"❌ Error: {result.get('error')}")
    
    # Example 2: Search for brain proteomics studies
    print("\n2. Searching for brain proteomics studies")
    print("-" * 40)
    
    result = tu.run({"name": "PRIDE_search_proteomics", "arguments": {
        "query": "brain",
        "page_size": 4
    }})
    
    if result and result.get("status") == "success":
        data = result.get("data", [])
        print(f"✅ Found {len(data)} proteomics experiments")
        
        for i, exp in enumerate(data[:2], 1):
            title = exp.get("title", "Unknown")
            accession = exp.get("accession", "Unknown")
            print(f"   {i}. {accession}: {title[:80]}...")
    else:
        print(f"❌ Error: {result.get('error')}")
    
    # Example 3: Search for specific species studies
    print("\n3. Searching for human proteomics studies")
    print("-" * 40)
    
    result = tu.run({"name": "PRIDE_search_proteomics", "arguments": {
        "query": "human",
        "page_size": 4
    }})
    
    if result and result.get("status") == "success":
        data = result.get("data", [])
        print(f"✅ Found {len(data)} proteomics experiments")
        
        for i, exp in enumerate(data[:2], 1):
            title = exp.get("title", "Unknown")
            accession = exp.get("accession", "Unknown")
            species = exp.get("species", ["Unknown"])[0] if exp.get("species") else "Unknown"
            print(f"   {i}. {accession}: {title[:60]}...")
            print(f"      Species: {species}")

if __name__ == "__main__":
    main()
