"""SGD_search sent ``query=`` to /backend/get_search_results, which ignores it.

Without the ``q`` parameter the endpoint answers with every one of its ~348k records
(downloads, references, diseases ...) for any text: "GAL4" and "zzzzqq" gave the
same list, and with category=locus "GAL4" returned ARS318 and ARS319. With ``q`` the
GAL4 locus is first and nonsense matches nothing.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.sgd_tool import SGDTool

pytestmark = pytest.mark.unit


def _search(arguments, body=None):
    response = MagicMock()
    response.json.return_value = body or {"total": {"value": 0}, "results": []}
    tool = SGDTool({"name": "SGD_search", "fields": {"endpoint_type": "search"}})
    with patch("tooluniverse.sgd_tool.requests.get", return_value=response) as get:
        result = tool.run(arguments)
    return result, get.call_args.kwargs["params"]


def test_query_text_is_sent_as_q_not_query():
    _, params = _search({"query": "GAL4", "category": "locus", "limit": 5})
    assert params["q"] == "GAL4"
    assert "query" not in params
    assert params["category"] == "locus" and params["limit"] == 5


def test_results_are_returned_from_the_q_search():
    body = {
        "total": {"value": 19},
        "results": [
            {"name": "GAL4 / YPL248C", "category": "locus", "href": "/locus/S000006169"}
        ],
    }
    result, _ = _search({"query": "GAL4", "category": "locus"}, body)
    assert result["status"] == "success"
    assert result["data"][0]["name"] == "GAL4 / YPL248C"
