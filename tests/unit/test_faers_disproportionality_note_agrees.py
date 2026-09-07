"""FAERS_calculate_disproportionality: the note must agree with its own verdict.

The concluding `note` was a constant that asserted "Disproportionality analysis
indicates potential safety signal" for every result, including results whose own
`signal_detection.signal_detected` was False. Confirmed live with
NALTREXONE + Hepatotoxicity: ROR 0.383 (95% CI 0.238-0.617, entirely below 1) and
`signal_detected: false`, yet the note still announced a potential signal -- the
opposite conclusion for a clinician skimming the summary line.

Offline: the four count lookups are patched, so no openFDA request is made.
"""

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


def _tool():
    from tooluniverse.faers_analytics_tool import FAERSAnalyticsTool

    return FAERSAnalyticsTool({"name": "t", "type": "FAERSAnalyticsTool"})


def _run(drug_event_count, drug_total, event_total, total):
    """Run the real calculation against fixed contingency-table counts."""
    tool = _tool()
    with (
        patch.object(
            tool,
            "_get_faers_count",
            side_effect=[drug_event_count, drug_total, event_total],
        ),
        patch.object(tool, "_get_faers_total_count", return_value=total),
    ):
        return tool._calculate_disproportionality(
            {"drug_name": "TESTDRUG", "adverse_event": "Test event"}
        )


class TestDisproportionalityNoteAgreesWithVerdict:
    def test_protective_direction_does_not_claim_a_signal(self):
        """Reproduces the NALTREXONE/Hepatotoxicity shape: ROR and CI below 1."""
        result = _run(50, 400_000, 300_000, 21_000_000)

        assert result["signal_detection"]["signal_detected"] is False
        assert result["metrics"]["ROR"]["ci_95_upper"] < 1.0

        note = result["note"]
        assert "indicates a potential safety signal" not in note
        assert "No safety signal" in note
        # Must not be misread as evidence the drug protects against the event.
        assert "not" in note.lower() and "protective" in note.lower()

    def test_detected_signal_still_reports_a_signal(self):
        result = _run(500, 10_000, 20_000, 21_000_000)

        assert result["signal_detection"]["signal_detected"] is True
        note = result["note"]
        assert "indicates a potential safety signal" in note
        assert result["signal_detection"]["signal_strength"] in note

    @pytest.mark.parametrize(
        "counts",
        [(50, 400_000, 300_000, 21_000_000), (500, 10_000, 20_000, 21_000_000)],
        ids=["no-signal", "signal"],
    )
    def test_every_note_keeps_the_causation_caveat(self, counts):
        note = _run(*counts)["note"]
        assert "does NOT prove causation" in note
        assert "Requires clinical evaluation." in note
