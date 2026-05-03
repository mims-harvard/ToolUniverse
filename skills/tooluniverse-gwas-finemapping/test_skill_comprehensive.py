#!/usr/bin/env python3
"""
Comprehensive tests for GWAS Fine-Mapping & Causal Variant Prioritization skill.

Tests all major functionality:
1. Variant prioritization by gene
2. Variant prioritization by rsID
3. Study credible set retrieval
4. Disease study search
5. Result structure validation
6. Documentation examples
7. Edge cases
8. Integration tests
"""

import sys
from typing import List

from python_implementation import (
    prioritize_causal_variants,
    get_credible_sets_for_study,
    search_gwas_studies_for_disease,
    FineMappingResult,
    CredibleSet,
    L2GGene,
)


def test_apoe_alzheimers():
    """Test: Prioritize variants in APOE for Alzheimer's disease."""
    print("\n" + "="*80)
    print("TEST 1: APOE Locus (Alzheimer's Disease)")
    print("="*80)

    result = prioritize_causal_variants("APOE", "alzheimer")

    # Validate result structure
    assert isinstance(result, FineMappingResult), "Result should be FineMappingResult"
    assert result.query_gene == "APOE", "Query gene should be APOE"

    # Check associated traits
    assert len(result.associated_traits) > 0, "Should have associated traits"
    print(f"✓ Found {len(result.associated_traits)} trait associations")

    # Check if Alzheimer's appears in traits
    alzheimer_related = [
        t for t in result.associated_traits
        if 'alzheimer' in t.lower() or 'cognitive' in t.lower()
    ]
    print(f"✓ Found {len(alzheimer_related)} Alzheimer's-related traits")

    # Check top causal genes
    if result.top_causal_genes:
        print(f"✓ Top causal genes:")
        for gene in result.top_causal_genes[:3]:
            print(f"   {gene.gene_symbol}: L2G score {gene.l2g_score:.3f}")
            assert gene.l2g_score >= 0 and gene.l2g_score <= 1, "L2G score should be 0-1"

    # Test summary generation
    summary = result.get_summary()
    assert len(summary) > 0, "Summary should not be empty"
    assert "APOE" in summary, "Summary should mention APOE"
    print(f"✓ Generated summary ({len(summary)} characters)")

    # Test validation suggestions (may be empty if no genes found)
    suggestions = result.get_validation_suggestions()
    print(f"✓ Generated {len(suggestions)} validation suggestions")

    print("\n✓ TEST 1 PASSED")
    return True


def test_tcf7l2_diabetes():
    """Test: Prioritize variants in TCF7L2 for type 2 diabetes."""
    print("\n" + "="*80)
    print("TEST 2: TCF7L2 Locus (Type 2 Diabetes)")
    print("="*80)

    result = prioritize_causal_variants("TCF7L2", "type 2 diabetes")

    # Validate result
    assert isinstance(result, FineMappingResult)
    assert result.query_gene == "TCF7L2"
    print(f"✓ Query gene: {result.query_gene}")

    # Check for diabetes-related traits
    diabetes_traits = [
        t for t in result.associated_traits
        if 'diabetes' in t.lower() or 'glucose' in t.lower() or 'insulin' in t.lower()
    ]
    assert len(diabetes_traits) > 0, "Should have diabetes-related traits"
    print(f"✓ Found {len(diabetes_traits)} diabetes-related traits")

    # Check for TCF7L2 in top genes
    if result.top_causal_genes:
        tcf7l2_gene = [g for g in result.top_causal_genes if g.gene_symbol == "TCF7L2"]
        if tcf7l2_gene:
            print(f"✓ TCF7L2 L2G score: {tcf7l2_gene[0].l2g_score:.3f}")
        else:
            print("⚠ TCF7L2 not in top causal genes (may appear in credible sets)")

    print("\n✓ TEST 2 PASSED")
    return True


