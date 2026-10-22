import json
from unittest.mock import Mock, patch

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool


def config():
    with open("src/tooluniverse/data/biorxiv_ext_tools.json") as handle:
        return json.load(handle)[0]


def response(cursor=0, count=30, total="360", new_papers="232"):
    result = Mock(status_code=200, text="", headers={"content-type": "application/json"})
    result.json.return_value = {
        "messages": [
            {
                "status": "ok",
                "cursor": str(cursor),
                "count": count,
                "count_new_papers": new_papers,
                "total": total,
            }
        ],
        "collection": [{"doi": f"10.1101/{cursor + i}"} for i in range(count)],
    }
    return result


@patch("tooluniverse.base_rest_tool.request_with_retry")
def test_biorxiv_uses_actual_batch_length_for_next_cursor(request):
    request.return_value = response(cursor=0)
    result = BaseRESTTool(config()).run(
        {"start_date": "2024-01-01", "end_date": "2024-01-03", "cursor": 0}
    )

    metadata = result["metadata"]
    assert result["count"] == 30
    assert metadata["total_results"] == 360
    assert metadata["unique_new_papers"] == 232
    assert metadata["next_cursor"] == 30
    assert metadata["next_cursor"] != 100
    assert metadata["cursor_semantics"] == "zero_based_record_offset_not_page_number"
    assert metadata["has_more"] is True


@patch("tooluniverse.base_rest_tool.request_with_retry")
def test_biorxiv_terminal_batch_clears_cursor(request):
    request.return_value = response(cursor=330, count=30)
    result = BaseRESTTool(config()).run(
        {"start_date": "2024-01-01", "end_date": "2024-01-03", "cursor": 330}
    )

    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_cursor"] is None


@pytest.mark.parametrize(
    "arguments,parameter",
    [
        ({"cursor": -1}, "cursor"),
        ({"cursor": True}, "cursor"),
        ({"start_date": "2024-13-01"}, "start_date"),
        ({"end_date": "not-a-date"}, "end_date"),
        ({"start_date": "2024-02-01", "end_date": "2024-01-01"}, "start_date"),
    ],
)
@patch("tooluniverse.base_rest_tool.request_with_retry")
def test_biorxiv_rejects_invalid_path_values_before_network(request, arguments, parameter):
    valid = {"start_date": "2024-01-01", "end_date": "2024-01-03"}
    result = BaseRESTTool(config()).run({**valid, **arguments})
    assert result["status"] == "error"
    assert result["parameter"] == parameter
    request.assert_not_called()
