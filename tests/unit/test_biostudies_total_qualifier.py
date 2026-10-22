"""BioStudies approximate totals must retain their upstream qualifier."""

from unittest.mock import MagicMock

import pytest

from tooluniverse.biostudies_tool import BioStudiesRESTTool

pytestmark = pytest.mark.unit


def _tool(name="biostudies_search"):
    return BioStudiesRESTTool({"name": name, "fields": {}})


def _response(*, hits=10, total=1036, exact=False, page=1, page_size=10):
    response = MagicMock()
    response.headers = {"content-type": "application/json"}
    response.url = "https://example.test/search"
    response.json.return_value = {
        "hits": [{"accession": f"S-TEST-{index}"} for index in range(hits)],
        "totalHits": total,
        "isTotalHitsExact": exact,
        "page": page,
        "pageSize": page_size,
    }
    return response


def test_approximate_total_is_marked_as_lower_bound_with_next_page():
    tool = _tool()
    tool.session.get = MagicMock(return_value=_response())

    result = tool.run({"query": "cancer", "pageSize": 10, "page": 1})

    data = result["data"]
    assert data["totalHits"] == 1036
    assert data["totalHitsExact"] is False
    assert data["totalHitsRelation"] == "lower_bound"
    assert "lower bound" in data["totalHitsWarning"]
    assert data["has_more"] is True
    assert data["next_page"] == 2


def test_exact_short_last_page_is_complete():
    tool = _tool("biostudies_search_by_collection")
    tool.session.get = MagicMock(
        return_value=_response(hits=3, total=13, exact=True, page=2, page_size=10)
    )

    result = tool.run(
        {"query": "x", "collection": "arrayexpress", "pageSize": 10, "page": 2}
    )

    assert result["data"]["totalHitsExact"] is True
    assert result["data"]["has_more"] is False
    assert result["data"]["next_page"] is None


@pytest.mark.parametrize("arguments", [{"pageSize": 0}, {"pageSize": 101}, {"page": 0}])
def test_invalid_pagination_fails_before_network(arguments):
    tool = _tool()
    tool.session.get = MagicMock()

    result = tool.run(arguments)

    assert result["status"] == "error"
    tool.session.get.assert_not_called()
