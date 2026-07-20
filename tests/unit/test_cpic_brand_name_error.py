"""Regression guard for Fix-R5C-2: CPIC_get_recommendations returned
"Use CPIC_list_guidelines to find valid guideline IDs" when a brand name
(e.g. "zoloft") failed to resolve to a guideline -- CPIC's own /drug table
only indexes generic names, so that suggestion doesn't actually solve a
caller's "I don't know the generic name" problem. The error now names the
real constraint and suggests trying the generic name instead.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.cpic_search_pairs_tool import CPICGetRecommendationsTool

pytestmark = pytest.mark.unit


def _empty_drug_lookup_response():
    resp = MagicMock()
    resp.json.return_value = []
    resp.raise_for_status.return_value = None
    return resp


def test_brand_name_error_suggests_generic_name():
    tool = CPICGetRecommendationsTool({"name": "CPIC_get_recommendations"})

    with patch(
        "tooluniverse.cpic_search_pairs_tool.requests.get",
        return_value=_empty_drug_lookup_response(),
    ):
        result = tool.run({"drug": "zoloft"})

    assert result["status"] == "error"
    assert "zoloft" in result["error"]
    assert "generic drug names" in result["error"]
    assert "sertraline" in result["error"]


def test_missing_drug_and_guideline_id_keeps_original_error():
    tool = CPICGetRecommendationsTool({"name": "CPIC_get_recommendations"})
    result = tool.run({})

    assert result["status"] == "error"
    assert "Either guideline_id or drug name is required" in result["error"]


def _resp(json_body):
    r = MagicMock()
    r.json.return_value = json_body
    r.raise_for_status.return_value = None
    return r


class TestEmptyRecommendationNoteAccuracy:
    """Regression guard for Fix-R31C-3: the "empty recommendations" note
    always blamed "guideline uses a dosing algorithm rather than a table",
    even for a multi-drug guideline (e.g. CYP2D6/opioids, 100416) filtered
    down to a specific drug it doesn't have a row for -- confirmed live
    that guideline has 66 real recommendation rows, just none for
    methadone/buprenorphine/naltrexone (only codeine/tramadol/hydrocodone).
    The note must now distinguish "no table at all" from "table exists,
    not for this drug"."""

    def test_drug_filtered_to_zero_rows_in_a_populated_guideline(self):
        tool = CPICGetRecommendationsTool({"name": "CPIC_get_recommendations"})

        def fake_get(url, params=None, **kwargs):
            if url.endswith("/drug"):
                return _resp([{"guidelineid": 100416, "rxnormid": "6813"}])
            if "drugid" in (params or {}):
                return _resp([])  # filtered to this drug: no rows
            return _resp([{"guidelineid": 100416}])  # unfiltered: guideline has rows

        with patch(
            "tooluniverse.cpic_search_pairs_tool.requests.get", side_effect=fake_get
        ):
            result = tool.run({"drug": "methadone"})

        note = result["data"]["note"]
        assert "other drugs it covers" in note
        assert "dosing algorithm" not in note

    def test_guideline_with_genuinely_no_table_keeps_dosing_algorithm_note(self):
        tool = CPICGetRecommendationsTool({"name": "CPIC_get_recommendations"})

        def fake_get(url, params=None, **kwargs):
            if url.endswith("/drug"):
                return _resp([{"guidelineid": 100425, "rxnormid": "11289"}])
            return _resp([])  # both the drug-filtered AND unfiltered checks are empty

        with patch(
            "tooluniverse.cpic_search_pairs_tool.requests.get", side_effect=fake_get
        ):
            result = tool.run({"drug": "warfarin"})

        assert "dosing algorithm" in result["data"]["note"]
