import json
from unittest.mock import MagicMock, patch

import jsonschema
import pytest
import requests

from tooluniverse.humanbase_tool import HumanBaseTool


pytestmark = pytest.mark.unit


def _tool():
    return HumanBaseTool(
        {"name": "humanbase_ppi_analysis", "type": "HumanBaseTool", "parameter": {}}
    )


def _response(payload):
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def _network(edges=None):
    return {
        "genes": [
            {"standard_name": "TP53", "entrez": "7157", "description": "p53"},
            {"standard_name": "BRCA1", "entrez": "672", "description": "BRCA1"},
            {"standard_name": "EGFR", "entrez": "1956", "description": "EGFR"},
        ],
        "edges": edges
        if edges is not None
        else [{"source": 0, "target": 1, "weight": 0.9}],
    }


def test_full_evidence_datasets_are_retained_and_marked_complete():
    tool = _tool()
    datasets = [{"title": f"dataset-{index}"} for index in range(466)]
    with patch.object(tool, "get_entrez_ids", return_value=["7157", "672"]), patch(
        "tooluniverse.humanbase_tool.requests.get",
        side_effect=[
            _response(_network()),
            _response(
                {
                    "datatypes": [{"title": "co-expression", "weight": 0.8}],
                    "datasets": datasets,
                }
            ),
            _response([{"title": "DNA repair"}]),
        ],
    ):
        result = tool.run(
            {
                "gene_list": ["TP53", "BRCA1"],
                "tissue": "brain",
                "max_node": 3,
                "string_mode": False,
            }
        )

    edge = result["data"]["graph"].edges["TP53", "BRCA1"]
    assert result["status"] == "success"
    assert edge["evidence_datasets"] == datasets
    assert edge["evidence_dataset_count"] == 466
    assert edge["evidence_datasets_complete"] is True
    assert result["metadata"]["edge_evidence_completed"] == 1
    assert result["metadata"]["requested_scope_complete"] is True
    assert result["metadata"]["complete"] is True


def test_limit_hit_is_explicit_and_prevents_complete_claim():
    tool = _tool()
    datasets = [{"id": index} for index in range(1000)]
    with patch.object(tool, "get_entrez_ids", return_value=["7157", "672"]), patch(
        "tooluniverse.humanbase_tool.requests.get",
        side_effect=[
            _response(_network()),
            _response({"datatypes": [], "datasets": datasets}),
            _response([]),
        ],
    ):
        result = tool.run(
            {"genes": ["TP53", "BRCA1"], "max_node": 3, "string_mode": False}
        )

    edge = result["data"]["graph"].edges["TP53", "BRCA1"]
    assert edge["evidence_dataset_count"] == 1000
    assert edge["evidence_datasets_complete"] is False
    assert result["metadata"]["edge_evidence_incomplete"] == [
        {"source": "TP53", "target": "BRCA1"}
    ]
    assert result["metadata"]["complete"] is False


def test_one_evidence_failure_does_not_abort_remaining_edges():
    tool = _tool()
    network = _network(
        [
            {"source": 0, "target": 1, "weight": 0.9},
            {"source": 1, "target": 2, "weight": 0.8},
        ]
    )
    with patch.object(
        tool, "get_entrez_ids", return_value=["7157", "672", "1956"]
    ), patch(
        "tooluniverse.humanbase_tool.requests.get",
        side_effect=[
            _response(network),
            requests.ConnectionError("evidence unavailable"),
            _response({"datatypes": [], "datasets": [{"title": "BioGRID"}]}),
            _response([]),
        ],
    ):
        result = tool.run(
            {"gene_list": ["TP53", "BRCA1", "EGFR"], "string_mode": False}
        )

    graph = result["data"]["graph"]
    assert graph.number_of_edges() == 2
    assert graph.edges["TP53", "BRCA1"]["evidence_error"] == "evidence unavailable"
    assert graph.edges["BRCA1", "EGFR"]["evidence_dataset_count"] == 1
    assert result["metadata"]["edge_evidence_completed"] == 1
    assert len(result["metadata"]["edge_evidence_failures"]) == 1
    assert result["metadata"]["complete"] is False


def test_invalid_inputs_fail_before_network_calls():
    tool = _tool()
    with patch("tooluniverse.humanbase_tool.requests.get") as get:
        assert tool.run({})["status"] == "error"
        assert tool.run({"gene_list": []})["status"] == "error"
        assert tool.run({"gene_list": ["TP53"], "max_node": 0})["status"] == "error"
        assert (
            tool.run({"gene_list": ["TP53"], "interaction": "not-real"})["status"]
            == "error"
        )
    get.assert_not_called()


def test_all_seven_datatypes_are_requested_by_default():
    tool = _tool()
    with patch.object(tool, "get_entrez_ids", return_value=["7157"]), patch(
        "tooluniverse.humanbase_tool.requests.get",
        side_effect=[_response({"genes": [], "edges": []}), _response([])],
    ) as get:
        tool.humanbase_ppi_retrieve(["TP53"], "brain", max_node=1)

    network_url = get.call_args_list[0].args[0]
    assert "datatypes=protein-domain" in network_url
    assert "datatypes=sequence-similarity" in network_url


def test_newly_exposed_datatype_filters_are_accepted():
    tool = _tool()
    graph = MagicMock()
    graph.number_of_nodes.return_value = 1
    with patch.object(tool, "humanbase_ppi_retrieve", return_value=(graph, [])) as retrieve:
        result = tool.run(
            {
                "gene_list": ["TP53"],
                "interaction": "protein-domain",
                "string_mode": False,
            }
        )
    assert result["status"] == "success"
    assert retrieve.call_args.args[3] == "protein-domain"


def test_schema_requires_one_gene_alias_and_accepts_both_modes():
    with open("src/tooluniverse/data/humanbase_tools.json") as handle:
        config = json.load(handle)[0]
    schema = config["parameter"]
    jsonschema.validate({"gene_list": ["TP53"]}, schema)
    jsonschema.validate({"genes": ["TP53"]}, schema)
    for invalid in ({}, {"gene_list": []}, {"genes": []}):
        try:
            jsonschema.validate(invalid, schema)
        except jsonschema.ValidationError:
            pass
        else:
            raise AssertionError(f"schema accepted invalid arguments: {invalid}")


def test_generated_wrapper_does_not_mask_top_n_alias():
    from tooluniverse.tools.humanbase_ppi_analysis import humanbase_ppi_analysis

    client = MagicMock()
    client.run_one_function.return_value = {"status": "success"}
    with patch(
        "tooluniverse.tools.humanbase_ppi_analysis.get_shared_client",
        return_value=client,
    ):
        humanbase_ppi_analysis(genes=["TP53"], top_n=7)

    arguments = client.run_one_function.call_args.args[0]["arguments"]
    assert arguments["top_n"] == 7
    assert "max_node" not in arguments


def test_neighbor_count_is_preferred_over_legacy_aliases():
    tool = _tool()
    with patch.object(tool, "humanbase_ppi_retrieve", return_value=(MagicMock(), [])) as retrieve:
        retrieve.return_value[0].number_of_nodes.return_value = 1
        tool.run(
            {
                "gene_list": ["TP53"],
                "neighbor_count": 4,
                "max_node": 6,
                "top_n": 8,
                "string_mode": False,
            }
        )
    assert retrieve.call_args.args[2] == 4