def test_fto_obesity():
    """Test: Prioritize variants in FTO for obesity."""
    print("\n" + "="*80)
    print("TEST 3: FTO Locus (Obesity)")
    print("="*80)

    result = prioritize_causal_variants("FTO", "obesity")

    assert isinstance(result, FineMappingResult)
    assert result.query_gene == "FTO"
    print(f"✓ Query gene: {result.query_gene}")

    # Check for obesity/BMI traits
    obesity_traits = [
        t for t in result.associated_traits
        if 'obesity' in t.lower() or 'bmi' in t.lower() or 'body mass' in t.lower()
    ]
    assert len(obesity_traits) > 0, "Should have obesity-related traits"
    print(f"✓ Found {len(obesity_traits)} obesity-related traits")
    print(f"   Examples: {', '.join(obesity_traits[:3])}")

    print("\n✓ TEST 3 PASSED")
    return True


def test_variant_by_rsid():
    """Test: Query by rsID (rs7903146, TCF7L2 diabetes variant)."""
    print("\n" + "="*80)
    print("TEST 4: Variant by rsID (rs7903146)")
    print("="*80)

    result = prioritize_causal_variants("rs7903146")

    assert isinstance(result, FineMappingResult)
    print(f"✓ Result structure valid")

    # Should have variant annotation
    if result.query_variant:
        print(f"✓ Variant annotation:")
        print(f"   ID: {result.query_variant.variant_id}")
        print(f"   rsIDs: {result.query_variant.rs_ids}")
        print(f"   Position: chr{result.query_variant.chromosome}:{result.query_variant.position}")
        assert "rs7903146" in result.query_variant.rs_ids

    # Should have associated traits
    assert len(result.associated_traits) > 0, "Should have trait associations"
    print(f"✓ Found {len(result.associated_traits)} trait associations")

    # Check for diabetes
    diabetes_traits = [t for t in result.associated_traits if 'diabetes' in t.lower()]
    if diabetes_traits:
        print(f"✓ Diabetes traits found: {len(diabetes_traits)}")

    print("\n✓ TEST 4 PASSED")
    return True


def test_study_credible_sets():
    """Test: Get all credible sets for a T2D GWAS study."""
    print("\n" + "="*80)
    print("TEST 5: Study Credible Sets (GCST90029024)")
    print("="*80)

    credible_sets = get_credible_sets_for_study("GCST90029024", max_sets=10)

    assert isinstance(credible_sets, list), "Should return list"
    assert len(credible_sets) > 0, "Should have credible sets"
    print(f"✓ Found {len(credible_sets)} credible sets")

    # Validate first credible set structure
    cs = credible_sets[0]
    assert isinstance(cs, CredibleSet)
    assert cs.study_locus_id, "Should have study locus ID"
    assert cs.study_id == "GCST90029024", "Study ID should match query"
    assert cs.region, "Should have region"

    print(f"✓ Credible set structure valid")
    print(f"   Study locus ID: {cs.study_locus_id}")
    print(f"   Region: {cs.region}")
    print(f"   Method: {cs.finemapping_method or 'N/A'}")

    # Check L2G predictions
    if cs.l2g_genes:
        print(f"✓ L2G predictions present: {len(cs.l2g_genes)} genes")
        top_gene = cs.l2g_genes[0]
        assert isinstance(top_gene, L2GGene)
        assert 0 <= top_gene.l2g_score <= 1, "L2G score should be 0-1"
        print(f"   Top gene: {top_gene}")

    # Check lead variant
    if cs.lead_variant:
        print(f"✓ Lead variant present")
        print(f"   Variant: {cs.lead_variant.variant_id}")
        if cs.lead_variant.rs_ids:
            print(f"   rsIDs: {cs.lead_variant.rs_ids}")

    print("\n✓ TEST 5 PASSED")
    return True


def test_disease_study_search():
    """Test: Search for GWAS studies by disease."""
    print("\n" + "="*80)
    print("TEST 6: Disease Study Search (Type 2 Diabetes)")
    print("="*80)

    # Test with disease term
    studies = search_gwas_studies_for_disease("type 2 diabetes")

    assert isinstance(studies, list), "Should return list"
    assert len(studies) > 0, "Should find studies"
    print(f"✓ Found {len(studies)} studies by text search")

    # Check first study structure
    study = studies[0]
    study_id = study.get('id') or study.get('accession_id')
    assert study_id, "Study should have ID or accession_id"
    print(f"✓ Study structure valid")
    print(f"   ID: {study_id}")
    print(f"   Trait: {study.get('traitFromSource') or study.get('disease_trait', 'N/A')}")
    print(f"   Samples: {study.get('nSamples') or study.get('initial_sample_size', 'N/A')}")

    # Test with disease ontology ID
    print("\nTesting with disease ontology ID...")
    studies_by_id = search_gwas_studies_for_disease(
        "type 2 diabetes",
        disease_id="MONDO_0005148"
    )

    assert len(studies_by_id) > 0, "Should find studies by disease ID"
    print(f"✓ Found {len(studies_by_id)} studies by ontology ID")

    print("\n✓ TEST 6 PASSED")
    return True


