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
