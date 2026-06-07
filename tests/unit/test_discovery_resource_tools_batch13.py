"""Unit tests for discovery-round batch 13 (AlphaFill). Network mocked."""

from unittest.mock import MagicMock, patch

from tooluniverse.alphafill_tool import AlphaFillTransplantsTool


def _resp(status=200, json_body=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_body
    r.raise_for_status.return_value = None
    return r


def _cfg():
    return {"name": "AlphaFill_get_transplants", "type": "AlphaFillTransplantsTool",
            "parameter": {"type": "object", "properties": {}}}


def test_requires_uniprot():
    out = AlphaFillTransplantsTool(_cfg()).run({})
    assert out["status"] == "error"
    assert "uniprot" in out["error"]


def test_aggregates_transplants_by_compound():
    body = {"alphafill_version": "2.1.1", "hits": [
        {"pdb_id": "1opl", "transplants": [
            {"compound_id": "STI", "local_rmsd": 1.5},
            {"compound_id": "NA", "local_rmsd": 0.9}]},
        {"pdb_id": "2hyy", "transplants": [
            {"compound_id": "STI", "local_rmsd": 0.8},
            {"compound_id": "NA", "local_rmsd": 1.2}]},
    ]}
    with patch("tooluniverse.alphafill_tool.requests.get", return_value=_resp(200, body)):
        out = AlphaFillTransplantsTool(_cfg()).run({"uniprot": "p00520"})
    assert out["status"] == "success"
    d = out["data"]
    assert d["uniprot"] == "P00520"
    assert d["n_homolog_hits"] == 2
    tp = {t["compound_id"]: t for t in d["transplants"]}
    assert tp["STI"]["occurrences"] == 2
    assert tp["STI"]["best_local_rmsd"] == 0.8  # min kept
    assert sorted(tp["STI"]["source_pdb_ids"]) == ["1opl", "2hyy"]
    assert tp["NA"]["best_local_rmsd"] == 0.9


def test_404_empty_transplants():
    with patch("tooluniverse.alphafill_tool.requests.get", return_value=_resp(404)):
        out = AlphaFillTransplantsTool(_cfg()).run({"uniprot": "Q00000"})
    assert out["status"] == "success"
    assert out["data"]["transplants"] == []


def test_no_hits_is_empty_success():
    with patch("tooluniverse.alphafill_tool.requests.get", return_value=_resp(200, {"hits": []})):
        out = AlphaFillTransplantsTool(_cfg()).run({"uniprot": "P12345"})
    assert out["status"] == "success"
    assert out["data"]["transplants"] == []
    assert out["data"]["n_homolog_hits"] == 0
