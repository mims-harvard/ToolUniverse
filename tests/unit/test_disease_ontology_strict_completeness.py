from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.disease_ontology_tool import DiseaseOntologyTool


pytestmark = pytest.mark.unit


def _tool(endpoint="get_term"):
    return DiseaseOntologyTool({"fields": {"endpoint": endpoint}})


def _term(doid="DOID:10283", name="prostate cancer", parents=None):
    return {
        "id": doid,
        "name": name,
        "definition": "definition",
        "parents": parents if parents is not None else [],
        "synonyms": ["prostate carcinoma EXACT []"],
        "xrefs": ["NCI:C4863"],
        "subsets": ["DO_cancer_slim"],
        "alternateIds": ["DOID:514"],
        "skos_broadMatch": ["MONDO:parent"],
        "skos_exactMatch": ["MONDO:exact"],
        "skos_narrowMatch": ["MONDO:child"],
        "neo4jid": "internal",
    }


@pytest.mark.parametrize("value", [None, 1, "", "DOID:abc", "MONDO:1", "DOID:1:2"])
def test_invalid_doid_is_rejected_before_network(value):
    with patch("tooluniverse.disease_ontology_tool.requests.get") as get:
        result = _tool().run({"doid": value})
    assert result["status"] == "error"
    assert "doid" in result["error"]
    get.assert_not_called()


def test_term_preserves_alternate_skos_and_parent_source_fields():
    term = _term(parents=[["is_a", "prostate disease", "DOID:47", "obo"]])
    with patch.object(DiseaseOntologyTool, "_fetch_term", return_value=term):
        result = _tool().run({"doid": "10283"})
    data = result["data"]
    assert data["alternate_ids"] == ["DOID:514"]
    assert data["skos_broad_matches"] == ["MONDO:parent"]
    assert data["skos_exact_matches"] == ["MONDO:exact"]
    assert data["skos_narrow_matches"] == ["MONDO:child"]
    assert data["parents"][0]["source"] == "obo"
    assert result["metadata"]["source_record_complete"] is True
    assert result["metadata"]["omitted_internal_fields"] == ["neo4jid"]


def test_fetch_verifies_returned_id():
    response = MagicMock()
    response.json.return_value = _term(doid="DOID:47")
    with patch(
        "tooluniverse.disease_ontology_tool.requests.get", return_value=response
    ):
        result = _tool().run({"doid": "DOID:10283"})
    assert result["status"] == "error"
    assert "different term" in result["error"]


def test_malformed_parent_relation_is_not_silently_dropped():
    with patch.object(
        DiseaseOntologyTool,
        "_fetch_term",
        return_value=_term(parents=[["is_a", "missing id"]]),
    ):
        result = _tool().run({"doid": "DOID:10283"})
    assert result["status"] == "error"
    assert "malformed parent" in result["error"]


def test_parent_expansion_reports_depth_and_complete_resolution():
    child = _term(parents=[["is_a", "prostate disease", "DOID:47", "obo"]])
    parent = _term(
        doid="DOID:47",
        name="prostate disease",
        parents=[["is_a", "male reproductive system disease", "DOID:48", "obo"]],
    )
    with patch.object(DiseaseOntologyTool, "_fetch_term", side_effect=[child, parent]):
        result = _tool("get_parents").run({"doid": "DOID:10283"})
    record = result["data"]["parents"][0]
    assert record["fetch_complete"] is True
    assert record["relationship"] == "is_a"
    assert record["grandparents"][0]["source"] == "obo"
    assert result["metadata"]["hierarchy_depth_returned"] == 2
    assert result["metadata"]["parent_expansion_complete"] is True
    assert result["metadata"]["full_ancestry_complete"] is False


def test_parent_fetch_failure_is_explicit_in_data_and_metadata():
    child = _term(parents=[["is_a", "prostate disease", "DOID:47", "obo"]])
    with patch.object(
        DiseaseOntologyTool,
        "_fetch_term",
        side_effect=[child, RuntimeError("upstream unavailable")],
    ):
        result = _tool("get_parents").run({"doid": "DOID:10283"})
    record = result["data"]["parents"][0]
    assert record["fetch_complete"] is False
    assert result["metadata"]["parent_expansion_complete"] is False
    assert result["metadata"]["resolved_parent_count"] == 0
    assert result["metadata"]["failed_parent_fetches"][0]["id"] == "DOID:47"
