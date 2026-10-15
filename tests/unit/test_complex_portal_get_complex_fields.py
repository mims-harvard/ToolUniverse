"""ComplexPortal_get_complex returned null name, species, taxonomy and description.

The Complex Portal record uses ``complexAc``/``name``/``species`` ("Mus musculus;
10090") and lists the description under ``functions`` and the type under
``complexAssemblies``; the tool read ``complexAC``/``complexName``/``organismName``/
``organismTaxId``/``description``/``complexType``. GO cross-references are labelled
"gene ontology" but were only recognised as "go", so ``go_annotations`` was always
empty. The record below is trimmed from the live response for CPX-100.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.complex_portal_tool import ComplexPortalTool

pytestmark = pytest.mark.unit

RECORD = {
    "ac": "CPX-100",
    "complexAc": "CPX-100",
    "name": "Cathepsin-B - cystatin-A complex",
    "systematicName": "Ctsb:Csta",
    "synonyms": ["Ctsb-Csta complex"],
    "species": "Mus musculus; 10090",
    "functions": ["Complex of cathepsin-B with its inhibitor cystatin-A."],
    "complexAssemblies": ["Heterodimer"],
    "predictedComplex": False,
    "properties": ["Displacement of the occluding loop ..."],
    "evidenceType": {"identifier": "ECO:0005544"},
    "participants": [
        {
            "identifier": "P35173",
            "name": "Csta",
            "description": "Cystatin-A",
            "stochiometry": "1",
            "interactorType": "protein",
        }
    ],
    "crossReferences": [
        {
            "database": "gene ontology",
            "identifier": "GO:0005764",
            "description": "lysosome",
        },
        {"database": "intact", "identifier": "EBI-1", "description": "IntAct"},
        {"database": "efo", "identifier": "EFO:0000001", "description": "a disease"},
    ],
}


def _get(record):
    response = MagicMock()
    response.json.return_value = record
    tool = ComplexPortalTool(
        {"name": "ComplexPortal_get_complex", "fields": {"operation": "get_complex"}}
    )
    with patch("tooluniverse.complex_portal_tool.requests.get", return_value=response):
        return tool.run({"operation": "get_complex", "complex_id": "CPX-100"})


def test_current_record_fills_identity_species_and_description():
    data = _get(RECORD)["data"]
    assert data["complex_id"] == "CPX-100"
    assert data["name"] == "Cathepsin-B - cystatin-A complex"
    assert data["systematic_name"] == "Ctsb:Csta"
    assert (data["species"], data["taxonomy_id"]) == ("Mus musculus", "10090")
    assert (
        data["description"] == "Complex of cathepsin-B with its inhibitor cystatin-A."
    )
    assert data["complex_type"] == "Heterodimer"
    assert data["predicted"] is False
    assert data["synonyms"] == ["Ctsb-Csta complex"]


def test_subunits_and_gene_ontology_cross_references_are_kept():
    data = _get(RECORD)["data"]
    assert [s["name"] for s in data["subunits"]] == ["Csta"]
    assert [g["identifier"] for g in data["go_annotations"]] == ["GO:0005764"]
    assert [x["database"] for x in data["cross_references"]] == ["intact"]
    assert [d["identifier"] for d in data["diseases"]] == ["EFO:0000001"]


def test_older_record_keys_still_work():
    old = {
        "complexAC": "CPX-9",
        "complexName": "Old complex",
        "organismName": "Homo sapiens",
        "organismTaxId": 9606,
        "description": "Old description",
        "complexType": "Heteromer",
    }
    data = _get(old)["data"]
    assert (data["complex_id"], data["name"], data["species"]) == (
        "CPX-9",
        "Old complex",
        "Homo sapiens",
    )
    assert data["taxonomy_id"] == 9606
    assert (
        data["description"] == "Old description" and data["complex_type"] == "Heteromer"
    )
