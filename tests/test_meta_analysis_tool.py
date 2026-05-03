"""Tests for MetaAnalysisTool."""

import math

import pytest


@pytest.fixture
def tool():
    from tooluniverse.meta_analysis_tool import MetaAnalysisTool

    config = {"name": "MetaAnalysis_run"}
    return MetaAnalysisTool(config)


class TestMetaAnalysisValidation:
    def test_missing_studies(self, tool):
        result = tool.run({})
        assert result["status"] == "error"

    def test_single_study_error(self, tool):
        result = tool.run(
            {"studies": [{"name": "A", "effect_size": 0.5, "se": 0.1}]}
        )
        assert result["status"] == "error"
        assert "At least 2" in result["error"]

    def test_missing_fields_error(self, tool):
        result = tool.run(
            {
                "studies": [
                    {"name": "A", "effect_size": 0.5},
                    {"name": "B", "effect_size": 0.3, "se": 0.1},
                ]
            }
        )
        assert result["status"] == "error"

    def test_zero_se_error(self, tool):
        result = tool.run(
            {
                "studies": [
                    {"name": "A", "effect_size": 0.5, "se": 0.0},
                    {"name": "B", "effect_size": 0.3, "se": 0.1},
                ]
            }
        )
        assert result["status"] == "error"
        assert "non-positive" in result["error"]

    def test_invalid_method_error(self, tool):
        result = tool.run(
            {
                "studies": [
                    {"name": "A", "effect_size": 0.5, "se": 0.1},
                    {"name": "B", "effect_size": 0.3, "se": 0.1},
                ],
                "method": "bayesian",
            }
        )
        assert result["status"] == "error"


class TestMetaAnalysisFixed:
    def test_fixed_effects_basic(self, tool):
        studies = [
            {"name": "A", "effect_size": 0.5, "se": 0.1},
            {"name": "B", "effect_size": 0.3, "se": 0.1},
        ]
        result = tool.run({"studies": studies, "method": "fixed"})
        assert result["status"] == "success"
        d = result["data"]
        assert d["method"] == "fixed"
        assert d["num_studies"] == 2
        # Equal weights → pooled is mean
        assert d["pooled_effect"] == pytest.approx(0.4, abs=0.01)
        assert d["heterogeneity"]["tau_squared"] is None

    def test_fixed_weights_inversely_proportional_to_variance(self, tool):
        studies = [
            {"name": "A", "effect_size": 0.5, "se": 0.1},
            {"name": "B", "effect_size": 0.3, "se": 0.2},
        ]
        result = tool.run({"studies": studies, "method": "fixed"})
        d = result["data"]
        # Study A has smaller SE → should have higher weight
        w_a = next(s for s in d["per_study"] if s["name"] == "A")["weight_pct"]
        w_b = next(s for s in d["per_study"] if s["name"] == "B")["weight_pct"]
        assert w_a > w_b
        # Specifically: w_A/w_B = (1/0.01)/(1/0.04) = 4
        assert w_a / w_b == pytest.approx(4.0, rel=0.01)


class TestMetaAnalysisRandom:
    def test_random_effects_default(self, tool):
        studies = [
            {"name": "A", "effect_size": 0.5, "se": 0.1},
            {"name": "B", "effect_size": 0.3, "se": 0.15},
            {"name": "C", "effect_size": 0.7, "se": 0.2},
        ]
        result = tool.run({"studies": studies})
        assert result["status"] == "success"
        d = result["data"]
        assert d["method"] == "random"
        assert d["heterogeneity"]["tau_squared"] is not None
        # Pooled should be between min and max effects
        assert 0.2 < d["pooled_effect"] < 0.8
        # CI should contain pooled effect
        assert d["pooled_ci_lower"] < d["pooled_effect"] < d["pooled_ci_upper"]

    def test_homogeneous_studies_low_heterogeneity(self, tool):
        # All studies have same effect → I² should be ~0
        studies = [
            {"name": "A", "effect_size": 0.5, "se": 0.1},
            {"name": "B", "effect_size": 0.5, "se": 0.15},
            {"name": "C", "effect_size": 0.5, "se": 0.2},
        ]
        result = tool.run({"studies": studies, "method": "random"})
        d = result["data"]
        assert d["heterogeneity"]["I_squared"] == 0.0
        assert d["pooled_effect"] == pytest.approx(0.5, abs=0.01)

    def test_heterogeneous_studies_high_i_squared(self, tool):
        # Very different effects → high I²
        studies = [
            {"name": "A", "effect_size": 0.1, "se": 0.05},
            {"name": "B", "effect_size": 1.0, "se": 0.05},
            {"name": "C", "effect_size": -0.5, "se": 0.05},
        ]
        result = tool.run({"studies": studies, "method": "random"})
        d = result["data"]
        assert d["heterogeneity"]["I_squared"] > 90


class TestMetaAnalysisStatistics:
    def test_significant_result(self, tool):
        studies = [
            {"name": "A", "effect_size": 0.5, "se": 0.1},
            {"name": "B", "effect_size": 0.6, "se": 0.1},
        ]
        result = tool.run({"studies": studies, "method": "fixed"})
        d = result["data"]
        assert d["pooled_p_value"] < 0.05
        assert "significant" in d["interpretation"]

    def test_ci_coverage(self, tool):
        studies = [
            {"name": "A", "effect_size": 0.5, "se": 0.1},
            {"name": "B", "effect_size": 0.3, "se": 0.15},
        ]
        result = tool.run({"studies": studies, "method": "fixed"})
        d = result["data"]
        # CI width = 2 * 1.96 * SE
        ci_width = d["pooled_ci_upper"] - d["pooled_ci_lower"]
        assert ci_width == pytest.approx(2 * 1.96 * d["pooled_se"], rel=0.01)

    def test_per_study_weights_sum_to_100(self, tool):
        studies = [
            {"name": "A", "effect_size": 0.5, "se": 0.1},
            {"name": "B", "effect_size": 0.3, "se": 0.15},
            {"name": "C", "effect_size": 0.7, "se": 0.2},
        ]
        result = tool.run({"studies": studies, "method": "random"})
        total = sum(s["weight_pct"] for s in result["data"]["per_study"])
        assert total == pytest.approx(100.0, abs=0.1)

    def test_q_statistic_properties(self, tool):
        studies = [
            {"name": "A", "effect_size": 0.5, "se": 0.1},
            {"name": "B", "effect_size": 0.3, "se": 0.15},
            {"name": "C", "effect_size": 0.7, "se": 0.2},
        ]
        result = tool.run({"studies": studies, "method": "random"})
        het = result["data"]["heterogeneity"]
        assert het["Q"] >= 0
        assert het["Q_df"] == 2  # k - 1
        assert 0 <= het["Q_p_value"] <= 1
        assert 0 <= het["I_squared"] <= 100


class TestMetaAnalysisInterpretation:
    def test_interpretation_present(self, tool):
        studies = [
            {"name": "A", "effect_size": 0.5, "se": 0.1},
            {"name": "B", "effect_size": 0.3, "se": 0.15},
        ]
        result = tool.run({"studies": studies, "method": "random"})
        interp = result["data"]["interpretation"]
        assert "Random-effects" in interp
        assert "2 studies" in interp
        assert "95% CI" in interp
