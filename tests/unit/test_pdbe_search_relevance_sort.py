"""PDBeSearch_search_structures ranks by relevance, not by resolution.

Sorting every match by resolution put the best-resolved structure that merely
mentions the query first: "insulin" returned human heart fatty-acid-binding
proteins (0 of the top 10 titles contained "insulin"; 10 of 10 with relevance
ordering, verified live), and TP53 / ubiquitin behaved the same way.
sort_by="resolution" keeps the old ordering. HTTP is mocked.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.pdbe_search_tool import PDBeSearchTool

pytestmark = pytest.mark.unit


def _tool():
    return PDBeSearchTool(
        {
            "name": "PDBeSearch_search_structures",
            "fields": {"endpoint_type": "search_structures"},
        }
    )


def _response():
    resp = Mock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "response": {
            "numFound": 1,
            "docs": [{"pdb_id": "7ins", "title": "STRUCTURE OF PORCINE INSULIN"}],
        }
    }
    return resp


def _sent_sort(arguments):
    with patch(
        "tooluniverse.pdbe_search_tool.requests.get", return_value=_response()
    ) as get:
        result = _tool().run(arguments)
    assert result["status"] == "success"
    return get.call_args.kwargs["params"]["sort"]


def test_default_ordering_is_relevance_with_resolution_as_tiebreaker():
    assert _sent_sort({"query": "insulin"}) == "score desc,resolution asc"


def test_relevance_can_be_requested_explicitly():
    assert _sent_sort({"query": "insulin", "sort_by": "relevance"}) == (
        "score desc,resolution asc"
    )


def test_resolution_ordering_is_still_available():
    assert _sent_sort({"query": "insulin", "sort_by": "resolution"}) == (
        "resolution asc"
    )
