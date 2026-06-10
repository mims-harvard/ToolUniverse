"""Depth tests for clinical-genetics-panels coverage tools.

Covers two new tools that reuse existing tool classes (no new registration):

* ``G2P_download_panel`` (BaseRESTTool) — downloads the FULL Gene2Phenotype
  panel as a CSV and parses it into structured per-record dicts. The prior
  ``G2P_get_panel`` returned only summary counts; this returns every
  gene-disease record. Exercises the new ``fields.parse_csv`` path in
  BaseRESTTool.
* ``HGNC_fetch_gene_family_members`` (HGNCTool) — enumerates every member
  gene of an HGNC gene family by ``gene_group_id`` via the ``fetch``
  endpoint, returning all docs (not just the first record).

All HTTP is mocked so the suite is offline/deterministic; live verification
is done separately via the CLI.
"""

import json
import os

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool
from tooluniverse.hgnc_tool import HGNCTool

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "src",
    "tooluniverse",
    "data",
)


def _load_tool_config(filename, tool_name):
    with open(os.path.join(DATA_DIR, filename)) as fh:
        configs = json.load(fh)
    matches = [c for c in configs if c.get("name") == tool_name]
    assert matches, f"{tool_name} not found in {filename}"
    return matches[0]


class _FakeResponse:
    def __init__(self, status_code=200, text="", content_type="text/csv"):
        self.status_code = status_code
        self.text = text
        self.headers = {"content-type": content_type}

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            import requests

            raise requests.exceptions.HTTPError(response=self)


# --- Sample CSV mirroring the real G2P panel download (header + 2 records) ---
_G2P_CSV = (
    "g2p id,gene symbol,gene mim,hgnc id,previous gene symbols,disease name,"
    "disease mim,disease MONDO,allelic requirement,cross cutting modifier,"
    "confidence,variant consequence,variant types,molecular mechanism,"
    "molecular mechanism support,molecular mechanism categorisation,"
    "molecular mechanism evidence,phenotypes,publications,"
    "additional mined publications,panel,comments,date of last review,review\n"
    "G2P00027,BRIP1,605882,20473,BACH1; FANCJ,BRIP1-related Fanconi anemia,"
    "609054,MONDO:0012187,biallelic_autosomal,,definitive,absent gene product,"
    ",loss of function,inferred,,,HP:0000007; HP:0000568,16116424,"
    "16116423; 26968956,DD; Cancer,,2025-01-28 23:03:26+00:00,\n"
    "G2P00119,TP53,191170,11998,,Li-Fraumeni syndrome,151623,MONDO:0018875,"
    "monoallelic_autosomal,,definitive,altered gene product structure,,"
    "dominant negative,evidence,,,HP:0006744,1978757,,Cancer,,"
    "2024-11-01 10:00:00+00:00,\n"
)


@pytest.mark.unit
def test_g2p_download_panel_parses_csv_records(monkeypatch):
    cfg = _load_tool_config("gene2phenotype_tools.json", "G2P_download_panel")
    tool = BaseRESTTool(cfg)

    captured = {}

    def fake_request(session, method, url, **kwargs):
        captured["url"] = url
        return _FakeResponse(200, _G2P_CSV, "text/csv")

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", fake_request)

    result = tool.run({"panel": "Cancer"})

    assert result["status"] == "success"
    # URL is built from the {panel} placeholder with /download/ suffix.
    assert captured["url"].endswith("/panel/Cancer/download/")
    # Two data records (header excluded), structured as dicts.
    assert result["count"] == 2
    assert isinstance(result["data"], list) and len(result["data"]) == 2
    first = result["data"][0]
    assert first["g2p id"] == "G2P00027"
    assert first["gene symbol"] == "BRIP1"
    assert first["disease MONDO"] == "MONDO:0012187"
    assert first["allelic requirement"] == "biallelic_autosomal"
    assert first["confidence"] == "definitive"
    assert "HP:0000007" in first["phenotypes"]
    # Column headers are surfaced for downstream consumers.
    assert "disease MONDO" in result["columns"]
    assert len(result["columns"]) == 24


@pytest.mark.unit
def test_g2p_download_panel_http_error(monkeypatch):
    """A non-2xx download response yields a status:error envelope with the code."""
    cfg = _load_tool_config("gene2phenotype_tools.json", "G2P_download_panel")
    tool = BaseRESTTool(cfg)

    def fake_request(session, method, url, **kwargs):
        return _FakeResponse(404, "Not found", "application/json")

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", fake_request)

    result = tool.run({"panel": "NotARealPanel"})
    assert result["status"] == "error"
    assert result["status_code"] == 404


