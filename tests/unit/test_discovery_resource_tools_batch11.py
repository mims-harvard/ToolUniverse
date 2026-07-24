"""Unit tests for discovery-round batch 11 (FooDB). Network mocked."""

from unittest.mock import MagicMock, patch

from tooluniverse.foodb_tool import FooDBCompoundTool


def _resp(status=200, json_body=None, history=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_body
    r.raise_for_status.return_value = None
    r.history = history if history is not None else []
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


def test_foodb_retired_id_redirect_not_returned_as_match():
    # Fix-R26A-1: FDB012199 is retired and 302-redirects to unrelated
    # compound FDB004133 (confirmed live). `requests` follows redirects
    # transparently, so without a history/public_id check the substituted
    # compound would silently be returned as if it matched the request.
    body = {"public_id": "FDB004133", "name": "3-Benzylisothiocyanate"}
    resp = _resp(200, body, history=[_resp(302)])
    with patch("tooluniverse.foodb_tool.requests.get", return_value=resp):
        out = FooDBCompoundTool(_cfg()).run({"fdb_id": "FDB012199"})
    assert out["status"] == "success"
    assert out["data"] == {}
    assert "FDB004133" in out["metadata"]["note"]
    assert out["metadata"]["query_fdb_id"] == "FDB012199"


def test_foodb_redirect_to_same_id_still_returns_data():
    # A redirect that lands on the *same* public_id (e.g. http->https,
    # case-normalization) should still return the compound normally.
    body = {"public_id": "FDB000004", "name": "Cyanidin 3-galactoside"}
    resp = _resp(200, body, history=[_resp(301)])
    with patch("tooluniverse.foodb_tool.requests.get", return_value=resp):
        out = FooDBCompoundTool(_cfg()).run({"fdb_id": "FDB000004"})
    assert out["status"] == "success"
    assert out["data"]["fdb_id"] == "FDB000004"
