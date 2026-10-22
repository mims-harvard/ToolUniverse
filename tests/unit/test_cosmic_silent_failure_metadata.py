import ast
import json
from pathlib import Path
from unittest.mock import patch

import jsonschema
import pytest

from tooluniverse.cosmic_tool import COSMICTool


pytestmark = pytest.mark.unit
_ROOT = Path(__file__).parents[2]


def _config(name):
    configs = json.loads(
        (_ROOT / "src/tooluniverse/data/cosmic_tools.json").read_text()
    )
    return next(config for config in configs if config["name"] == name)


def _payload(total=4044):
    return [
        total,
        ["224188057", "224188057", "25022340"],
        {
            "GeneName": ["BRAF", "BRAF", "BRAF"],
            "MutationCDS": ["c.?", "c.?", "c.*102del"],
            "MutationAA": ["p.?", "p.?", "p.?"],
            "PrimarySite": ["breast", "lung", "large_intestine"],
            "PrimaryHistology": ["carcinoma", "carcinoma", "carcinoma"],
            "MutationGenomePosition": [":-", ":-", "7:140000-140000"],
            "MutationStrand": ["-", "-", "+"],
            "Fathmm": [None, None, "PATHOGENIC"],
        },
        [],
    ]


@pytest.mark.parametrize(
    "name,arguments,expected_filter",
    [
        ("COSMIC_search_mutations", {"terms": "BRAF", "max_results": 1}, None),
        (
            "COSMIC_get_mutations_by_gene",
            {"gene": "BRAF", "max_results": 1},
            "GeneName:BRAF",
        ),
    ],
)
def test_cosmic_uses_full_accessible_window_and_discloses_no_pagination(
    name, arguments, expected_filter
):
    tool = COSMICTool(_config(name))
    with patch("tooluniverse.cosmic_tool.requests.get") as request:
        request.return_value.json.return_value = _payload()
        request.return_value.raise_for_status.return_value = None
        result = tool.run(arguments)

    params = request.call_args.kwargs["params"]
    assert params["maxList"] == 500
    assert "offset" not in params
    assert "count" not in params
    assert params.get("q") == expected_filter
    assert result["status"] == "success"
    assert result["data"]["count"] == 1
    assert result["metadata"] == {
        "source": "COSMIC via NLM Clinical Tables API",
        "query": "BRAF",
        "server_reported_total": 4044,
        "server_total_may_be_capped": False,
        "raw_records_retrieved": 3,
        "accessible_unique_mutations": 2,
        "returned_count": 1,
        "max_results": 1,
        "pagination_supported": False,
        "has_more_in_accessible_window": True,
        "upstream_truncated": True,
        "truncated": True,
        "result_set_complete": False,
        "next_offset": None,
        "warning": (
            "The NLM COSMIC service does not support pagination due to source-data "
            "terms of use. These unique mutations are aggregated only from its first "
            "3 matching source records; refine the query for other records."
        ),
        **({"gene": "BRAF"} if name.endswith("by_gene") else {}),
    }
    jsonschema.validate(result["data"], _config(name)["return_schema"])


def test_cosmic_aggregates_contexts_and_retains_uncertain_variants():
    tool = COSMICTool(_config("COSMIC_search_mutations"))
    with patch("tooluniverse.cosmic_tool.requests.get") as request:
        request.return_value.json.return_value = _payload()
        request.return_value.raise_for_status.return_value = None
        result = tool.run({"terms": "BRAF", "max_results": 2})

    uncertain = result["data"]["results"][0]
    assert uncertain["mutation_cds"] == "c.?"
    assert uncertain["mutation_aa"] == "p.?"
    assert uncertain["cancer_contexts"] == [
        {"primary_site": "breast", "primary_histology": "carcinoma"},
        {"primary_site": "lung", "primary_histology": "carcinoma"},
    ]


def test_cosmic_marks_server_total_cap():
    tool = COSMICTool(_config("COSMIC_search_mutations"))
    with patch("tooluniverse.cosmic_tool.requests.get") as request:
        request.return_value.json.return_value = _payload(total=10_000)
        request.return_value.raise_for_status.return_value = None
        result = tool.run({"terms": "TP53"})

    assert result["metadata"]["server_total_may_be_capped"] is True
    assert "capped at 10,000" in result["metadata"]["warning"]


@pytest.mark.parametrize("max_results", [0, 501, -1, True, "20", 1.5])
def test_cosmic_rejects_invalid_max_results_before_network(max_results):
    tool = COSMICTool(_config("COSMIC_search_mutations"))
    with patch("tooluniverse.cosmic_tool.requests.get") as request:
        result = tool.run({"terms": "BRAF", "max_results": max_results})

    assert result["status"] == "error"
    assert result["parameter"] == "max_results"
    request.assert_not_called()


@pytest.mark.parametrize("genome_build", [36, 39, True, "37", 37.0])
def test_cosmic_rejects_invalid_genome_build_before_network(genome_build):
    tool = COSMICTool(_config("COSMIC_search_mutations"))
    with patch("tooluniverse.cosmic_tool.requests.get") as request:
        result = tool.run({"terms": "BRAF", "genome_build": genome_build})

    assert result["status"] == "error"
    assert result["parameter"] == "genome_build"
    request.assert_not_called()


@pytest.mark.parametrize("gene", ["", "BRAF OR *", "BRAF:TP53", True, 123])
def test_cosmic_rejects_invalid_gene_before_network(gene):
    tool = COSMICTool(_config("COSMIC_get_mutations_by_gene"))
    with patch("tooluniverse.cosmic_tool.requests.get") as request:
        result = tool.run({"gene": gene})

    assert result["status"] == "error"
    assert result["parameter"] == "gene"
    request.assert_not_called()


@pytest.mark.parametrize(
    "name,expected",
    [
        (
            "COSMIC_search_mutations",
            ["operation", "terms", "max_results", "genome_build"],
        ),
        (
            "COSMIC_get_mutations_by_gene",
            ["operation", "gene", "max_results", "genome_build"],
        ),
    ],
)
def test_generated_wrappers_expose_only_canonical_query_parameter(name, expected):
    module = ast.parse((_ROOT / f"src/tooluniverse/tools/{name}.py").read_text())
    function = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )
    # Compare as a set: every argument is keyword-capable, so declaration order
    # is an artifact of the JSON property order, not part of the contract.  The
    # contract is *which* parameters exist -- no deprecated query aliases.
    assert sorted(argument.arg for argument in function.args.args) == sorted(expected)

