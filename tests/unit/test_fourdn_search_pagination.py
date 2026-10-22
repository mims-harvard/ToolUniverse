"""Regression tests for recoverable 4DN search pagination."""

from unittest.mock import MagicMock, patch

from tooluniverse.fourdn_tool import FourDNTool


def _response(payload, url="https://data.4dnucleome.org/search/"):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    response.url = url
    return response


def _tool():
    return FourDNTool(
        {"name": "FourDN_search_data", "fields": {"operation": "search"}}
    )


@patch("tooluniverse.fourdn_tool.requests.get")
def test_search_forwards_offset_and_returns_continuation(mock_get):
    mock_get.return_value = _response(
        {"total": 9, "@graph": [{"accession": f"4DNFI{i}"} for i in range(3)]}
    )

    data = _tool().run(
        {
            "operation": "search",
            "query": "Hi-C",
            "item_type": "File",
            "limit": 3,
            "offset": 3,
        }
    )["data"]

    assert mock_get.call_args.kwargs["params"]["from"] == 3
    assert data["returned"] == 3
    assert data["offset"] == 3
    assert data["total"] == 9
    assert data["total_is_exact"] is True
    assert data["has_more"] is True
    assert data["next_offset"] == 6


@patch("tooluniverse.fourdn_tool.requests.get")
def test_later_page_10000_sentinel_is_replaced_by_exact_count(mock_get):
    page = _response(
        {"total": 10000, "@graph": [{"accession": f"4DNFI{i}"} for i in range(3)]}
    )
    count = _response({"total": 34178, "@graph": []})
    mock_get.side_effect = [page, count]

    data = _tool().run(
        {"operation": "search", "query": "Hi-C", "limit": 3, "offset": 3}
    )["data"]

    assert mock_get.call_count == 2
    assert mock_get.call_args_list[1].kwargs["params"]["limit"] == 0
    assert mock_get.call_args_list[1].kwargs["params"]["from"] == 0
    assert data["upstream_page_total"] == 10000
    assert data["total"] == 34178
    assert data["total_is_exact"] is True
    assert "warning" not in data


@patch("tooluniverse.fourdn_tool.requests.get")
def test_failed_count_probe_marks_total_as_inexact_without_losing_page(mock_get):
    page = _response({"total": 10000, "@graph": [{"accession": "4DNFIX"}]})
    mock_get.side_effect = [page, RuntimeError("count endpoint unavailable")]

    data = _tool().run({"operation": "search", "limit": 1, "offset": 3})["data"]

    assert data["results"] == [{"accession": "4DNFIX"}]
    assert data["total"] == 10000
    assert data["total_is_exact"] is False
    assert data["has_more"] is True
    assert data["next_offset"] == 4
    assert "lower bound" in data["warning"]
