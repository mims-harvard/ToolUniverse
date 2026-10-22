from unittest.mock import Mock

import pytest

from tooluniverse.pathwaycommons_tool import PathwayCommonsTool


def _tool():
    return PathwayCommonsTool(
        {
            "name": "PathwayCommons_search",
            "type": "PathwayCommonsTool",
            "fields": {"operation": "search"},
            "parameter": {"type": "object", "properties": {}},
        }
    )


def _response(page, total=250, size=100, returned=100):
    response = Mock(status_code=200)
    response.json.return_value = {
        "numHits": total,
        "maxHitsPerPage": size,
        "pageNo": page,
        "searchHit": [
            {"uri": f"uri:{page}:{i}", "name": f"hit-{page}-{i}"}
            for i in range(returned)
        ],
    }
    return response


@pytest.mark.parametrize("page", [-1, 1.5, True, "1"])
def test_search_rejects_invalid_pages_without_calling_api(page):
    tool = _tool()
    tool.session.get = Mock()

    result = tool.run({"query": "cancer", "page": page})

    assert result["status"] == "error"
    assert "non-negative integer" in result["error"]
    tool.session.get.assert_not_called()


def test_search_exposes_exact_recoverable_page_navigation():
    tool = _tool()
    tool.session.get = Mock()
    tool.session.get.return_value = _response(1)

    result = tool.run({"query": "cancer", "page": 1})

    assert result["status"] == "success"
    assert len(result["data"]) == 100
    assert result["metadata"] == {
        "total_hits": 250,
        "total_hits_is_exact": True,
        "returned": 100,
        "max_hits_per_page": 100,
        "page": 1,
        "total_pages": 3,
        "has_more": True,
        "next_page": 2,
        "pagination_stalled": False,
        "complete": False,
        "query": "cancer",
    }
    assert tool.session.get.call_args.kwargs["params"]["page"] == 1


def test_search_marks_last_page_complete():
    tool = _tool()
    tool.session.get = Mock()
    tool.session.get.return_value = _response(2, returned=50)

    result = tool.run({"query": "cancer", "page": 2})

    assert result["metadata"]["returned"] == 50
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_page"] is None
    assert result["metadata"]["complete"] is True


def test_search_defaults_to_first_page_and_handles_zero_hits():
    tool = _tool()
    tool.session.get = Mock()
    tool.session.get.return_value = _response(0, total=0, returned=0)

    result = tool.run({"query": "impossible"})

    assert result["metadata"]["page"] == 0
    assert result["metadata"]["total_pages"] == 0
    assert result["metadata"]["has_more"] is False
    assert tool.session.get.call_args.kwargs["params"]["page"] == 0


def test_search_does_not_offer_self_advancing_page_when_upstream_stalls():
    tool = _tool()
    tool.session.get = Mock(return_value=_response(1, returned=0))

    result = tool.run({"query": "cancer", "page": 1})

    assert result["metadata"]["pagination_stalled"] is True
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_page"] is None
    assert result["metadata"]["complete"] is False


@pytest.mark.parametrize(
    "payload",
    [
        {"numHits": "250", "maxHitsPerPage": 100, "pageNo": 0},
        {"numHits": 250, "maxHitsPerPage": 0, "pageNo": 0},
        {"numHits": 250, "maxHitsPerPage": 100, "pageNo": "0"},
    ],
)
def test_search_rejects_invalid_upstream_pagination_metadata(payload):
    tool = _tool()
    response = Mock(status_code=200)
    response.json.return_value = {**payload, "searchHit": []}
    tool.session.get = Mock(return_value=response)

    result = tool.run({"query": "cancer"})

    assert result["status"] == "error"
    assert "pagination metadata" in result["error"]
