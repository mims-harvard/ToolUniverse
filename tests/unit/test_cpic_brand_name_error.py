"""Regression guard for Fix-R5C-2: CPIC_get_recommendations returned
"Use CPIC_list_guidelines to find valid guideline IDs" when a brand name
(e.g. "zoloft") failed to resolve to a guideline -- CPIC's own /drug table
only indexes generic names, so that suggestion doesn't actually solve a
caller's "I don't know the generic name" problem. The error now names the
real constraint and suggests trying the generic name instead.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from tooluniverse.cpic_search_pairs_tool import (
    CPICGetRecommendationsTool,
    _resolve_drug_to_guideline_id,
)

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


class TestRequestFailureDistinctFromGenuineNotFound:
    """Regression guard for Fix-R56A-1: _resolve_drug_to_guideline_id's bare
    `except Exception: pass` reported a transient CPIC API failure (network
    error, timeout) identically to a drug genuinely not being in CPIC's
    database -- confirmed live for simvastatin, which IS in CPIC's /drug
    table with a real guidelineid (100426), but a connection hiccup while
    testing this exact endpoint produced "No CPIC guideline found for drug
    'simvastatin'", wrongly implying the drug has no CPIC coverage at all.
    A request failure must now surface as its own distinct error."""

    def test_connection_error_reports_api_failure_not_drug_not_found(self):
        tool = CPICGetRecommendationsTool({"name": "CPIC_get_recommendations"})

        with patch(
            "tooluniverse.cpic_search_pairs_tool.requests.get",
            side_effect=requests.exceptions.ConnectionError("simulated connection failure"),
        ):
            result = tool.run({"drug": "simvastatin"})

        assert result["status"] == "error"
        assert "CPIC API error" in result["error"]
        assert "simvastatin" in result["error"]
        # Must NOT claim the drug has no guideline -- that's a different,
        # false claim about CPIC's actual data.
        assert "No CPIC guideline found" not in result["error"]

    def test_genuinely_empty_drug_lookup_still_reports_not_found(self):
        """A real 'not in CPIC' case (request succeeds, zero rows) must
        keep reporting the original not-found message, not an API error."""
        tool = CPICGetRecommendationsTool({"name": "CPIC_get_recommendations"})

        with patch(
            "tooluniverse.cpic_search_pairs_tool.requests.get",
            return_value=_empty_drug_lookup_response(),
        ):
            result = tool.run({"drug": "not-a-real-drug-xyz"})

        assert result["status"] == "error"
        assert "No CPIC guideline found" in result["error"]
        assert "CPIC API error" not in result["error"]

    def test_resolve_helper_raises_on_request_failure_rather_than_swallowing_it(self):
        with patch(
            "tooluniverse.cpic_search_pairs_tool.requests.get",
            side_effect=requests.exceptions.Timeout("simulated timeout"),
        ):
            with pytest.raises(requests.exceptions.RequestException):
                _resolve_drug_to_guideline_id("simvastatin")


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


class TestExactMatchPreferredOverSubstring:
    """Regression guard for Fix-R35C-1: CPIC's /drug lookup used a fuzzy
    `ilike.*name*` substring match and always took the first result --
    confirmed live that querying "citalopram" (a substring of
    "escitalopram") silently returned escitalopram's guideline/rxnorm id
    instead, because escitalopram happened to sort first in CPIC's
    unordered response. Same collision confirmed for "phenytoin" (a
    substring of "fosphenytoin"). A clinician asking for one drug's dosing
    guidance would silently receive a different, related drug's guidance
    with no indication of the substitution."""

    def test_exact_match_wins_over_a_substring_match_sorted_first(self):
        # escitalopram sorts before citalopram in the fuzzy result set, but
        # querying "citalopram" must resolve to citalopram's own record.
        rows = [
            {"name": "escitalopram", "guidelineid": 100413, "rxnormid": "321988"},
            {"name": "citalopram", "guidelineid": 100413, "rxnormid": "2556"},
        ]
        resp = MagicMock()
        resp.json.return_value = rows
        resp.raise_for_status.return_value = None

        with patch(
            "tooluniverse.cpic_search_pairs_tool.requests.get", return_value=resp
        ):
            guideline_id, rxnorm_id = _resolve_drug_to_guideline_id("citalopram")

        assert guideline_id == 100413
        assert rxnorm_id == "2556"

    def test_no_exact_match_falls_back_to_first_fuzzy_hit(self):
        rows = [{"name": "escitalopram", "guidelineid": 100413, "rxnormid": "321988"}]
        resp = MagicMock()
        resp.json.return_value = rows
        resp.raise_for_status.return_value = None

        with patch(
            "tooluniverse.cpic_search_pairs_tool.requests.get", return_value=resp
        ):
            guideline_id, rxnorm_id = _resolve_drug_to_guideline_id("citalop")

        assert guideline_id == 100413
        assert rxnorm_id == "321988"

    def test_end_to_end_recommendations_use_the_exact_drug(self):
        tool = CPICGetRecommendationsTool({"name": "CPIC_get_recommendations"})

        def fake_get(url, params=None, **kwargs):
            if url.endswith("/drug"):
                return _resp(
                    [
                        {
                            "name": "fosphenytoin",
                            "guidelineid": 100412,
                            "rxnormid": "72236",
                        },
                        {
                            "name": "phenytoin",
                            "guidelineid": 100412,
                            "rxnormid": "8183",
                        },
                    ]
                )
            assert params.get("drugid") == "eq.RxNorm:8183"
            return _resp(
                [{"drugid": "RxNorm:8183", "drug": {"name": "phenytoin"}}]
            )

        with patch(
            "tooluniverse.cpic_search_pairs_tool.requests.get", side_effect=fake_get
        ):
            result = tool.run({"drug": "phenytoin"})

        assert result["data"]["recommendations"][0]["drug"]["name"] == "phenytoin"
