import json
from pathlib import Path
from unittest.mock import Mock, patch

from tooluniverse.gene_ontology_tool import GeneOntologyTool


_CONFIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "src/tooluniverse/data/gene_ontology_tools.json"
)


def _config():
    configs = json.loads(_CONFIG_PATH.read_text())
    return next(config for config in configs if config["name"] == "GO_search_terms")


def _response():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "response": {
            "numFound": 292,
            "start": 2,
            "docs": [
                {
                    "id": "GO:0097194",
                    "annotation_class_label": "execution phase of apoptosis",
                    "idspace": "GO",
                    "is_obsolete": False,
                },
                {
                    "id": "GO:1900119",
                    "annotation_class_label": "positive regulation of execution phase of apoptosis",
                    "idspace": "GO",
                    "is_obsolete": False,
                },
            ],
        }
    }
    return response


def test_keyword_search_uses_labels_synonyms_go_only_and_non_obsolete_terms():
    endpoint = _config()["fields"]["endpoint"]

    assert "annotation_class_label_searchable" in endpoint
    assert "synonym_searchable" in endpoint
    assert 'idspace:"GO"' in endpoint
    assert "is_obsolete:false" in endpoint
    assert "sort=score desc,id asc" in endpoint
    assert "fl=id,annotation_class_label,description" in endpoint
    assert 'annotation_class_label:"{query}"' not in endpoint


def test_search_honors_rows_start_and_reports_exact_term_total():
    tool = GeneOntologyTool(_config())
    with patch(
        "tooluniverse.gene_ontology_tool.requests.get", return_value=_response()
    ) as get:
        result = tool.run({"query": "apoptosis", "rows": 2, "start": 2})

    url = get.call_args.args[0]
    assert "rows=2" in url
    assert "start=2" in url
    assert 'annotation_class_label_searchable:"apoptosis"' in url
    assert result["status"] == "success"
    assert len(result["data"]) == 2
    assert result["metadata"]["total_results"] == 292
    assert result["metadata"]["total_results_is_exact"] is True
    assert result["metadata"]["result_unit"] == "ontology_terms"
    assert result["metadata"]["next_start"] == 4


def test_search_no_longer_hardcodes_ten_rows():
    config = _config()

    assert "rows=10" not in config["fields"]["endpoint"]
    assert config["parameter"]["properties"]["rows"]["maximum"] == 1000
    assert "start" in config["parameter"]["properties"]
