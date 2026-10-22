"""Regression tests for UniRef search limits and identity semantics."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.uniref_tool import UniRefTool


def _tool():
    return UniRefTool(
        {"name": "UniRef_search_clusters", "fields": {"endpoint": "search_clusters"}}
    )


def _response(payload, headers=None):
    response = MagicMock()
    response.json.return_value = payload
    response.headers = headers or {}
    response.raise_for_status.return_value = None
    return response


def test_official_500_page_size_is_forwarded_without_old_25_cap():
    payload = {
        "results": [
            {"id": f"UniRef90_{index}", "entryType": "UniRef90"}
            for index in range(500)
        ]
    }
    with patch(
        "tooluniverse.uniref_tool.requests.get",
        return_value=_response(payload, {"x-total-results": "1000"}),
    ) as get:
        result = _tool().run(
            {"query": "p53", "cluster_type": "UniRef90", "size": 500}
        )

    assert get.call_args.kwargs["params"]["size"] == 500
    assert get.call_args.kwargs["params"]["query"] == "p53 AND identity:0.9"
    assert len(result["data"]) == 500


@pytest.mark.parametrize("size", [0, 501, -1, True, 1.5, "bad"])
def test_invalid_sizes_error_instead_of_being_silently_clamped(size):
    with patch("tooluniverse.uniref_tool.requests.get") as get:
        result = _tool().run({"query": "p53", "size": size})

    assert result["status"] == "error"
    assert "1 to 500" in result["error"]
    get.assert_not_called()


def test_invalid_cluster_type_errors_instead_of_dropping_identity_filter():
    with patch("tooluniverse.uniref_tool.requests.get") as get:
        result = _tool().run({"query": "p53", "cluster_type": "UniRef95"})

    assert result["status"] == "error"
    assert "cluster_type" in result["error"]
    assert "unfiltered" in result["error"]
    get.assert_not_called()


def test_config_enforces_real_limit_and_cluster_type_enum():
    config_path = (
        Path(__file__).parents[2]
        / "src"
        / "tooluniverse"
        / "data"
        / "uniref_tools.json"
    )
    configs = {item["name"]: item for item in json.loads(config_path.read_text())}
    properties = configs["UniRef_search_clusters"]["parameter"]["properties"]

    assert properties["size"]["minimum"] == 1
    assert properties["size"]["maximum"] == 500
    assert properties["cluster_type"]["enum"] == [
        "UniRef100",
        "UniRef90",
        "UniRef50",
    ]
