#!/usr/bin/env python3
"""
Usage examples for dbSNP tools in ToolUniverse

This script demonstrates how to use the dbSNP database tools for variant lookup,
gene-based searches, and allele frequency analysis.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.tooluniverse import ToolUniverse

def example_get_variant_by_rsid():
    """Get variant information by rsID"""
    print("🧬 Getting variant information for rs429358...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.run({
        "name": "dbsnp_get_variant_by_rsid",
        "arguments": {
            "rsid": "rs429358"  # APOE ε4 variant
        }
    })
    
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        data = result.get('data', {})
        print(f"rsID: {result.get('rsid')}")
        print(f"dbSNP ID: {data.get('refsnp_id')}")
        print(f"Chromosome: {data.get('chromosome')}")
        print(f"Position: {data.get('position')}")
        print(f"Allele: {data.get('allele')}")
        print(f"SNP Class: {data.get('snp_class')}")
        print(f"Genes: {', '.join(data.get('genes', []))}")
        print(f"Clinical Significance: {', '.join(data.get('clinical_significance', []))}")
        print(f"Function Class: {', '.join(data.get('function_class', []))}")
    else:
        print(f"Error: {result.get('error')}")
    
    return result

def example_get_variant_without_rs_prefix():
    """Get variant information without 'rs' prefix"""
    print("\n🧬 Getting variant information for 429358 (without rs prefix)...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.run({
        "name": "dbsnp_get_variant_by_rsid",
        "arguments": {
            "rsid": "429358"  # Without rs prefix
        }
    })
    
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        data = result.get('data', {})
        print(f"rsID: {result.get('rsid')}")
        print(f"dbSNP ID: {data.get('refsnp_id')}")
        print(f"Chromosome: {data.get('chromosome')}")
        print(f"Position: {data.get('position')}")
        print(f"Allele: {data.get('allele')}")
    else:
        print(f"Error: {result.get('error')}")
    
    return result

def example_search_by_gene():
    """Search for variants in BRCA1 gene"""
    print("\n🧬 Searching for variants in BRCA1 gene...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.run({
        "name": "dbsnp_search_by_gene",
        "arguments": {
            "gene_symbol": "BRCA1",
            "limit": 10
        }
    })
    
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        data = result.get('data', {})
        variants = data.get('variants', [])
        print(f"Found {len(variants)} variants in {result.get('gene_symbol')}")
        for i, variant in enumerate(variants[:5]):  # Show first 5
            print(f"  {i+1}. {variant.get('refsnp_id')} at position {variant.get('position')}")
    else:
        print(f"Error: {result.get('error')}")
    
    return result

def example_get_frequencies():
    """Get allele frequencies for a variant"""
    print("\n🧬 Getting allele frequencies for rs429358...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.run({
        "name": "dbsnp_get_frequencies",
        "arguments": {
            "rsid": "rs429358"
        }
    })
    
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        data = result.get('data', {})
        frequencies = data.get('frequencies', [])
        print(f"rsID: {result.get('rsid')}")
        print(f"Found {len(frequencies)} frequency records")
        for freq in frequencies[:3]:  # Show first 3
            print(f"  Study: {freq.get('study')}, Allele: {freq.get('allele')}, Frequency: {freq.get('frequency')}, Samples: {freq.get('sample_count')}")
    else:
        print(f"Error: {result.get('error')}")
    
    return result

def example_combined_search():
    """Search for variants and get details for the first result"""
    print("\n🔗 Combined gene search and variant details...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # First search for variants in TP53
    search_result = tu.run({
        "name": "dbsnp_search_by_gene",
        "arguments": {
            "gene_symbol": "TP53",
            "limit": 3
        }
    })
    
    if search_result.get('status') == 'success':
        data = search_result.get('data', {})
        variants = data.get('variants', [])
        
        if variants:
            print(f"Found {len(variants)} variants in TP53")
            first_variant = variants[0]
            rsid = first_variant.get('refsnp_id')
            
            if rsid:
                print(f"Getting details for {rsid}...")
                
                # Get details for first variant
                details_result = tu.run({
                    "name": "dbsnp_get_variant_by_rsid",
                    "arguments": {
                        "rsid": rsid
                    }
                })
                
                print(f"Details status: {details_result.get('status')}")
                if details_result.get('status') == 'success':
                    details_data = details_result.get('data', {})
                    print(f"Successfully retrieved details for {rsid}")
                    print(f"dbSNP ID: {details_data.get('refsnp_id')}")
                else:
                    print(f"Error getting details: {details_result.get('error')}")
        else:
            print("No variants found")
    else:
        print(f"Search failed: {search_result.get('error')}")
    
    return search_result

def main():
    """Run all dbSNP tool examples"""
    print("🚀 dbSNP Tools Usage Examples")
    print("=" * 40)
    
    try:
        # Run examples
        example_get_variant_by_rsid()
        example_get_variant_without_rs_prefix()
        example_search_by_gene()
        example_get_frequencies()
        example_combined_search()
        
        print("\n✅ All examples completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