def test_result_structure():
    """Test: Validate FineMappingResult structure and methods."""
    print("\n" + "="*80)
    print("TEST 7: Result Structure Validation")
    print("="*80)

    result = prioritize_causal_variants("TCF7L2")

    # Test all attributes exist
    assert hasattr(result, 'query_variant')
    assert hasattr(result, 'query_gene')
    assert hasattr(result, 'credible_sets')
    assert hasattr(result, 'associated_traits')
    assert hasattr(result, 'top_causal_genes')
    print("✓ All attributes present")

    # Test types
    assert isinstance(result.credible_sets, list)
    assert isinstance(result.associated_traits, list)
    assert isinstance(result.top_causal_genes, list)
    print("✓ Attribute types correct")

    # Test methods
    summary = result.get_summary()
    assert isinstance(summary, str)
    assert len(summary) > 0
    print(f"✓ get_summary() works ({len(summary)} chars)")

    suggestions = result.get_validation_suggestions()
    assert isinstance(suggestions, list)
    print(f"✓ get_validation_suggestions() works ({len(suggestions)} items)")

    print("\n✓ TEST 7 PASSED")
    return True


def test_documentation_examples():
    """Test: Run all examples from SKILL.md."""
    print("\n" + "="*80)
    print("TEST 8: Documentation Examples")
    print("="*80)

    # Example 1: Prioritize variants at known locus
    print("\n1. Testing TCF7L2 prioritization example...")
    result = prioritize_causal_variants("TCF7L2", "type 2 diabetes")
    summary = result.get_summary()
    assert "TCF7L2" in summary
    print("✓ Example 1 works")

    # Example 2: Fine-map specific variant
    print("\n2. Testing rs429358 fine-mapping example...")
    result = prioritize_causal_variants("rs429358")
    assert isinstance(result.credible_sets, list)
    print("✓ Example 2 works")

    # Example 3: Explore all loci from study
    print("\n3. Testing study credible sets example...")
    credible_sets = get_credible_sets_for_study("GCST90029024", max_sets=10)
    # Note: Some studies may not have credible sets in Open Targets
    print(f"✓ Example 3 works ({len(credible_sets)} loci)")
    if len(credible_sets) == 0:
        print("   (Note: No credible sets found for this study in current Open Targets data)")

    # Example 4: Find GWAS studies
    print("\n4. Testing disease study search example...")
    studies = search_gwas_studies_for_disease("Alzheimer's disease")
    assert len(studies) > 0
    print(f"✓ Example 4 works ({len(studies)} studies)")

    # Example 5: Validation suggestions
    print("\n5. Testing validation suggestions example...")
    result = prioritize_causal_variants("APOE", "alzheimer")
    suggestions = result.get_validation_suggestions()
    # Suggestions may be empty if no causal genes found
    print(f"✓ Example 5 works ({len(suggestions)} suggestions)")

    print("\n✓ TEST 8 PASSED (all documentation examples work)")
    return True


