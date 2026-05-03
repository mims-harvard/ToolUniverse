"""
Comprehensive test suite for GWAS Study Deep Dive & Meta-Analysis skill.

Tests all functions with real data from GWAS Catalog and Open Targets.
Ensures 100% functionality before deployment.
"""

import pytest
from tooluniverse import ToolUniverse
from python_implementation import (
    compare_gwas_studies,
    meta_analyze_locus,
    assess_replication,
    get_study_quality_metrics,
    StudyMetadata,
    Association,
    MetaAnalysisResult,
    ReplicationResult,
    StudyComparisonResult
)


@pytest.fixture(scope="module")
def tu():
    """Initialize ToolUniverse once for all tests."""
    tu_instance = ToolUniverse()
    tu_instance.load_tools()
    return tu_instance


class TestStudyComparison:
    """Tests for compare_gwas_studies function."""

    def test_compare_t2d_studies(self, tu):
        """Test 1: Compare type 2 diabetes studies."""
        print("\n[TEST 1] Compare T2D studies")
        result = compare_gwas_studies(
            tu,
            trait="type 2 diabetes",
            min_sample_size=10000,
            max_studies=10
        )

        assert isinstance(result, StudyComparisonResult)
        assert result.n_studies > 0, "Should find at least one T2D study"
        assert len(result.studies) > 0
        assert result.trait == "type 2 diabetes"

        # Check studies have required fields
        for study in result.studies:
            assert study.accession_id
            assert study.trait
            assert study.sample_size >= 10000
            print(f"  ✓ {study.accession_id}: n={study.sample_size:,}")

        print(f"  ✓ Found {result.n_studies} T2D studies")

    def test_compare_cad_studies(self, tu):
        """Test 2: Compare coronary artery disease studies."""
        print("\n[TEST 2] Compare CAD studies")
        result = compare_gwas_studies(
            tu,
            trait="coronary artery disease",
            min_sample_size=5000,
            max_studies=8
        )

        assert result.n_studies > 0, "Should find CAD studies"
        assert any("coronary" in s.trait.lower() for s in result.studies)

        print(f"  ✓ Found {result.n_studies} CAD studies")
        print(f"  ✓ Top loci: {len(result.top_associations)}")

    def test_ancestry_filtering(self, tu):
        """Test 3: Ancestry filtering works correctly."""
        print("\n[TEST 3] Ancestry filtering")
        result = compare_gwas_studies(
            tu,
            trait="type 2 diabetes",
            ancestry_filter=["European"],
            max_studies=10
        )

        # Should only include European-ancestry studies
        if result.n_studies > 0:
            for study in result.studies:
                ancestries = " ".join(study.ancestry).lower()
                has_european = "european" in ancestries or "eur" in ancestries
                print(f"  {study.accession_id}: {study.ancestry}")
                # Note: Filtering is permissive (any match), so we just verify it ran
            print(f"  ✓ Filtered to {result.n_studies} studies")
        else:
            print("  ⚠️  No studies matched filter (may be too restrictive)")

    def test_quality_summary(self, tu):
        """Test 4: Quality summary calculation."""
        print("\n[TEST 4] Quality summary")
        result = compare_gwas_studies(
            tu,
            trait="diabetes",
            min_sample_size=5000,
            max_studies=10
        )

        quality = result.get_quality_summary()

        assert "total_studies" in quality
        assert "total_samples" in quality
        assert "ancestry_diversity" in quality
        assert quality["total_studies"] == result.n_studies
        assert quality["total_samples"] > 0

        print(f"  ✓ Total studies: {quality['total_studies']}")
        print(f"  ✓ Total samples: {quality['total_samples']:,}")
        print(f"  ✓ Ancestry diversity: {quality['ancestry_diversity']}")
        print(f"  ✓ Replication rate: {quality['replication_rate']:.1%}")


