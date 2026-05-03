"""
Phase 2: Tool Testing - Verify GWAS tools before documentation

CRITICAL: Test ALL tools BEFORE writing skill documentation to verify:
1. Parameter names (don't assume!)
2. Response formats (data structure)
3. Real example queries work

NOTE: Some tools have oneOf validation bugs - use validate=False when needed
"""

from tooluniverse.tools import (
    gwas_search_associations,
    gwas_get_associations_for_trait,
    gwas_search_snps,
    gwas_get_snp_by_id,
    gwas_get_study_by_id,
    gwas_search_studies,
    OpenTargets_get_variant_info,
    OpenTargets_get_variant_credible_sets,
    OpenTargets_search_gwas_studies_by_disease,
    OpenTargets_get_gwas_study,
    OpenTargets_get_study_credible_sets,
)
import json


def test_gwas_catalog_tools():
    """Test GWAS Catalog tools"""

    print("\n=== Testing GWAS Catalog Tools ===\n")

    # Test 1: gwas_get_associations_for_trait (sorted by p-value)
    print("1. Testing gwas_get_associations_for_trait with 'type 2 diabetes'...")
    try:
        result = gwas_get_associations_for_trait(
            disease_trait="type 2 diabetes",
            size=5,
            validate=False  # Skip validation due to oneOf bug
        )
        data = result['data']
        print(f"   ✓ Returned {len(data)} associations")
        if data:
            assoc = data[0]
            print(f"   - Top association: p={assoc.get('p_value')}, genes={assoc.get('mapped_genes', [])[:3]}")
            print(f"   - Available fields: {list(assoc.keys())[:10]}")
    except Exception as e:
        print(f"   ✗ FAILED: {e}")

    # Test 2: gwas_get_snp_by_id
    print("\n2. Testing gwas_get_snp_by_id for rs7903146 (TCF7L2, T2D)...")
    try:
        result = gwas_get_snp_by_id(rs_id="rs7903146")
        print(f"   ✓ SNP data retrieved: {result.get('rs_id')}")
        print(f"   - MAF: {result.get('maf')}, consequence: {result.get('most_severe_consequence')}")
        print(f"   - Mapped genes: {result.get('mapped_genes')}")
    except Exception as e:
        print(f"   ✗ FAILED: {e}")

    # Test 3: gwas_search_snps (gene mapping)
    print("\n3. Testing gwas_search_snps for TCF7L2...")
    try:
        result = gwas_search_snps(
            mapped_gene="TCF7L2",
            size=5,
            validate=False
        )
        data = result['data']
        print(f"   ✓ Returned {len(data)} SNPs")
        if data:
            snp = data[0]
            print(f"   - Sample SNP: {snp.get('rs_id')}, consequence={snp.get('most_severe_consequence')}")
    except Exception as e:
        print(f"   ✗ FAILED: {e}")

    # Test 4: gwas_get_study_by_id
    print("\n4. Testing gwas_get_study_by_id for GCST000392 (T1D)...")
    try:
        result = gwas_get_study_by_id(study_id="GCST000392")
        print(f"   ✓ Study retrieved: {result.get('disease_trait')}")
        print(f"   - Sample size: {result.get('initial_sample_size')}")
        print(f"   - Has summary stats: {result.get('full_summary_stats_available')}")
    except Exception as e:
        print(f"   ✗ FAILED: {e}")


def test_opentargets_tools():
    """Test Open Targets Genetics tools"""

    print("\n\n=== Testing Open Targets Genetics Tools ===\n")

    # Test 1: OpenTargets_get_variant_info
    print("1. Testing OpenTargets_get_variant_info...")
    try:
        result = OpenTargets_get_variant_info(
            variantId="10_112998590_C_T"  # rs7903146 (TCF7L2, T2D)
        )
        variant = result['data']['variant']
        print(f"   ✓ Variant: {variant['id']}, rsIDs={variant.get('rsIds')}")
        print(f"   - Consequence: {variant.get('mostSevereConsequence', {}).get('label')}")
        print(f"   - Allele frequencies: {len(variant.get('alleleFrequencies', []))} populations")
    except Exception as e:
        print(f"   ✗ FAILED: {e}")

    # Test 2: OpenTargets_get_variant_credible_sets
    print("\n2. Testing OpenTargets_get_variant_credible_sets...")
    try:
        result = OpenTargets_get_variant_credible_sets(
            variantId="10_112998590_C_T",
            size=3
        )
        credible_sets = result['data']['variant']['credibleSets']
        count = credible_sets.get('count', 0)
        print(f"   ✓ Found {count} credible sets")
        if credible_sets.get('rows'):
            cs = credible_sets['rows'][0]
            print(f"   - Study: {cs['study'].get('traitFromSource')}")
            print(f"   - L2G predictions: {len(cs.get('l2GPredictions', {}).get('rows', []))} genes")
    except Exception as e:
        print(f"   ✗ FAILED: {e}")

    # Test 3: OpenTargets_search_gwas_studies_by_disease
    print("\n3. Testing OpenTargets_search_gwas_studies_by_disease...")
    try:
        result = OpenTargets_search_gwas_studies_by_disease(
            diseaseIds=["MONDO_0005148"],  # Type 2 diabetes
            size=3
        )
        studies = result['data']['studies']
        count = studies.get('count', 0)
        print(f"   ✓ Found {count} studies for T2D")
        if studies.get('rows'):
            study = studies['rows'][0]
            print(f"   - Sample: {study['id']}, n={study.get('nSamples')}")
    except Exception as e:
        print(f"   ✗ FAILED: {e}")

    # Test 4: OpenTargets_get_gwas_study
    print("\n4. Testing OpenTargets_get_gwas_study...")
    try:
        result = OpenTargets_get_gwas_study(studyId="GCST000392")
        study = result['data']['study']
        print(f"   ✓ Study: {study['id']}, trait={study.get('traitFromSource')}")
        print(f"   - N={study.get('nSamples')}, has sumstats={study.get('hasSumstats')}")
    except Exception as e:
        print(f"   ✗ FAILED: {e}")

    # Test 5: OpenTargets_get_study_credible_sets
    print("\n5. Testing OpenTargets_get_study_credible_sets...")
    try:
        result = OpenTargets_get_study_credible_sets(
            studyIds=["GCST000392"],
            size=5
        )
        credible_sets = result['data']['credibleSets']
        count = credible_sets.get('count', 0)
        print(f"   ✓ Found {count} credible sets for GCST000392")
        if credible_sets.get('rows'):
            cs = credible_sets['rows'][0]
            print(f"   - Lead variant: {cs.get('variant', {}).get('id')}")
            print(f"   - L2G genes: {[t['target']['approvedSymbol'] for t in cs.get('l2GPredictions', {}).get('rows', [])[:3]]}")
    except Exception as e:
        print(f"   ✗ FAILED: {e}")


