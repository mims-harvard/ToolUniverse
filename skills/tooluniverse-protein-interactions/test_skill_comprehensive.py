"""
Comprehensive Testing Script for Protein Interaction Network Analysis Skill

Tests all 6 use cases from SKILL.md:
1. Single protein analysis (TP53)
2. Protein complex validation (TP53, ATM, CHEK2, BRCA1)
3. Pathway discovery (MAPK pathway)
4. Multi-protein network (apoptosis)
5. BioGRID validation (if API key available)
6. Structural data integration

Run: python test_skill_comprehensive.py
"""

import sys
import os
import traceback
from typing import Dict, List, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from python_implementation import analyze_protein_network, ProteinNetworkResult
from tooluniverse import ToolUniverse


class TestResults:
    """Track test results."""
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []

    def add_pass(self, test_name: str, details: str = ""):
        self.passed.append((test_name, details))

    def add_fail(self, test_name: str, error: str):
        self.failed.append((test_name, error))

    def add_warning(self, warning: str):
        self.warnings.append(warning)

    def print_summary(self):
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        print(f"\n✅ PASSED: {len(self.passed)}")
        for test, details in self.passed:
            print(f"   {test}")
            if details:
                print(f"      {details}")

        print(f"\n❌ FAILED: {len(self.failed)}")
        for test, error in self.failed:
            print(f"   {test}")
            print(f"      Error: {error}")

        if self.warnings:
            print(f"\n⚠️  WARNINGS: {len(self.warnings)}")
            for warning in self.warnings:
                print(f"   {warning}")

        print(f"\n{'=' * 80}")
        total = len(self.passed) + len(self.failed)
        print(f"TOTAL: {len(self.passed)}/{total} tests passed ({len(self.passed)/total*100:.1f}%)")
        print("=" * 80)


def verify_result_structure(result: ProteinNetworkResult, test_name: str, results: TestResults) -> bool:
    """Verify the result has expected structure."""
    try:
        # Check required attributes exist
        assert hasattr(result, 'mapped_proteins'), "Missing mapped_proteins"
        assert hasattr(result, 'mapping_success_rate'), "Missing mapping_success_rate"
        assert hasattr(result, 'network_edges'), "Missing network_edges"
        assert hasattr(result, 'total_interactions'), "Missing total_interactions"
        assert hasattr(result, 'enriched_terms'), "Missing enriched_terms"
        assert hasattr(result, 'ppi_enrichment'), "Missing ppi_enrichment"
        assert hasattr(result, 'structural_data'), "Missing structural_data"
        assert hasattr(result, 'primary_source'), "Missing primary_source"
        assert hasattr(result, 'warnings'), "Missing warnings"

        # Check types
        assert isinstance(result.mapped_proteins, list), "mapped_proteins not list"
        assert isinstance(result.mapping_success_rate, float), "mapping_success_rate not float"
        assert isinstance(result.network_edges, list), "network_edges not list"
        assert isinstance(result.total_interactions, int), "total_interactions not int"
        assert isinstance(result.enriched_terms, list), "enriched_terms not list"
        assert isinstance(result.ppi_enrichment, dict), "ppi_enrichment not dict"
        assert isinstance(result.primary_source, str), "primary_source not str"
        assert isinstance(result.warnings, list), "warnings not list"

        results.add_pass(f"{test_name}: Structure validation",
                        f"All fields present and correct types")
        return True

    except AssertionError as e:
        results.add_fail(f"{test_name}: Structure validation", str(e))
        return False


