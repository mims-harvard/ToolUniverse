#!/usr/bin/env python3
"""
Usage examples for ClinVar tools in ToolUniverse

This script demonstrates how to use the ClinVar database tools for clinical variant
search, detailed variant information retrieval, and clinical significance analysis.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.tooluniverse import ToolUniverse

def example_search_variants_by_gene():
    """Search for variants in BRCA1 gene"""
    print("🔍 Searching for BRCA1 variants in ClinVar...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.run({
        "name": "clinvar_search_variants",
        "arguments": {
            "gene": "BRCA1",
            "max_results": 10
        }
    })
    
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        if 'formatted_results' in result:
            formatted = result['formatted_results']
            print(f"Summary: {formatted['summary']}")
            print(f"Total count: {formatted['total_count']}")
            print(f"Variant IDs: {formatted['variant_ids'][:5]}")  # Show first 5
            print(f"Query translation: {formatted['query_translation']}")
        else:
            # Fallback to original format
            data = result.get('data', {})
            esearch = data.get('esearchresult', {})
            print(f"Found {esearch.get('count')} variants")
            idlist = esearch.get('idlist', [])
            print(f"Variant IDs: {idlist[:5]}")  # Show first 5
    else:
        print(f"Error: {result.get('error')}")
    
    return result

def example_search_variants_by_condition():
    """Search for variants associated with breast cancer"""
    print("\n🔍 Searching for breast cancer variants in ClinVar...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.run({
        "name": "clinvar_search_variants",
        "arguments": {
            "condition": "breast cancer",
            "max_results": 5
        }
    })
    
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        if 'formatted_results' in result:
            formatted = result['formatted_results']
            print(f"Summary: {formatted['summary']}")
            print(f"Total count: {formatted['total_count']}")
            print(f"Variant IDs: {formatted['variant_ids']}")
            print(f"Query translation: {formatted['query_translation']}")
        else:
            # Fallback to original format
            data = result.get('data', {})
            esearch = data.get('esearchresult', {})
            print(f"Found {esearch.get('count')} variants")
            idlist = esearch.get('idlist', [])
            print(f"Variant IDs: {idlist}")
    else:
        print(f"Error: {result.get('error')}")
    
    return result

def example_get_variant_details():
    """Get detailed information for a specific variant"""
    print("\n📊 Getting detailed variant information...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # Use a known ClinVar variant ID (this is an example)
    result = tu.run({
        "name": "clinvar_get_variant_details",
        "arguments": {
            "variant_id": "4279240"  # Use a real variant ID
        }
    })
    
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        if 'formatted_data' in result:
            formatted = result['formatted_data']
            print(f"Variant ID: {formatted['variant_id']}")
            print(f"Accession: {formatted['accession']}")
            print(f"Title: {formatted['title']}")
            print(f"Object Type: {formatted['obj_type']}")
            print(f"Genes: {formatted['genes'][:5]}")  # Show first 5 genes
            print(f"Clinical Significance: {formatted['clinical_significance']}")
            print(f"Review Status: {formatted['review_status']}")
            print(f"Chromosome: {formatted['chromosome']}")
            print(f"Location: {formatted['location']}")
        else:
            # Fallback to original format
            data = result.get('data', {})
            print(f"Variant ID: {result.get('variant_id')}")
            print(f"Data type: {type(data)}")
            if isinstance(data, dict):
                print(f"Data keys: {list(data.keys())}")
    else:
        print(f"Error: {result.get('error')}")
    
    return result

def example_get_clinical_significance():
    """Get clinical significance for a variant"""
    print("\n🏥 Getting clinical significance information...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.run({
        "name": "clinvar_get_clinical_significance",
        "arguments": {
            "variant_id": "4279240"  # Use a real variant ID
        }
    })
    
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        if 'formatted_data' in result:
            formatted = result['formatted_data']
            print(f"Variant ID: {formatted['variant_id']}")
            print("Germline Classification:")
            print(f"  Description: {formatted['germline_classification']['description']}")
            print(f"  Review Status: {formatted['germline_classification']['review_status']}")
            print(f"  Last Evaluated: {formatted['germline_classification']['last_evaluated']}")
            print(f"  FDA Recognized: {formatted['germline_classification']['fda_recognized']}")
            print(f"  Traits: {formatted['germline_classification']['traits']}")
            print("Clinical Impact:")
            print(f"  Description: {formatted['clinical_impact']['description']}")
            print(f"  Review Status: {formatted['clinical_impact']['review_status']}")
            print("Oncogenicity:")
            print(f"  Description: {formatted['oncogenicity']['description']}")
            print(f"  Review Status: {formatted['oncogenicity']['review_status']}")
        else:
            # Fallback to original format
            data = result.get('data', {})
            print(f"Variant ID: {result.get('variant_id')}")
            print(f"Data type: {type(data)}")
            if isinstance(data, dict):
                print(f"Data keys: {list(data.keys())}")
    else:
        print(f"Error: {result.get('error')}")
    
    return result

def example_combined_search():
    """Search for variants and get details for the first result"""
    print("\n🔗 Combined search and details retrieval...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # First search for variants
    search_result = tu.run({
        "name": "clinvar_search_variants",
        "arguments": {
            "gene": "BRCA2",
            "max_results": 3
        }
    })
    
    if search_result.get('status') == 'success':
        data = search_result.get('data', {})
        esearch = data.get('esearchresult', {})
        idlist = esearch.get('idlist', [])
        
        if idlist:
            print(f"Found {len(idlist)} variants, getting details for first one...")
            
            # Get details for first variant
            details_result = tu.run({
                "name": "clinvar_get_variant_details",
                "arguments": {
                    "variant_id": idlist[0]
                }
            })
            
            print(f"Details status: {details_result.get('status')}")
            if details_result.get('status') == 'success':
                print(f"Successfully retrieved details for variant {idlist[0]}")
            else:
                print(f"Error getting details: {details_result.get('error')}")
        else:
            print("No variants found")
    else:
        print(f"Search failed: {search_result.get('error')}")
    
    return search_result

def main():
    """Run all ClinVar tool examples"""
    print("🚀 ClinVar Tools Usage Examples")
    print("=" * 40)
    
    try:
        # Run examples
        example_search_variants_by_gene()
        example_search_variants_by_condition()
        example_get_variant_details()
        example_get_clinical_significance()
        example_combined_search()
        
        print("\n✅ All examples completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
