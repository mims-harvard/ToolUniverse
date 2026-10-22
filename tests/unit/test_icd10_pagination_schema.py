import ast
import json
from pathlib import Path
from unittest.mock import Mock, patch

import jsonschema
import pytest

from tooluniverse.icd_tool import ICD10Tool


pytestmark = pytest.mark.unit
_ROOT = Path(__file__).parents[2]


def _config(name):
    path = _ROOT / "src/tooluniverse/data/icd_tools.json"
    return next(item for item in json.loads(path.read_text()) if item["name"] == name)


def _response(total=481, rows=None):
    rows = rows or [["P70.2", "Neonatal diabetes mellitus"]]
    response = Mock(status_code=200)
    response.json.return_value = [total, [row[0] for row in rows], None, rows]
    return response


def test_search_uses_count_offset_and_exposes_continuation():
    with patch("tooluniverse.icd_tool.requests.get", return_value=_response()) as get:
        result = ICD10Tool(_config("ICD10_search_codes")).run(
            {"query": " diabetes ", "limit": 2, "offset": 2}
        )

    assert get.call_args.kwargs["params"] == {
        "sf": "code,name",
        "df": "code,name",
        "terms": "diabetes",
        "count": 2,
        "offset": 2,
    }
    assert result["status"] == "success"
    assert result["data"] == {
        "total": 481,
        "results": [{"code": "P70.2", "name": "Neonatal diabetes mellitus"}],
    }
    metadata = result["metadata"]
    assert metadata["total_results"] == 481
    assert metadata["returned_count"] == 1
    assert metadata["offset"] == 2
    assert metadata["limit"] == 2
    assert metadata["has_more"] is True
    assert metadata["next_offset"] == 3
    jsonschema.validate(result["data"], _config("ICD10_search_codes")["return_schema"])


@pytest.mark.parametrize("limit", [0, 501, -1, True, "20", 1.5])
def test_search_rejects_invalid_limit_before_network(limit):
    with patch("tooluniverse.icd_tool.requests.get") as get:
        result = ICD10Tool(_config("ICD10_search_codes")).run(
            {"query": "diabetes", "limit": limit}
        )

    assert result["status"] == "error"
    assert result["parameter"] == "limit"
    get.assert_not_called()


@pytest.mark.parametrize("offset", [-1, True, "2", 1.5])
def test_search_rejects_invalid_offset_before_network(offset):
    with patch("tooluniverse.icd_tool.requests.get") as get:
        result = ICD10Tool(_config("ICD10_search_codes")).run(
            {"query": "diabetes", "offset": offset}
        )

    assert result["status"] == "error"
    assert result["parameter"] == "offset"
    get.assert_not_called()


def test_search_rejects_request_beyond_nlm_window():
    with patch("tooluniverse.icd_tool.requests.get") as get:
        result = ICD10Tool(_config("ICD10_search_codes")).run(
            {"query": "diabetes", "offset": 7499, "limit": 2}
        )

    assert result["status"] == "error"
    assert "7500" in result["error"]
    get.assert_not_called()


def test_get_code_info_schema_describes_data_not_outer_envelope():
    with patch(
        "tooluniverse.icd_tool.requests.get",
        return_value=_response(1, [["E11.9", "Type 2 diabetes mellitus"]]),
    ):
        result = ICD10Tool(_config("ICD10_get_code_info")).run({"code": "E11.9"})

    assert result["status"] == "success"
    jsonschema.validate(result["data"], _config("ICD10_get_code_info")["return_schema"])


def test_generated_search_wrapper_exposes_offset():
    path = _ROOT / "src/tooluniverse/tools/ICD10_search_codes.py"
    module = ast.parse(path.read_text())
    function = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == "ICD10_search_codes"
    )
    names = [argument.arg for argument in function.args.args]
    assert names == ["query", "limit", "offset"]
    assert [ast.literal_eval(value) for value in function.args.defaults] == [20, 0]
