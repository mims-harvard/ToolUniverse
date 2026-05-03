#!/usr/bin/env python3
"""
Unit tests for EuropePMC_get_fulltext_snippets (fullTextXML snippet extraction).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.europe_pmc_tool import EuropePMCFullTextSnippetsTool


class _FakeResponse:
    def __init__(self, *, status_code=200, text="", url=""):
        self.status_code = status_code
        self.text = text
        self.url = url or "https://example.test"
        self.headers = {}


@pytest.mark.unit
def test_europe_pmc_fulltext_snippets_finds_terms_in_xml(monkeypatch):
    tool = EuropePMCFullTextSnippetsTool({"name": "EuropePMC_get_fulltext_snippets"})

    xml_payload = """<?xml version="1.0" encoding="UTF-8"?>
<article>
  <front>
    <article-meta>
      <title-group>
        <article-title>A. baumannii readily evolved resistance to meropenem, ciprofloxacin, and gentamicin</article-title>
      </title-group>
    </article-meta>
  </front>
  <body>
    <sec>
      <title>A. lwoffii only evolved resistance to ciprofloxacin</title>
      <p>Selection experiments were set up.</p>
    </sec>
  </body>
</article>
"""

    def fake_request_with_retry(
        session, method, url, *, timeout=None, max_attempts=None, **kwargs
    ):
        assert url.endswith("/PMC11237425/fullTextXML")
        return _FakeResponse(status_code=200, text=xml_payload, url=url)

    monkeypatch.setattr(
        "tooluniverse.europe_pmc_tool.request_with_retry", fake_request_with_retry
    )

    out = tool.run(
        {
            "pmcid": "PMC11237425",
            "terms": ["ciprofloxacin", "meropenem", "lwoffii"],
            "window_chars": 60,
            "max_snippets_per_term": 2,
            "max_total_chars": 2000,
        }
    )

    assert out["status"] == "success"
    assert out["snippets_count"] >= 3
    assert any(
        "evolved resistance to ciprofloxacin" in s["snippet"].lower()
        for s in out["snippets"]
    )


@pytest.mark.unit
def test_europe_pmc_fulltext_snippets_accepts_keywords_alias(monkeypatch):
    tool = EuropePMCFullTextSnippetsTool({"name": "EuropePMC_get_fulltext_snippets"})

    xml_payload = """<?xml version="1.0" encoding="UTF-8"?>
<article>
  <body>
    <p>Selection experiments used ciprofloxacin.</p>
  </body>
</article>
"""

    def fake_request_with_retry(
        session, method, url, *, timeout=None, max_attempts=None, **kwargs
    ):
        assert url.endswith("/PMC11237425/fullTextXML")
        return _FakeResponse(status_code=200, text=xml_payload, url=url)

    monkeypatch.setattr(
        "tooluniverse.europe_pmc_tool.request_with_retry", fake_request_with_retry
    )

    out = tool.run(
        {
            "pmcid": "PMC11237425",
            "keywords": ["ciprofloxacin"],
            "window_chars": 60,
            "max_snippets_per_term": 2,
            "max_total_chars": 2000,
        }
    )

    assert out["status"] == "success"
    assert out["snippets_count"] >= 1
    assert any("ciprofloxacin" in s["snippet"].lower() for s in out["snippets"])


@pytest.mark.unit
def test_europe_pmc_fulltext_snippets_falls_back_to_pmc_oai(monkeypatch):
    tool = EuropePMCFullTextSnippetsTool({"name": "EuropePMC_get_fulltext_snippets"})

    def fake_request_with_retry(
        session, method, url, *, timeout=None, max_attempts=None, **kwargs
    ):
        # Primary Europe PMC fullTextXML missing
        if url.endswith("/PMC11237425/fullTextXML"):
            return _FakeResponse(status_code=404, text="not found", url=url)
        # Fallback: NCBI PMC OAI returns JATS wrapped in OAI-PMH
        if "ncbi.nlm.nih.gov/pmc/oai/oai.cgi" in url:
            oai_xml = """<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
  <GetRecord>
    <record>
      <metadata>
        <article>
          <front>
            <abstract><p>Selection experiments used ciprofloxacin.</p></abstract>
          </front>
          <body>
            <p>A. lwoffii only evolved resistance to ciprofloxacin.</p>
          </body>
        </article>
      </metadata>
    </record>
  </GetRecord>
</OAI-PMH>
"""
            return _FakeResponse(status_code=200, text=oai_xml, url=url)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(
        "tooluniverse.europe_pmc_tool.request_with_retry", fake_request_with_retry
    )

    out = tool.run(
        {
            "pmcid": "PMC11237425",
            "terms": ["ciprofloxacin"],
            "window_chars": 80,
            "max_snippets_per_term": 2,
            "max_total_chars": 2000,
        }
    )

    assert out["status"] == "success"
    assert out["snippets_count"] >= 1
    assert any("ciprofloxacin" in s["snippet"].lower() for s in out["snippets"])


@pytest.mark.unit
def test_europe_pmc_fulltext_snippets_falls_back_to_pmc_html(monkeypatch):
    tool = EuropePMCFullTextSnippetsTool({"name": "EuropePMC_get_fulltext_snippets"})

    def fake_request_with_retry(
        session, method, url, *, timeout=None, max_attempts=None, **kwargs
    ):
        # Primary Europe PMC fullTextXML missing
        if url.endswith("/PMC5234727/fullTextXML"):
            return _FakeResponse(status_code=404, text="not found", url=url)
        # OAI endpoint exists but doesn't provide XML for this document
        if "ncbi.nlm.nih.gov/pmc/oai/oai.cgi" in url:
            return _FakeResponse(
                status_code=400,
                text='<OAI-PMH><error code="cannotDisseminateFormat"/></OAI-PMH>',
                url=url,
            )
        # efetch may return an XML stub indicating download restriction
        if (
            "eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi" in url
            and "db=pmc" in url
        ):
            stub = (
                '<?xml version="1.0"?><pmc-articleset>'
                "<article><!--The publisher of this article does not allow download--></article>"
                "</pmc-articleset>"
            )
            return _FakeResponse(status_code=200, text=stub, url=url)
        # HTML fallback
        if "pmc.ncbi.nlm.nih.gov/articles/PMC5234727/" in url:
            html = "<html><body><p>PNPLA3 and TM6SF2 increase alanine aminotransferase (ALT).</p></body></html>"
            return _FakeResponse(status_code=200, text=html, url=url)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(
        "tooluniverse.europe_pmc_tool.request_with_retry", fake_request_with_retry
    )

    out = tool.run(
        {
            "pmcid": "PMC5234727",
            "terms": ["PNPLA3", "TM6SF2", "alanine", "ALT"],
            "window_chars": 60,
            "max_snippets_per_term": 2,
            "max_total_chars": 2000,
        }
    )

    assert out["status"] == "success"
    assert out["source"] == "NCBI PMC HTML"
    assert out["snippets_count"] >= 2
    assert any("pnpla3" in s["snippet"].lower() for s in out["snippets"])