@pytest.mark.unit
def test_g2p_download_panel_html_error(monkeypatch):
    """An HTML error page (not CSV) is detected and reported as an error."""
    cfg = _load_tool_config("gene2phenotype_tools.json", "G2P_download_panel")
    tool = BaseRESTTool(cfg)

    def fake_request(session, method, url, **kwargs):
        return _FakeResponse(200, "<!DOCTYPE html><html>oops</html>", "text/html")

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", fake_request)

    result = tool.run({"panel": "Cancer"})
    assert result["status"] == "error"
    assert "HTML" in result["error"]


# --- HGNC family members -----------------------------------------------------

_HGNC_GROUP_JSON = json.dumps(
    {
        "response": {
            "numFound": 3,
            "docs": [
                {
                    "hgnc_id": "HGNC:12607",
                    "symbol": "USP1",
                    "name": "ubiquitin specific peptidase 1",
                    "locus_type": "gene with protein product",
                    "location": "1p31.3",
                    "gene_group": ["Ubiquitin specific peptidases"],
                    "gene_group_id": [366],
                    "ensembl_gene_id": "ENSG00000162607",
                    "entrez_id": "7398",
                    "uniprot_ids": ["O94782"],
                },
                {
                    "hgnc_id": "HGNC:1093",
                    "symbol": "CYLD",
                    "name": "CYLD lysine 63 deubiquitinase",
                    "locus_type": "gene with protein product",
                    "location": "16q12.1",
                    "gene_group": ["Ubiquitin specific peptidases"],
                    "gene_group_id": [366],
                },
                {
                    "hgnc_id": "HGNC:23039",
                    "symbol": "PAN2",
                    "name": "poly(A) specific ribonuclease subunit PAN2",
                    "locus_type": "gene with protein product",
                    "location": "12q13.3",
                    "gene_group_id": [366],
                },
            ],
        }
    }
)


@pytest.mark.unit
def test_hgnc_fetch_gene_family_members_returns_all(monkeypatch):
    """gene_group_id returns every family member as a list of full records."""
    cfg = _load_tool_config("hgnc_tools.json", "HGNC_fetch_gene_family_members")
    tool = HGNCTool(cfg)

    captured = {}

    def fake_get(url, headers=None, timeout=None):
        captured["url"] = url
        return _FakeResponse(200, _HGNC_GROUP_JSON, "application/json")

    monkeypatch.setattr("tooluniverse.hgnc_tool.requests.get", fake_get)

    result = tool.run({"gene_group_id": "366"})

    assert result["status"] == "success"
    assert captured["url"].endswith("/fetch/gene_group_id/366")
    # All member docs returned as a list (not just the first record).
    assert isinstance(result["data"], list)
    assert len(result["data"]) == 3
    symbols = [d["symbol"] for d in result["data"]]
    assert symbols == ["USP1", "CYLD", "PAN2"]
    assert result["metadata"]["num_found"] == 3
    assert result["metadata"]["query_field"] == "gene_group_id"
    # Full records carry cross-references.
    assert result["data"][0]["ensembl_gene_id"] == "ENSG00000162607"


@pytest.mark.unit
def test_hgnc_fetch_gene_family_members_integer_input(monkeypatch):
    """An integer gene_group_id is coerced into a clean URL path segment."""
    cfg = _load_tool_config("hgnc_tools.json", "HGNC_fetch_gene_family_members")
    tool = HGNCTool(cfg)

    captured = {}

    def fake_get(url, headers=None, timeout=None):
        captured["url"] = url
        return _FakeResponse(200, _HGNC_GROUP_JSON, "application/json")

    monkeypatch.setattr("tooluniverse.hgnc_tool.requests.get", fake_get)

    # An integer gene_group_id must be coerced to a clean path segment.
    result = tool.run({"gene_group_id": 366})
    assert result["status"] == "success"
    assert captured["url"].endswith("/fetch/gene_group_id/366")


@pytest.mark.unit
def test_hgnc_fetch_gene_family_members_missing_id():
    """An empty gene_group_id errors before any HTTP request."""
    cfg = _load_tool_config("hgnc_tools.json", "HGNC_fetch_gene_family_members")
    tool = HGNCTool(cfg)

    # Empty id short-circuits with an error before any HTTP call.
    result = tool.run({"gene_group_id": ""})
    assert result["status"] == "error"
    assert "gene_group_id" in result["error"]


@pytest.mark.unit
def test_hgnc_fetch_gene_family_members_never_raises(monkeypatch):
    """A network exception is caught and returned as status:error, never raised."""
    cfg = _load_tool_config("hgnc_tools.json", "HGNC_fetch_gene_family_members")
    tool = HGNCTool(cfg)

    def fake_get(url, headers=None, timeout=None):
        raise RuntimeError("network down")

    monkeypatch.setattr("tooluniverse.hgnc_tool.requests.get", fake_get)

    result = tool.run({"gene_group_id": "366"})
    assert result["status"] == "error"
