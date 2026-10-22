import ast
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.disprot_tool import DisProtTool


pytestmark = pytest.mark.unit
_ROOT = Path(__file__).parents[2]


def _config(name):
    configs = json.loads(
        (_ROOT / "src/tooluniverse/data/disprot_tools.json").read_text()
    )
    return next(config for config in configs if config["name"] == name)


def _response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


@pytest.mark.parametrize("page_size", [0, 501, -1, True, "20", 1.5])
def test_search_rejects_invalid_page_size_before_network(page_size):
    tool = DisProtTool(_config("DisProt_search"))
    with patch("tooluniverse.disprot_tool.requests.get") as request:
        result = tool.run({"query": "TP53", "page_size": page_size})

    assert result["status"] == "error"
    assert result["parameter"] == "page_size"
    request.assert_not_called()


@pytest.mark.parametrize("page", [-1, True, "1", 1.5])
def test_search_rejects_invalid_page_before_network(page):
    tool = DisProtTool(_config("DisProt_search"))
    with patch("tooluniverse.disprot_tool.requests.get") as request:
        result = tool.run({"query": "TP53", "page": page})

    assert result["status"] == "error"
    assert result["parameter"] == "page"
    request.assert_not_called()


def test_search_accepts_documented_large_page_and_reports_exact_continuation():
    tool = DisProtTool(_config("DisProt_search"))
    payload = {"size": 120, "data": [{"disprot_id": "DP001", "genes": []}]}
    with patch(
        "tooluniverse.disprot_tool.requests.get", return_value=_response(payload)
    ) as request:
        result = tool.run({"query": "protein", "page_size": 50, "page": 1})

    assert request.call_args.kwargs["params"]["page_size"] == 50
    assert request.call_args.kwargs["params"]["page"] == 1
    assert result["metadata"]["page_start"] == 50
    assert result["metadata"]["next_page"] == 2
    assert result["metadata"]["result_set_complete"] is False


@pytest.mark.parametrize(
    "parameter,value",
    [
        ("region_offset", -1),
        ("region_offset", True),
        ("region_offset", "1"),
        ("region_limit", 0),
        ("region_limit", 501),
        ("region_limit", True),
        ("region_limit", "30"),
    ],
)
def test_entry_rejects_invalid_region_controls_before_network(parameter, value):
    tool = DisProtTool(_config("DisProt_get_entry"))
    with patch("tooluniverse.disprot_tool.requests.get") as request:
        result = tool.run({"accession": "P04637", parameter: value})

    assert result["status"] == "error"
    assert result["parameter"] == parameter
    request.assert_not_called()


@pytest.mark.parametrize(
    "name,expected_defaults",
    [
        ("DisProt_search", [10, 0]),
        ("DisProt_get_entry", [0, 30]),
    ],
)
def test_generated_wrappers_publish_pagination_defaults(name, expected_defaults):
    module = ast.parse((_ROOT / f"src/tooluniverse/tools/{name}.py").read_text())
    function = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )
    assert [ast.literal_eval(default) for default in function.args.defaults] == (
        expected_defaults
    )

