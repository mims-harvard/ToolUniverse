#!/usr/bin/env python3
"""
Test script for Systems Biology skill
Verifies the complete pipeline works correctly
"""

import sys
import os

# Add parent directory to path to import python_implementation
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python_implementation import systems_biology_pipeline

def test_gene_list_analysis():
    """Test pathway enrichment with gene list"""
    print("\n" + "="*80)
    print("TEST 1: Gene List Pathway Enrichment")
    print("="*80)

    genes = ["TP53", "BRCA1", "EGFR", "MYC", "KRAS"]
    output = systems_biology_pipeline(
        gene_list=genes,
        output_file="test1_genelist.md"
    )

    # Verify output file created
    assert os.path.exists(output), f"Output file {output} not created"
    print(f"✅ Test 1 PASSED: {output}")

def test_protein_pathways():
    """Test protein-pathway mapping"""
    print("\n" + "="*80)
    print("TEST 2: Protein-Pathway Mapping")
    print("="*80)

    output = systems_biology_pipeline(
        protein_id="P53350",  # TP53
        output_file="test2_protein.md"
    )

    assert os.path.exists(output), f"Output file {output} not created"
    print(f"✅ Test 2 PASSED: {output}")

def test_keyword_search():
    """Test keyword-based pathway search"""
    print("\n" + "="*80)
    print("TEST 3: Keyword Pathway Search")
    print("="*80)

    output = systems_biology_pipeline(
        pathway_keyword="apoptosis",
        organism="Homo sapiens",
        output_file="test3_keyword.md"
    )

    assert os.path.exists(output), f"Output file {output} not created"
    print(f"✅ Test 3 PASSED: {output}")

def test_combined_analysis():
    """Test combined analysis with multiple inputs"""
    print("\n" + "="*80)
    print("TEST 4: Combined Multi-Input Analysis")
    print("="*80)

    genes = ["TP53", "MDM2", "BCL2"]
    output = systems_biology_pipeline(
        gene_list=genes,
        protein_id="P04637",  # TP53
        pathway_keyword="cell death",
        output_file="test4_combined.md"
    )

    assert os.path.exists(output), f"Output file {output} not created"

    # Check report contains all sections
    with open(output, 'r') as f:
        content = f.read()
        assert "Pathway Enrichment" in content, "Missing enrichment section"
        assert "Pathways for Protein" in content, "Missing protein section"
        assert "Pathway Search" in content, "Missing keyword section"
        assert "Top-Level Human Pathways" in content, "Missing top pathways"

    print(f"✅ Test 4 PASSED: {output}")

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("SYSTEMS BIOLOGY SKILL TEST SUITE")
    print("="*80)

    tests = [
        ("Gene List Analysis", test_gene_list_analysis),
        ("Protein Pathways", test_protein_pathways),
        ("Keyword Search", test_keyword_search),
        ("Combined Analysis", test_combined_analysis),
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
    all_passed = all("PASS" in result for result in results.values())
    if all_passed:
        print("\n✅ ALL TESTS PASSED - Skill is ready to use!")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED - Please review errors above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
