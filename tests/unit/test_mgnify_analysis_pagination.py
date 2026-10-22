import ast
import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from tooluniverse.mgnify_expanded_tool import MGnifyExpandedTool


pytestmark = pytest.mark.unit
_ROOT = Path(__file__).parents[2]
_TOOLS = (
    ("MGnify_get_taxonomy", "taxonomy/ssu", "organism_id"),
    ("MGnify_get_go_terms", "go-terms", "go_id"),
    ("MGnify_get_interpro", "interpro-identifiers", "interpro_id"),
    ("MGnify_list_analysis_downloads", "downloads", "file_id"),
)


def _config(name):
    path = _ROOT / "src/tooluniverse/data/mgnify_expanded_tools.json"
    return next(item for item in json.loads(path.read_text()) if item["name"] == name)


def _response(endpoint):
    if endpoint == "taxonomy/ssu":
        data = [
            {
                "id": "Bacteria::Actinobacteria",
                "attributes": {
                    "name": "Actinobacteria",
                    "rank": "phylum",
                    "domain": "Bacteria",
                    "count": 10,
                    "lineage": "Bacteria;Actinobacteria",
                },
            }
        ]
        total, pages = 26, 13
    elif endpoint == "go-terms":
        data = [
            {
                "id": "GO:0006355",
                "attributes": {
                    "accession": "GO:0006355",
                    "description": "regulation of DNA-templated transcription",
                    "count": 101,
                    "lineage": "biological_process",
                },
            }
        ]
        total, pages = 1309, 655
    elif endpoint == "interpro-identifiers":
        data = [
            {
                "id": "IPR036188",
                "attributes": {
                    "accession": "IPR036188",
                    "description": "FAD/NAD(P)-binding domain",
                    "count": 99,
                },
            }
        ]
        total, pages = 5211, 2606
    else:
        data = [
            {
                "id": "ERZ2272727_FASTA_predicted_orf.ffn.gz",
                "attributes": {
                    "alias": "predicted_orf",
                    "description": {"label": "Predicted ORF", "description": "ORFs"},
                    "file-format": {"name": "FASTA", "compression": True},
                    "group-type": "Sequence data",
                },
                "links": {"self": "https://example.test/file"},
            }
        ]
        total, pages = 40, 20

    response = Mock(status_code=200)
    response.json.return_value = {
        "data": data,
        "meta": {"pagination": {"page": 2, "pages": pages, "count": total}},
        "links": {"next": "https://example.test/next?page=3"},
    }
    return response


@pytest.mark.parametrize("name,endpoint,id_field", _TOOLS)
def test_analysis_endpoints_forward_page_and_expose_continuation(
    name, endpoint, id_field
):
    tool = MGnifyExpandedTool(_config(name))
    arguments = {"analysis_id": "MGYA00585482", "page": 2, "page_size": 2}
    if name == "MGnify_get_taxonomy":
        arguments["rna_type"] = "ssu"

    with patch(
        "tooluniverse.mgnify_expanded_tool.requests.get",
        return_value=_response(endpoint),
    ) as get:
        result = tool.run(arguments)

    assert get.call_args.kwargs["params"] == {
        "format": "json",
        "page": 2,
        "page_size": 2,
    }
    assert get.call_args.args[0].endswith(f"/analyses/MGYA00585482/{endpoint}")
    assert result["data"][0][id_field]
    metadata = result["metadata"]
    assert metadata["page"] == 2
    assert metadata["requested_page"] == 2
    assert metadata["page_size"] == 2
    assert metadata["returned_count"] == 1
    assert metadata["has_more"] is True
    assert metadata["next_page"] == 3
    assert metadata["truncated"] is True
    assert metadata["result_set_complete"] is False
    assert metadata["next_url"].endswith("page=3")


@pytest.mark.parametrize("page", [0, -1, True, "2", 1.5])
def test_analysis_pagination_rejects_invalid_page_before_network(page):
    with patch("tooluniverse.mgnify_expanded_tool.requests.get") as get:
        result = MGnifyExpandedTool(_config("MGnify_get_go_terms")).run(
            {"analysis_id": "MGYA00585482", "page": page}
        )

    assert result["status"] == "error"
    assert result["parameter"] == "page"
    get.assert_not_called()


@pytest.mark.parametrize("page_size", [0, 101, -1, True, "25", 1.5])
def test_analysis_pagination_rejects_invalid_page_size_without_clamping(page_size):
    with patch("tooluniverse.mgnify_expanded_tool.requests.get") as get:
        result = MGnifyExpandedTool(_config("MGnify_get_interpro")).run(
            {"analysis_id": "MGYA00585482", "page_size": page_size}
        )

    assert result["status"] == "error"
    assert result["parameter"] == "page_size"
    get.assert_not_called()


def test_taxonomy_rejects_invalid_rna_type_instead_of_silently_using_ssu():
    with patch("tooluniverse.mgnify_expanded_tool.requests.get") as get:
        result = MGnifyExpandedTool(_config("MGnify_get_taxonomy")).run(
            {"analysis_id": "MGYA00585482", "rna_type": "16s"}
        )

    assert result["status"] == "error"
    assert result["parameter"] == "rna_type"
    get.assert_not_called()


@pytest.mark.parametrize(
    "name,expected_defaults",
    [
        ("MGnify_get_taxonomy", ["ssu", 1, 25]),
        ("MGnify_get_go_terms", [1, 25]),
        ("MGnify_get_interpro", [1, 25]),
        ("MGnify_list_analysis_downloads", [1, 100]),
    ],
)
def test_generated_wrappers_expose_page_controls(name, expected_defaults):
    path = _ROOT / f"src/tooluniverse/tools/{name}.py"
    module = ast.parse(path.read_text())
    function = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )
    names = [argument.arg for argument in function.args.args]
    assert "page" in names
    assert "page_size" in names
    assert [ast.literal_eval(value) for value in function.args.defaults] == expected_defaults
