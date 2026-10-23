import ast
import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from tooluniverse.mgnify_expanded_tool import MGnifyExpandedTool


pytestmark = pytest.mark.unit
_ROOT = Path(__file__).parents[2]


def _config(name):
    path = _ROOT / "src/tooluniverse/data/mgnify_expanded_tools.json"
    return next(item for item in json.loads(path.read_text()) if item["name"] == name)


def _response(name):
    if name == "MGnify_search_genomes":
        item = {
            "id": "MGYG000515849",
            "attributes": {
                "type": "MAG",
                "taxon-lineage": "Bacteria;Bacteroidota;Bacteroides",
                "completeness": 95.0,
                "contamination": 1.0,
                "length": 2000000,
                "num-proteins": 1800,
                "gc-content": 42.0,
            },
        }
        total, pages = 136, 68
    elif name == "MGnify_list_biomes":
        item = {
            "id": "root:Engineered:Bioreactor",
            "attributes": {"biome-name": "Bioreactor", "samples-count": 400},
        }
        total, pages = 491, 246
    else:
        item = {
            "id": "ERS490597",
            "attributes": {
                "biosample": "SAMEA000001",
                "sample-name": "sample",
                "geo-loc-name": "Atlantic Ocean",
            },
        }
        total, pages = 136, 68

    response = Mock(status_code=200)
    response.json.return_value = {
        "data": [item],
        "meta": {"pagination": {"page": 2, "pages": pages, "count": total}},
        "links": {"next": "https://example.test?page=3"},
    }
    return response


@pytest.mark.parametrize(
    "name,arguments,expected_filter,id_field,expected_id",
    [
        (
            "MGnify_search_genomes",
            {"taxonomy": "Bacteroides", "page": 2, "page_size": 2},
            ("taxon_lineage", "Bacteroides"),
            "genome_id",
            "MGYG000515849",
        ),
        (
            "MGnify_list_biomes",
            {"page": 2, "page_size": 2},
            None,
            "biome_id",
            "root:Engineered:Bioreactor",
        ),
        (
            "MGnify_get_samples",
            {"study_accession": "MGYS00002008", "page": 2, "page_size": 2},
            ("study_accession", "MGYS00002008"),
            "sample_accession",
            "ERS490597",
        ),
    ],
)
def test_collection_pages_forward_controls_and_expose_continuation(
    name, arguments, expected_filter, id_field, expected_id
):
    with patch(
        "tooluniverse.mgnify_expanded_tool.requests.get",
        return_value=_response(name),
    ) as get:
        result = MGnifyExpandedTool(_config(name)).run(arguments)

    params = get.call_args.kwargs["params"]
    assert params["page"] == 2
    assert params["page_size"] == 2
    if expected_filter:
        assert params[expected_filter[0]] == expected_filter[1]
    assert result["data"][0][id_field] == expected_id
    metadata = result["metadata"]
    assert metadata["page"] == 2
    assert metadata["requested_page"] == 2
    assert metadata["returned_count"] == 1
    assert metadata["has_more"] is True
    assert metadata["next_page"] == 3
    assert metadata["next_url"].endswith("page=3")


@pytest.mark.parametrize(
    "name", ["MGnify_search_genomes", "MGnify_list_biomes", "MGnify_get_samples"]
)
@pytest.mark.parametrize("page_size", [0, 101, True, "25"])
def test_collection_pages_reject_invalid_page_size_before_network(name, page_size):
    arguments = {"page_size": page_size}
    if name == "MGnify_get_samples":
        arguments["study_accession"] = "MGYS00002008"
    with patch("tooluniverse.mgnify_expanded_tool.requests.get") as get:
        result = MGnifyExpandedTool(_config(name)).run(arguments)

    assert result["status"] == "error"
    assert result["parameter"] == "page_size"
    get.assert_not_called()


@pytest.mark.parametrize(
    "name,expected_defaults",
    [
        ("MGnify_search_genomes", [None, 1, 25]),
        ("MGnify_list_biomes", [None, None, 1, 25]),  # depth, lineage, page, page_size
        ("MGnify_get_samples", [None, None, None, 1, 25]),
    ],
)
def test_generated_collection_wrappers_have_explicit_defaults(name, expected_defaults):
    module = ast.parse((_ROOT / f"src/tooluniverse/tools/{name}.py").read_text())
    function = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )
    names = [argument.arg for argument in function.args.args]
    assert "page" in names and "page_size" in names
    assert [
        ast.literal_eval(value) for value in function.args.defaults
    ] == expected_defaults
    if name == "MGnify_search_genomes":
        assert "genome_type" not in names
