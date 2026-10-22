"""Regression tests for IGSR's real 500-record Elasticsearch page limit."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tooluniverse.igsr_tool import IGSRTool


def _tool(operation):
    return IGSRTool(
        {
            "name": f"IGSR_{operation}",
            "parameter": {"properties": {"operation": {"default": operation}}},
        }
    )


def _empty_hits(total=0):
    return {"hits": {"total": total, "hits": []}}


@pytest.mark.parametrize(
    "operation",
    ["search_populations", "search_samples", "list_data_collections"],
)
def test_all_operations_forward_official_500_max(operation):
    tool = _tool(operation)
    with patch.object(tool, "_es_search", return_value=_empty_hits()) as search:
        result = tool.run({"operation": operation, "limit": 500, "offset": 0})

    assert result["status"] == "success"
    assert search.call_args.args[1]["size"] == 500


def test_superpopulation_full_fetch_uses_server_max_not_old_300_cap():
    tool = _tool("search_populations")
    with patch.object(tool, "_es_search", return_value=_empty_hits()) as search:
        tool.run(
            {
                "operation": "search_populations",
                "superpopulation": "AFR",
                "limit": 25,
            }
        )

    assert search.call_args.args[1]["size"] == 500


@pytest.mark.parametrize(
    "arguments",
    [
        {"operation": "search_samples", "limit": 0},
        {"operation": "search_samples", "limit": 501},
        {"operation": "search_samples", "offset": -1},
        {"operation": "search_samples", "limit": 1.5},
        {"operation": "search_samples", "offset": True},
    ],
)
def test_invalid_pagination_errors_instead_of_being_changed(arguments):
    tool = _tool("search_samples")
    with patch.object(tool, "_es_search") as search:
        result = tool.run(arguments)

    assert result["status"] == "error"
    search.assert_not_called()


def test_all_configs_match_real_server_limit():
    config_path = (
        Path(__file__).parents[2]
        / "src"
        / "tooluniverse"
        / "data"
        / "igsr_tools.json"
    )
    configs = {item["name"]: item for item in json.loads(config_path.read_text())}

    for name in (
        "IGSR_search_populations",
        "IGSR_search_samples",
        "IGSR_list_data_collections",
    ):
        limit = configs[name]["parameter"]["properties"]["limit"]
        assert limit["minimum"] == 1
        assert limit["maximum"] == 500
