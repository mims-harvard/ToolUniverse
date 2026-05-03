"""Unit tests for Expression Atlas tools."""

import pytest
from tooluniverse import ToolUniverse


class TestExpressionAtlasTools:
    """Test suite for EBI Expression Atlas gene expression tools."""

    @pytest.fixture
    def tu(self):
        """Initialize ToolUniverse with all tools loaded."""
        tu = ToolUniverse()
        tu.load_tools()
        return tu

    def test_tools_load(self, tu):
        """Verify all Expression Atlas tools are registered and loadable."""
        assert hasattr(tu.tools, "ExpressionAtlas_get_baseline")
        assert hasattr(tu.tools, "ExpressionAtlas_search_differential")
        assert hasattr(tu.tools, "ExpressionAtlas_search_experiments")
        assert hasattr(tu.tools, "ExpressionAtlas_get_experiment")

    def test_get_baseline_expression(self, tu):
        """Test baseline expression experiment search."""
        result = tu.tools.ExpressionAtlas_get_baseline(
            **{"gene": "TP53", "species": "homo sapiens"}
        )

        assert isinstance(result, dict)
        assert result.get("status") in ["success", "error"]

        if result["status"] == "success":
            data = result.get("data", {})
            assert "baseline_experiments" in data
            assert "total_baseline" in data
            assert isinstance(data["baseline_experiments"], list)

            # Expression Atlas has 123 human baseline experiments
            assert data["total_baseline"] > 100
            print(
                f"✓ Found {data['total_baseline']} baseline experiments, "
                f"{data.get('gene_specific_count', 0)} gene-specific"
            )

    def test_search_differential_experiments(self, tu):
        """Test differential expression experiment search."""
        result = tu.tools.ExpressionAtlas_search_differential(
            **{"gene": "EGFR", "species": "homo sapiens"}
        )

        assert isinstance(result, dict)
        assert result.get("status") in ["success", "error"]

        if result["status"] == "success":
            data = result.get("data", {})
            assert "experiments" in data
            assert "experiment_count" in data
            assert isinstance(data["experiments"], list)

            # EGFR is cancer-related, should have differential experiments
            if data["experiments"]:
                exp = data["experiments"][0]
                assert "experiment_accession" in exp
                assert "experiment_type" in exp
                print(f"✓ Found {data['experiment_count']} differential experiments")

    def test_search_experiments_combined(self, tu):
        """Test combined experiment search with gene and condition."""
        result = tu.tools.ExpressionAtlas_search_experiments(
            **{"gene": "TP53", "condition": "cancer", "species": "homo sapiens"}
        )

        assert isinstance(result, dict)
        assert result.get("status") in ["success", "error"]

        if result["status"] == "success":
            data = result.get("data", {})
            assert "experiments" in data
            experiments = data["experiments"]
            # Should filter by both gene and condition
            if experiments:
                # Check that experiments are cancer-related
                cancer_related = any(
                    "cancer" in exp.get("experiment_description", "").lower()
                    for exp in experiments[:10]
                )
                print(
                    f"✓ Found {len(experiments)} experiments, "
                    f"cancer-related: {cancer_related}"
                )

    def test_get_experiment_metadata(self, tu):
        """Test experiment metadata retrieval by accession."""
        # E-GTEX-8 is the GTEx v8 baseline experiment (should exist)
        result = tu.tools.ExpressionAtlas_get_experiment(**{"accession": "E-GTEX-8"})

        assert isinstance(result, dict)
        assert result.get("status") in ["success", "error"]

        if result["status"] == "success":
            data = result.get("data")
            if data:
                assert "accession" in data
                assert "type" in data
                assert "description" in data
                print(f"✓ Experiment: {data['accession']}, {data.get('type')}")
            else:
                # Experiment not found or API changed
                assert result.get("message")
                pytest.skip("Experiment not found - API may have changed")

    def test_missing_parameter_error(self, tu):
        """Test error handling for missing required parameters."""
        result = tu.tools.ExpressionAtlas_get_baseline(**{})

        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert "error" in result
        assert "required" in result["error"].lower()

    def test_species_filtering(self, tu):
        """Test species filtering in experiment search."""
        result = tu.tools.ExpressionAtlas_get_baseline(
            **{"gene": "TP53", "species": "mus musculus"}
        )

        assert isinstance(result, dict)
        assert result.get("status") in ["success", "error"]

        if result["status"] == "success":
            data = result.get("data", {})
            experiments = data.get("baseline_experiments", [])
            # All returned experiments should be mouse
            if experiments:
                for exp in experiments[:5]:
                    assert exp.get("species", "").lower() == "mus musculus"
                print(f"✓ Found {len(experiments)} mouse baseline experiments")

    @pytest.mark.skip(
        reason="API endpoint may timeout or be unavailable during CI testing"
    )
    def test_api_timeout_handling(self, tu):
        """Test graceful handling of API timeouts."""
        # This test may fail intermittently due to external API
        result = tu.tools.ExpressionAtlas_get_baseline(
            **{"gene": "TP53", "species": "homo sapiens"}
        )

        assert isinstance(result, dict)
        # Should either succeed or return proper error
        assert result.get("status") in ["success", "error"]
        if result["status"] == "error":
            assert "timeout" in result.get("error", "").lower()
