"""Round 228: NPAtlas full-record claims must preserve every official field."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from jsonschema import validate

from tooluniverse.npatlas_tool import NPAtlasCompoundTool

pytestmark = pytest.mark.unit

CONFIG_PATH = (
    Path(__file__).parents[2] / "src" / "tooluniverse" / "data" / "npatlas_tools.json"
)


def _config():
    configs = json.loads(CONFIG_PATH.read_text())
    return next(c for c in configs if c["name"] == "NPAtlas_get_compound")


def _response(payload, status=200):
    response = MagicMock(status_code=status)
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def _source_record(npaid="NPA000001"):
    return {
        "id": 1,
        "node_id": 2,
        "cluster_id": 3,
        "npaid": npaid,
        "original_name": "Curvularide C",
        "mol_formula": "C19H37NO5",
        "mol_weight": 359.5,
        "exact_mass": 359.267,
        "m_plus_h": 360.274,
        "m_plus_na": 382.256,
        "inchikey": "BZL",
        "inchi": "InChI=1S",
        "smiles": "CC",
        "origin_organism": {"taxon": "Curvularia sp."},
        "origin_reference": {"title": "Paper", "doi": "10.x"},
        "synonyms": ["synonym"],
        "external_ids": [],
        "mol_structures": [{"type": "2d"}],
        "exclusions": [{"reason": "test"}],
        "has_exclusions": True,
        "reassignments": [{"name": "old"}],
        "syntheses": [{"doi": "10.synthesis"}],
    }


def test_full_source_record_is_lossless_alongside_normalized_projection():
    """Fields omitted by the legacy projection must remain available verbatim."""
    source = _source_record()
    with patch(
        "tooluniverse.npatlas_tool.requests.get", return_value=_response(source)
    ):
        result = NPAtlasCompoundTool(_config()).run({"npaid": "npa000001"})

    assert result["status"] == "success"
    assert result["data"]["source_record"] == source
    assert result["data"]["name"] == "Curvularide C"
    assert result["metadata"]["source_record_complete"] is True
    assert result["metadata"]["source_field_count"] == len(source)
    assert result["metadata"]["source_fields"] == sorted(source)
    validate(result["data"], _config()["return_schema"])


def test_wrong_compound_identity_is_rejected():
    """A valid record for another NPAID cannot satisfy the requested lookup."""
    with patch(
        "tooluniverse.npatlas_tool.requests.get",
        return_value=_response(_source_record("NPA000002")),
    ):
        result = NPAtlasCompoundTool(_config()).run({"npaid": "NPA000001"})
    assert result["status"] == "error"
    assert "identity mismatch" in result["error"]


@pytest.mark.parametrize(
    "arguments,fragment",
    [
        ({"npaid": "NPA1"}, "six digits"),
        ({"npaid": 1}, "required"),
        ({"npaid": "NPA000001", "field": "all"}, "field"),
    ],
)
def test_invalid_or_unknown_arguments_fail_before_network(arguments, fragment):
    """Malformed IDs and ignored controls cannot become broad or wrong lookups."""
    with patch("tooluniverse.npatlas_tool.requests.get") as request:
        result = NPAtlasCompoundTool(_config()).run(arguments)
    assert result["status"] == "error"
    assert fragment.lower() in result["error"].lower()
    request.assert_not_called()
