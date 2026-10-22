from unittest.mock import Mock

import pytest

from tooluniverse.biogrid_tool import BioGRIDRESTTool


def _tool(default_limit=2):
    return BioGRIDRESTTool(
        {
            "name": "BioGRID_get_interactions",
            "fields": {"endpoint": "/interactions/", "return_format": "JSON"},
            "parameter": {
                "properties": {"limit": {"default": default_limit}},
                "required": [],
            },
        }
    )


def _record(kind="physical"):
    return {"EXPERIMENTAL_SYSTEM_TYPE": kind}


def test_biogrid_forwards_start_and_uses_lookahead_for_recoverable_pages():
    tool = _tool()
    tool._make_request = Mock(
        side_effect=[
            {"10": _record(), "11": _record(), "12": _record()},
            {"12": _record(), "13": _record()},
        ]
    )

    first = tool.run({"api_key": "test", "limit": 2, "offset": 0})
    second = tool.run({"api_key": "test", "limit": 2, "offset": 2})

    assert list(first["data"]) == ["10", "11"]
    assert list(second["data"]) == ["12", "13"]
    assert first["metadata"]["has_more"] is True
    assert first["metadata"]["next_offset"] == 2
    assert first["metadata"]["upstream_total_lower_bound"] == 3
    assert second["metadata"]["has_more"] is False
    assert second["metadata"]["upstream_total"] == 4
    assert tool._make_request.call_args_list[0].args[1]["start"] == 0
    assert tool._make_request.call_args_list[0].args[1]["max"] == 3
    assert tool._make_request.call_args_list[1].args[1]["start"] == 2


def test_biogrid_filtered_page_advances_by_upstream_records_not_filtered_count():
    tool = _tool()
    tool._make_request = Mock(
        return_value={
            "20": _record("genetic"),
            "21": _record("physical"),
            "22": _record("physical"),
        }
    )

    result = tool.run(
        {"api_key": "test", "interaction_type": "physical", "limit": 2, "offset": 20}
    )

    assert list(result["data"]) == ["21"]
    assert result["metadata"]["interaction_count"] == 1
    assert result["metadata"]["upstream_returned"] == 2
    assert result["metadata"]["next_offset"] == 22


@pytest.mark.parametrize(
    "arguments",
    [
        {"limit": 0},
        {"limit": 10000},
        {"limit": True},
        {"offset": -1},
        {"offset": "2"},
    ],
)
def test_biogrid_rejects_invalid_pagination_before_network(arguments):
    tool = _tool()
    tool._make_request = Mock(side_effect=AssertionError("must not request"))

    result = tool.run({"api_key": "test", **arguments})

    assert result["status"] == "error"
    tool._make_request.assert_not_called()
