from unittest.mock import Mock

import pytest

from tooluniverse.core_tool import CoreTool


def _response(ids, total=5, offset=0):
    response = Mock(status_code=200)
    response.json.return_value = {
        "totalHits": total,
        "limit": len(ids),
        "offset": offset,
        "results": [
            {
                "id": value,
                "title": f"paper-{value}",
                "authors": [],
                "language": {"code": "en"},
            }
            for value in ids
        ],
    }
    return response


def test_core_forwards_offset_and_exposes_exact_continuation(monkeypatch):
    request = Mock(
        side_effect=[_response([1, 2], offset=0), _response([3, 4], offset=2)]
    )
    monkeypatch.setattr("tooluniverse.core_tool.request_with_retry", request)
    tool = CoreTool({"name": "CORE_search_papers"})

    first = tool.run({"query": "CRISPR", "limit": 2, "offset": 0})
    second = tool.run({"query": "CRISPR", "limit": 2, "offset": 2})

    assert [paper["title"] for paper in first["data"]] == ["paper-1", "paper-2"]
    assert [paper["title"] for paper in second["data"]] == ["paper-3", "paper-4"]
    assert first["metadata"]["upstream_total_results"] == 5
    assert first["metadata"]["next_offset"] == 2
    assert first["metadata"]["has_more"] is True
    assert request.call_args_list[0].kwargs["params"]["offset"] == 0
    assert request.call_args_list[1].kwargs["params"]["offset"] == 2
    assert "page" not in request.call_args_list[0].kwargs["params"]


def test_core_client_filter_does_not_hide_upstream_continuation(monkeypatch):
    response = _response([1, 2], total=20, offset=0)
    response.json.return_value["results"][0]["publishedDate"] = "2010-01-01"
    response.json.return_value["results"][1]["publishedDate"] = "2011-01-01"
    monkeypatch.setattr(
        "tooluniverse.core_tool.request_with_retry", Mock(return_value=response)
    )

    result = CoreTool({"name": "test"}).run(
        {"query": "CRISPR", "limit": 2, "offset": 0, "year_from": 2020}
    )

    assert result["data"] == []
    assert result["metadata"]["upstream_returned"] == 2
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 2
    assert result["metadata"]["filtered_total_results"] is None
    assert "continue" in result["metadata"]["warning"]


@pytest.mark.parametrize(
    "arguments",
    [
        {"limit": 0},
        {"limit": 101},
        {"limit": "2"},
        {"offset": -1},
        {"offset": True},
        {"limit": 5, "page_size": 4},
    ],
)
def test_core_rejects_invalid_or_conflicting_pagination(arguments):
    result = CoreTool({"name": "test"}).run({"query": "CRISPR", **arguments})

    assert result["status"] == "error"
