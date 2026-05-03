#!/usr/bin/env python3
"""
Example script for CIViC (Clinical Interpretation of Variants in Cancer) Tools.

This example demonstrates how to use all CIViC tools to:
- Search for genes, variants, evidence items, assertions, molecular profiles
- Get detailed information by ID
- Browse diseases and therapies
- Explore cancer variant interpretations

CIViC is a community knowledgebase for expert-curated interpretations of variants in cancer.
"""

import os
import sys
import json

# Ensure src is in path to import tooluniverse
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from tooluniverse import ToolUniverse

def print_result(tool_name, result):
    """Print formatted result."""
    print(f"\n{'='*80}")
    print(f"Results for {tool_name}")
    print(f"{'='*80}")
    if result and "error" not in result:
        # Print summary
        data = result.get("data", {})
        if data:
            print(f"✅ Success!")
            print(f"Response keys: {list(data.keys())}")
            
            # Print a sample of the data
            result_str = json.dumps(result, indent=2)
            if len(result_str) > 1000:
                print(f"\nResponse preview (first 1000 chars):")
                print(result_str[:1000] + "...")
            else:
                print(f"\nFull response:")
                print(result_str)
        else:
            print("⚠️  No data returned")
    elif "error" in result:
        print(f"❌ Error: {result.get('error')}")
        if "errors" in result:
            print(f"   Details: {result.get('errors')}")
    else:
        print("❌ No result found or error occurred.")
    print("-" * 80)

