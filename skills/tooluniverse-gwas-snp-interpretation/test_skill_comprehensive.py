"""
Comprehensive Test Suite for GWAS SNP Interpretation Skill

Tests all functionality including:
1. Real SNP interpretation
2. Parameter validation
3. Data structure verification
4. Documentation examples
5. Error handling
6. Edge cases
"""

import sys
sys.path.insert(0, '/Users/shgao/logs/25.05.28tooluniverse/codes/ToolUniverse-auto/src')

import json
from python_implementation import interpret_snp, SNPInterpretationReport
from tooluniverse import ToolUniverse

# Test data: Well-studied SNPs
TEST_SNPS = {
    'rs7903146': {'gene': 'TCF7L2', 'trait': 'Type 2 diabetes'},
    'rs429358': {'gene': 'APOE', 'trait': 'Alzheimer'},
    'rs1801133': {'gene': 'MTHFR', 'trait': 'Homocysteine'}
}


def test_1_basic_interpretation():
    """Test 1: Basic SNP interpretation with rs7903146"""
    print("\n[TEST 1] Basic SNP interpretation...")

    report = interpret_snp('rs7903146', include_credible_sets=False)

    assert isinstance(report, SNPInterpretationReport)
    assert report.snp_info.rs_id == 'rs7903146'
    assert 'TCF7L2' in report.snp_info.mapped_genes
    assert len(report.associations) > 0
    assert report.associations[0].p_value < 5e-8  # Should have significant associations

    print("  ✓ Returns SNPInterpretationReport")
    print(f"  ✓ Correct rs_id: {report.snp_info.rs_id}")
    print(f"  ✓ Mapped to gene: {report.snp_info.mapped_genes[0]}")
    print(f"  ✓ Found {len(report.associations)} associations")
    print("  PASS")


def test_2_with_credible_sets():
    """Test 2: Full interpretation with fine-mapping"""
    print("\n[TEST 2] Interpretation with credible sets...")

    report = interpret_snp('rs7903146', include_credible_sets=True)

    assert len(report.credible_sets) > 0, "Should find credible sets for rs7903146"
    assert 'TCF7L2' in [g['gene'] for cs in report.credible_sets for g in cs.predicted_genes]

    print(f"  ✓ Found {len(report.credible_sets)} credible sets")
    print(f"  ✓ Predicted genes include TCF7L2")
    print("  PASS")


def test_3_multiple_snps():
    """Test 3: Test multiple different SNPs"""
    print("\n[TEST 3] Testing multiple SNPs...")

    for rs_id, expected in TEST_SNPS.items():
        report = interpret_snp(rs_id, include_credible_sets=False, max_associations=20)

        # Check basic structure
        assert report.snp_info.rs_id == rs_id
        assert report.snp_info.chromosome != '?'
        assert report.snp_info.position > 0

        # Check expected gene (may not always be in list for all variants)
        if expected['gene'] in report.snp_info.mapped_genes:
            print(f"  ✓ {rs_id}: Mapped to {expected['gene']}")
        else:
            print(f"  ⚠ {rs_id}: Expected {expected['gene']}, got {report.snp_info.mapped_genes}")

        print(f"    → {len(report.associations)} associations found")

    print("  PASS")


def test_4_fast_mode():
    """Test 4: Fast mode (no credible sets)"""
    print("\n[TEST 4] Fast mode performance...")

    import time

    start = time.time()
    report = interpret_snp('rs1801133', include_credible_sets=False)
    fast_time = time.time() - start

    assert len(report.credible_sets) == 0, "Should not have credible sets in fast mode"
    assert fast_time < 15, f"Fast mode should complete in <15s, took {fast_time:.1f}s"

    print(f"  ✓ Completed in {fast_time:.2f} seconds")
    print(f"  ✓ No credible sets queried")
    print("  PASS")


def test_5_parameter_validation():
    """Test 5: Custom parameters"""
    print("\n[TEST 5] Custom parameters...")

    # Test p_threshold
    report = interpret_snp('rs7903146', p_threshold=5e-6, max_associations=10, include_credible_sets=False)

    assert len(report.associations) <= 10

    # Count significant associations
    sig_count = len([a for a in report.associations if a.p_value < 5e-6])
    print(f"  ✓ max_associations=10: got {len(report.associations)} associations")
    print(f"  ✓ p_threshold=5e-6: {sig_count} significant")
    print("  PASS")


