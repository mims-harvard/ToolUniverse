"""Regression tests for UniProt reference search page sizes."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.uniprot_ref_tool import UniProtRefTool


def _response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.headers = {"x-total-results": "900"}
    response.raise_for_status.return_value = None
    return response


@pytest.mark.parametrize(
    ("endpoint", "payload"),
    [
        ("search_diseases", {"results": [{"id": "DI-1", "statistics": {}}]}),
        (
            "search_keywords",
            {
                "results": [
                    {"keyword": {"id": "KW-1", "name": "Test"}, "statistics": {}}
                ]
            },
        ),
        (
            "search_proteomes",
            {"results": [{"id": "UP0001", "taxonomy": {}, "components": []}]},
        ),
    ],
)
def test_all_reference_searches_forward_official_500_max(endpoint, payload):
    tool = UniProtRefTool(
        {"name": f"UniProtRef_{endpoint}", "fields": {"endpoint": endpoint}}
    )
    with patch(
        "tooluniverse.uniprot_ref_tool.requests.get",
        return_value=_response(payload),
    ) as get:
        result = tool.run({"query": "*", "size": 500})

    assert result["status"] == "success"
    assert get.call_args.kwargs["params"]["size"] == 500


@pytest.mark.parametrize(
    "endpoint", ["search_diseases", "search_keywords", "search_proteomes"]
)
@pytest.mark.parametrize("size", [0, 501, -1, True, 1.5, "bad"])
def test_invalid_sizes_error_before_any_request(endpoint, size):
    tool = UniProtRefTool(
        {"name": f"UniProtRef_{endpoint}", "fields": {"endpoint": endpoint}}
    )
    with patch("tooluniverse.uniprot_ref_tool.requests.get") as get:
        result = tool.run({"query": "*", "size": size})

    assert result["status"] == "error"
    assert "1 to 500" in result["error"]
    get.assert_not_called()


def test_all_three_configs_match_official_limit():
    config_path = (
        Path(__file__).parents[2]
        / "src"
        / "tooluniverse"
        / "data"
        / "uniprot_ref_tools.json"
    )
    configs = {item["name"]: item for item in json.loads(config_path.read_text())}

    for name in (
        "UniProtRef_search_diseases",
        "UniProtRef_search_keywords",
        "UniProtRef_search_proteomes",
    ):
        size = configs[name]["parameter"]["properties"]["size"]
        assert size["minimum"] == 1
        assert size["maximum"] == 500
