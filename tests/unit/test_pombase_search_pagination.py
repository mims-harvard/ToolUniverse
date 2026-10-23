"""Regression tests for complete PomBase gene-summary search pagination."""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.pombase_tool import PomBaseTool


pytestmark = pytest.mark.unit


def _tool():
    return PomBaseTool({"fields": {"endpoint_type": "gene_summary_search"}})


def _response():
    response = MagicMock()
    response.json.return_value = [
        {
            "uniquename": f"SPTEST.{index:02d}",
            "name": f"kin{index}",
            "product": "protein kinase",
        }
        for index in range(12)
    ]
    return response


def test_search_second_page_is_reachable_and_counted():
    with patch("tooluniverse.pombase_tool.requests.get", return_value=_response()):
        result = _tool().run({"query": "kinase", "limit": 5, "offset": 5})

    assert [row["systematic_id"] for row in result["data"]] == [
        f"SPTEST.{index:02d}" for index in range(5, 10)
    ]
    assert result["metadata"]["total_matches"] == 12
    assert result["metadata"]["next_offset"] == 10


def test_search_tail_terminates():
    with patch("tooluniverse.pombase_tool.requests.get", return_value=_response()):
        result = _tool().run({"query": "kinase", "limit": 5, "offset": 10})

    assert len(result["data"]) == 2
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_offset"] is None


@pytest.mark.parametrize(
    "arguments, message",
    [
        ({"limit": 0}, "limit"),
        ({"limit": True}, "limit"),
        ({"offset": -1}, "offset"),
        ({"offset": True}, "offset"),
    ],
)
def test_invalid_search_pagination_is_rejected_before_request(arguments, message):
    with patch("tooluniverse.pombase_tool.requests.get") as get:
        result = _tool().run({"query": "kinase", **arguments})

    assert result["status"] == "error"
    assert message in result["error"]
    get.assert_not_called()
