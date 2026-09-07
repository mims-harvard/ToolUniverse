"""Unit tests for UniChem_search_compound returning the real InChIKey.

Regression: ``_search_compound`` used to set
``"inchikey": compound if search_type == "inchikey" else None``, so any
search by ``sourceID`` or ``uci`` returned ``inchikey: null`` even though
the ``/compounds`` response carries ``standardInchiKey`` at the top level
(the same field ``_connectivity_search`` already reads correctly).

All tests are offline: ``requests.post`` is patched.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.unichem_tool import UniChemTool

INCHIKEY = "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"


def _make_tool():
    return UniChemTool(
        {
            "name": "UniChem_search_compound",
            "type": "UniChemTool",
            "fields": {"endpoint_type": "search_compound"},
            "parameter": {"type": "object", "properties": {}},
        }
    )


def _compounds_payload(include_inchikey=True):
    compound = {
        "inchi": {
            "inchi": "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)",
            "formula": "C9H8O4",
        },
        "uci": 161671,
        "sources": [
            {
                "shortName": "chembl",
                "longName": "ChEMBL",
                "compoundId": "CHEMBL25",
                "url": "https://www.ebi.ac.uk/chembldb/compound/inspect/CHEMBL25",
            }
        ],
    }
    if include_inchikey:
        compound["standardInchiKey"] = INCHIKEY
    return {"compounds": [compound]}


def _mock_post(payload):
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status.return_value = None
    resp.json.return_value = payload
    return patch("tooluniverse.unichem_tool.requests.post", return_value=resp)


@pytest.mark.unit
def test_source_id_search_returns_inchikey_from_response():
    """Searching by sourceID must surface standardInchiKey, not None."""
    tool = _make_tool()
    with _mock_post(_compounds_payload()):
        result = tool.run(
            {"compound": "CHEMBL25", "type": "sourceID", "sourceID": "1"}
        )

    assert result["status"] == "success"
    assert result["data"]["inchikey"] == INCHIKEY
    # Previously-working fields must be untouched.
    assert result["data"]["formula"] == "C9H8O4"
    assert result["data"]["inchi"].startswith("InChI=1S/C9H8O4/")
    assert result["data"]["source_count"] == 1


@pytest.mark.unit
def test_uci_is_surfaced_from_response():
    """``uci`` is additive, mirroring UniChem_connectivity_search."""
    tool = _make_tool()
    with _mock_post(_compounds_payload()):
        result = tool.run(
            {"compound": "CHEMBL25", "type": "sourceID", "sourceID": "1"}
        )

    assert result["data"]["uci"] == 161671


@pytest.mark.unit
def test_inchikey_search_still_echoes_query_when_field_absent():
    """Fallback: no standardInchiKey in the response must not regress."""
    tool = _make_tool()
    with _mock_post(_compounds_payload(include_inchikey=False)):
        result = tool.run({"compound": INCHIKEY, "type": "inchikey"})

    assert result["status"] == "success"
    assert result["data"]["inchikey"] == INCHIKEY


@pytest.mark.unit
def test_non_inchikey_search_without_field_stays_none():
    """Fallback keeps the old behaviour when nothing better is available."""
    tool = _make_tool()
    with _mock_post(_compounds_payload(include_inchikey=False)):
        result = tool.run(
            {"compound": "CHEMBL25", "type": "sourceID", "sourceID": "1"}
        )

    assert result["data"]["inchikey"] is None


@pytest.mark.unit
def test_empty_compounds_response_includes_uci_key():
    tool = _make_tool()
    with _mock_post({"compounds": []}):
        result = tool.run({"compound": "NOPE", "type": "inchikey"})

    assert result["status"] == "success"
    assert result["data"]["uci"] is None
    assert result["data"]["source_count"] == 0
