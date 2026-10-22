import json
from pathlib import Path
from unittest.mock import Mock, patch

from tooluniverse.gene_ontology_tool import GeneOntologyTool


_CONFIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "src/tooluniverse/data/gene_ontology_tools.json"
)


def _config(name):
    configs = json.loads(_CONFIG_PATH.read_text())
    return next(config for config in configs if config["name"] == name)


def _response():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "response": {
            "numFound": 1812,
            "start": 3,
            "docs": [
                {
                    "bioentity": "UniProtKB:P04637",
                    "bioentity_label": "TP53",
                    "taxon": "NCBITaxon:9606",
                    "evidence_type": "IDA",
                },
                {
                    "bioentity": "UniProtKB:P04637",
                    "bioentity_label": "TP53",
                    "taxon": "NCBITaxon:9606",
                    "evidence_type": "IEA",
                },
                {
                    "bioentity": "UniProtKB:Q9H3D4",
                    "bioentity_label": "TP63",
                    "taxon": "NCBITaxon:9606",
                    "evidence_type": "IMP",
                },
            ],
        }
    }
    return response


def test_annotation_tool_honors_rows_start_and_taxon():
    tool = GeneOntologyTool(_config("GO_get_annotations_for_gene"))
    with patch("tooluniverse.gene_ontology_tool.requests.get", return_value=_response()) as get:
        result = tool.run(
            {
                "gene_id": "TP53",
                "taxon": "NCBITaxon:9606",
                "rows": 3,
                "start": 3,
            }
        )

    url = get.call_args.args[0]
    assert 'taxon:"NCBITaxon%3A9606"' in url
    assert "rows=3" in url
    assert "start=3" in url
    assert result["status"] == "success"
    assert len(result["data"]) == 3
    assert result["metadata"]["total_results"] == 1812
    assert result["metadata"]["total_results_is_exact"] is True
    assert result["metadata"]["next_start"] == 6


def test_distinct_gene_results_do_not_claim_annotation_count_as_gene_total():
    tool = GeneOntologyTool(_config("GO_get_genes_for_term"))
    with patch("tooluniverse.gene_ontology_tool.requests.get", return_value=_response()):
        result = tool.run(
            {"id": "GO:0006915", "taxon": "NCBITaxon:9606", "rows": 3, "start": 3}
        )

    assert len(result["data"]) == 2
    assert result["metadata"]["returned"] == 2
    assert result["metadata"]["returned_annotation_rows"] == 3
    assert result["metadata"]["total_annotation_rows"] == 1812
    assert result["metadata"]["total_results"] is None
    assert result["metadata"]["total_results_is_exact"] is False
    assert result["metadata"]["result_unit"] == "distinct_genes"


def test_paginated_zero_hit_is_successful_complete_result():
    empty = _response()
    empty.json.return_value = {"response": {"numFound": 0, "start": 0, "docs": []}}
    tool = GeneOntologyTool(_config("GO_get_annotations_for_gene"))

    with patch("tooluniverse.gene_ontology_tool.requests.get", return_value=empty):
        result = tool.run({"gene_id": "NO_SUCH_SYMBOL", "rows": 5, "start": 0})

    assert result["status"] == "success"
    assert result["data"] == []
    assert result["metadata"]["total_results"] == 0
    assert result["metadata"]["result_set_complete"] is True


def test_invalid_go_pagination_values_fail_before_network():
    tool = GeneOntologyTool(_config("GO_get_annotations_for_gene"))

    with patch("tooluniverse.gene_ontology_tool.requests.get") as get:
        assert tool.run({"gene_id": "TP53", "rows": 0})["status"] == "error"
        assert tool.run({"gene_id": "TP53", "rows": True})["status"] == "error"
        assert tool.run({"gene_id": "TP53", "start": -1})["status"] == "error"
        assert tool.run({"gene_id": "TP53", "start": False})["status"] == "error"
    get.assert_not_called()