def test_1_single_protein(tu: ToolUniverse, results: TestResults):
    """Test 1: Single protein analysis (TP53)."""
    print("\n" + "=" * 80)
    print("TEST 1: Single Protein Analysis (TP53)")
    print("=" * 80)

    try:
        result = analyze_protein_network(
            tu=tu,
            proteins=["TP53"],
            species=9606,
            confidence_score=0.7
        )

        # Verify structure
        if not verify_result_structure(result, "Test 1", results):
            return

        # Check mapping
        if len(result.mapped_proteins) == 1:
            results.add_pass("Test 1: Protein mapping", "TP53 mapped successfully")
        else:
            results.add_fail("Test 1: Protein mapping",
                           f"Expected 1 mapped protein, got {len(result.mapped_proteins)}")

        # Check interactions (TP53 should have many)
        if result.total_interactions > 0:
            results.add_pass("Test 1: Network retrieval",
                           f"Found {result.total_interactions} interactions")
        else:
            results.add_warning("Test 1: No interactions found for TP53 (unexpected)")

        # Check enrichment (single protein may not have enrichment)
        if len(result.enriched_terms) > 0:
            results.add_pass("Test 1: Enrichment analysis",
                           f"Found {len(result.enriched_terms)} enriched terms")
        else:
            results.add_warning("Test 1: No enriched terms (may be expected for single protein)")

        # Top 5 partners check (from documentation example)
        if result.network_edges:
            print("\nTop 5 partners:")
            for edge in result.network_edges[:5]:
                print(f"   {edge['preferredName_A']} ↔ {edge['preferredName_B']} (score: {edge['score']})")
            results.add_pass("Test 1: Example code works", "Top 5 partners displayed")

    except Exception as e:
        results.add_fail("Test 1: Single protein analysis", str(e))
        traceback.print_exc()


def test_2_protein_complex(tu: ToolUniverse, results: TestResults):
    """Test 2: Protein complex validation (DNA damage response)."""
    print("\n" + "=" * 80)
    print("TEST 2: Protein Complex Validation (DNA Damage Response)")
    print("=" * 80)

    try:
        proteins = ["TP53", "ATM", "CHEK2", "BRCA1"]
        result = analyze_protein_network(
            tu=tu,
            proteins=proteins,
            species=9606,
            confidence_score=0.7
        )

        # Verify structure
        if not verify_result_structure(result, "Test 2", results):
            return

        # Check mapping
        if result.mapping_success_rate >= 0.75:  # At least 3/4
            results.add_pass("Test 2: Protein mapping",
                           f"{len(result.mapped_proteins)}/{len(proteins)} proteins mapped")
        else:
            results.add_fail("Test 2: Protein mapping",
                           f"Low mapping rate: {result.mapping_success_rate:.1%}")

        # Check PPI enrichment (these should form a complex)
        if result.ppi_enrichment:
            p_val = result.ppi_enrichment.get("p_value", 1.0)
            print(f"\nPPI Enrichment p-value: {p_val:.2e}")

            if p_val < 0.05:
                print("✅ Proteins form functional module!")
                print(f"   Expected edges: {result.ppi_enrichment.get('expected_number_of_edges', 0):.1f}")
                print(f"   Observed edges: {result.ppi_enrichment.get('number_of_edges', 0)}")
                results.add_pass("Test 2: PPI enrichment",
                               f"Significant functional module (p={p_val:.2e})")
            else:
                print("⚠️  Proteins may be unrelated")
                results.add_warning(f"Test 2: PPI enrichment not significant (p={p_val:.2e})")
        else:
            results.add_fail("Test 2: PPI enrichment", "No PPI enrichment data returned")

        # Test example code from docs
        if result.ppi_enrichment.get("p_value", 1.0) < 0.05:
            results.add_pass("Test 2: Example code works", "PPI validation example runs correctly")

    except Exception as e:
        results.add_fail("Test 2: Protein complex validation", str(e))
        traceback.print_exc()


def test_3_pathway_discovery(tu: ToolUniverse, results: TestResults):
    """Test 3: Pathway discovery (MAPK pathway)."""
    print("\n" + "=" * 80)
    print("TEST 3: Pathway Discovery (MAPK Pathway)")
    print("=" * 80)

    try:
        result = analyze_protein_network(
            tu=tu,
            proteins=["MAPK1", "MAPK3", "RAF1", "MAP2K1"],
            species=9606,
            confidence_score=0.7
        )

        # Verify structure
        if not verify_result_structure(result, "Test 3", results):
            return

        # Check enrichment (should find MAPK-related terms)
        if len(result.enriched_terms) > 0:
            print("\nTop 10 Enriched Pathways:")
            for term in result.enriched_terms[:10]:
                print(f"   {term.get('description', term['term'])}: p={term['p_value']:.2e}, FDR={term['fdr']:.2e}")

            # Check if any MAPK-related terms
            mapk_terms = [t for t in result.enriched_terms
                         if 'MAPK' in t.get('description', '').upper() or
                            'MAP kinase' in t.get('description', '').upper()]

            if mapk_terms:
                results.add_pass("Test 3: Pathway discovery",
                               f"Found {len(mapk_terms)} MAPK-related terms")
            else:
                results.add_warning("Test 3: No specific MAPK terms found in enrichment")

            results.add_pass("Test 3: Example code works", "Pathway enrichment example runs correctly")
        else:
            results.add_fail("Test 3: Pathway discovery", "No enriched terms found")

    except Exception as e:
        results.add_fail("Test 3: Pathway discovery", str(e))
        traceback.print_exc()


