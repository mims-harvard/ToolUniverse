import ast
import json
from pathlib import Path
from unittest.mock import patch

import jsonschema
import pytest

from tooluniverse.loinc_tool import LOINCTool


pytestmark = pytest.mark.unit
_ROOT = Path(__file__).parents[2]
_CASES = (
    (
        "LOINC_search_tests",
        [
            "LOINC_NUM",
            "LONG_COMMON_NAME",
            "COMPONENT",
            "SYSTEM",
            "SCALE_TYP",
            "METHOD_TYP",
            "CLASS",
        ],
    ),
    (
        "LOINC_search_forms",
        ["LOINC_NUM", "LONG_COMMON_NAME", "CLASS", "STATUS"],
    ),
)


def _config(name):
    path = _ROOT / "src/tooluniverse/data/loinc_tools.json"
    return next(item for item in json.loads(path.read_text()) if item["name"] == name)


def _payload(fields):
    values = ["" for _ in fields]
    values[fields.index("LOINC_NUM")] = "94872-9"
    values[fields.index("LONG_COMMON_NAME")] = "Cholesterol and triglyceride panel"
    return [207, ["94872-9"], None, [values]]


@pytest.mark.parametrize("name,fields", _CASES)
def test_searches_use_count_offset_and_expose_continuation(name, fields):
    tool = LOINCTool(_config(name))
    arguments = {"terms": "cholesterol", "max_results": 2, "offset": 2}
    with patch.object(tool, "_make_request", return_value=_payload(fields)) as request:
        result = tool.run(arguments)

    endpoint, params = request.call_args.args
    assert endpoint == "loinc_items/v3/search"
    assert params["count"] == 2
    assert params["offset"] == 2
    assert "maxList" not in params
    if name == "LOINC_search_forms":
        assert params["type"] == "form"
        assert params["available"] == "true"
        assert "sf" not in params
    assert result["status"] == "success"
    assert result["data"]["results"][0]["code"] == "94872-9"
    assert result["data"]["count"] == 1
    assert result["metadata"] == {
        "total_results": 207,
        "accessible_results": 207,
        "upstream_truncated": False,
        "returned_count": 1,
        "offset": 2,
        "max_results": 2,
        "has_more": True,
        "next_offset": 3,
        "truncated": True,
        "result_set_complete": False,
        "warning": None,
    }
    jsonschema.validate(result["data"], _config(name)["return_schema"])


def test_form_search_keeps_official_form_even_when_class_is_blank():
    fields = dict(_CASES)["LOINC_search_forms"]
    tool = LOINCTool(_config("LOINC_search_forms"))
    with patch.object(tool, "_make_request", return_value=_payload(fields)):
        result = tool.run({"terms": "PHQ-9"})

    assert result["status"] == "success"
    assert result["data"]["count"] == 1
    assert result["data"]["results"][0]["CLASS"] == ""


@pytest.mark.parametrize("name,_", _CASES)
@pytest.mark.parametrize("max_results", [0, 501, -1, True, "20", 1.5])
def test_searches_reject_invalid_count_before_network(name, _, max_results):
    tool = LOINCTool(_config(name))
    with patch.object(tool, "_make_request") as request:
        result = tool.run({"terms": "cholesterol", "max_results": max_results})

    assert result["status"] == "error"
    assert result["parameter"] == "max_results"
    request.assert_not_called()


@pytest.mark.parametrize("name,_", _CASES)
@pytest.mark.parametrize("offset", [-1, True, "2", 1.5])
def test_searches_reject_invalid_offset_before_network(name, _, offset):
    tool = LOINCTool(_config(name))
    with patch.object(tool, "_make_request") as request:
        result = tool.run({"terms": "cholesterol", "offset": offset})

    assert result["status"] == "error"
    assert result["parameter"] == "offset"
    request.assert_not_called()


def test_search_discloses_nlm_retrieval_window():
    metadata = LOINCTool._pagination_metadata(10000, 2, 7498, 2)

    assert metadata["accessible_results"] == 7500
    assert metadata["upstream_truncated"] is True
    assert metadata["has_more"] is False
    assert metadata["next_offset"] is None
    assert metadata["truncated"] is True
    assert metadata["warning"]


def test_search_rejects_request_past_nlm_window():
    tool = LOINCTool(_config("LOINC_search_tests"))
    with patch.object(tool, "_make_request") as request:
        result = tool.run({"terms": "cholesterol", "offset": 7499, "max_results": 2})

    assert result["status"] == "error"
    assert "7500" in result["error"]
    request.assert_not_called()


@pytest.mark.parametrize(
    "name,expected_defaults",
    [
        ("LOINC_search_tests", [20, 0, True]),
        ("LOINC_search_forms", [20, 0]),
    ],
)
def test_generated_wrappers_expose_offset(name, expected_defaults):
    module = ast.parse((_ROOT / f"src/tooluniverse/tools/{name}.py").read_text())
    function = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )
    names = [argument.arg for argument in function.args.args]
    assert "offset" in names
    assert [
        ast.literal_eval(value) for value in function.args.defaults
    ] == expected_defaults
