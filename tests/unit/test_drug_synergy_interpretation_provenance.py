"""Threshold and provenance tests for derived drug-synergy labels."""

import pytest

from tooluniverse.drug_synergy_tool import DrugSynergyTool


pytestmark = pytest.mark.unit


def _tool() -> DrugSynergyTool:
    return DrugSynergyTool({"name": "DrugSynergy_calculate"})


@pytest.mark.parametrize(
    ("score", "label"),
    [
        (0.096, "Synergy"),
        (0.1, "Strong synergy"),
        (-0.096, "Antagonism"),
        (-0.1, "Strong antagonism"),
    ],
)
def test_bliss_uses_raw_score_at_strong_effect_boundaries(score, label):
    """Display rounding cannot promote a score across the ±0.10 boundary."""
    effect_a = 0.2
    effect_b = 0.3
    expected = effect_a + effect_b - effect_a * effect_b
    result = _tool().run(
        {
            "operation": "calculate_bliss",
            "effect_a": effect_a,
            "effect_b": effect_b,
            "effect_combination": expected + score,
        }
    )

    assert result["status"] == "success"
    data = result["data"]
    assert data["interpretation"] == label
    assert data["bliss_synergy_score"] == pytest.approx(score)
    assert data["interpretation_criteria"]["metric_value"] == pytest.approx(score)


def test_bliss_interpretation_is_explicitly_tooluniverse_derived():
    """The response carries machine-readable units, rules, and provenance."""
    result = _tool().run(
        {
            "operation": "calculate_bliss",
            "effect_a": 0.2,
            "effect_b": 0.3,
            "effect_combination": 0.536,
        }
    )

    criteria = result["data"]["interpretation_criteria"]
    assert criteria["derived"] is True
    assert criteria["derived_by"] == "ToolUniverse"
    assert criteria["units"] == "fractional inhibition"
    assert criteria["strong_synergy_rule"] == "score >= 0.10"
    assert criteria["strong_antagonism_rule"] == "score <= -0.10"


def test_hsa_uses_raw_mean_and_publishes_criteria():
    """HSA shares the same raw-score boundary and provenance semantics."""
    result = _tool().run(
        {
            "operation": "calculate_hsa",
            "effects_a": [0.2, 0.2],
            "effects_b": [0.3, 0.3],
            "effects_combo": [0.396, 0.396],
        }
    )

    data = result["data"]
    assert data["mean_hsa_synergy_score"] == pytest.approx(0.096)
    assert data["interpretation"] == "Synergy"
    assert data["interpretation_criteria"]["metric_value"] == pytest.approx(0.096)
