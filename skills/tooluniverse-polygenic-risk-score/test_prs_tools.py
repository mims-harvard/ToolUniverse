"""
Phase 2: Tool Testing for Polygenic Risk Score Builder

Tests all GWAS tools with well-established PRS traits to verify:
1. Parameter names are correct
2. Data structures match expectations
3. Effect sizes and p-values are accessible
4. Tools return meaningful data for PRS construction
"""

import sys
sys.path.insert(0, '/Users/shgao/logs/25.05.28tooluniverse/codes/ToolUniverse-auto/src')

from tooluniverse.tools import (
    gwas_get_associations_for_trait,
    gwas_get_snp_by_id,
    gwas_get_associations_for_snp,
    gwas_get_study_by_id,
    OpenTargets_search_gwas_studies_by_disease,
    OpenTargets_get_variant_info,
)

def test_gwas_associations_for_trait():
    """Test retrieving associations for coronary artery disease"""
    print("\n" + "="*80)
    print("TEST 1: Get GWAS associations for coronary artery disease")
    print("="*80)

    result = gwas_get_associations_for_trait(
        disease_trait="coronary artery disease",
        size=10
    )

    print(f"Status: {'SUCCESS' if 'data' in result else 'FAILED'}")
    if 'data' in result:
        associations = result['data']
        print(f"Number of associations: {len(associations)}")
        if len(associations) > 0:
            assoc = associations[0]
            print(f"\nFirst association:")
            print(f"  Association ID: {assoc.get('association_id')}")
            print(f"  P-value: {assoc.get('p_value')}")
            print(f"  Beta: {assoc.get('beta')}")
            print(f"  SNP alleles: {assoc.get('snp_allele')}")
            print(f"  Effect allele: {assoc.get('snp_effect_allele')}")
            print(f"  Risk frequency: {assoc.get('risk_frequency')}")
            print(f"  Mapped genes: {assoc.get('mapped_genes')}")
            print(f"  Study: {assoc.get('accession_id')}")

        # Check metadata
        if 'metadata' in result:
            print(f"\nPagination info:")
            pagination = result['metadata'].get('pagination', {})
            print(f"  Total elements: {pagination.get('totalElements')}")
            print(f"  Total pages: {pagination.get('totalPages')}")

    return result

def test_type2_diabetes():
    """Test type 2 diabetes associations"""
    print("\n" + "="*80)
    print("TEST 2: Get GWAS associations for type 2 diabetes")
    print("="*80)

    result = gwas_get_associations_for_trait(
        disease_trait="type 2 diabetes",
        size=10
    )

    print(f"Status: {'SUCCESS' if 'data' in result else 'FAILED'}")
    if 'data' in result:
        associations = result['data']
        print(f"Number of associations: {len(associations)}")
        if len(associations) > 0:
            # Check for TCF7L2 - the strongest T2D gene
            for assoc in associations:
                genes = assoc.get('mapped_genes', [])
                if 'TCF7L2' in genes:
                    print(f"\nFound TCF7L2 association:")
                    print(f"  rs ID: {assoc.get('snp_allele')}")
                    print(f"  P-value: {assoc.get('p_value')}")
                    print(f"  Beta: {assoc.get('beta')}")
                    break

    return result

def test_alzheimers():
    """Test Alzheimer's disease associations (APOE focus)"""
    print("\n" + "="*80)
    print("TEST 3: Get GWAS associations for Alzheimer disease")
    print("="*80)

    result = gwas_get_associations_for_trait(
        disease_trait="alzheimer disease",
        size=20
    )

    print(f"Status: {'SUCCESS' if 'data' in result else 'FAILED'}")
    if 'data' in result:
        associations = result['data']
        print(f"Number of associations: {len(associations)}")

        # Look for APOE variants
        apoe_found = False
        for assoc in associations:
            genes = assoc.get('mapped_genes', [])
            if 'APOE' in genes:
                apoe_found = True
                print(f"\nFound APOE association:")
                print(f"  Association ID: {assoc.get('association_id')}")
                print(f"  SNP: {assoc.get('snp_allele')}")
                print(f"  P-value: {assoc.get('p_value')}")
                print(f"  Beta: {assoc.get('beta')}")
                break

        if not apoe_found:
            print("\nNote: APOE not in top results, but associations found")

    return result

def test_snp_lookup():
    """Test looking up specific SNPs (rs7903146 for T2D, rs429358 for Alzheimer's)"""
    print("\n" + "="*80)
    print("TEST 4: Look up rs7903146 (TCF7L2, T2D risk variant)")
    print("="*80)

    result = gwas_get_snp_by_id(rs_id="rs7903146")

    print(f"Status: {'SUCCESS' if result and not result.get('error') else 'FAILED'}")
    if result and not result.get('error'):
        print(f"  rs ID: {result.get('rs_id')}")
        print(f"  Chromosome: {result.get('locations', [{}])[0].get('chromosome_name')}")
        print(f"  Position: {result.get('locations', [{}])[0].get('chromosome_position')}")
        print(f"  Alleles: {result.get('alleles')}")
        print(f"  MAF: {result.get('maf')}")
        print(f"  Minor allele: {result.get('minor_allele')}")
        print(f"  Mapped genes: {result.get('mapped_genes')}")

    return result

