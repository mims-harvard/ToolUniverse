#!/usr/bin/env python3
"""
InterPro Protein Domain Analysis Example

This example shows how to use the InterPro tool to analyze protein domains
and functional annotations for well-known proteins.
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
    
    print("🧬 InterPro Protein Domain Analysis Examples")
    print("=" * 50)
    
    # Example 1: Analyze p53 protein domains
    print("\n1. Analyzing p53 protein domains (P04637)")
    print("-" * 40)
    
    result = tu.run({"name": "InterPro_get_protein_domains", "arguments": {
        "protein_id": "P04637"
    }})
    
    print(f"Result type: {type(result)}")
    print(f"Result: {result}")
    
    if result and result.get("status") == "success":
        data = result.get("data", [])
        print(f"✅ Found {len(data)} domain annotations")
        
        # Show key domains
        for domain in data[:3]:
            print(f"   • {domain.get('metadata', {}).get('name', 'Unknown')}")
            print(f"     Type: {domain.get('metadata', {}).get('type', 'Unknown')}")
            print(f"     Source: {domain.get('metadata', {}).get('source_database', 'Unknown')}")
    else:
        print(f"❌ Error: {result.get('error') if result else 'No result returned'}")
    
    # Example 2: Analyze BRCA1 protein domains
    print("\n2. Analyzing BRCA1 protein domains (P38398)")
    print("-" * 40)
    
    result = tu.run({"name": "InterPro_get_protein_domains", "arguments": {
        "protein_id": "P38398"
    }})
    
    if result and result.get("status") == "success":
        data = result.get("data", [])
        print(f"✅ Found {len(data)} domain annotations")
        
        for domain in data[:2]:
            print(f"   • {domain.get('metadata', {}).get('name', 'Unknown')}")
    else:
        print(f"❌ Error: {result.get('error') if result else 'No result returned'}")
    
    # Example 3: Analyze insulin protein domains
    print("\n3. Analyzing insulin protein domains (P01308)")
    print("-" * 40)
    
    result = tu.run({"name": "InterPro_get_protein_domains", "arguments": {
        "protein_id": "P01308"
    }})
    
    if result and result.get("status") == "success":
        data = result.get("data", [])
        print(f"✅ Found {len(data)} domain annotations")
        
        for domain in data[:2]:
            print(f"   • {domain.get('metadata', {}).get('name', 'Unknown')}")
    else:
        print(f"❌ Error: {result.get('error') if result else 'No result returned'}")

if __name__ == "__main__":
    main()