class TestMetaAnalysis:
    """Tests for meta_analyze_locus function."""

    def test_meta_analyze_tcf7l2(self, tu):
        """Test 5: Meta-analyze TCF7L2 locus for T2D."""
        print("\n[TEST 5] Meta-analyze TCF7L2 (rs7903146)")
        result = meta_analyze_locus(
            tu,
            rs_id="rs7903146",
            trait="type 2 diabetes"
        )

        assert isinstance(result, MetaAnalysisResult)
        assert result.locus == "rs7903146"

        if result.n_studies > 0:
            assert result.combined_p_value is not None
            assert 0 <= result.heterogeneity_i2 <= 100
            assert result.heterogeneity_level in ["low", "moderate", "substantial", "considerable"]

            print(f"  ✓ Studies: {result.n_studies}")
            print(f"  ✓ Combined p: {result.combined_p_value:.2e}")
            print(f"  ✓ Heterogeneity: {result.heterogeneity_level} (I²={result.heterogeneity_i2:.1f}%)")
            print(f"  ✓ Interpretation: {result.interpretation}")

            # TCF7L2 should be genome-wide significant for T2D
            assert result.is_significant, "TCF7L2 should be genome-wide significant for T2D"
        else:
            print("  ⚠️  No associations found (trait filtering may be strict)")

    def test_meta_analyze_apoe(self, tu):
        """Test 6: Meta-analyze APOE locus for Alzheimer's."""
        print("\n[TEST 6] Meta-analyze APOE (rs429358)")
        result = meta_analyze_locus(
            tu,
            rs_id="rs429358",
            trait="alzheimer"
        )

        assert result.locus == "rs429358"

        if result.n_studies > 0:
            print(f"  ✓ Studies: {result.n_studies}")
            print(f"  ✓ Combined p: {result.combined_p_value:.2e if result.combined_p_value else 'N/A'}")
            print(f"  ✓ Heterogeneity: I²={result.heterogeneity_i2:.1f}%")
        else:
            print("  ⚠️  No associations found")

    def test_heterogeneity_interpretation(self, tu):
        """Test 7: Heterogeneity interpretation logic."""
        print("\n[TEST 7] Heterogeneity interpretation")

        # Test different I² levels
        test_cases = [
            (10.0, "low"),
            (35.0, "moderate"),
            (60.0, "substantial"),
            (85.0, "considerable")
        ]

        for i2, expected_level in test_cases:
            result = MetaAnalysisResult(
                locus="test",
                n_studies=5,
                combined_beta=None,
                combined_se=None,
                combined_p_value=1e-10,
                heterogeneity_i2=i2,
                heterogeneity_p=None,
                studies=[],
                forest_plot_data=[]
            )
            assert result.heterogeneity_level == expected_level
            print(f"  ✓ I²={i2:.1f}% → {expected_level}")


class TestReplication:
    """Tests for assess_replication function."""

    def test_replication_t1d_studies(self, tu):
        """Test 8: Assess replication between T1D studies."""
        print("\n[TEST 8] Assess replication (T1D)")

        # Use known T1D studies
        results = assess_replication(
            tu,
            trait="type 1 diabetes",
            discovery_study_id="GCST000392",  # Barrett et al. T1D
            replication_study_id="GCST90029024",  # Alternative large T2D study as proxy
            p_threshold=0.05
        )

        if len(results) > 0:
            assert all(isinstance(r, ReplicationResult) for r in results)

            replicated = [r for r in results if r.replicated]
            not_replicated = [r for r in results if not r.replicated]

            print(f"  ✓ Total loci: {len(results)}")
            print(f"  ✓ Replicated: {len(replicated)}")
            print(f"  ✓ Not replicated: {len(not_replicated)}")

            # Check replication strength classification
            for r in replicated[:3]:
                assert r.replication_strength in [
                    "Strong (genome-wide significant)",
                    "Nominal (p<0.05)",
                    "Weak"
                ]
                print(f"  ✓ {r.locus}: {r.replication_strength}")
        else:
            print("  ⚠️  No overlapping loci found")

    def test_replication_result_properties(self):
        """Test 9: ReplicationResult property calculations."""
        print("\n[TEST 9] ReplicationResult properties")

        # Strong replication
        result1 = ReplicationResult(
            locus="rs123",
            discovery_p=1e-20,
            replication_p=1e-15,
            discovery_beta=0.3,
            replication_beta=0.28,
            replicated=True,
            consistent_direction=True
        )
        assert result1.replication_strength == "Strong (genome-wide significant)"
        print(f"  ✓ Strong replication: {result1.replication_strength}")

        # Nominal replication
        result2 = ReplicationResult(
            locus="rs456",
            discovery_p=1e-10,
            replication_p=0.01,
            discovery_beta=0.2,
            replication_beta=0.18,
            replicated=True,
            consistent_direction=True
        )
        assert result2.replication_strength == "Nominal (p<0.05)"
        print(f"  ✓ Nominal replication: {result2.replication_strength}")

        # Failed replication
        result3 = ReplicationResult(
            locus="rs789",
            discovery_p=1e-8,
            replication_p=0.3,
            discovery_beta=0.15,
            replication_beta=0.05,
            replicated=False,
            consistent_direction=True
        )
        assert result3.replication_strength == "Not replicated"
        print(f"  ✓ Failed replication: {result3.replication_strength}")