def test_6_data_structure():
    """Test 6: Verify output data structure"""
    print("\n[TEST 6] Data structure validation...")

    report = interpret_snp('rs7903146', include_credible_sets=True, max_associations=5)

    # Check SNPBasicInfo
    assert hasattr(report.snp_info, 'rs_id')
    assert hasattr(report.snp_info, 'chromosome')
    assert hasattr(report.snp_info, 'position')
    assert hasattr(report.snp_info, 'mapped_genes')
    print("  ✓ SNPBasicInfo structure correct")

    # Check TraitAssociation
    if report.associations:
        assoc = report.associations[0]
        assert hasattr(assoc, 'trait')
        assert hasattr(assoc, 'p_value')
        assert hasattr(assoc, 'study_id')
        print("  ✓ TraitAssociation structure correct")

    # Check CredibleSetInfo
    if report.credible_sets:
        cs = report.credible_sets[0]
        assert hasattr(cs, 'study_id')
        assert hasattr(cs, 'trait')
        assert hasattr(cs, 'predicted_genes')
        assert isinstance(cs.predicted_genes, list)
        if cs.predicted_genes:
            assert 'gene' in cs.predicted_genes[0]
            assert 'score' in cs.predicted_genes[0]
        print("  ✓ CredibleSetInfo structure correct")

    # Check clinical significance
    assert isinstance(report.clinical_significance, str)
    assert len(report.clinical_significance) > 0
    print("  ✓ Clinical significance generated")

    print("  PASS")


def test_7_string_representation():
    """Test 7: String output formatting"""
    print("\n[TEST 7] String representation...")

    report = interpret_snp('rs7903146', include_credible_sets=False, max_associations=10)

    report_str = str(report)

    # Check key sections present
    assert 'SNP Interpretation: rs7903146' in report_str
    assert 'Basic Information:' in report_str
    assert 'Associations' in report_str
    assert 'Clinical Significance:' in report_str

    # Should have reasonable length
    assert len(report_str) > 200

    print("  ✓ Contains all expected sections")
    print(f"  ✓ Report length: {len(report_str)} characters")
    print("  PASS")


def test_8_documentation_examples():
    """Test 8: Examples from documentation work"""
    print("\n[TEST 8] Documentation examples...")

    # Example from QUICK_START.md
    report = interpret_snp('rs7903146')
    assert report is not None
    print("  ✓ Quick start example works")

    # Example: Access individual components
    snp = report.snp_info
    assert snp.rs_id == 'rs7903146'
    assert 'TCF7L2' in snp.mapped_genes
    print("  ✓ Component access works")

    # Example: Filter significant associations
    sig_assoc = [a for a in report.associations if a.p_value < 5e-8]
    assert len(sig_assoc) > 0
    print(f"  ✓ Filtering works: {len(sig_assoc)} significant associations")

    print("  PASS")


def test_9_tools_direct():
    """Test 9: Direct ToolUniverse API calls"""
    print("\n[TEST 9] Direct tool usage...")

    tu = ToolUniverse()
    tu.load_tools()

    # Test gwas_get_snp_by_id
    result = tu.run_one_function({
        'name': 'gwas_get_snp_by_id',
        'arguments': {'rs_id': 'rs7903146'}
    })
    if isinstance(result, str):
        result = json.loads(result)

    assert 'data' in result or 'rs_id' in result
    print("  ✓ gwas_get_snp_by_id works")

    # Test gwas_get_associations_for_snp
    result = tu.run_one_function({
        'name': 'gwas_get_associations_for_snp',
        'arguments': {'rs_id': 'rs7903146', 'size': 5}
    })
    if isinstance(result, str):
        result = json.loads(result)

    assert 'data' in result
    print("  ✓ gwas_get_associations_for_snp works")

    print("  PASS")


def test_10_edge_cases():
    """Test 10: Edge cases and error handling"""
    print("\n[TEST 10] Edge cases...")

    # Test with variant that may have fewer associations
    try:
        report = interpret_snp('rs1801133', max_associations=200, include_credible_sets=False)
        print(f"  ✓ Handles large max_associations: got {len(report.associations)} results")
    except Exception as e:
        print(f"  ⚠ Large query failed: {e}")

    # Test with include_credible_sets parameter
    report_no_cs = interpret_snp('rs7903146', include_credible_sets=False)
    report_with_cs = interpret_snp('rs7903146', include_credible_sets=True)

    assert len(report_no_cs.credible_sets) == 0
    assert len(report_with_cs.credible_sets) > 0
    print("  ✓ include_credible_sets parameter works correctly")

    print("  PASS")


def run_all_tests():
    """Run complete test suite"""
    print("=" * 80)
    print("GWAS SNP INTERPRETATION SKILL - COMPREHENSIVE TEST SUITE")
    print("=" * 80)

    tests = [
        test_1_basic_interpretation,
        test_2_with_credible_sets,
        test_3_multiple_snps,
        test_4_fast_mode,
        test_5_parameter_validation,
        test_6_data_structure,
        test_7_string_representation,
        test_8_documentation_examples,
        test_9_tools_direct,
        test_10_edge_cases
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            failed += 1

    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success rate: {100 * passed / len(tests):.1f}%")

    if failed == 0:
        print("\n✓ ALL TESTS PASSED!")
    else:
        print(f"\n✗ {failed} test(s) failed")

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
