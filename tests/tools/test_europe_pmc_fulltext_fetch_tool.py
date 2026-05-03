#!/usr/bin/env python3
"""
Unit tests for EuropePMC_get_fulltext (machine-friendly full text retrieval).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.europe_pmc_tool import EuropePMCFullTextFetchTool


class _FakeResponse:
    def __init__(self, *, status_code=200, text="", url=""):
        self.status_code = status_code
        self.text = text
        self.url = url or "https://example.test"
        self.headers = {}


@pytest.mark.unit
def test_europe_pmc_fulltext_fetch_falls_back_to_html_when_oai_errors(monkeypatch):
    tool = EuropePMCFullTextFetchTool({"name": "EuropePMC_get_fulltext"})

    def fake_request_with_retry(
        session, method, url, *, timeout=None, max_attempts=None, **kwargs
    ):
        # Primary Europe PMC fullTextXML missing
        if url.endswith("/PMC5234727/fullTextXML"):
            return _FakeResponse(status_code=404, text="not found", url=url)
        # NCBI OAI returns HTTP 200 with an OAI-PMH error (realistic behavior)
        if "ncbi.nlm.nih.gov/pmc/oai/oai.cgi" in url:
            err = (
                "<?xml version=\"1.0\"?>"
                "<OAI-PMH xmlns=\"http://www.openarchives.org/OAI/2.0/\">"
                "<error code=\"cannotDisseminateFormat\">nope</error>"
                "</OAI-PMH>"
            )
            return _FakeResponse(status_code=200, text=err, url=url)
        # efetch returns an XML stub indicating download restriction
        if "eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi" in url and "db=pmc" in url:
            stub = (
                "<?xml version=\"1.0\"?><pmc-articleset>"
                "<article><!--The publisher of this article does not allow download--></article>"
                "</pmc-articleset>"
            )
            return _FakeResponse(status_code=200, text=stub, url=url)
        # HTML fallback
        if "pmc.ncbi.nlm.nih.gov/articles/PMC5234727/" in url:
            html = (
                "<html><body>"
                "<main id=\"maincontent\">"
                "<p>PNPLA3 and TM6SF2 increase alanine aminotransferase (ALT).</p>"
                "</main>"
                "</body></html>"
            )
            return _FakeResponse(status_code=200, text=html, url=url)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(
        "tooluniverse.europe_pmc_tool.request_with_retry", fake_request_with_retry
    )

    out = tool.run({"pmcid": "PMC5234727", "output_format": "text", "max_chars": 2000})

    assert out["status"] == "success"
    assert out["source"] == "NCBI PMC HTML"
    assert "pnpla3" in out["text"].lower()
    # Ensure the OAI-PMH logical error is not treated as success.
    assert any(
        (e.get("attempt") == "ncbi_pmc_oai" and (e.get("note") or "").startswith("oai_error:"))
        for e in out.get("retrieval_trace", [])
    )


@pytest.mark.unit
def test_europe_pmc_fulltext_fetch_raw_returns_bounded_content(monkeypatch):
    tool = EuropePMCFullTextFetchTool({"name": "EuropePMC_get_fulltext"})

    xml_payload = "<article><body><p>" + ("A" * 5000) + "</p></body></article>"

    def fake_request_with_retry(
        session, method, url, *, timeout=None, max_attempts=None, **kwargs
    ):
        assert url.endswith("/PMC111/fullTextXML")
        return _FakeResponse(status_code=200, text=xml_payload, url=url)

    monkeypatch.setattr(
        "tooluniverse.europe_pmc_tool.request_with_retry", fake_request_with_retry
    )

    out = tool.run(
        {
            "pmcid": "PMC111",
            "output_format": "raw",
            "max_chars": 1000,
            "include_raw": True,
            "max_raw_chars": 1500,
        }
    )

    assert out["status"] == "success"
    assert out["format"] == "xml"
    assert isinstance(out.get("content"), str)
    assert len(out["content"]) == 1000
    assert out["truncated"] is True
    assert isinstance(out.get("raw"), str)
    assert len(out["raw"]) == 1500
    assert out["raw_truncated"] is True
