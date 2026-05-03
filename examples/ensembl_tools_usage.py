#!/usr/bin/env python3
"""
Usage examples for Ensembl tools in ToolUniverse

This script demonstrates how to use the Ensembl genome browser tools for gene lookup,
sequence retrieval, variant analysis, and homology searches.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.tooluniverse import ToolUniverse

def example_lookup_gene():
    """Lookup gene information by Ensembl ID"""
    print("🧬 Looking up BRCA2 gene information...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.run({
        "name": "ensembl_lookup_gene",
        "arguments": {
            "gene_id": "ENSG00000139618"  # BRCA2 gene
        }
    })
    
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        data = result.get('data', {})
        print(f"Gene ID: {data.get('id')}")
        print(f"Symbol: {data.get('display_name')}")
        print(f"Description: {data.get('description')}")
        print(f"Biotype: {data.get('biotype')}")
        print(f"Location: {data.get('seq_region_name')}:{data.get('start')}-{data.get('end')}")
    else:
        print(f"Error: {result.get('error')}")
    
    return result

def example_lookup_gene_by_symbol():
    """Lookup gene information by gene symbol (Note: This example uses Ensembl ID since the API requires it)"""
    print("\n🧬 Looking up BRCA1 gene by Ensembl ID...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.run({
        "name": "ensembl_lookup_gene",
        "arguments": {
            "gene_id": "ENSG00000012048"  # BRCA1 gene ID
        }
    })
    
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        data = result.get('data', {})
        print(f"Gene ID: {data.get('id')}")
        print(f"Symbol: {data.get('display_name')}")
        print(f"Description: {data.get('description')}")
    else:
        print(f"Error: {result.get('error')}")
    
    return result

def example_get_sequence():
    """Get DNA sequence for a gene"""
    print("\n🧬 Getting genomic sequence for BRCA2...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.run({
        "name": "ensembl_get_sequence",
        "arguments": {
            "sequence_id": "ENSG00000139618",
            "type": "genomic"
        }
    })
    
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        data = result.get('data', [])
        if data:
            seq_info = data[0]
            print(f"Sequence ID: {seq_info.get('id')}")
            print(f"Length: {seq_info.get('length')} bp")
            print(f"Description: {seq_info.get('desc')}")
            print(f"Sequence preview: {seq_info.get('seq', '')[:50]}...")
    else:
        print(f"Error: {result.get('error')}")
    
    return result

def example_get_protein_sequence():
    """Get protein sequence for a gene"""
    print("\n🧬 Getting protein sequence for BRCA2...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.run({
        "name": "ensembl_get_sequence",
        "arguments": {
            "sequence_id": "ENSG00000139618",
            "type": "protein"
        }
    })
    
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        data = result.get('data', [])
        if data:
            seq_info = data[0]
            print(f"Sequence ID: {seq_info.get('id')}")
            print(f"Length: {seq_info.get('length')} aa")
            print(f"Description: {seq_info.get('desc')}")
            print(f"Protein sequence preview: {seq_info.get('seq', '')[:50]}...")
    else:
        print(f"Error: {result.get('error')}")
    
    return result

def example_get_variants():
    """Get variants in a genomic region"""
    print("\n🧬 Getting variants in BRCA2 region...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.run({
        "name": "ensembl_get_variants",
        "arguments": {
            "region": "17:41196312..41196312"  # BRCA2 region
        }
    })
    
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        data = result.get('data', [])
        print(f"Found {len(data)} variants in region")
        for i, variant in enumerate(data[:5]):  # Show first 5
            print(f"  {i+1}. {variant.get('id')}: {variant.get('allele_string')} ({variant.get('consequence_type')})")
    else:
        print(f"Error: {result.get('error')}")
    
    return result


def main():
    """Run all Ensembl tool examples"""
    print("🚀 Ensembl Tools Usage Examples")
    print("=" * 40)
    
    try:
        # Run examples
        example_lookup_gene()
        example_lookup_gene_by_symbol()
        example_get_sequence()
        example_get_protein_sequence()
        example_get_variants()
        
        print("\n✅ All examples completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
