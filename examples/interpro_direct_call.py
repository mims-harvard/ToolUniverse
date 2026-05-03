#!/usr/bin/env python3
"""
InterPro Protein Domain Analysis Example - Direct Tool Call

This example shows how to use the InterPro tool directly to analyze protein domains
and functional annotations for well-known proteins.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.tooluniverse.interpro_tool import InterProRESTTool
import json

def main():
    print("🧬 InterPro Protein Domain Analysis Examples (Direct Call)")
    print("=" * 60)
    
    # Load tool config
    config_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'tooluniverse', 'data', 'interpro_tools.json')
    with open(config_path, 'r') as f:
        configs = json.load(f)
    
    config = configs[0]  # InterPro_get_protein_domains
    tool = InterProRESTTool(config)
    
    # Example 1: Analyze p53 protein domains
    print("\n1. Analyzing p53 protein domains (P04637)")
    print("-" * 40)
    
    result = tool.run({"protein_id": "P04637"})
    
    if result and result.get("status") == "success":
        data = result.get("data", [])
        print(f"✅ Found {len(data)} domain annotations")
        
        # Show key domains
        for i, domain in enumerate(data[:3], 1):
            metadata = domain.get('metadata', {})
            print(f"   {i}. {metadata.get('name', 'Unknown')}")
            print(f"      Type: {metadata.get('type', 'Unknown')}")
            print(f"      Source: {metadata.get('source_database', 'Unknown')}")
            print(f"      Accession: {metadata.get('accession', 'Unknown')}")
            
            # Show GO terms if available
            go_terms = metadata.get('go_terms', [])
            if go_terms:
                print(f"      GO Terms: {', '.join([gt.get('name', '') for gt in go_terms[:3]])}")
    else:
        print(f"❌ Error: {result.get('error') if result else 'No result returned'}")
    
    # Example 2: Analyze BRCA1 protein domains
    print("\n2. Analyzing BRCA1 protein domains (P38398)")
    print("-" * 40)
    
    result = tool.run({"protein_id": "P38398"})
    
    if result and result.get("status") == "success":
        data = result.get("data", [])
        print(f"✅ Found {len(data)} domain annotations")
        
        for i, domain in enumerate(data[:2], 1):
            metadata = domain.get('metadata', {})
            print(f"   {i}. {metadata.get('name', 'Unknown')}")
            print(f"      Type: {metadata.get('type', 'Unknown')}")
    else:
        print(f"❌ Error: {result.get('error') if result else 'No result returned'}")
    
    # Example 3: Analyze insulin protein domains
    print("\n3. Analyzing insulin protein domains (P01308)")
    print("-" * 40)
    
    result = tool.run({"protein_id": "P01308"})
    
    if result and result.get("status") == "success":
        data = result.get("data", [])
        print(f"✅ Found {len(data)} domain annotations")
        
        for i, domain in enumerate(data[:2], 1):
            metadata = domain.get('metadata', {})
            print(f"   {i}. {metadata.get('name', 'Unknown')}")
            print(f"      Type: {metadata.get('type', 'Unknown')}")
    else:
        print(f"❌ Error: {result.get('error') if result else 'No result returned'}")

if __name__ == "__main__":
    main()