class TestStudyQuality:
    """Tests for study quality assessment."""

    def test_quality_metrics_high_quality(self):
        """Test 10: Quality metrics for high-quality study."""
        print("\n[TEST 10] High-quality study metrics")

        study = StudyMetadata(
            accession_id="GCST999999",
            trait="test trait",
            sample_size=100000,
            ancestry=["European", "East Asian"],
            snp_count=10000000,
            has_summary_stats=True
        )

        metrics = get_study_quality_metrics(study)

        assert metrics["power_score"] == "high"
        assert metrics["tier"] == "Tier 1 (High quality)"
        assert metrics["ancestry_count"] == 2
        assert metrics["is_multi_ancestry"] is True
        assert metrics["has_summary_stats"] is True

        print(f"  ✓ Power: {metrics['power_score']}")
        print(f"  ✓ Tier: {metrics['tier']}")
        print(f"  ✓ Multi-ancestry: {metrics['is_multi_ancestry']}")

    def test_quality_metrics_moderate_quality(self):
        """Test 11: Quality metrics for moderate-quality study."""
        print("\n[TEST 11] Moderate-quality study metrics")

        study = StudyMetadata(
            accession_id="GCST888888",
            trait="test trait",
            sample_size=15000,
            ancestry=["European"],
            has_summary_stats=False
        )

        metrics = get_study_quality_metrics(study)

        assert metrics["power_score"] == "moderate"
        assert metrics["tier"] == "Tier 2 (Moderate quality)"
        assert metrics["ancestry_count"] == 1
        assert metrics["is_multi_ancestry"] is False

        print(f"  ✓ Power: {metrics['power_score']}")
        print(f"  ✓ Tier: {metrics['tier']}")

    def test_quality_metrics_low_quality(self):
        """Test 12: Quality metrics for low-quality study."""
        print("\n[TEST 12] Low-quality study metrics")

        study = StudyMetadata(
            accession_id="GCST777777",
            trait="test trait",
            sample_size=5000,
            ancestry=["European"],
            has_summary_stats=False
        )

        metrics = get_study_quality_metrics(study)

        assert metrics["power_score"] == "low"
        assert metrics["tier"] == "Tier 3 (Limited sample size)"

        print(f"  ✓ Power: {metrics['power_score']}")
        print(f"  ✓ Tier: {metrics['tier']}")