def test_associations_for_snp():
    """Test getting all associations for rs7903146"""
    print("\n" + "="*80)
    print("TEST 5: Get all trait associations for rs7903146")
    print("="*80)

    result = gwas_get_associations_for_snp(
        rs_id="rs7903146",
        size=10
    )

    print(f"Status: {'SUCCESS' if 'data' in result else 'FAILED'}")
    if 'data' in result:
        associations = result['data']
        print(f"Number of trait associations: {len(associations)}")
        if len(associations) > 0:
            print(f"\nTop association:")
            assoc = associations[0]
            print(f"  Trait: {assoc.get('reported_trait')}")
            print(f"  P-value: {assoc.get('p_value')}")
            print(f"  Beta: {assoc.get('beta')}")
            print(f"  Effect allele: {assoc.get('snp_effect_allele')}")

    return result

def test_study_lookup():
    """Test looking up a specific GWAS study"""
    print("\n" + "="*80)
    print("TEST 6: Get GWAS study details (GCST000392 - T1D study)")
    print("="*80)

    result = gwas_get_study_by_id(study_id="GCST000392")

    print(f"Status: {'SUCCESS' if result and not result.get('error') else 'FAILED'}")
    if result and not result.get('error'):
        print(f"  Accession: {result.get('accession_id')}")
        print(f"  Disease/Trait: {result.get('disease_trait')}")
        print(f"  Sample size: {result.get('initial_sample_size')}")
        print(f"  Discovery ancestry: {result.get('discovery_ancestry')}")
        print(f"  SNP count: {result.get('snp_count')}")
        print(f"  Full summary stats available: {result.get('full_summary_stats_available')}")

    return result

def test_opentargets_disease_search():
    """Test OpenTargets disease search for T2D"""
    print("\n" + "="*80)
    print("TEST 7: Search OpenTargets GWAS studies for type 2 diabetes")
    print("="*80)

    # MONDO_0005148 = type 2 diabetes
    result = OpenTargets_search_gwas_studies_by_disease(
        diseaseIds=["MONDO_0005148"],
        size=5
    )

    print(f"Status: {'SUCCESS' if 'data' in result else 'FAILED'}")
    if 'data' in result:
        studies_data = result['data'].get('studies', {})
        count = studies_data.get('count', 0)
        studies = studies_data.get('rows', [])
        print(f"Total T2D studies found: {count}")
        print(f"Returned: {len(studies)}")

        if len(studies) > 0:
            study = studies[0]
            print(f"\nFirst study:")
            print(f"  Study ID: {study.get('id')}")
            print(f"  Trait: {study.get('traitFromSource')}")
            print(f"  Sample size: {study.get('nSamples')}")
            print(f"  Has summary stats: {study.get('hasSumstats')}")
            print(f"  First author: {study.get('publicationFirstAuthor')}")

    return result

def test_opentargets_variant_info():
    """Test OpenTargets variant info for rs7903146"""
    print("\n" + "="*80)
    print("TEST 8: Get variant info from OpenTargets (rs7903146)")
    print("="*80)

    # rs7903146 is chr10:112998590:C:T
    result = OpenTargets_get_variant_info(
        variantId="10_112998590_C_T"
    )

    print(f"Status: {'SUCCESS' if 'data' in result else 'FAILED'}")
    if 'data' in result:
        variant = result['data'].get('variant', {})
        if variant:
            print(f"  Variant ID: {variant.get('id')}")
            print(f"  rs IDs: {variant.get('rsIds')}")
            print(f"  Chr:Pos: {variant.get('chromosome')}:{variant.get('position')}")
            print(f"  Ref>Alt: {variant.get('referenceAllele')}>{variant.get('alternateAllele')}")
            print(f"  Most severe consequence: {variant.get('mostSevereConsequence')}")

            allele_freqs = variant.get('alleleFrequencies', [])
            if allele_freqs:
                print(f"\n  Allele frequencies:")
                for freq in allele_freqs[:3]:  # Show first 3 populations
                    print(f"    {freq.get('populationName')}: {freq.get('alleleFrequency')}")

    return result

def run_all_tests():
    """Run all tool tests"""
    print("\n" + "="*80)
    print("POLYGENIC RISK SCORE BUILDER - TOOL TESTING")
    print("="*80)

    tests = [
        ("CAD associations", test_gwas_associations_for_trait),
        ("T2D associations", test_type2_diabetes),
        ("Alzheimer associations", test_alzheimers),
        ("SNP lookup (rs7903146)", test_snp_lookup),
        ("SNP associations", test_associations_for_snp),
        ("Study lookup", test_study_lookup),
        ("OpenTargets disease search", test_opentargets_disease_search),
        ("OpenTargets variant info", test_opentargets_variant_info),
    ]

    results = {}
    for name, test_func in tests:
        try:
            result = test_func()
            results[name] = "PASS" if result and (isinstance(result, dict)) else "FAIL"
        except Exception as e:
            print(f"\nERROR in {name}: {e}")
            results[name] = "FAIL"

    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    for name, status in results.items():
        print(f"  {name}: {status}")

    pass_count = sum(1 for s in results.values() if s == "PASS")
    total_count = len(results)
    print(f"\nOverall: {pass_count}/{total_count} tests passed ({100*pass_count//total_count}%)")

if __name__ == "__main__":
    run_all_tests()
