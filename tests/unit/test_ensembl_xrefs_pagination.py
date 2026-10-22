import ast
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import jsonschema
import pytest

from tooluniverse.ensembl_xrefs_tool import EnsemblXrefsTool


pytestmark = pytest.mark.unit
_ROOT = Path(__file__).parents[2]


def _config(name):
    configs = json.loads(
        (_ROOT / "src/tooluniverse/data/ensembl_xrefs_tools.json").read_text()
    )
    return next(config for config in configs if config["name"] == name)


def _response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def test_xrefs_by_id_exposes_later_records_and_page_specific_summary():
    tool = EnsemblXrefsTool(_config("Ensembl_get_cross_references"))
    payload = [
        {
            "dbname": "HGNC" if index < 2 else "EntrezGene",
            "db_display_name": "HGNC" if index < 2 else "NCBI gene",
            "primary_id": str(index),
            "display_id": f"ID{index}",
            "description": None,
            "info_type": "DIRECT",
            "synonyms": [],
        }
        for index in range(5)
    ]
    with patch(
        "tooluniverse.ensembl_xrefs_tool.requests.get",
        return_value=_response(payload),
    ):
        first = tool.run({"ensembl_id": "ENSG1", "limit": 2, "offset": 0})
        second = tool.run({"ensembl_id": "ENSG1", "limit": 2, "offset": 2})

    assert [x["primary_id"] for x in first["data"]["xrefs"]] == ["0", "1"]
    assert [x["primary_id"] for x in second["data"]["xrefs"]] == ["2", "3"]
    assert first["data"]["database_summary"] == {"HGNC": 2, "EntrezGene": 3}
    assert first["data"]["page_database_summary"] == {"HGNC": 2}
    assert second["data"]["page_database_summary"] == {"EntrezGene": 2}
    assert first["metadata"]["next_offset"] == 2
    assert second["metadata"]["next_offset"] == 4
    jsonschema.validate(
        first["data"], _config("Ensembl_get_cross_references")["return_schema"]
    )


def test_xrefs_by_symbol_exposes_later_ids():
    tool = EnsemblXrefsTool(_config("Ensembl_lookup_gene_by_symbol"))
    payload = [{"id": f"ENSG{index}", "type": "gene"} for index in range(5)]
    with patch(
        "tooluniverse.ensembl_xrefs_tool.requests.get",
        return_value=_response(payload),
    ):
        first = tool.run({"symbol": "TP53", "limit": 2, "offset": 0})
        second = tool.run({"symbol": "TP53", "limit": 2, "offset": 2})

    assert [x["id"] for x in first["data"]["ensembl_ids"]] == ["ENSG0", "ENSG1"]
    assert [x["id"] for x in second["data"]["ensembl_ids"]] == ["ENSG2", "ENSG3"]
    assert first["metadata"]["next_offset"] == 2
    assert second["metadata"]["next_offset"] == 4
    jsonschema.validate(
        first["data"], _config("Ensembl_lookup_gene_by_symbol")["return_schema"]
    )


@pytest.mark.parametrize(
    "endpoint,name,required",
    [
        ("xrefs_by_id", "Ensembl_get_cross_references", {"ensembl_id": "ENSG1"}),
        ("xrefs_by_symbol", "Ensembl_lookup_gene_by_symbol", {"symbol": "TP53"}),
    ],
)
@pytest.mark.parametrize(
    "parameter,value",
    [
        ("limit", 0),
        ("limit", 5001),
        ("limit", True),
        ("limit", "50"),
        ("offset", -1),
        ("offset", True),
        ("offset", "2"),
    ],
)
def test_xref_operations_reject_invalid_pagination_before_network(
    endpoint, name, required, parameter, value
):
    tool = EnsemblXrefsTool(_config(name))
    with patch("tooluniverse.ensembl_xrefs_tool.requests.get") as request:
        result = tool.run({**required, parameter: value})

    assert result["status"] == "error"
    assert result["parameter"] == parameter
    request.assert_not_called()


@pytest.mark.parametrize(
    "name,expected_defaults",
    [
        ("Ensembl_get_cross_references", [None, 500, 0]),
        ("Ensembl_lookup_gene_by_symbol", ["human", None, 50, 0]),
    ],
)
def test_generated_wrappers_publish_xref_pagination_defaults(name, expected_defaults):
    module = ast.parse((_ROOT / f"src/tooluniverse/tools/{name}.py").read_text())
    function = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )
    assert [ast.literal_eval(default) for default in function.args.defaults] == (
        expected_defaults
    )
