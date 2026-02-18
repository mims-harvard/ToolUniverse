#!/usr/bin/env python3
"""
Test script for Metabolomics skill
Verifies the complete pipeline works correctly
"""

import sys
import os

# Add parent directory to path to import python_implementation
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from python_implementation import metabolomics_analysis_pipeline

def test_metabolite_analysis():
    """Test metabolite identification and annotation"""
    print("\n" + "="*80)
    print("TEST 1: Metabolite Analysis")
    print("="*80)

    output = metabolomics_analysis_pipeline(
        metabolite_list=["glucose", "lactate"],
        output_file="test1_metabolites.md"
    )

    # Verify output file created
    assert os.path.exists(output), f"Output file {output} not created"

    # Verify report has expected sections
    with open(output, 'r') as f:
        content = f.read()
        assert "Metabolomics Research Analysis Report" in content, "Missing report header"
        assert "Metabolite Identification" in content or "no data" in content.lower(), "Missing Phase 1"
        assert "glucose" in content.lower(), "Missing metabolite in report"

        # Validate actual data (not just "N/A" or errors)
        assert "PubChem CID" in content, "Missing PubChem data"
        assert "Formula" in content, "Missing chemical formula"
        assert "Molecular Weight" in content, "Missing molecular weight"
        assert "Error querying HMDB: 0" not in content, "HMDB parsing error still present"

    print(f"✅ Test 1 PASSED: {output}")

def test_study_retrieval():
    """Test study retrieval from MetaboLights"""
    print("\n" + "="*80)
    print("TEST 2: Study Retrieval")
    print("="*80)

    output = metabolomics_analysis_pipeline(
        study_id="MTBLS1",
        output_file="test2_study.md"
    )

    assert os.path.exists(output), f"Output file {output} not created"

    with open(output, 'r') as f:
        content = f.read()
        assert "Study Details" in content or "Study" in content, "Missing study section"
        assert "MTBLS1" in content, "Missing study ID"

        # Validate actual study data
        assert "Study Status" in content, "Missing study status field"
        assert "MetaboLights" in content, "Missing database attribution"
        # Check we got real data, not all N/A
        assert content.count("N/A") < 5, "Too many N/A fields - API parsing may be broken"

    print(f"✅ Test 2 PASSED: {output}")

def test_study_search():
    """Test study search functionality"""
    print("\n" + "="*80)
    print("TEST 3: Study Search")
    print("="*80)

    output = metabolomics_analysis_pipeline(
        search_query="glucose",
        output_file="test3_search.md"
    )

    assert os.path.exists(output), f"Output file {output} not created"

    with open(output, 'r') as f:
        content = f.read()
        assert "Study Search" in content or "Search" in content, "Missing search section"

    print(f"✅ Test 3 PASSED: {output}")

def test_comprehensive_analysis():
    """Test comprehensive analysis with multiple inputs"""
    print("\n" + "="*80)
    print("TEST 4: Comprehensive Analysis")
    print("="*80)

    output = metabolomics_analysis_pipeline(
        metabolite_list=["glucose", "pyruvate"],
        study_id="MTBLS1",
        search_query="diabetes",
        output_file="test4_comprehensive.md"
    )

    assert os.path.exists(output), f"Output file {output} not created"

    # Check report contains all expected sections
    with open(output, 'r') as f:
        content = f.read()

        # Required sections
        assert "# Metabolomics Research Analysis Report" in content, "Missing report title"
        assert "Generated" in content, "Missing timestamp"

        # Multiple phases
        section_count = content.count("##")
        assert section_count >= 3, f"Expected at least 3 sections, found {section_count}"

        # Data quality
        assert len(content) > 500, "Report seems too short"

        # Validate actual data is present (not just errors/N/A)
        assert "PubChem CID" in content, "Missing metabolite data"
        assert "Formula" in content, "Missing chemical formulas"
        assert "Study Status" in content, "Missing study status"
        assert "Error querying HMDB: 0" not in content, "HMDB parsing bug still present"

        # Check data completeness
        metabolite_count = content.count("### Metabolite:")
        assert metabolite_count == 2, f"Expected 2 metabolites, found {metabolite_count}"

    print(f"✅ Test 4 PASSED: {output}")

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("METABOLOMICS SKILL TEST SUITE")
    print("="*80)

    tests = [
        ("Metabolite Analysis", test_metabolite_analysis),
        ("Study Retrieval", test_study_retrieval),
        ("Study Search", test_study_search),
        ("Comprehensive Analysis", test_comprehensive_analysis),
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
    else:
        print("\n⚠️  SOME TESTS FAILED - Review failures before release")
        return 1

if __name__ == "__main__":
    sys.exit(main())
