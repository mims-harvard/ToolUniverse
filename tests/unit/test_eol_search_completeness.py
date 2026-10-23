from unittest.mock import patch

import pytest

from tooluniverse.eol_tool import EOLTool


pytestmark = pytest.mark.unit


def _tool():
    return EOLTool({"fields": {"endpoint": "search"}})


@pytest.mark.parametrize(
    "arguments,error",
    [
        ({"query": 123}, "non-empty string"),
        ({"query": "lion", "page": 0}, "positive integer"),
        ({"query": "lion", "page": "2"}, "positive integer"),
        ({"query": "lion", "exact": "false"}, "exact must be a boolean"),
    ],
)
def test_invalid_search_controls_are_rejected_before_network(arguments, error):
    with patch("tooluniverse.eol_tool._eol_http_get") as get:
        result = _tool().run(arguments)
    assert result["status"] == "error"
    assert error in result["error"]
    get.assert_not_called()


def test_search_page_exposes_recoverable_pagination():
    payload = {
        "totalResults": 120,
        "startIndex": 51,
        "itemsPerPage": 50,
        "results": [{"id": 2, "title": "Lion"}, {"id": 3, "title": "Tiger"}],
    }
    with patch("tooluniverse.eol_tool._eol_http_get", return_value=payload) as get:
        result = _tool().run({"query": "cat", "page": 2, "exact": False})
    assert "page=2" in get.call_args.args[0]
    metadata = result["metadata"]
    assert metadata["total_results"] == 120
    assert metadata["returned"] == 2
    assert metadata["has_more"] is True
    assert metadata["next_page"] == 3
    assert metadata["result_set_complete"] is False
    assert metadata["requested_page_complete"] is True


def test_empty_page_before_total_is_stalled_not_a_recoverable_next_page():
    payload = {
        "totalResults": 120,
        "startIndex": 51,
        "itemsPerPage": 50,
        "results": [],
    }
    with patch("tooluniverse.eol_tool._eol_http_get", return_value=payload):
        result = _tool().run({"query": "cat", "page": 2})
    metadata = result["metadata"]
    assert metadata["has_more"] is True
    assert metadata["pagination_stalled"] is True
    assert metadata["requested_page_complete"] is False
    assert metadata["next_page"] is None


def test_malformed_pagination_metadata_is_explicit():
    payload = {"totalResults": "36", "results": []}
    with patch("tooluniverse.eol_tool._eol_http_get", return_value=payload):
        result = _tool().run({"query": "Homo sapiens"})
    assert result["status"] == "error"
    assert "pagination metadata" in result["error"]
