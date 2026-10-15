"""Topic searches of the society tools rank by relevance; listings stay newest-first.

NCCN_search_guidelines("melanoma immunotherapy") used to open with a
single-institution outcomes study that merely has NCCN in its title, because
the shared PubMed helper always sorted by date. The NCCN melanoma guidelines
now come first; AHA_ACC_search_guidelines("atrial fibrillation") likewise now
includes the 2023 ACC/AHA AF guideline in its top 5, which date order missed.
"""

from unittest.mock import patch

import pytest

from tooluniverse import clinical_society_tools as C

pytestmark = pytest.mark.unit


def _sorts(tool_cls, operation, arguments):
    tool = tool_cls({"name": "t", "fields": {"operation": operation}})
    with patch.object(C, "_pubmed_search", return_value=[]) as search:
        tool.run(arguments)
    return search.call_args.kwargs["sort"]


@pytest.mark.parametrize(
    "tool_cls, operation",
    [
        (C.NCCNGuidelineTool, "search"),
        (C.AHAACCGuidelineTool, "search"),
        (C.ADAStandardsTool, "search"),
    ],
)
def test_topic_searches_rank_by_relevance(tool_cls, operation):
    assert (
        _sorts(tool_cls, operation, {"query": "melanoma immunotherapy"}) == "relevance"
    )


@pytest.mark.parametrize("operation", ["list_aha", "list_acc"])
def test_organisation_listings_stay_newest_first(operation):
    assert _sorts(C.AHAACCGuidelineTool, operation, {"limit": 5}) == "date"


def test_no_pmids_is_an_empty_list():
    with patch.object(C, "_pubmed_search", return_value=[]):
        assert C._search_and_fetch("anything", limit=5, sort="relevance") == []
