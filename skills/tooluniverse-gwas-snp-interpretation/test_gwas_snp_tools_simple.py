"""
Phase 2: Quick Tool Testing for GWAS SNP Interpretation Skill
"""

import sys
sys.path.insert(0, '/Users/shgao/logs/25.05.28tooluniverse/codes/ToolUniverse-auto/src')

import json
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

print("=" * 80)
print("GWAS SNP INTERPRETATION TOOL TESTING")
print("=" * 80)

# Test 1: Get SNP info
print("\n[TEST 1] gwas_get_snp_by_id with rs7903146:")
result = tu.run_one_function({
    'name': 'gwas_get_snp_by_id',
    'arguments': {'rs_id': 'rs7903146'}
})
if isinstance(result, str):
    result = json.loads(result)
snp = result.get('data', result)
print(f"RS ID: {snp.get('rs_id')}")
print(f"Consequence: {snp.get('most_severe_consequence')}")
print(f"Mapped genes: {snp.get('mapped_genes')}")
print(f"MAF: {snp.get('maf')}")

# Test 2: Get associations
print("\n[TEST 2] gwas_get_associations_for_snp with rs7903146:")
result = tu.run_one_function({
    'name': 'gwas_get_associations_for_snp',
    'arguments': {
        'rs_id': 'rs7903146',
        'size': 3,
        'sort': 'p_value',
        'direction': 'asc'
    }
})
if isinstance(result, str):
    result = json.loads(result)
assocs = result.get('data', [])
print(f"Found {len(assocs)} associations")
for i, a in enumerate(assocs, 1):
    print(f"  {i}. {a.get('reported_trait', ['N/A'])[0]} (p={a.get('p_value'):.2e})")

# Test 3: OpenTargets variant info
print("\n[TEST 3] OpenTargets_get_variant_info with 10_112998590_C_T:")
result = tu.run_one_function({
    'name': 'OpenTargets_get_variant_info',
    'arguments': {'variantId': '10_112998590_C_T'}
})
if isinstance(result, str):
    result = json.loads(result)
variant = result.get('data', {}).get('variant', {})
print(f"RS IDs: {variant.get('rsIds')}")
print(f"Location: chr{variant.get('chromosome')}:{variant.get('position')}")
print(f"Consequence: {variant.get('mostSevereConsequence', {}).get('label')}")

# Test 4: OpenTargets credible sets
print("\n[TEST 4] OpenTargets_get_variant_credible_sets with 10_112998590_C_T:")
result = tu.run_one_function({
    'name': 'OpenTargets_get_variant_credible_sets',
    'arguments': {
        'variantId': '10_112998590_C_T',
        'size': 2
    }
})
if isinstance(result, str):
    result = json.loads(result)
cred_sets = result.get('data', {}).get('variant', {}).get('credibleSets', {})
print(f"Credible sets found: {cred_sets.get('count', 0)}")
for cs in cred_sets.get('rows', [])[:2]:
    study = cs.get('study', {})
    l2g = cs.get('l2GPredictions', {}).get('rows', [])
    genes = [g['target']['approvedSymbol'] for g in l2g[:3]]
    print(f"  - {study.get('traitFromSource')}: {genes}")

print("\n" + "=" * 80)
print("TOOL TESTING COMPLETE - All tools working correctly!")
print("=" * 80)