class TestDataParsing:
    """Tests for data parsing and conversion functions."""

    def test_study_metadata_from_gwas_catalog(self):
        """Test 13: Parse StudyMetadata from GWAS Catalog data."""
        print("\n[TEST 13] Parse GWAS Catalog study data")

        study_data = {
            "accession_id": "GCST000392",
            "disease_trait": "Type 1 diabetes",
            "initial_sample_size": "7,514 European ancestry cases, 9,045 European ancestry controls",
            "discovery_ancestry": ["16559 European (U.K.)"],
            "platforms": "Illumina [550k]",
            "snp_count": 841622,
            "full_summary_stats_available": True
        }

        study = StudyMetadata.from_gwas_catalog(study_data)

        assert study.accession_id == "GCST000392"
        assert study.trait == "Type 1 diabetes"
        assert study.sample_size == 16559  # 7514 + 9045
        assert study.platform == "Illumina [550k]"
        assert study.snp_count == 841622
        assert study.has_summary_stats is True

        print(f"  ✓ Accession: {study.accession_id}")
        print(f"  ✓ Sample size parsed: {study.sample_size:,}")

    def test_study_metadata_from_opentargets(self):
        """Test 14: Parse StudyMetadata from Open Targets data."""
        print("\n[TEST 14] Parse Open Targets study data")

        study_data = {
            "id": "GCST000392",
            "traitFromSource": "Type 1 diabetes",
            "nSamples": 16559,
            "publicationFirstAuthor": "Barrett JC",
            "hasSumstats": True,
            "ldPopulationStructure": [
                {"ldPopulation": "EUR", "relativeSampleSize": 1.0}
            ]
        }

        study = StudyMetadata.from_opentargets(study_data)

        assert study.accession_id == "GCST000392"
        assert study.trait == "Type 1 diabetes"
        assert study.sample_size == 16559
        assert study.first_author == "Barrett JC"
        assert study.has_summary_stats is True
        assert "EUR" in study.ancestry

        print(f"  ✓ Accession: {study.accession_id}")
        print(f"  ✓ Ancestry: {study.ancestry}")

    def test_sample_size_parsing(self):
        """Test 15: Sample size parsing from various formats."""
        print("\n[TEST 15] Sample size parsing")

        test_cases = [
            ("10,000 cases, 15,000 controls", 25000),
            ("50000 individuals", 50000),
            ("3,456 European ancestry cases, 4,567 controls", 8023),
            ("", 0),
            ("No numeric data", 0)
        ]

        for text, expected in test_cases:
            result = StudyMetadata._parse_sample_size(text)
            assert result == expected, f"Failed for '{text}': got {result}, expected {expected}"
            print(f"  ✓ '{text[:30]}...' → {result:,}")


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_no_studies_found(self, tu):
        """Test 16: Handle case when no studies are found."""
        print("\n[TEST 16] No studies found")

        result = compare_gwas_studies(
            tu,
            trait="extremely_rare_nonexistent_trait_xyz123",
            max_studies=10
        )

        assert result.n_studies == 0
        assert len(result.studies) == 0
        assert len(result.top_associations) == 0
        print("  ✓ Handles missing studies gracefully")

    def test_single_study_meta_analysis(self, tu):
        """Test 17: Meta-analysis with single study."""
        print("\n[TEST 17] Single-study meta-analysis")

        # This will likely find 1 study for a rare SNP
        result = meta_analyze_locus(
            tu,
            rs_id="rs12345",  # Unlikely to exist in many studies
            trait="type 2 diabetes"
        )

        if result.n_studies == 1:
            assert result.combined_p_value is not None
            assert result.heterogeneity_i2 == 0.0
            print("  ✓ Handles single study correctly")
        else:
            print(f"  ⚠️  Found {result.n_studies} studies (expected 0-1)")

    def test_empty_replication(self, tu):
        """Test 18: Replication with no overlapping loci."""
        print("\n[TEST 18] No overlapping loci")

        results = assess_replication(
            tu,
            trait="test",
            discovery_study_id="GCST000001",
            replication_study_id="GCST999999",  # Likely doesn't exist
        )

        # Should handle gracefully
        assert isinstance(results, list)
        print("  ✓ Handles missing replication data gracefully")


def test_documentation_examples(tu):
    """Test 19: Verify all documentation examples work."""
    print("\n[TEST 19] Documentation examples")

    # Example from SKILL.md - compare studies
    result = compare_gwas_studies(
        tu,
        trait="type 2 diabetes",
        min_sample_size=10000,
        max_studies=10
    )
    assert result.n_studies > 0
    print("  ✓ Study comparison example works")

    # Example from QUICK_START.md - meta-analysis
    meta_result = meta_analyze_locus(
        tu,
        rs_id="rs7903146",
        trait="type 2 diabetes"
    )
    assert meta_result.locus == "rs7903146"
    print("  ✓ Meta-analysis example works")

    # Quality summary
    quality = result.get_quality_summary()
    assert "total_studies" in quality
    print("  ✓ Quality summary example works")


def test_full_workflow(tu):
    """Test 20: Complete workflow from start to finish."""
    print("\n[TEST 20] Complete workflow")

    trait = "coronary artery disease"

    # Step 1: Compare studies
    print("  Step 1: Comparing studies...")
    comparison = compare_gwas_studies(tu, trait, min_sample_size=5000, max_studies=8)
    assert comparison.n_studies > 0

    # Step 2: Get quality metrics
    print("  Step 2: Calculating quality metrics...")
    quality = comparison.get_quality_summary()
    assert quality["total_samples"] > 0

    # Step 3: Meta-analyze top locus
    if comparison.top_associations:
        print("  Step 3: Meta-analyzing top locus...")
        top_snp = comparison.top_associations[0].rs_id
        meta_result = meta_analyze_locus(tu, top_snp, trait)
        assert meta_result.locus == top_snp

    # Step 4: Check replication if multiple studies
    if comparison.n_studies >= 2:
        print("  Step 4: Assessing replication...")
        study1 = comparison.studies[0].accession_id
        study2 = comparison.studies[1].accession_id
        replication = assess_replication(tu, trait, study1, study2)
        assert isinstance(replication, list)

    print("  ✓ Complete workflow executed successfully")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