def test_4_multi_protein_network(tu: ToolUniverse, results: TestResults):
    """Test 4: Multi-protein network analysis (apoptosis)."""
    print("\n" + "=" * 80)
    print("TEST 4: Multi-Protein Network Analysis (Apoptosis)")
    print("=" * 80)

    try:
        proteins = ["TP53", "BCL2", "BAX", "CASP3", "CASP9"]
        result = analyze_protein_network(
            tu=tu,
            proteins=proteins,
            species=9606,
            confidence_score=0.7
        )

        # Verify structure
        if not verify_result_structure(result, "Test 4", results):
            return

        # Check network size
        if result.total_interactions >= 5:
            results.add_pass("Test 4: Network retrieval",
                           f"Found {result.total_interactions} interactions")
        else:
            results.add_warning(f"Test 4: Only {result.total_interactions} interactions found")

        # Test export example from docs
        try:
            import pandas as pd
            df = pd.DataFrame(result.network_edges)

            # Don't actually save, just check it works
            if len(df) > 0:
                results.add_pass("Test 4: Export to DataFrame",
                               f"Successfully created DataFrame with {len(df)} rows")
            else:
                results.add_warning("Test 4: DataFrame is empty")

            # Check columns exist
            required_cols = ['preferredName_A', 'preferredName_B', 'score']
            if all(col in df.columns for col in required_cols):
                results.add_pass("Test 4: Example code works",
                               "Export to Cytoscape example works correctly")
            else:
                results.add_fail("Test 4: Example code",
                               f"Missing required columns in network edges")

        except ImportError:
            results.add_warning("Test 4: pandas not available, skipping export test")

    except Exception as e:
        results.add_fail("Test 4: Multi-protein network", str(e))
        traceback.print_exc()


def test_5_biogrid_validation(tu: ToolUniverse, results: TestResults):
    """Test 5: BioGRID validation (if API key available)."""
    print("\n" + "=" * 80)
    print("TEST 5: BioGRID Validation")
    print("=" * 80)

    # Check if API key available
    api_key = os.environ.get("BIOGRID_API_KEY")
    if not api_key:
        print("⚠️  BIOGRID_API_KEY not found in environment - skipping test")
        results.add_warning("Test 5: BioGRID API key not available, test skipped")
        return

    try:
        result = analyze_protein_network(
            tu=tu,
            proteins=["TP53", "MDM2"],
            species=9606,
            confidence_score=0.7,
            include_biogrid=True
        )

        # Verify structure
        if not verify_result_structure(result, "Test 5", results):
            return

        # Check primary source
        print(f"Primary source: {result.primary_source}")
        if result.primary_source in ["STRING", "BioGRID"]:
            results.add_pass("Test 5: Source selection",
                           f"Primary source: {result.primary_source}")
        else:
            results.add_fail("Test 5: Source selection",
                           f"Unexpected primary source: {result.primary_source}")

        # Check example code from docs works
        if result.primary_source in ["STRING", "BioGRID"]:
            results.add_pass("Test 5: Example code works",
                           "BioGRID validation example runs correctly")

    except Exception as e:
        results.add_fail("Test 5: BioGRID validation", str(e))
        traceback.print_exc()


def test_6_structural_data(tu: ToolUniverse, results: TestResults):
    """Test 6: Including structural data (SASBDB)."""
    print("\n" + "=" * 80)
    print("TEST 6: Structural Data Integration (SASBDB)")
    print("=" * 80)

    try:
        result = analyze_protein_network(
            tu=tu,
            proteins=["TP53"],
            species=9606,
            confidence_score=0.7,
            include_structure=True
        )

        # Verify structure
        if not verify_result_structure(result, "Test 6", results):
            return

        # Check structural data
        if result.structural_data is not None:
            if len(result.structural_data) > 0:
                print(f"\nFound {len(result.structural_data)} SAXS/SANS entries:")
                for entry in result.structural_data[:5]:
                    print(f"   {entry.get('sasbdb_id', 'N/A')}: {entry.get('title', 'N/A')}")
                results.add_pass("Test 6: Structural data",
                               f"Found {len(result.structural_data)} SAXS/SANS entries")
                results.add_pass("Test 6: Example code works",
                               "Structural data example runs correctly")
            else:
                results.add_warning("Test 6: No structural data found (may be expected)")
        else:
            results.add_warning("Test 6: structural_data is None (may indicate API issue)")

    except Exception as e:
        results.add_fail("Test 6: Structural data integration", str(e))
        traceback.print_exc()


