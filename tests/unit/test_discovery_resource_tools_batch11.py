"""Unit tests for discovery-round batch 11 (FooDB). Network mocked."""

from unittest.mock import MagicMock, patch

from tooluniverse.foodb_tool import FooDBCompoundTool


def _resp(status=200, json_body=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_body
    r.raise_for_status.return_value = None
    return r


def _cfg():
    return {"name": "FooDB_get_compound", "type": "FooDBCompoundTool",
            "parameter": {"type": "object", "properties": {}}}


def test_foodb_requires_id():
    out = FooDBCompoundTool(_cfg()).run({})
    assert out["status"] == "error"
    assert "fdb_id" in out["error"]


def test_foodb_curates_structure_and_xrefs():
    body = {"public_id": "FDB000004", "name": "Cyanidin 3-galactoside",
            "description": "Constituent of leaves...", "cas_number": "350602-26-5",
            "moldb_formula": "C23H23O12", "moldb_smiles": "[H]C1...",
            "moldb_inchikey": "HBXXDBKJLPLXPR-DLBZZEGUSA-O", "moldb_logp": "0.81",
            "hmdb_id": "HMDB29236", "kegg_compound_id": None, "chebi_id": None}
    with patch("tooluniverse.foodb_tool.requests.get", return_value=_resp(200, body)):
        out = FooDBCompoundTool(_cfg()).run({"fdb_id": "fdb000004"})
    assert out["status"] == "success"
    d = out["data"]
    assert d["fdb_id"] == "FDB000004"
    assert d["formula"] == "C23H23O12"
    assert d["inchikey"] == "HBXXDBKJLPLXPR-DLBZZEGUSA-O"
    assert d["cross_references"]["hmdb_id"] == "HMDB29236"


def test_foodb_404_empty():
    with patch("tooluniverse.foodb_tool.requests.get", return_value=_resp(404)):
        out = FooDBCompoundTool(_cfg()).run({"fdb_id": "FDB999999"})
    assert out["status"] == "success"
    assert out["data"] == {}


def test_foodb_non_compound_body_empty():
    with patch("tooluniverse.foodb_tool.requests.get", return_value=_resp(200, None)):
        out = FooDBCompoundTool(_cfg()).run({"fdb_id": "FDB000004"})
    assert out["status"] == "success"
    assert out["data"] == {}
