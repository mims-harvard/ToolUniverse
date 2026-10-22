import ast
import json
from pathlib import Path
from unittest.mock import Mock, patch

import jsonschema
import pytest

from tooluniverse.nci_thesaurus_tool import NCIThesaurusTool


pytestmark = pytest.mark.unit


def _config():
    path = Path(__file__).parents[2] / "src/tooluniverse/data/nci_thesaurus_tools.json"
    return next(
        item
        for item in json.loads(path.read_text())
        if item["name"] == "NCIThesaurus_search"
    )


def _response():
    response = Mock(status_code=200)
    response.json.return_value = {
        "total": 6,
        "parameters": {
            "term": "breast",
            "type": "contains",
            "fromRecord": 2,
            "pageSize": 2,
        },
        "concepts": [
            {
                "code": "C25596",
                "name": "Breast Feeding",
                "terminology": "ncit",
                "leaf": True,
            },
            {
                "code": "C116438",
                "name": "Breast Irradiation",
                "terminology": "ncit",
                "leaf": False,
            },
        ],
    }
    return response


def test_search_forwards_official_from_record_and_match_type():
    tool = NCIThesaurusTool(_config())
    with patch("tooluniverse.nci_thesaurus_tool.requests.get", return_value=_response()) as get:
        result = tool.run(
            {
                "term": " breast ",
                "page_size": 2,
                "offset": 2,
                "match_type": "contains",
            }
        )

    assert get.call_args.kwargs["params"] == {
        "term": "breast",
        "type": "contains",
        "include": "minimal",
        "fromRecord": 2,
        "pageSize": 2,
    }
    assert result["metadata"] == {
        "source": "NCI Thesaurus (NCIt)",
        "total_results": 6,
        "returned_count": 2,
        "query": "breast",
        "match_type": "contains",
        "offset": 2,
        "page_size": 2,
        "has_more": True,
        "next_offset": 4,
        "truncated": True,
        "result_set_complete": False,
    }
    jsonschema.validate(result["data"], _config()["return_schema"])


def test_search_defaults_are_explicit_and_backward_compatible():
    response = _response()
    response.json.return_value["total"] = 2
    with patch("tooluniverse.nci_thesaurus_tool.requests.get", return_value=response) as get:
        result = NCIThesaurusTool(_config()).run({"term": "cancer"})

    params = get.call_args.kwargs["params"]
    assert params["type"] == "match"
    assert params["fromRecord"] == 0
    assert params["pageSize"] == 10
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_offset"] is None


@pytest.mark.parametrize("page_size", [0, 101, -1, True, "10", 1.5])
def test_search_rejects_invalid_page_size_without_silent_clamping(page_size):
    with patch("tooluniverse.nci_thesaurus_tool.requests.get") as get:
        result = NCIThesaurusTool(_config()).run(
            {"term": "breast", "page_size": page_size}
        )

    assert result["status"] == "error"
    assert result["parameter"] == "page_size"
    get.assert_not_called()


@pytest.mark.parametrize("offset", [-1, True, "2", 1.5])
def test_search_rejects_invalid_offset_before_network(offset):
    with patch("tooluniverse.nci_thesaurus_tool.requests.get") as get:
        result = NCIThesaurusTool(_config()).run({"term": "breast", "offset": offset})

    assert result["status"] == "error"
    assert result["parameter"] == "offset"
    get.assert_not_called()


def test_search_rejects_unknown_match_type_before_network():
    with patch("tooluniverse.nci_thesaurus_tool.requests.get") as get:
        result = NCIThesaurusTool(_config()).run(
            {"term": "breast", "match_type": "substring"}
        )

    assert result["status"] == "error"
    assert result["parameter"] == "match_type"
    get.assert_not_called()


def test_generated_wrapper_exposes_all_search_controls():
    path = (
        Path(__file__).parents[2]
        / "src/tooluniverse/tools/NCIThesaurus_search.py"
    )
    module = ast.parse(path.read_text())
    function = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == "NCIThesaurus_search"
    )
    names = [argument.arg for argument in function.args.args]
    assert names == ["term", "page_size", "offset", "match_type"]
    assert [ast.literal_eval(value) for value in function.args.defaults] == [
        10,
        0,
        "match",
    ]