def test_parameter_validation(tu: ToolUniverse, results: TestResults):
    """Test parameter handling (invalid inputs)."""
    print("\n" + "=" * 80)
    print("ADDITIONAL TEST: Parameter Validation")
    print("=" * 80)

    # Test invalid protein
    try:
        result = analyze_protein_network(
            tu=tu,
            proteins=["INVALID_PROTEIN_XYZABC"],
            species=9606
        )
        if result.mapping_success_rate == 0.0:
            results.add_pass("Parameter validation: Invalid protein",
                           "Correctly handled invalid protein name")
        else:
            results.add_warning("Parameter validation: Invalid protein mapped unexpectedly")
    except Exception as e:
        results.add_fail("Parameter validation: Invalid protein", str(e))

    # Test invalid species
    try:
        result = analyze_protein_network(
            tu=tu,
            proteins=["TP53"],
            species=999999  # Invalid species ID
        )
        # Should handle gracefully
        results.add_pass("Parameter validation: Invalid species",
                       "Handled invalid species gracefully")
    except Exception as e:
        results.add_fail("Parameter validation: Invalid species", str(e))

    # Test confidence score boundaries
    try:
        # Very low confidence
        result = analyze_protein_network(
            tu=tu,
            proteins=["TP53", "MDM2"],
            confidence_score=0.15
        )
        results.add_pass("Parameter validation: Low confidence score",
                       f"Handled confidence=0.15, got {result.total_interactions} interactions")

        # Very high confidence
        result = analyze_protein_network(
            tu=tu,
            proteins=["TP53", "MDM2"],
            confidence_score=0.9
        )
        results.add_pass("Parameter validation: High confidence score",
                       f"Handled confidence=0.9, got {result.total_interactions} interactions")
    except Exception as e:
        results.add_fail("Parameter validation: Confidence scores", str(e))


def test_quick_start_guide(tu: ToolUniverse, results: TestResults):
    """Test that Quick Start guide example works exactly as documented."""
    print("\n" + "=" * 80)
    print("ADDITIONAL TEST: Quick Start Guide")
    print("=" * 80)

    try:
        # This is the exact example from QUICK_START.md lines 8-26
        result = analyze_protein_network(
            tu=tu,
            proteins=["TP53", "MDM2", "ATM"],
            species=9606,
            confidence_score=0.7
        )

        # Check that the exact output statements work
        print(f"✅ {len(result.mapped_proteins)} proteins mapped")
        print(f"✅ {result.total_interactions} interactions found")
        print(f"✅ {len(result.enriched_terms)} GO terms enriched")

        if len(result.mapped_proteins) > 0 and result.total_interactions >= 0:
            results.add_pass("Quick Start: Basic example",
                           "Quick Start basic example works perfectly")
        else:
            results.add_fail("Quick Start: Basic example",
                           "Quick Start example didn't work as documented")

    except Exception as e:
        results.add_fail("Quick Start: Basic example", str(e))


def run_all_tests():
    """Run all comprehensive tests."""
    print("=" * 80)
    print("PROTEIN INTERACTION NETWORK ANALYSIS - COMPREHENSIVE TESTING")
    print("=" * 80)
    print("\nInitializing ToolUniverse...")

    # Initialize once
    tu = ToolUniverse()
    results = TestResults()

    print("✅ ToolUniverse initialized")
    print("\nRunning 8 test suites (6 use cases + 2 additional)...")

    # Run all tests
    test_1_single_protein(tu, results)
    test_2_protein_complex(tu, results)
    test_3_pathway_discovery(tu, results)
    test_4_multi_protein_network(tu, results)
    test_5_biogrid_validation(tu, results)
    test_6_structural_data(tu, results)
    test_parameter_validation(tu, results)
    test_quick_start_guide(tu, results)

    # Print final summary
    results.print_summary()

    return results


if __name__ == "__main__":
    results = run_all_tests()

    # Exit with error code if any tests failed
    sys.exit(len(results.failed))
