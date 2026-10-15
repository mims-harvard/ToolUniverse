"""MouseMine falls back to MGI's own reports only while MouseMine is down.

Every MouseMine endpoint has answered 504 since 2026-10-03 while the InterMine
registry lists it as Running -- an outage, not a retirement -- so MouseMine
stays primary. MGI, its data source, serves the same records as TSV reports,
and those answer only on a server error, a timeout or a refused connection.

Alliance's search_autocomplete was the obvious alternative and was measured
and rejected: ten results across all species, no mouse hit for Tp53, insulin
or CRISPR, and no alleles at all.
"""

import json
from pathlib import Path

import pytest

import tooluniverse.mousemine_tool as mm

pytestmark = pytest.mark.unit

DATA = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"

MARKER_TSV = (
    "Chromosome\tStart\tEnd\tcM\tstrand GRCm39\tMGI ID\tFeature Type\tSymbol\t"
    "Name\tMatching Text\t\r\n"
    "5\t140690766\t140705134\t79.25\t+\tMGI:1891679\tprotein coding gene\t"
    "Brat1\tBRCA1-associated ATM activator 1\t\t\r\n"
    "11\t101379590\t101442781\t65.18\t-\tMGI:104537\tprotein coding gene\t"
    "Brca1\tbreast cancer 1, early onset\t\t\r\n"
)
ALLELE_TSV = (
    "MGI Allele ID\tAllele Symbol\tAllele Name\tChromosome\tSynonyms\t"
    "Allele Type\tAllele Attributes\tTransmission\t\r\n"
    "MGI:7425483\tAbraxas1<em1(IMPC)Ccpcz>\tendonuclease-mediated mutation 1\t"
    "5\t\tEndonuclease-mediated\tNull/knockout\tGermline\t\r\n"
    "MGI:5000001\tBrca1<tm1Aash>\ttargeted mutation 1\t11\t\tTargeted\t"
    "Null/knockout\tGermline\t\r\n"
)


def _tool(name):
    config = next(
        t for t in json.loads((DATA / "mousemine_tools.json").read_text("utf-8"))
        if t["name"] == name
    )
    return mm.MouseMineTool(config)


class _Resp:
    status_code = 200

    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


@pytest.fixture
def mgi(monkeypatch):
    calls = []

    def fake(session, method, url, **kwargs):
        calls.append(url)
        return _Resp(ALLELE_TSV if "allele" in url else MARKER_TSV)

    monkeypatch.setattr(mm, "request_with_retry", fake)
    return calls


def _mousemine_returns(monkeypatch, envelope):
    monkeypatch.setattr(mm.BaseRESTTool, "run", lambda self, args: envelope)


def test_a_504_falls_back_to_mgi_and_says_so(monkeypatch, mgi):
    _mousemine_returns(monkeypatch, {"status": "error", "status_code": 504,
                                     "error": "MouseMine returned HTTP 504"})

    result = _tool("MouseMine_search_genes").run({"q": "Brca1", "size": 5})

    assert result["status"] == "success"
    assert result["metadata"]["source"] == "Mouse Genome Informatics (MouseMine fallback)"
    assert result["data"]["totalHits"] == 2
    first = result["data"]["results"][0]
    assert first["fields"]["symbol"] == "Brca1", "the exact hit comes first"
    assert first["fields"]["primaryIdentifier"] == "MGI:104537"
    assert first["type"] == "ProteinCodingGene"
    assert mgi == [mm.MGI_MARKER_REPORT]


def test_a_timeout_falls_back_too(monkeypatch, mgi):
    _mousemine_returns(monkeypatch, {"status": "error",
                                     "error": "MouseMine request timed out"})

    result = _tool("MouseMine_search_genes").run({"q": "Brca1"})

    assert result["status"] == "success"


def test_a_client_error_is_not_masked(monkeypatch, mgi):
    """A 4xx is about the request; falling back would hide that."""
    envelope = {"status": "error", "status_code": 400, "error": "bad request"}
    _mousemine_returns(monkeypatch, envelope)

    result = _tool("MouseMine_search_genes").run({"q": "Brca1"})

    assert result is envelope
    assert mgi == []


def test_a_working_mousemine_is_left_alone(monkeypatch, mgi):
    envelope = {"status": "success", "data": {"totalHits": 1, "results": []}}
    _mousemine_returns(monkeypatch, envelope)

    assert _tool("MouseMine_search_genes").run({"q": "Brca1"}) is envelope
    assert mgi == []


def test_alleles_of_the_queried_gene_come_first(monkeypatch, mgi):
    """MGI returns alphabetically, which led with Abraxas1's allele."""
    _mousemine_returns(monkeypatch, {"status": "error", "status_code": 504})

    result = _tool("MouseMine_search_alleles").run({"q": "Brca1", "size": 5})

    symbols = [r["fields"]["symbol"] for r in result["data"]["results"]]
    assert symbols[0] == "Brca1<tm1Aash>"
    first = result["data"]["results"][0]["fields"]
    assert first["alleleType"] == "Targeted"
    assert first["attributeString"] == "Null/knockout"
    assert mgi == [mm.MGI_ALLELE_REPORT]


def test_ids_with_no_mgi_equivalent_are_omitted_not_invented(monkeypatch, mgi):
    _mousemine_returns(monkeypatch, {"status": "error", "status_code": 504})

    result = _tool("MouseMine_search_genes").run({"q": "Brca1"})

    for item in result["data"]["results"]:
        assert "id" not in item, "MouseMine's internal object id has no MGI equivalent"
        assert "relevance" not in item


def test_the_general_search_says_facets_are_unavailable(monkeypatch, mgi):
    _mousemine_returns(monkeypatch, {"status": "error", "status_code": 504})

    result = _tool("MouseMine_search").run({"q": "Brca1"})

    assert result["data"]["facets"] == {}
    assert "Facet counts are not available" in result["metadata"]["note"]
    assert set(mgi) == {mm.MGI_MARKER_REPORT, mm.MGI_ALLELE_REPORT}


def test_if_mgi_is_down_too_the_original_error_is_reported(monkeypatch):
    import requests

    envelope = {"status": "error", "status_code": 504, "error": "MouseMine 504"}
    _mousemine_returns(monkeypatch, envelope)

    def boom(*a, **k):
        raise requests.exceptions.ConnectionError("down")

    monkeypatch.setattr(mm, "request_with_retry", boom)

    assert _tool("MouseMine_search_genes").run({"q": "Brca1"}) is envelope


def test_the_configs_use_the_fallback_class():
    for tool in json.loads((DATA / "mousemine_tools.json").read_text("utf-8")):
        assert tool["type"] == "MouseMineTool", tool["name"]
