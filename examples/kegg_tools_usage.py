#!/usr/bin/env python3
"""
Usage examples for KEGG tools in ToolUniverse

This script demonstrates how to use the KEGG database tools for pathway analysis,
gene search, and organism information retrieval.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.tooluniverse import ToolUniverse

def example_search_pathways():
    """Search for pathways related to diabetes"""
    print("🔍 Searching for diabetes-related pathways...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.run({
        "name": "kegg_search_pathway",
        "arguments": {
            "keyword": "diabetes"
        }
    })
    
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        data = result.get('data', [])
        print(f"Found {len(data)} pathways:")
        for pathway in data[:5]:  # Show first 5
            print(f"  - {pathway['pathway_id']}: {pathway['description']}")
    else:
        print(f"Error: {result.get('error')}")
    
    return result

def example_get_pathway_info():
    """Get detailed information about a specific pathway"""
    print("\n📊 Getting pathway information for glycolysis...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.run({
        "name": "kegg_get_pathway_info",
        "arguments": {
            "pathway_id": "hsa00010"  # Glycolysis pathway
        }
    })
    
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        data = result.get('data', {})
        print(f"Pathway ID: {data.get('pathway_id')}")
        print(f"Data lines: {data.get('lines')}")
        print("Raw data preview:")
        print(data.get('raw_data', '')[:200] + "...")
    else:
        print(f"Error: {result.get('error')}")
    
    return result

def example_find_genes():
    """Find genes related to insulin in human"""
    print("\n🧬 Finding insulin-related genes in human...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.run({
        "name": "kegg_find_genes",
        "arguments": {
            "keyword": "insulin",
            "organism": "hsa"  # Human
        }
    })
    
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        data = result.get('data', [])
        print(f"Found {len(data)} genes:")
        for gene in data[:5]:  # Show first 5
            print(f"  - {gene['gene_id']}: {gene['description']}")
    else:
        print(f"Error: {result.get('error')}")
    
    return result

def example_get_gene_info():
    """Get detailed information about a specific gene"""
    print("\n🧬 Getting gene information for insulin gene...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.run({
        "name": "kegg_get_gene_info",
        "arguments": {
            "gene_id": "hsa:348"  # INS gene
        }
    })
    
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        data = result.get('data', {})
        print(f"Gene ID: {data.get('gene_id')}")
        print(f"Data lines: {data.get('lines')}")
        print("Raw data preview:")
        print(data.get('raw_data', '')[:200] + "...")
    else:
        print(f"Error: {result.get('error')}")
    
    return result

def example_list_organisms():
    """List available organisms in KEGG"""
    print("\n🌍 Listing available organisms...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.run({
        "name": "kegg_list_organisms",
        "arguments": {}
    })
    
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        data = result.get('data', [])
        print(f"Found {len(data)} organisms:")
        for org in data[:10]:  # Show first 10
            print(f"  - {org['organism_code']}: {org['organism_name']}")
    else:
        print(f"Error: {result.get('error')}")
    
    return result

def main():
    """Run all KEGG tool examples"""
    print("🚀 KEGG Tools Usage Examples")
    print("=" * 40)
    
    try:
        # Run examples
        example_search_pathways()
        example_get_pathway_info()
        example_find_genes()
        example_get_gene_info()
        example_list_organisms()
        
        print("\n✅ All examples completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
