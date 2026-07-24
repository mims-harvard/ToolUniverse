"""Regression guard for Fix-R79A-1: CPIC_get_recommendations had no way to
filter by gene/phenotype -- "gene" and "phenotype" are not real parameters
(no additionalProperties: false on this schema, so they were silently
accepted and dropped rather than rejected), confirmed live that
{"drug": "clopidogrel", "gene": "CYP2C19", "phenotype": "Poor Metabolizer"}
returned all 24 rows across every phenotype/population combination for the
guideline, completely unfiltered, with no indication either filter had zero
effect. A caller very naturally guesses these names, since the tool's own
description says it "links genotype/phenotype to prescribing actions" and
every row already carries a `phenotypes` dict keyed by gene symbol.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.cpic_search_pairs_tool import CPICGetRecommendationsTool

pytestmark = pytest.mark.unit

_CLOPIDOGREL_ROWS = [
    {"id": 1, "phenotypes": {"CYP2C19": "Indeterminate"}, "drugrecommendation": "No recommendation"},
    {"id": 2, "phenotypes": {"CYP2C19": "Poor Metabolizer"}, "drugrecommendation": "Avoid clopidogrel"},
    {"id": 3, "phenotypes": {"CYP2C19": "Likely Poor Metabolizer"}, "drugrecommendation": "Avoid clopidogrel (likely)"},
    {"id": 4, "phenotypes": {"CYP2C19": "Normal Metabolizer"}, "drugrecommendation": "Standard dose"},
    {"id": 5, "phenotypes": {"CYP2C19": "Poor Metabolizer"}, "drugrecommendation": "Avoid clopidogrel (alt population)"},
]


def _resp(json_body):
    r = MagicMock()
    r.json.return_value = json_body
    r.raise_for_status.return_value = None
    return r


def _fake_get_for_guideline_id(rows):
    def fake_get(url, params=None, **kwargs):
        return _resp(rows)

    return fake_get


def test_gene_and_phenotype_together_returns_only_exact_matches():
    tool = CPICGetRecommendationsTool({"name": "CPIC_get_recommendations"})

    with patch(
        "tooluniverse.cpic_search_pairs_tool.requests.get",
        side_effect=_fake_get_for_guideline_id(_CLOPIDOGREL_ROWS),
    ):
        result = tool.run(
            {"guideline_id": 100411, "gene": "CYP2C19", "phenotype": "Poor Metabolizer"}
        )

    recs = result["data"]["recommendations"]
    assert result["data"]["count"] == 2
    assert {r["id"] for r in recs} == {2, 5}
    # "Poor Metabolizer" must not also match "Likely Poor Metabolizer" -- a
    # distinct, clinically different CPIC category, not a synonym.
    assert all(r["phenotypes"]["CYP2C19"] == "Poor Metabolizer" for r in recs)


def test_phenotype_alone_matches_any_gene_in_the_row():
    tool = CPICGetRecommendationsTool({"name": "CPIC_get_recommendations"})

    with patch(
        "tooluniverse.cpic_search_pairs_tool.requests.get",
        side_effect=_fake_get_for_guideline_id(_CLOPIDOGREL_ROWS),
    ):
        result = tool.run({"guideline_id": 100411, "phenotype": "poor metabolizer"})

    # case-insensitive match, no gene given
    assert result["data"]["count"] == 2
    assert {r["id"] for r in result["data"]["recommendations"]} == {2, 5}


def test_gene_alone_matches_all_phenotypes_for_that_gene():
    tool = CPICGetRecommendationsTool({"name": "CPIC_get_recommendations"})

    with patch(
        "tooluniverse.cpic_search_pairs_tool.requests.get",
        side_effect=_fake_get_for_guideline_id(_CLOPIDOGREL_ROWS),
    ):
        result = tool.run({"guideline_id": 100411, "gene": "cyp2c19"})

    assert result["data"]["count"] == len(_CLOPIDOGREL_ROWS)


def test_no_match_returns_helpful_note_with_available_phenotypes():
    tool = CPICGetRecommendationsTool({"name": "CPIC_get_recommendations"})

    with patch(
        "tooluniverse.cpic_search_pairs_tool.requests.get",
        side_effect=_fake_get_for_guideline_id(_CLOPIDOGREL_ROWS),
    ):
        result = tool.run(
            {"guideline_id": 100411, "gene": "CYP2C19", "phenotype": "Super Metabolizer"}
        )

    assert result["data"]["count"] == 0
    note = result["data"]["note"]
    assert "Super Metabolizer" in note
    assert "Poor Metabolizer" in note  # a real available value is surfaced
    assert "dosing algorithm" not in note  # must not collide with Fix-R31C-3's note


def test_limit_and_offset_apply_after_filtering_not_before():
    tool = CPICGetRecommendationsTool({"name": "CPIC_get_recommendations"})

    with patch(
        "tooluniverse.cpic_search_pairs_tool.requests.get",
        side_effect=_fake_get_for_guideline_id(_CLOPIDOGREL_ROWS),
    ):
        result = tool.run(
            {"guideline_id": 100411, "phenotype": "Poor Metabolizer", "limit": 1}
        )

    # 2 rows match "Poor Metabolizer"; limit=1 must slice the FILTERED set
    # (giving id 2), not the raw unfiltered 5-row table.
    assert result["data"]["count"] == 1
    assert result["data"]["recommendations"][0]["id"] == 2


def test_no_gene_or_phenotype_given_keeps_original_unfiltered_behavior():
    """Existing callers with no gene/phenotype must see zero behavior
    change: the request goes out with the caller's own limit/offset, no
    client-side filtering happens at all."""
    tool = CPICGetRecommendationsTool({"name": "CPIC_get_recommendations"})
    captured_params = {}

    def fake_get(url, params=None, **kwargs):
        captured_params.update(params or {})
        return _resp(_CLOPIDOGREL_ROWS)

    with patch("tooluniverse.cpic_search_pairs_tool.requests.get", side_effect=fake_get):
        result = tool.run({"guideline_id": 100411, "limit": 10, "offset": 5})

    assert captured_params["limit"] == 10
    assert captured_params["offset"] == 5
    assert result["data"]["count"] == len(_CLOPIDOGREL_ROWS)
    assert "note" not in result["data"]