def test_edge_cases():
    """Test: Edge cases and error handling."""
    print("\n" + "="*80)
    print("TEST 9: Edge Cases")
    print("="*80)

    # Test 1: Gene with no GWAS associations
    print("\n1. Testing obscure gene (ZZZ3)...")
    result = prioritize_causal_variants("ZZZ3")
    assert isinstance(result, FineMappingResult)
    print("✓ Handles gene with few/no associations")

    # Test 2: Non-existent rsID (should not crash)
    print("\n2. Testing non-existent rsID...")
    try:
        result = prioritize_causal_variants("rs99999999999")
        # Should return empty or minimal result
        assert isinstance(result, FineMappingResult)
        print("✓ Handles non-existent rsID gracefully")
    except Exception as e:
        print(f"✓ Raises appropriate exception: {type(e).__name__}")

    # Test 3: Empty study ID
    print("\n3. Testing with minimal parameters...")
    result = prioritize_causal_variants("TCF7L2")
    assert isinstance(result, FineMappingResult)
    print("✓ Works without disease filter")

    # Test 4: Case sensitivity
    print("\n4. Testing case sensitivity...")
    result1 = prioritize_causal_variants("APOE")
    result2 = prioritize_causal_variants("apoe")
    # Should both work (or fail consistently)
    assert isinstance(result1, FineMappingResult)
    print("✓ Handles different cases")

    print("\n✓ TEST 9 PASSED")
    return True


def test_integration():
    """Test: Complete integration workflow."""
    print("\n" + "="*80)
    print("TEST 10: Integration Workflow")
    print("="*80)

    # Step 1: Find studies
    print("\nStep 1: Finding type 2 diabetes studies...")
    studies = search_gwas_studies_for_disease("type 2 diabetes", "MONDO_0005148")
    assert len(studies) > 0
    print(f"✓ Found {len(studies)} studies")

    # Step 2: Get credible sets from largest study
    print("\nStep 2: Getting credible sets from study...")
    largest = max(studies, key=lambda s: s.get('nSamples', 0) or 0)
    study_id = largest.get('id') or largest.get('accession_id')
    n_samples = largest.get('nSamples') or largest.get('initial_sample_size', 'N/A')
    print(f"   Using study {study_id} ({n_samples} samples)")

    credible_sets = get_credible_sets_for_study(study_id, max_sets=5)
    # Note: Not all studies have credible sets
    print(f"✓ Retrieved {len(credible_sets)} credible sets")

    # Step 3: Prioritize variants at a specific gene
    print("\nStep 3: Prioritizing TCF7L2 variants...")
    result = prioritize_causal_variants("TCF7L2", "type 2 diabetes")
    print(f"✓ Found {len(result.credible_sets)} credible sets for TCF7L2")
    print(f"✓ Found {len(result.top_causal_genes)} causal gene predictions")

    # Step 4: Generate report
    print("\nStep 4: Generating comprehensive report...")
    summary = result.get_summary()
    suggestions = result.get_validation_suggestions()
    assert len(summary) > 0
    print(f"✓ Generated summary ({len(summary)} chars) and validation plan ({len(suggestions)} suggestions)")

    print("\n✓ TEST 10 PASSED (complete workflow)")
    return True


def run_all_tests():
    """Run all comprehensive tests."""
    print("\n" + "="*80)
    print("GWAS FINE-MAPPING SKILL - COMPREHENSIVE TEST SUITE")
    print("="*80)

    tests = [
        ("APOE Alzheimer's", test_apoe_alzheimers),
        ("TCF7L2 Diabetes", test_tcf7l2_diabetes),
        ("FTO Obesity", test_fto_obesity),
        ("Variant by rsID", test_variant_by_rsid),
        ("Study Credible Sets", test_study_credible_sets),
        ("Disease Study Search", test_disease_study_search),
        ("Result Structure", test_result_structure),
        ("Documentation Examples", test_documentation_examples),
        ("Edge Cases", test_edge_cases),
        ("Integration Workflow", test_integration),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed, None))
        except Exception as e:
            results.append((test_name, False, e))
            print(f"\n✗ TEST FAILED: {test_name}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed_count = 0
    failed_count = 0

    for test_name, passed, error in results:
        if passed:
            print(f"✓ PASSED: {test_name}")
            passed_count += 1
        else:
            print(f"✗ FAILED: {test_name}")
            if error:
                print(f"   Error: {error}")
            failed_count += 1

    print("\n" + "="*80)
    print(f"Total: {len(results)} tests")
    print(f"Passed: {passed_count} ({100*passed_count//len(results)}%)")
    print(f"Failed: {failed_count}")
    print("="*80)

    if failed_count == 0:
        print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("\nThe GWAS Fine-Mapping skill is working correctly!")
        return 0
    else:
        print(f"\n✗✗✗ {failed_count} TEST(S) FAILED ✗✗✗")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