def test_trait_to_gene_workflow():
    """Test complete trait-to-gene discovery workflow"""

    print("\n\n=== Testing Complete Trait-to-Gene Workflow ===\n")

    trait = "type 2 diabetes"
    print(f"Discovering genes for trait: {trait}\n")

    # Step 1: Search associations
    print("Step 1: Searching GWAS associations...")
    try:
        assoc_result = gwas_get_associations_for_trait(
            disease_trait=trait,
            size=50,
            validate=False  # Skip validation due to oneOf bug
        )
        associations = assoc_result['data']
        print(f"   ✓ Found {len(associations)} associations")

        # Step 2: Extract mapped genes
        print("\nStep 2: Extracting mapped genes from associations...")
        gene_to_snps = {}
        gene_to_min_p = {}

        for assoc in associations:
            p_value = assoc.get('p_value')
            snps = assoc.get('snp_allele', [])
            genes = assoc.get('mapped_genes', [])

            if p_value and p_value < 5e-8:  # Genome-wide significance
                for gene in genes:
                    if gene not in gene_to_snps:
                        gene_to_snps[gene] = []
                        gene_to_min_p[gene] = p_value
                    gene_to_snps[gene].extend([s.get('rs_id') for s in snps if s.get('rs_id')])
                    gene_to_min_p[gene] = min(gene_to_min_p[gene], p_value)

        print(f"   ✓ Found {len(gene_to_snps)} genes with genome-wide significant associations")

        # Step 3: Rank by significance
        print("\nStep 3: Ranking genes by significance...")
        ranked_genes = sorted(gene_to_min_p.items(), key=lambda x: x[1])[:10]

        print("\n   Top 10 genes associated with type 2 diabetes:")
        for i, (gene, p_val) in enumerate(ranked_genes, 1):
            snp_count = len(set(gene_to_snps[gene]))
            print(f"   {i:2d}. {gene:10s} p={p_val:.2e} ({snp_count} SNPs)")

        print("\n✓ Workflow complete!")

    except Exception as e:
        print(f"   ✗ FAILED: {e}")


def verify_tool_availability():
    """Verify all required tools are loaded"""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    print("\n=== Verifying Tool Availability ===\n")

    required_tools = [
        # GWAS Catalog
        "gwas_search_associations",
        "gwas_get_associations_for_trait",
        "gwas_search_snps",
        "gwas_get_snp_by_id",
        "gwas_get_study_by_id",
        "gwas_search_studies",
        # Open Targets
        "OpenTargets_get_variant_info",
        "OpenTargets_get_variant_credible_sets",
        "OpenTargets_search_gwas_studies_by_disease",
        "OpenTargets_get_gwas_study",
        "OpenTargets_get_study_credible_sets",
    ]

    all_available = True
    for tool in required_tools:
        available = tool in tu.all_tool_dict
        status = "✓" if available else "✗"
        print(f"{status} {tool}")
        if not available:
            all_available = False

    print(f"\n{'✓ All tools available!' if all_available else '✗ Some tools missing!'}")
    return all_available


if __name__ == "__main__":
    print("=" * 70)
    print("GWAS Trait-to-Gene Discovery: Tool Testing")
    print("=" * 70)

    # Phase 1: Verify tools are loaded
    if not verify_tool_availability():
        print("\n✗ CRITICAL: Not all tools available. Cannot proceed.")
        exit(1)

    # Phase 2: Test individual tools
    test_gwas_catalog_tools()
    test_opentargets_tools()

    # Phase 3: Test complete workflow
    test_trait_to_gene_workflow()

    print("\n" + "=" * 70)
    print("Testing complete! Proceed to documentation phase.")
    print("=" * 70)