def main():
    print("="*80)
    print("CIViC Tools Example")
    print("="*80)
    print("\nInitializing ToolUniverse...")
    tu = ToolUniverse()
    tu.load_tools(tool_type=["civic"])
    
    # Example 1: Search for genes
    print("\n" + "="*80)
    print("Example 1: Search for genes in CIViC")
    print("="*80)
    try:
        result = tu.run_one_function({
            "name": "civic_search_genes",
            "arguments": {"limit": 5}
        })
        print_result("civic_search_genes", result)
        
        # Extract gene IDs for later examples
        gene_id = None
        if result and "data" in result:
            genes = result["data"].get("genes", {}).get("nodes", [])
            if genes:
                gene_id = genes[0].get("id")
                print(f"\n📋 Found {len(genes)} genes:")
                for i, gene in enumerate(genes[:5], 1):
                    print(f"   {i}. {gene.get('name')} (ID: {gene.get('id')}) - {gene.get('description', 'No description')[:50]}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Example 2: Get variants by gene
    if gene_id:
        print("\n" + "="*80)
        print(f"Example 2: Get variants for gene ID {gene_id}")
        print("="*80)
        try:
            result = tu.run_one_function({
                "name": "civic_get_variants_by_gene",
                "arguments": {"gene_id": gene_id, "limit": 5}
            })
            print_result("civic_get_variants_by_gene", result)
            
            if result and "data" in result:
                gene_data = result["data"].get("gene", {})
                variants = gene_data.get("variants", {}).get("nodes", [])
                print(f"\n🧬 Gene: {gene_data.get('name')}")
                print(f"   Found {len(variants)} variants:")
                for i, variant in enumerate(variants[:5], 1):
                    print(f"      {i}. {variant.get('name')} (ID: {variant.get('id')})")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Example 3: Search for variants
    print("\n" + "="*80)
    print("Example 3: Search for variants")
    print("="*80)
    try:
        result = tu.run_one_function({
            "name": "civic_search_variants",
            "arguments": {"limit": 5}
        })
        print_result("civic_search_variants", result)
        
        variant_id = None
        if result and "data" in result:
            variants = result["data"].get("variants", {}).get("nodes", [])
            if variants:
                variant_id = variants[0].get("id")
                print(f"\n🔬 Found {len(variants)} variants:")
                for i, variant in enumerate(variants[:5], 1):
                    print(f"   {i}. {variant.get('name')} (ID: {variant.get('id')})")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Example 4: Get variant by ID
    if variant_id:
        print("\n" + "="*80)
        print(f"Example 4: Get variant details for variant ID {variant_id}")
        print("="*80)
        try:
            result = tu.run_one_function({
                "name": "civic_get_variant",
                "arguments": {"variant_id": variant_id}
            })
            print_result("civic_get_variant", result)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Example 5: Search for evidence items
    print("\n" + "="*80)
    print("Example 5: Search for evidence items")
    print("="*80)
    try:
        result = tu.run_one_function({
            "name": "civic_search_evidence_items",
            "arguments": {"limit": 5}
        })
        print_result("civic_search_evidence_items", result)
        
        evidence_id = None
        if result and "data" in result:
            evidence_items = result["data"].get("evidenceItems", {}).get("nodes", [])
            if evidence_items:
                evidence_id = evidence_items[0].get("id")
                print(f"\n📚 Found {len(evidence_items)} evidence items:")
                for i, item in enumerate(evidence_items[:5], 1):
                    desc = item.get("description", "")[:80]
                    level = item.get("evidenceLevel", "N/A")
                    etype = item.get("evidenceType", "N/A")
                    print(f"   {i}. [{level}] {etype}: {desc}...")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Example 6: Get evidence item by ID
    if evidence_id:
        print("\n" + "="*80)
        print(f"Example 6: Get evidence item details for ID {evidence_id}")
        print("="*80)
        try:
            result = tu.run_one_function({
                "name": "civic_get_evidence_item",
                "arguments": {"evidence_id": evidence_id}
            })
            print_result("civic_get_evidence_item", result)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Example 7: Search for assertions
    print("\n" + "="*80)
    print("Example 7: Search for assertions")
    print("="*80)
    try:
        result = tu.run_one_function({
            "name": "civic_search_assertions",
            "arguments": {"limit": 5}
        })
        print_result("civic_search_assertions", result)
        
        if result and "data" in result:
            assertions = result["data"].get("assertions", {}).get("nodes", [])
            print(f"\n📋 Found {len(assertions)} assertions")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Example 8: Search for molecular profiles
    print("\n" + "="*80)
    print("Example 8: Search for molecular profiles")
    print("="*80)
    try:
        result = tu.run_one_function({
            "name": "civic_search_molecular_profiles",
            "arguments": {"limit": 5}
        })
        print_result("civic_search_molecular_profiles", result)
        
        profile_id = None
        if result and "data" in result:
            profiles = result["data"].get("molecularProfiles", {}).get("nodes", [])
            if profiles:
                profile_id = profiles[0].get("id")
                print(f"\n🧪 Found {len(profiles)} molecular profiles:")
                for i, profile in enumerate(profiles[:5], 1):
                    print(f"   {i}. {profile.get('name', 'Unknown')} (ID: {profile.get('id')})")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Example 9: Get molecular profile by ID
    if profile_id:
        print("\n" + "="*80)
        print(f"Example 9: Get molecular profile details for ID {profile_id}")
        print("="*80)
        try:
            result = tu.run_one_function({
                "name": "civic_get_molecular_profile",
                "arguments": {"molecular_profile_id": profile_id}
            })
            print_result("civic_get_molecular_profile", result)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Example 10: Search for diseases
    print("\n" + "="*80)
    print("Example 10: Search for diseases")
    print("="*80)
    try:
        result = tu.run_one_function({
            "name": "civic_search_diseases",
            "arguments": {"limit": 5}
        })
        print_result("civic_search_diseases", result)
        
        if result and "data" in result:
            diseases = result["data"].get("browseDiseases", {}).get("nodes", [])
            print(f"\n🏥 Found {len(diseases)} diseases:")
            for i, disease in enumerate(diseases[:5], 1):
                print(f"   {i}. {disease.get('name')} (ID: {disease.get('id')})")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Example 11: Search for therapies
    print("\n" + "="*80)
    print("Example 11: Search for therapies")
    print("="*80)
    try:
        result = tu.run_one_function({
            "name": "civic_search_therapies",
            "arguments": {"limit": 5}
        })
        print_result("civic_search_therapies", result)
        
        if result and "data" in result:
            therapies = result["data"].get("browseTherapies", {}).get("nodes", [])
            print(f"\n💊 Found {len(therapies)} therapies:")
            for i, therapy in enumerate(therapies[:5], 1):
                print(f"   {i}. {therapy.get('name')} (ID: {therapy.get('id')})")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "="*80)
    print("CIViC Tools Example Complete!")
    print("="*80)
    print("\n💡 Tips:")
    print("   - Start with civic_search_genes to find genes of interest")
    print("   - Use civic_get_variants_by_gene to explore variants for a gene")
    print("   - Evidence items link variants to clinical outcomes")
    print("   - Assertions integrate multiple evidence items")
    print("   - Molecular profiles represent biomarker combinations")
    print("   - Use browse tools (diseases, therapies) to explore available entities")
    print("   - All tools support limit parameter for pagination")

if __name__ == "__main__":
    main()
