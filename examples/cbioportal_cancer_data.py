#!/usr/bin/env python3
"""
cBioPortal Cancer Data Analysis Example

This example shows how to use the cBioPortal tools to query cancer genomics
data from The Cancer Genome Atlas (TCGA) and other studies.

Updated to use the new cBioPortal API structure (2026).
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
    
    print("🎗️ cBioPortal Cancer Data Analysis Examples")
    print("=" * 60)
    
    # Example 1: Query TCGA breast cancer studies
    print("\n1. Getting cancer studies")
    print("-" * 60)
    
    result = tu.run({"name": "cBioPortal_get_cancer_studies", "arguments": {
        "limit": 5
    }})
    
    if result and result.get("status") == "success":
        data = result.get("data", [])
        print(f"✅ Found {len(data)} cancer studies")
        
        for i, study in enumerate(data[:3], 1):
            study_id = study.get("studyId", "Unknown")
            name = study.get("name", "Unknown")
            sample_count = study.get("allSampleCount", 0)
            print(f"   {i}. {study_id}: {name} ({sample_count} samples)")
    else:
        print(f"❌ Error: {result.get('error')}")
    
    # Example 2: Get molecular profiles
    print("\n2. Getting molecular profiles for breast cancer study")
    print("-" * 60)
    
    result = tu.run({"name": "cBioPortal_get_molecular_profiles", "arguments": {
        "study_id": "brca_tcga"
    }})
    
    if result and result.get("status") == "success":
        data = result.get("data", [])
        print(f"✅ Found {len(data)} molecular profiles")
        print("\nAvailable data types:")
        for profile in data[:5]:
            profile_id = profile.get("molecularProfileId")
            alt_type = profile.get("molecularAlterationType")
            print(f"   - {profile_id}: {alt_type}")
    else:
        print(f"❌ Error: {result.get('error')}")
    
    # Example 3: Get gene information
    print("\n3. Looking up gene information")
    print("-" * 60)
    
    result = tu.run({"name": "cBioPortal_get_genes", "arguments": {
        "keyword": "BRCA2"
    }})
    
    if result and result.get("status") == "success":
        data = result.get("data", [])
        print(f"✅ Found {len(data)} genes")
        if data:
            gene = data[0]
            print(f"   Symbol: {gene.get('hugoGeneSymbol')}")
            print(f"   Entrez ID: {gene.get('entrezGeneId')}")
            print(f"   Type: {gene.get('type')}")
    else:
        print(f"❌ Error: {result.get('error')}")
    
    # Example 4: Get mutations (THE FIX!)
    print("\n4. Getting BRCA2 mutations in breast cancer")
    print("-" * 60)
    
    result = tu.run({"name": "cBioPortal_get_mutations", "arguments": {
        "study_id": "brca_tcga",
        "gene_list": "BRCA2"
    }})
    
    if result and result.get("status") == "success":
        data = result.get("data", [])
        print(f"✅ SUCCESS! Found {len(data)} BRCA2 mutations")
        
        if data:
            # Show first few mutations
            print("\nExample mutations:")
            for i, mut in enumerate(data[:3], 1):
                sample = mut.get("sampleId")
                protein = mut.get("proteinChange", "N/A")
                mut_type = mut.get("mutationType", "N/A")
                print(f"   {i}. Sample: {sample}")
                print(f"      Protein Change: {protein}")
                print(f"      Mutation Type: {mut_type}")
    else:
        print(f"❌ Error: {result.get('error')}")
    
    # Example 5: Get mutations for multiple genes
    print("\n5. Getting mutations for multiple genes")
    print("-" * 60)
    
    result = tu.run({"name": "cBioPortal_get_mutations", "arguments": {
        "study_id": "brca_tcga",
        "gene_list": "BRCA1,BRCA2,TP53"
    }})
    
    if result and result.get("status") == "success":
        data = result.get("data", [])
        print(f"✅ Found {len(data)} total mutations")
        
        # Count mutations per gene
        gene_counts = {}
        for mut in data:
            gene = mut.get("gene", {}).get("hugoGeneSymbol", "Unknown")
            gene_counts[gene] = gene_counts.get(gene, 0) + 1
        
        print("\nMutations per gene:")
        for gene, count in sorted(gene_counts.items()):
            if gene != "Unknown":
                print(f"   {gene}: {count} mutations")
    else:
        print(f"❌ Error: {result.get('error')}")
    
    # Example 6: Get samples
    print("\n6. Getting samples from breast cancer study")
    print("-" * 60)
    
    result = tu.run({"name": "cBioPortal_get_samples", "arguments": {
        "study_id": "brca_tcga",
        "page_size": 5
    }})
    
    if result and result.get("status") == "success":
        data = result.get("data", [])
        print(f"✅ Found {len(data)} samples")
        
        if data:
            print("\nExample samples:")
            for i, sample in enumerate(data[:3], 1):
                sample_id = sample.get("sampleId")
                patient_id = sample.get("patientId")
                sample_type = sample.get("sampleType")
                print(f"   {i}. {sample_id} (Patient: {patient_id})")
                print(f"      Type: {sample_type}")
    else:
        print(f"❌ Error: {result.get('error')}")
    
    print("\n" + "=" * 60)
    print("✨ All examples completed!")
    print("The cBioPortal API now uses the updated endpoint structure.")

if __name__ == "__main__":
    main()
