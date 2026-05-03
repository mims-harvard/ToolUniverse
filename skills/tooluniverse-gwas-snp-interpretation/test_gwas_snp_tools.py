"""
Phase 2: Tool Testing for GWAS SNP Interpretation Skill

Test all relevant GWAS tools with real SNPs to verify:
1. Parameter names and formats
2. Data structures returned
3. Tool availability in ToolUniverse
"""

import sys
sys.path.insert(0, '/Users/shgao/logs/25.05.28tooluniverse/codes/ToolUniverse-auto/src')

import json
from tooluniverse import ToolUniverse

# Initialize ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# Test SNPs (well-studied variants)
TEST_SNPS = {
    'rs7903146': 'TCF7L2 - type 2 diabetes (chr 10:112998590)',
    'rs429358': 'APOE - Alzheimer disease (chr 19:44908684)',
    'rs1801133': 'MTHFR - various traits (chr 1:11796321)',
}

print("=" * 80)
print("PHASE 2: GWAS SNP INTERPRETATION TOOL TESTING")
print("=" * 80)

# Test 1: Verify tools are loaded
print("\n[TEST 1] Verifying tool availability...")
gwas_tools = [name for name in tu.all_tool_dict.keys() if 'gwas' in name.lower() or 'OpenTargets' in name]
print(f"Found {len(gwas_tools)} GWAS tools:")
for tool in sorted(gwas_tools):
    print(f"  - {tool}")

# Test 2: Get SNP basic info (gwas_get_snp_by_id)
print("\n[TEST 2] Testing gwas_get_snp_by_id...")
for rs_id, desc in TEST_SNPS.items():
    print(f"\nTesting {rs_id} ({desc}):")
    try:
        result_str = tu.run_one_function('gwas_get_snp_by_id', {'rs_id': rs_id})
        result = json.loads(result_str) if isinstance(result_str, str) else result_str
        if 'error' in result:
            print(f"  ERROR: {result['error']}")
        else:
            snp_data = result.get('data', result)
            print(f"  ✓ RS ID: {snp_data.get('rs_id')}")
            print(f"  ✓ Location: chr{snp_data.get('locations', [{}])[0].get('chromosome_name')}:"
                  f"{snp_data.get('locations', [{}])[0].get('chromosome_position')}")
            print(f"  ✓ Consequence: {snp_data.get('most_severe_consequence')}")
            print(f"  ✓ MAF: {snp_data.get('maf')}")
            print(f"  ✓ Mapped genes: {', '.join(snp_data.get('mapped_genes', []))}")
    except Exception as e:
        print(f"  ERROR: {e}")

# Test 3: Get associations for SNP
print("\n[TEST 3] Testing gwas_get_associations_for_snp...")
for rs_id, desc in list(TEST_SNPS.items())[:1]:  # Test just one to save time
    print(f"\nTesting {rs_id}:")
    try:
        result = tu.run_one_function('gwas_get_associations_for_snp', {
            'rs_id': rs_id,
            'size': 5,
            'sort': 'p_value',
            'direction': 'asc'
        })
        if 'error' in result:
            print(f"  ERROR: {result['error']}")
        else:
            data = result.get('data', [])
            print(f"  ✓ Found {len(data)} associations")
            for i, assoc in enumerate(data[:3], 1):
                traits = assoc.get('reported_trait', [])
                p_val = assoc.get('p_value')
                print(f"  {i}. Trait: {traits[0] if traits else 'N/A'}, P-value: {p_val:.2e}")
    except Exception as e:
        print(f"  ERROR: {e}")

# Test 4: OpenTargets variant info (need to convert rs to variant ID format)
print("\n[TEST 4] Testing OpenTargets_get_variant_info...")
# Note: OpenTargets uses chr_pos_ref_alt format, not rs IDs directly
# We'll use known variant IDs from the config
test_variants = {
    '10_112998590_C_T': 'rs7903146 (TCF7L2)',
    '19_44908684_T_C': 'rs429358 (APOE)'
}

for variant_id, desc in test_variants.items():
    print(f"\nTesting {variant_id} ({desc}):")
    try:
        result = tu.run_one_function('OpenTargets_get_variant_info', {'variantId': variant_id})
        if 'error' in result:
            print(f"  ERROR: {result['error']}")
        else:
            variant = result.get('data', {}).get('variant', {})
            print(f"  ✓ RS IDs: {', '.join(variant.get('rsIds', []))}")
            print(f"  ✓ Location: chr{variant.get('chromosome')}:{variant.get('position')}")
            print(f"  ✓ Alleles: {variant.get('referenceAllele')}>{variant.get('alternateAllele')}")
            print(f"  ✓ Consequence: {variant.get('mostSevereConsequence', {}).get('label')}")
            freqs = variant.get('alleleFrequencies', [])
            if freqs:
                print(f"  ✓ Frequencies: {len(freqs)} populations")
    except Exception as e:
        print(f"  ERROR: {e}")

# Test 5: OpenTargets credible sets
print("\n[TEST 5] Testing OpenTargets_get_variant_credible_sets...")
for variant_id, desc in list(test_variants.items())[:1]:
    print(f"\nTesting {variant_id}:")
    try:
        result = tu.run_one_function('OpenTargets_get_variant_credible_sets', {
            'variantId': variant_id,
            'size': 3
        })
        if 'error' in result:
            print(f"  ERROR: {result['error']}")
        else:
            variant = result.get('data', {}).get('variant', {})
            cred_sets = variant.get('credibleSets', {})
            count = cred_sets.get('count', 0)
            rows = cred_sets.get('rows', [])
            print(f"  ✓ Found {count} credible sets")
            for i, cs in enumerate(rows[:2], 1):
                study = cs.get('study', {})
                trait = study.get('traitFromSource', 'N/A')
                method = cs.get('finemappingMethod', 'N/A')
                l2g = cs.get('l2GPredictions', {}).get('rows', [])
                genes = [g['target']['approvedSymbol'] for g in l2g[:3]]
                print(f"  {i}. Trait: {trait}")
                print(f"     Method: {method}, L2G genes: {', '.join(genes)}")
    except Exception as e:
        print(f"  ERROR: {e}")

# Test 6: Search SNPs by gene
print("\n[TEST 6] Testing gwas_search_snps (by mapped gene)...")
try:
    result = tu.run_one_function('gwas_search_snps', {'mapped_gene': 'APOE', 'size': 5})
    if 'error' in result:
        print(f"  ERROR: {result['error']}")
    else:
        data = result.get('data', [])
        print(f"  ✓ Found {len(data)} SNPs for APOE")
        for snp in data[:3]:
            print(f"    - {snp.get('rs_id')}: {snp.get('most_severe_consequence')}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n" + "=" * 80)
print("TESTING COMPLETE")
print("=" * 80)
print("\nKEY FINDINGS:")
print("1. GWAS Catalog tools use 'rs_id' parameter (string)")
print("2. OpenTargets tools use 'variantId' in chr_pos_ref_alt format")
print("3. Need rsID -> variantId conversion for OpenTargets integration")
print("4. Both return comprehensive data structures with nested objects")
print("5. Credible sets provide L2G predictions for gene mapping")
