"""Regression tests for InterMine search start/size pagination."""

import json
import ast
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit

SEARCH_TOOLS = [
    ("flymine_tools.json", "FlyMine_search"),
    ("flymine_tools.json", "FlyMine_search_genes"),
    ("mousemine_tools.json", "MouseMine_search"),
    ("mousemine_tools.json", "MouseMine_search_genes"),
    ("mousemine_tools.json", "MouseMine_search_alleles"),
    ("humanmine_tools.json", "HumanMine_search"),
    ("humanmine_tools.json", "HumanMine_search_genes"),
    ("humanmine_tools.json", "HumanMine_search_pathways"),
    ("targetmine_tools.json", "TargetMine_search"),
    ("targetmine_tools.json", "TargetMine_search_genes"),
]


def _config(filename, name):
    path = Path(__file__).parents[2] / "src/tooluniverse/data" / filename
    return next(item for item in json.loads(path.read_text()) if item["name"] == name)


def _response(payload):
    response = Mock(status_code=200, text="")
    response.json.return_value = payload
    return response


@pytest.mark.parametrize("filename,name", SEARCH_TOOLS)
def test_all_intermine_searches_expose_start_and_exact_total(
    monkeypatch, filename, name
):
    requested = {}

    def request(session, method, url, **kwargs):
        requested.update(kwargs["params"])
        return _response({"totalHits": 9, "results": [{"id": 4}, {"id": 5}, {"id": 6}]})

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    result = BaseRESTTool(_config(filename, name)).run(
        {"q": "Notch", "size": 3, "start": 3}
    )
    assert requested["size"] == 3
    assert requested["start"] == 3
    assert result["metadata"]["total_results"] == 9
    assert result["metadata"]["total_results_is_exact"] is True
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_start"] == 6


@pytest.mark.parametrize(
    "arguments, parameter",
    [
        ({"q": "x", "size": 0}, "size"),
        ({"q": "x", "size": 101}, "size"),
        ({"q": "x", "size": True}, "size"),
        ({"q": "x", "start": -1}, "start"),
        ({"q": "x", "start": 1.5}, "start"),
    ],
)
def test_invalid_pagination_is_explicit(arguments, parameter):
    result = BaseRESTTool(_config("flymine_tools.json", "FlyMine_search")).run(
        arguments
    )
    assert result["status"] == "error"
    assert result["parameter"] == parameter


def test_complete_first_page_is_marked_complete(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.base_rest_tool.request_with_retry",
        lambda *args, **kwargs: _response(
            {"totalHits": 2, "results": [{"id": 1}, {"id": 2}]}
        ),
    )
    metadata = BaseRESTTool(_config("flymine_tools.json", "FlyMine_search")).run(
        {"q": "dpp", "size": 10}
    )["metadata"]
    assert metadata["result_set_complete"] is True
    assert metadata["next_start"] is None


@pytest.mark.parametrize("filename,name", SEARCH_TOOLS)
def test_generated_wrapper_and_config_both_expose_start(filename, name):
    config = _config(filename, name)
    assert config["fields"]["pagination"] == "intermine_start"
    assert "start" in config["parameter"]["properties"]
    wrapper = Path(__file__).parents[2] / "src/tooluniverse/tools" / f"{name}.py"
    module = ast.parse(wrapper.read_text())
    function = next(node for node in module.body if isinstance(node, ast.FunctionDef))
    assert "start" in [argument.arg for argument in function.args.args]
