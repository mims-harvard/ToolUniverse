"""Regression tests for GO API association offset pagination and honest totals."""

import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.go_api_tool import GOAPITool
from tooluniverse.tools.GOAPI_get_gene_functions import GOAPI_get_gene_functions
from tooluniverse.tools.GOAPI_get_genes_by_function import (
    GOAPI_get_genes_by_function,
)


def _tool(endpoint):
    return GOAPITool({"name": f"GOAPI_{endpoint}", "fields": {"endpoint": endpoint}})


def _response(associations):
    response = MagicMock()
    response.json.return_value = {"associations": associations}
    response.raise_for_status.return_value = None
    return response


def _association(index):
    return {
        "subject": {
            "id": f"HGNC:{index}",
            "label": f"GENE{index}",
            "taxon": {"id": "NCBITaxon:9606", "label": "Homo sapiens"},
        },
        "object": {
            "id": f"GO:{index:07d}",
            "label": f"term {index}",
            "category": ["biological_process"],
        },
        "reference": [],
    }


def test_gene_functions_forwards_start_and_uses_one_record_lookahead():
    with patch(
        "tooluniverse.go_api_tool.requests.get",
        return_value=_response([_association(2), _association(3), _association(4)]),
    ) as get:
        result = _tool("gene_functions").run(
            {"gene_id": "HGNC:11998", "rows": 2, "start": 2}
        )

    assert get.call_args.kwargs["params"]["rows"] == 3
    assert get.call_args.kwargs["params"]["start"] == 2
    assert len(result["data"]) == 2
    assert result["metadata"]["total_results"] is None
    assert result["metadata"]["total_results_exact"] is False
    assert result["metadata"]["matching_associations_lower_bound"] == 5
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_start"] == 4


def test_genes_by_function_deduplicates_and_aggregates_association_rows():
    associations = [
        _association(1),
        _association(1),
        _association(2),
        _association(2),
        _association(3),
        _association(4),
    ]
    associations[1]["object"]["id"] = "GO:7654321"
    with patch(
        "tooluniverse.go_api_tool.requests.get",
        return_value=_response(associations),
    ) as get:
        result = _tool("search_annotations").run(
            {"go_id": "GO:0006915", "rows": 2, "offset": 1}
        )

    assert get.call_args.kwargs["params"]["rows"] == 1000
    assert get.call_args.kwargs["params"]["start"] == 0
    assert [gene["gene_id"] for gene in result["data"]] == ["HGNC:2", "HGNC:3"]
    assert result["data"][0]["associations_returned"] == 2
    assert result["data"][0]["associations_complete"] is True
    assert result["metadata"]["total_unique_genes"] == 4
    assert result["metadata"]["total_unique_genes_exact"] is True
    assert result["metadata"]["next_offset"] == 3


def test_unique_gene_scan_budget_failure_is_explicit():
    with patch(
        "tooluniverse.go_api_tool.requests.get",
        return_value=_response([_association(1), _association(1)]),
    ):
        result = _tool("search_annotations").run(
            {
                "go_id": "GO:0006915",
                "rows": 2,
                "offset": 0,
                "max_associations_scanned": 2,
            }
        )

    assert result["metadata"]["scan_limit_reached"] is True
    assert result["metadata"]["has_more_known"] is False
    assert result["metadata"]["page_complete"] is False
    assert result["data"][0]["associations_complete"] is False


def test_short_final_page_reports_exact_total():
    with patch(
        "tooluniverse.go_api_tool.requests.get",
        return_value=_response([_association(4)]),
    ):
        result = _tool("gene_functions").run(
            {"gene_id": "HGNC:11998", "rows": 2, "start": 4}
        )

    assert result["metadata"]["total_results"] == 5
    assert result["metadata"]["total_results_exact"] is True
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_start"] is None


@pytest.mark.parametrize(
    "arguments",
    [
        {"gene_id": "HGNC:11998", "rows": 0},
        {"gene_id": "HGNC:11998", "rows": 1001},
        {"gene_id": "HGNC:11998", "start": -1},
        {"gene_id": "HGNC:11998", "rows": 1.5},
        {"gene_id": "HGNC:11998", "start": True},
    ],
)
def test_invalid_pagination_errors_instead_of_being_changed(arguments):
    with patch("tooluniverse.go_api_tool.requests.get") as get:
        result = _tool("gene_functions").run(arguments)

    assert result["status"] == "error"
    get.assert_not_called()


def test_configs_and_wrappers_expose_start_and_real_rows_limit():
    config_path = (
        Path(__file__).parents[2]
        / "src"
        / "tooluniverse"
        / "data"
        / "go_api_tools.json"
    )
    configs = {item["name"]: item for item in json.loads(config_path.read_text())}

    functions = configs["GOAPI_get_gene_functions"]["parameter"]["properties"]
    assert functions["rows"]["maximum"] == 1000
    assert functions["start"]["minimum"] == 0
    assert "start" in inspect.signature(GOAPI_get_gene_functions).parameters

    genes = configs["GOAPI_get_genes_by_function"]["parameter"]["properties"]
    assert genes["rows"]["maximum"] == 1000
    assert genes["offset"]["minimum"] == 0
    assert "max_associations_scanned" in genes
    signature = inspect.signature(GOAPI_get_genes_by_function).parameters
    assert "offset" in signature
    assert "max_associations_scanned" in signature
