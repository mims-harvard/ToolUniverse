"""Regression guard for Fix-R9E-1: PubMedGuidelinesTool.run() returned
_search_pubmed_guidelines's bare list of results directly on success,
never wrapped in the standard {"status": "success", "data": [...]}
envelope every sibling tool (e.g. PubMed_search_articles) uses. This exact
inconsistency was independently reported by personas across 4 separate
rounds (R5D-2, R7B-1, R7D-2, R9E-1).
"""

from unittest.mock import patch

import pytest

from tooluniverse.unified_guideline_tools import PubMedGuidelinesTool

pytestmark = pytest.mark.unit


def _tool():
    return PubMedGuidelinesTool({"name": "PubMed_Guidelines_Search"})


def test_success_result_is_wrapped_in_standard_envelope():
    tool = _tool()
    with patch.object(
        PubMedGuidelinesTool,
        "_search_pubmed_guidelines",
        return_value=[{"pmid": "123", "title": "A guideline"}],
    ):
        result = tool.run({"query": "sepsis management"})

    assert result == {
        "status": "success",
        "data": [{"pmid": "123", "title": "A guideline"}],
    }


def test_empty_result_is_wrapped_too():
    tool = _tool()
    with patch.object(
        PubMedGuidelinesTool, "_search_pubmed_guidelines", return_value=[]
    ):
        result = tool.run({"query": "an extremely obscure query"})

    assert result == {"status": "success", "data": []}


def test_error_dict_passes_through_unwrapped():
    tool = _tool()
    with patch.object(
        PubMedGuidelinesTool,
        "_search_pubmed_guidelines",
        return_value={"status": "error", "error": "boom"},
    ):
        result = tool.run({"query": "sepsis management"})

    assert result == {"status": "error", "error": "boom"}


def test_missing_query_still_errors_before_search():
    tool = _tool()
    result = tool.run({})

    assert result == {"status": "error", "error": "Query parameter is required"}
