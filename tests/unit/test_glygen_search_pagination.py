import ast
import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from tooluniverse.glygen_tool import GlyGenTool


pytestmark = pytest.mark.unit
_ROOT = Path(__file__).parents[2]
_CASES = (
    (
        "GlyGen_search_glycans",
        {"mass_min": 1000, "mass_max": 2000, "limit": 2, "offset": 3},
        "glycan/list/",
        "glytoucan_ac",
        "G02815KT",
    ),
    (
        "GlyGen_search_glycoproteins",
        {"organism_id": 9606, "limit": 2, "offset": 3},
        "protein/list/",
        "uniprot_canonical_ac",
        "P62987-1",
    ),
)


def _config(name):
    path = _ROOT / "src/tooluniverse/data/glygen_tools.json"
    return next(item for item in json.loads(path.read_text()) if item["name"] == name)


def _response(payload):
    response = Mock(status_code=200)
    response.json.return_value = payload
    return response


def _responses(name):
    search = _response({"list_id": "live-list-id", "result_count": 100})
    if name == "GlyGen_search_glycans":
        item = {
            "glytoucan_ac": "G02815KT",
            "mass": 1234.5,
            "number_proteins": 2,
            "number_enzymes": 1,
            "number_species": 3,
            "hit_score": 1.0,
        }
    else:
        item = {
            "uniprot_canonical_ac": "P62987-1",
            "protein_name": "protein",
            "gene_name": "GENE",
            "organism": {"id": 9606, "name": "Homo sapiens"},
            "total_n_glycosites": None,
            "total_o_glycosites": 2,
            "hit_score": 1.0,
        }
    listing = _response(
        {
            "results": [item],
            "pagination": {
                "offset": 3,
                "limit": 2,
                "total_length": 100,
                "sort": "hit_score",
                "order": "desc",
            },
        }
    )
    return search, listing


@pytest.mark.parametrize("name,arguments,list_path,id_field,expected_id", _CASES)
def test_searches_forward_offset_and_expose_exact_continuation(
    name, arguments, list_path, id_field, expected_id
):
    with patch(
        "tooluniverse.glygen_tool.requests.post",
        side_effect=_responses(name),
    ) as post:
        result = GlyGenTool(_config(name)).run(arguments)

    assert post.call_count == 2
    assert post.call_args_list[1].args[0].endswith(list_path)
    assert post.call_args_list[1].kwargs["json"] == {
        "id": "live-list-id",
        "offset": 3,
        "limit": 2,
        "sort": "hit_score",
        "order": "desc",
    }
    assert result["data"][0][id_field] == expected_id
    metadata = result["metadata"]
    assert metadata["total_results"] == 100
    assert metadata["returned_count"] == 1
    assert metadata["offset"] == 3
    assert metadata["requested_offset"] == 3
    assert metadata["limit"] == 2
    assert metadata["has_more"] is True
    assert metadata["next_offset"] == 4
    assert metadata["truncated"] is True
    assert metadata["result_set_complete"] is False


@pytest.mark.parametrize("name,arguments,list_path,id_field,expected_id", _CASES)
@pytest.mark.parametrize("limit", [0, 51, -1, True, "20", 1.5])
def test_searches_reject_invalid_limit_before_network(
    name, arguments, list_path, id_field, expected_id, limit
):
    arguments = {**arguments, "limit": limit}
    with patch("tooluniverse.glygen_tool.requests.post") as post:
        result = GlyGenTool(_config(name)).run(arguments)

    assert result["status"] == "error"
    assert result["parameter"] == "limit"
    post.assert_not_called()


@pytest.mark.parametrize("name,arguments,list_path,id_field,expected_id", _CASES)
@pytest.mark.parametrize("offset", [0, -1, True, "3", 1.5])
def test_searches_reject_invalid_offset_before_network(
    name, arguments, list_path, id_field, expected_id, offset
):
    arguments = {**arguments, "offset": offset}
    with patch("tooluniverse.glygen_tool.requests.post") as post:
        result = GlyGenTool(_config(name)).run(arguments)

    assert result["status"] == "error"
    assert result["parameter"] == "offset"
    post.assert_not_called()


@pytest.mark.parametrize("name,arguments,list_path,id_field,expected_id", _CASES)
def test_empty_search_is_still_an_explicit_success(
    name, arguments, list_path, id_field, expected_id
):
    with patch(
        "tooluniverse.glygen_tool.requests.post",
        return_value=_response({"result_count": 0}),
    ) as post:
        result = GlyGenTool(_config(name)).run(arguments)

    assert post.call_count == 1
    assert result["status"] == "success"
    assert result["data"] == []
    assert result["metadata"]["total_results"] == 0
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_offset"] is None


@pytest.mark.parametrize(
    "name,expected_defaults",
    [
        ("GlyGen_search_glycans", [None, None, None, None, None, 20, 1]),
        (
            "GlyGen_search_glycoproteins",
            [None, None, None, None, None, 20, 1],
        ),
    ],
)
def test_generated_wrappers_have_explicit_pagination_defaults(name, expected_defaults):
    module = ast.parse((_ROOT / f"src/tooluniverse/tools/{name}.py").read_text())
    function = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )
    assert [ast.literal_eval(value) for value in function.args.defaults] == expected_defaults
