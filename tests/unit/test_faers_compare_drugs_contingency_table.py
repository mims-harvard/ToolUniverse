"""FAERS_compare_drugs must show the case counts its verdict rests on (Fix-R37).

`_compare_drugs` computed a full 2x2 contingency table for each drug -- it
calls `_calculate_disproportionality`, which builds one -- and then discarded
it, returning only ROR/PRR/IC and a sentence such as "LORAZEPAM and DIAZEPAM
show similar-strength detected signals". A ratio of two ratios is
uninterpretable without its denominators: "similar-strength" means something
very different when both arms rest on thousands of co-reported cases than when
one rests on a handful, and nothing in the output warned the reader to check.
Recovering the counts took two further calls to the sibling tool.

The fix is strictly additive -- every previously returned value keeps its
value -- and reuses the sibling's exact key names rather than inventing a
second vocabulary for the same concept.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

CONTINGENCY_KEYS = {
    "a_drug_and_event",
    "b_drug_no_event",
    "c_no_drug_event",
    "d_no_drug_no_event",
}


def _tool():
    from tooluniverse.faers_analytics_tool import FAERSAnalyticsTool

    return FAERSAnalyticsTool({"name": "t", "type": "FAERSAnalyticsTool"})


def _disproportionality_result(a, ror, signal_detected=True):
    """A `_calculate_disproportionality` payload shaped like the real one.

    b/c/d are held at realistic FAERS magnitudes so the only thing varying
    across tests is the `a` cell the caveat keys off.
    """
    return {
        "status": "success",
        "contingency_table": {
            "a_drug_and_event": a,
            "b_drug_no_event": 172162,
            "c_no_drug_event": 321527,
            "d_no_drug_no_event": 20192437,
        },
        "metrics": {"ROR": {"value": ror}},
        "signal_detection": {
            "signal_detected": signal_detected,
            "signal_strength": "Moderate signal" if signal_detected else "No signal",
        },
    }


def _compare(results, drug1="LORAZEPAM", drug2="DIAZEPAM", event="Fall"):
    tool = _tool()
    with patch.object(tool, "_calculate_disproportionality", side_effect=results):
        return tool._compare_drugs(
            {"drug1": drug1, "drug2": drug2, "adverse_event": event}
        )


def _baseline():
    """The live lorazepam/diazepam + Fall figures this fix was verified on."""
    return _compare(
        [
            _disproportionality_result(6564, 2.394),
            _disproportionality_result(4310, 2.31),
        ]
    )


class TestCompareDrugsContingencyTable:
    def test_both_arms_return_the_counts_behind_their_metrics(self):
        # Reusing FAERS_calculate_disproportionality's vocabulary is half the
        # point: a second set of names for the same concept is worse than none.
        result = _baseline()

        assert result["status"] == "success"
        assert result["drug1"]["contingency_table"]["a_drug_and_event"] == 6564
        assert result["drug2"]["contingency_table"]["a_drug_and_event"] == 4310
        for arm in ("drug1", "drug2"):
            assert set(result[arm]["contingency_table"]) == CONTINGENCY_KEYS

    def test_counts_are_passed_through_not_recomputed(self):
        # The arm must echo whatever the disproportionality path produced, so
        # the two tools can never disagree about the same drug/event pair.
        table = {
            "a_drug_and_event": 11,
            "b_drug_no_event": 22,
            "c_no_drug_event": 33,
            "d_no_drug_no_event": 44,
        }
        upstream = _disproportionality_result(0, 3.0)
        upstream["contingency_table"] = table

        downstream = _disproportionality_result(4310, 2.31)
        result = _compare([upstream, downstream])

        assert result["drug1"]["contingency_table"] == table
        assert result["drug2"]["contingency_table"] == downstream["contingency_table"]

    def test_the_fix_is_additive(self):
        # Every value the tool returned before the fix must be untouched --
        # the verdict text, the metrics, and the standing note.
        result = _baseline()

        assert (
            result["comparison"]
            == "LORAZEPAM and DIAZEPAM show similar-strength detected signals"
        )
        assert result["adverse_event"] == "Fall"
        assert result["drug1"]["name"] == "LORAZEPAM"
        assert result["drug1"]["metrics"] == {"ROR": {"value": 2.394}}
        assert result["drug2"]["metrics"] == {"ROR": {"value": 2.31}}
        assert result["drug1"]["signal_detection"]["signal_detected"] is True
        assert result["note"].startswith("Direct comparison of safety signals.")

    def test_missing_upstream_table_yields_null_rather_than_an_error(self):
        # Older/degenerate payloads without a table must not break the arm.
        bare = {
            "status": "success",
            "metrics": {"ROR": {"value": 2.0}},
            "signal_detection": {"signal_detected": True},
        }

        result = _compare([bare, bare])

        assert result["status"] == "success"
        assert result["drug1"]["contingency_table"] is None
        assert result["comparison_caveat"] is None


class TestCompareDrugsSmallCountCaveat:
    def test_a_single_digit_arm_qualifies_the_similar_strength_verdict(self):
        # The headline case: both RORs land inside the 1.5x "similar" band, but
        # one arm is 6 cases. The verdict text is unchanged; the caveat says so.
        result = _compare(
            [
                _disproportionality_result(6564, 2.394),
                _disproportionality_result(6, 2.31),
            ]
        )

        assert (
            result["comparison"]
            == "LORAZEPAM and DIAZEPAM show similar-strength detected signals"
        )
        caveat = result["comparison_caveat"]
        assert "DIAZEPAM rests on 6 co-reported cases" in caveat
        assert "LORAZEPAM rests on" not in caveat
        assert "equal-confidence" in caveat

    def test_both_small_arms_are_both_named(self):
        result = _compare(
            [
                _disproportionality_result(4, 2.394),
                _disproportionality_result(1, 2.31),
            ]
        )

        caveat = result["comparison_caveat"]
        assert "LORAZEPAM rests on 4 co-reported cases" in caveat
        # Singular, so the sentence reads correctly for a one-case arm.
        assert "DIAZEPAM rests on 1 co-reported case" in caveat
        assert "DIAZEPAM rests on 1 co-reported cases" not in caveat

    def test_threshold_boundary(self):
        from tooluniverse.faers_analytics_tool import _SMALL_CASE_COUNT_THRESHOLD

        # An arm exactly at the threshold is precise enough; one below is not.
        at = _compare(
            [
                _disproportionality_result(_SMALL_CASE_COUNT_THRESHOLD, 2.394),
                _disproportionality_result(4310, 2.31),
            ]
        )
        below = _compare(
            [
                _disproportionality_result(_SMALL_CASE_COUNT_THRESHOLD - 1, 2.394),
                _disproportionality_result(4310, 2.31),
            ]
        )

        assert at["comparison_caveat"] is None
        assert below["comparison_caveat"] is not None


class TestCompareDrugsReturnSchema:
    """The declared schema must describe exactly what the code emits."""

    @staticmethod
    def _config():
        path = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "tooluniverse"
            / "data"
            / "faers_analytics_tools.json"
        )
        configs = json.loads(path.read_text())
        return next(c for c in configs if c["name"] == "FAERS_compare_drugs")

    def test_schema_matches_the_emitted_keys_exactly(self):
        # Equality in both directions: every added key is declared, and no key
        # is declared that the code does not actually emit.
        result = _baseline()
        properties = self._config()["return_schema"]["properties"]

        assert set(properties) == set(result) - {"status"}
        for arm in ("drug1", "drug2"):
            assert set(properties[arm]["properties"]) == set(result[arm])
            table = properties[arm]["properties"]["contingency_table"]
            assert set(table["properties"]) == CONTINGENCY_KEYS

    def test_description_mentions_the_added_keys(self):
        description = self._config()["description"]

        assert "contingency_table" in description
        assert "comparison_caveat" in description
        assert "a_drug_and_event" in description
