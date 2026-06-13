"""Offline unit tests for the ProteomicsDB meltome + ClusPro peptide-docking tools.

ProteomicsDB is keyless (mock the OData GETs); ClusPro is key-gated (mock the
submit POST and exercise the no-key / missing-arg guards).
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.proteomicsdb_meltome_tool import ProteomicsDBGetProteinMeltomeTool
from tooluniverse.cluspro_tool import ClusProSubmitPeptideDockingTool, _make_sig

pytestmark = pytest.mark.unit


# --------------------------- ProteomicsDB meltome ---------------------------

def _odata_resp(results):
    resp = MagicMock()
    resp.json.return_value = {"d": {"results": results}}
    resp.raise_for_status = lambda: None
    return resp


def _meltome_get(url, *a, **k):
    """Route the two OData GETs (Protein lookup, then Curve)."""
    if "/Protein?" in url:
        return _odata_resp([
            {"PROTEIN_ID": 1826, "GENE_NAME": "MAPK1", "UNIQUE_IDENTIFIER": "P28482", "PROTEIN_NAME": "MAPK1"}
        ])
    if "/Curve?" in url:
        return _odata_resp([
            {"CURVE_ID": 1, "COD": "0.992", "P_VALUE": "0.001", "BIC": "-7.1", "SCOPE": "cell",
             "FittedParameters": {"results": [{"VALUE": "0.012"}, {"VALUE": "0.31"}, {"VALUE": "55.5"}]}},
            {"CURVE_ID": 2, "COD": "0.98", "P_VALUE": "0.002", "BIC": "-6.0", "SCOPE": "cell",
             "FittedParameters": {"results": [{"VALUE": "0.02"}, {"VALUE": "0.29"}, {"VALUE": "56.7"}]}},
        ])
    raise AssertionError(f"unexpected URL {url}")


def test_meltome_success_extracts_tm():
    """Melting curves parse and the apparent Tm = the in-range inflection param."""
    with patch("tooluniverse.proteomicsdb_meltome_tool.requests.get", _meltome_get):
        out = ProteomicsDBGetProteinMeltomeTool({}).run({"gene_symbol": "MAPK1"})
    assert out["status"] == "success"
    d = out["data"]
    assert d["gene_name"] == "MAPK1" and d["protein_id"] == 1826
    assert d["n_melting_curves"] == 2
    assert d["curves"][0]["apparent_tm_celsius"] == 55.5
    assert d["median_apparent_tm_celsius"] in (55.5, 56.7)


def test_meltome_requires_an_identifier():
    """Omitting both gene and accession errors before any HTTP call."""
    out = ProteomicsDBGetProteinMeltomeTool({}).run({})
    assert out["status"] == "error"
    assert "gene_symbol or uniprot_accession" in out["error"]


def test_meltome_protein_not_found():
    """An unknown protein yields a clean not-found error."""
    with patch("tooluniverse.proteomicsdb_meltome_tool.requests.get", lambda *a, **k: _odata_resp([])):
        out = ProteomicsDBGetProteinMeltomeTool({}).run({"gene_symbol": "NOPE"})
    assert out["status"] == "error"
    assert "No ProteomicsDB protein" in out["error"]


def test_meltome_network_error_envelope():
    """A request exception is caught and returned as an error envelope."""
    import requests

    def _boom(*a, **k):
        raise requests.RequestException("conn reset")

    with patch("tooluniverse.proteomicsdb_meltome_tool.requests.get", _boom):
        out = ProteomicsDBGetProteinMeltomeTool({}).run({"gene_symbol": "MAPK1"})
    assert out["status"] == "error"
    assert "lookup failed" in out["error"]


# ------------------------------- ClusPro ------------------------------------

def test_make_sig_matches_reference_algorithm():
    """_make_sig reproduces cluspro-api: HMAC-MD5 of sorted key+value concat."""
    import hashlib
    import hmac

    form = {"username": "u", "recpdb": "1A2K", "pepseq": "KGRRL"}
    expected = hmac.new(b"sek", "pepseqKGRRLrecpdb1A2Kusernameu".encode(), hashlib.md5).hexdigest()
    assert _make_sig(form, "sek") == expected


def test_cluspro_requires_keys(monkeypatch):
    """Without CLUSPRO_USERNAME/SECRET the tool errors before any HTTP call."""
    monkeypatch.delenv("CLUSPRO_USERNAME", raising=False)
    monkeypatch.delenv("CLUSPRO_API_SECRET", raising=False)
    out = ClusProSubmitPeptideDockingTool({}).run({"receptor_pdb_id": "1A2K", "peptide_sequence": "KGRRL"})
    assert out["status"] == "error"
    assert "CLUSPRO_USERNAME" in out["error"]


def test_cluspro_missing_receptor(monkeypatch):
    """With keys set, a missing receptor still errors before HTTP."""
    monkeypatch.setenv("CLUSPRO_USERNAME", "u")
    monkeypatch.setenv("CLUSPRO_API_SECRET", "s")
    out = ClusProSubmitPeptideDockingTool({}).run({"peptide_sequence": "KGRRL"})
    assert out["status"] == "error"
    assert "receptor_pdb_id" in out["error"]


def test_cluspro_submit_success(monkeypatch):
    """A successful submit returns the ClusPro job id; motif defaults to sequence."""
    monkeypatch.setenv("CLUSPRO_USERNAME", "u")
    monkeypatch.setenv("CLUSPRO_API_SECRET", "s")
    captured = {}

    def _post(url, data=None, timeout=None, **k):
        captured["form"] = data
        resp = MagicMock()
        resp.json.return_value = {"status": "success", "id": 987654}
        resp.raise_for_status = lambda: None
        return resp

    with patch("tooluniverse.cluspro_tool.requests.post", _post):
        out = ClusProSubmitPeptideDockingTool({}).run({"receptor_pdb_id": "1a2k", "peptide_sequence": "kgrrl"})
    assert out["status"] == "success"
    assert out["data"]["job_id"] == 987654
    # peptide mode + sequence uppercased + motif defaulted to sequence + signature present
    assert captured["form"]["peptidemode"] == "1"
    assert captured["form"]["pepseq"] == "KGRRL"
    assert captured["form"]["pepmot"] == "KGRRL"
    assert len(captured["form"]["sig"]) == 32


def test_cluspro_server_rejection(monkeypatch):
    """A ClusPro error response is surfaced as an error envelope."""
    monkeypatch.setenv("CLUSPRO_USERNAME", "u")
    monkeypatch.setenv("CLUSPRO_API_SECRET", "s")

    def _post(url, data=None, timeout=None, **k):
        resp = MagicMock()
        resp.json.return_value = {"status": "error", "errors": "invalid PDB code"}
        resp.raise_for_status = lambda: None
        return resp

    with patch("tooluniverse.cluspro_tool.requests.post", _post):
        out = ClusProSubmitPeptideDockingTool({}).run({"receptor_pdb_id": "ZZZZ", "peptide_sequence": "KGRRL"})
    assert out["status"] == "error"
    assert "invalid PDB code" in out["error"]
