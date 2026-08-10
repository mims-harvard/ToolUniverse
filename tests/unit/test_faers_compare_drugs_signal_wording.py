"""FAERS_compare_drugs comparison-text wording (Fix-19B-2).

`_compare_drugs` used to rank drugs purely by raw ROR magnitude ("X shows
stronger signal than Y") even when neither drug actually crossed this
tool's own signal-detection threshold (signal_detection.signal_detected).
Confirmed live with nirsevimab/palivizumab + anaphylactic reaction: both
drugs had signal_detected=False (ROR < 1, i.e. no elevated-risk
association) but the narrative still claimed one showed a "stronger
signal" -- misleading language for a clinician skimming only the text.
"""

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


def _tool():
    from tooluniverse.faers_analytics_tool import FAERSAnalyticsTool

    return FAERSAnalyticsTool({"name": "t", "type": "FAERSAnalyticsTool"})


def _disproportionality_result(ror, signal_detected):
    return {
        "status": "success",
        "metrics": {"ROR": {"value": ror}},
        "signal_detection": {
            "signal_detected": signal_detected,
            "signal_strength": "Weak signal" if signal_detected else "No signal",
        },
    }


class TestFAERSCompareDrugsSignalWording:
    def test_neither_drug_has_a_detected_signal(self):
        # Both RORs are < 1 (no elevated-risk association), so the
        # comparison must not claim either drug "shows a stronger signal".
        tool = _tool()
        with patch.object(
            tool,
            "_calculate_disproportionality",
            side_effect=[
                _disproportionality_result(0.22, False),
                _disproportionality_result(0.47, False),
            ],
        ):
            result = tool._compare_drugs(
                {
                    "drug1": "nirsevimab",
                    "drug2": "palivizumab",
                    "adverse_event": "anaphylactic reaction",
                }
            )

        assert result["status"] == "success"
        comparison = result["comparison"]
        assert "Neither" in comparison
        assert "stronger signal" not in comparison

    def test_only_one_drug_has_a_detected_signal(self):
        tool = _tool()
        with patch.object(
            tool,
            "_calculate_disproportionality",
            side_effect=[
                _disproportionality_result(5.0, True),
                _disproportionality_result(0.8, False),
            ],
        ):
            result = tool._compare_drugs(
                {"drug1": "drugA", "drug2": "drugB", "adverse_event": "some event"}
            )

        comparison = result["comparison"]
        assert "drugA shows a detected safety signal" in comparison
        assert "drugB does not" in comparison

    def test_both_drugs_have_a_detected_signal_ranks_by_magnitude(self):
        tool = _tool()
        with patch.object(
            tool,
            "_calculate_disproportionality",
            side_effect=[
                _disproportionality_result(8.0, True),
                _disproportionality_result(2.0, True),
            ],
        ):
            result = tool._compare_drugs(
                {"drug1": "drugA", "drug2": "drugB", "adverse_event": "some event"}
            )

        comparison = result["comparison"]
        assert "Both show a detected signal" in comparison
        assert "drugA's is stronger" in comparison
