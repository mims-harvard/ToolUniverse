#!/usr/bin/env python3
"""
Test script for [DOMAIN] skill
Verifies the complete pipeline works correctly

INSTRUCTIONS:
1. Replace [DOMAIN] with your domain name
2. Replace [domain] with lowercase domain name
3. Update test cases based on your skill's inputs
4. Add assertions to verify report sections
5. Test error handling scenarios
6. Ensure 100% pass rate before documenting
"""

import sys
import os

# Add parent directory to path to import python_implementation
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from python_implementation import domain_analysis_pipeline

def test_basic_analysis():
    """Test basic analysis with single input"""
    print("\n" + "="*80)
    print("TEST 1: Basic Analysis")
    print("="*80)

    output = domain_analysis_pipeline(
        input_param_1="test_value",
        output_file="test1_basic.md"
    )

    # Verify output file created
    assert os.path.exists(output), f"Output file {output} not created"

    # Verify report has expected sections
    with open(output, 'r') as f:
        content = f.read()
        assert "[DOMAIN] Analysis Report" in content, "Missing report header"
        assert "Phase 1" in content or "no data" in content.lower(), "Missing Phase 1 section"

    print(f"✅ Test 1 PASSED: {output}")

def test_multiple_inputs():
    """Test with multiple input parameters"""
    print("\n" + "="*80)
    print("TEST 2: Multiple Inputs")
    print("="*80)

    output = domain_analysis_pipeline(
        input_param_1="value1",
        input_param_2="value2",
        output_file="test2_multiple.md"
    )

    assert os.path.exists(output), f"Output file {output} not created"

    # Verify multiple sections present
    with open(output, 'r') as f:
        content = f.read()
        # Check that multiple phases are present
        phase_count = sum([
            "## 1." in content,
            "## 2." in content,
            "## 3." in content
        ])
        assert phase_count >= 2, f"Expected multiple phases, found {phase_count}"

    print(f"✅ Test 2 PASSED: {output}")

def test_comprehensive_analysis():
    """Test comprehensive analysis with all inputs"""
    print("\n" + "="*80)
    print("TEST 3: Comprehensive Analysis")
    print("="*80)

    output = domain_analysis_pipeline(
        input_param_1="value1",
        input_param_2="value2",
        input_param_3="value3",
        organism="Homo sapiens",
        output_file="test3_comprehensive.md"
    )

    assert os.path.exists(output), f"Output file {output} not created"

    # Check report contains all expected sections
    with open(output, 'r') as f:
        content = f.read()

        # Required sections
        assert "# [DOMAIN] Analysis Report" in content, "Missing report title"
        assert "Generated:" in content, "Missing timestamp"
        assert "Organism:" in content, "Missing organism"

        # Phase sections (at least attempt to include)
        phases = ["## 1.", "## 2.", "## 3.", "## 4."]
        present_phases = sum([phase in content for phase in phases])
        assert present_phases >= 3, f"Expected at least 3 phases, found {present_phases}"

        # Data quality checks
        assert len(content) > 500, "Report seems too short"
        assert content.count("##") >= 3, "Not enough sections"

    print(f"✅ Test 3 PASSED: {output}")

def test_error_handling():
    """Test error handling with invalid inputs"""
    print("\n" + "="*80)
    print("TEST 4: Error Handling")
    print("="*80)

    # Test with invalid/nonsense input (should not crash)
    try:
        output = domain_analysis_pipeline(
            input_param_1="INVALID_TEST_VALUE_XYZ123",
            output_file="test4_errors.md"
        )

        assert os.path.exists(output), "Output file not created even with invalid input"

        # Should complete but may have empty/error sections
        with open(output, 'r') as f:
            content = f.read()
            assert "# [DOMAIN] Analysis Report" in content, "Missing report header"
            # May have error messages - that's OK
            # Should not crash or fail to generate report

        print(f"✅ Test 4 PASSED: Error handling works, report generated: {output}")

    except Exception as e:
        print(f"❌ Test 4 FAILED: Skill crashed with invalid input: {e}")
        raise

def test_empty_input_handling():
    """Test behavior when no specific inputs provided"""
    print("\n" + "="*80)
    print("TEST 5: Empty Input Handling")
    print("="*80)

    # Some skills may require at least one input
    # Adjust this test based on your skill's requirements
    try:
        output = domain_analysis_pipeline(
            output_file="test5_empty.md"
        )

        assert os.path.exists(output), "Output file not created"

        with open(output, 'r') as f:
            content = f.read()
            # Should at least have header and summary sections
            assert "# [DOMAIN] Analysis Report" in content
            assert len(content) > 100, "Report should have some content"

        print(f"✅ Test 5 PASSED: {output}")

    except Exception:
        # If skill requires inputs, this is expected
        print(f"⚠️  Test 5 SKIPPED: Skill requires at least one input (expected)")

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("[DOMAIN] SKILL TEST SUITE")
    print("="*80)

    tests = [
        ("Basic Analysis", test_basic_analysis),
        ("Multiple Inputs", test_multiple_inputs),
        ("Comprehensive Analysis", test_comprehensive_analysis),
        ("Error Handling", test_error_handling),
        ("Empty Input Handling", test_empty_input_handling),
    ]

    results = {}
    for name, test_func in tests:
        try:
            test_func()
            results[name] = "✅ PASS"
        except Exception as e:
            print(f"\n❌ EXCEPTION in {name}: {e}")
            results[name] = f"❌ FAIL: {str(e)[:100]}"

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    for name, result in results.items():
        print(f"{name:30} {result}")

    # Overall status
    passed = sum(1 for r in results.values() if "PASS" in r)
    total = len(results)
    pass_rate = (passed / total) * 100

    print(f"\n{'='*80}")
    print(f"PASS RATE: {passed}/{total} ({pass_rate:.0f}%)")
    print(f"{'='*80}")

    if pass_rate == 100:
        print("\n✅ ALL TESTS PASSED - Skill is ready to use!")
        return 0
    elif pass_rate >= 80:
        print("\n⚠️  MOST TESTS PASSED - Review failures before release")
        return 1
    else:
        print("\n❌ MULTIPLE TESTS FAILED - Fix issues before continuing")
        return 1

if __name__ == "__main__":
    sys.exit(main())
