"""Unit tests for ChEBI_get_ontology_parents.

Closes the upward-navigation gap: the existing ChEBI_get_ontology_children
tool only walks ontology CHILDREN (incoming_relations). The parents tool
walks UPWARD via the /ontology/parents/{id}/ endpoint, parsing
outgoing_relations into {relation_type, parent_id, parent_name}.
"""
from unittest.mock import MagicMock, patch

import pytest
import requests

from tooluniverse.chebi_tool import ChEBITool


def _make_parents_tool():
    return ChEBITool(
        {
            "name": "ChEBI_get_ontology_parents",
            "type": "ChEBITool",
            "fields": {"endpoint_type": "ontology_parents"},
            "parameter": {"type": "object", "properties": {}},
        }
    )


# Trimmed slice of the live response for CHEBI:15377 (water). final_name
# includes an <em> tag to exercise HTML stripping.
_WATER_PARENTS = {
    "id": 15377,
    "chebi_accession": "CHEBI:15377",
    "ontology_relations": {
        "outgoing_relations": [
            {
                "init_id": 15377,
                "init_name": "water",
                "relation_type": "is a",
                "final_id": 37176,
                "final_name": "mononuclear parent hydride",
            },
            {
                "init_id": 15377,
                "init_name": "water",
                "relation_type": "has role",
                "final_id": 76971,
                "final_name": "<em>Escherichia coli</em> metabolite",
            },
            {
                "init_id": 15377,
                "init_name": "water",
                "relation_type": "is conjugate acid of",
                "final_id": 16234,
                "final_name": "hydroxide",
            },
        ]
    },
}


@pytest.mark.unit
@patch("tooluniverse.chebi_tool.requests.get")
def test_ontology_parents_parses_outgoing_relations(mock_get):
    resp = MagicMock()
    resp.json.return_value = _WATER_PARENTS
    resp.raise_for_status.return_value = None
    mock_get.return_value = resp

    result = _make_parents_tool().run({"chebi_id": 15377})

    # Correct endpoint hit (upward, not children).
    called_url = mock_get.call_args[0][0]
    assert "/ontology/parents/15377/" in called_url

    assert result["status"] == "success"
    data = result["data"]
    assert data["chebi_id"] == 15377
    assert data["chebi_accession"] == "CHEBI:15377"
    assert data["relation_count"] == 3
    assert result["metadata"]["endpoint"] == "ontology/parents"

    rels = data["relations"]
    # Output uses final_id/final_name -> parent_id/parent_name; no child_* keys.
    assert rels[0] == {
        "relation_type": "is a",
        "parent_id": 37176,
        "parent_name": "mononuclear parent hydride",
    }
    assert "child_id" not in rels[0]
    # HTML highlight markup is stripped from parent_name.
    assert rels[1]["parent_name"] == "Escherichia coli metabolite"
    assert rels[2]["relation_type"] == "is conjugate acid of"


@pytest.mark.unit
@patch("tooluniverse.chebi_tool.requests.get")
def test_ontology_parents_empty_relations(mock_get):
    resp = MagicMock()
    resp.json.return_value = {
        "id": 99999,
        "chebi_accession": "CHEBI:99999",
        "ontology_relations": {"outgoing_relations": []},
    }
    resp.raise_for_status.return_value = None
    mock_get.return_value = resp

    result = _make_parents_tool().run({"chebi_id": 99999})

    assert result["status"] == "success"
    assert result["data"]["relation_count"] == 0
    assert result["data"]["relations"] == []


@pytest.mark.unit
def test_ontology_parents_missing_id():
    result = _make_parents_tool().run({})
    assert result["status"] == "error"
    assert "chebi_id" in result["error"]


@pytest.mark.unit
@patch("tooluniverse.chebi_tool.requests.get")
def test_ontology_parents_http_error(mock_get):
    err = requests.exceptions.HTTPError()
    err.response = MagicMock(status_code=404)
    resp = MagicMock()
    resp.raise_for_status.side_effect = err
    mock_get.return_value = resp

    result = _make_parents_tool().run({"chebi_id": 404})

    assert result["status"] == "error"
    assert "404" in result["error"]
