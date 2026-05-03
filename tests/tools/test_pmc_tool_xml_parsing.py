#!/usr/bin/env python3
"""
Unit tests for PMC esummary XML parsing and stable output.
"""

import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.pmc_tool import PMCTool


class _FakeResponse:
    def __init__(self, *, status_code=200, json_payload=None, text="", url=""):
        self.status_code = status_code
        self._json_payload = json_payload
        self.text = text
        self.url = url or "https://example.test"

    def json(self):
        if self._json_payload is None:
            raise ValueError("No JSON payload")
        return self._json_payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


@pytest.mark.unit
def test_pmc_search_uses_xml_esummary_and_parses_docsum(monkeypatch):
    tool = PMCTool({"name": "PMC_search_papers"})

    xml_payload = """<?xml version="1.0" encoding="UTF-8"?>
<eSummaryResult>
  <DocSum>
    <Id>123</Id>
    <Item Name="Title" Type="String">Test PMC Title</Item>
    <Item Name="AuthorList" Type="List">
      <Item Name="Author" Type="String">Author A</Item>
      <Item Name="Author" Type="String">Author B</Item>
    </Item>
    <Item Name="PubDate" Type="String">2024 Jan 01</Item>
    <Item Name="Source" Type="String">Example Journal</Item>
    <Item Name="ArticleIds" Type="List">
      <Item Name="pubmed" Type="String">999</Item>
      <Item Name="pmc" Type="String">123</Item>
      <Item Name="doi" Type="String">10.1000/example</Item>
    </Item>
    <Item Name="PmcRefCount" Type="Integer">5</Item>
  </DocSum>
</eSummaryResult>
"""

    def fake_request_with_retry(
        session,
        method,
        url,
        *,
        params=None,
        timeout=None,
        max_attempts=None,
        **kwargs,
    ):
        if url.endswith("/esearch.fcgi"):
            return _FakeResponse(
                status_code=200,
                json_payload={"esearchresult": {"idlist": ["123"]}},
                url=url,
            )
        if url.endswith("/esummary.fcgi"):
            assert params.get("retmode") == "xml"
            assert params.get("db") == "pmc"
            return _FakeResponse(status_code=200, text=xml_payload, url=url)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(
        "tooluniverse.pmc_tool.request_with_retry", fake_request_with_retry
    )

    results = tool._search("anything", limit=1)

    assert isinstance(results, list)
    assert len(results) == 1
    paper = results[0]
    assert paper["pmc_id"] == "PMC123"
    assert paper["pmid"] == "999"
    assert paper["doi"] == "10.1000/example"
    assert paper["title"] == "Test PMC Title"
    assert paper["authors"] == ["Author A", "Author B"]
    assert paper["year"] == "2024"
    assert paper["citations"] == 5
    assert paper["url"].endswith("/PMC123/")


@pytest.mark.unit
def test_pmc_search_include_abstract_enriches_from_pubmed(monkeypatch):
    tool = PMCTool({"name": "PMC_search_papers"})

    pmc_xml_payload = """<?xml version="1.0" encoding="UTF-8"?>
<eSummaryResult>
  <DocSum>
    <Id>123</Id>
    <Item Name="Title" Type="String">Test PMC Title</Item>
    <Item Name="ArticleIds" Type="List">
      <Item Name="pubmed" Type="String">999</Item>
      <Item Name="pmc" Type="String">123</Item>
    </Item>
  </DocSum>
</eSummaryResult>
"""

    pubmed_xml_payload = """<?xml version="1.0" encoding="UTF-8"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>999</PMID>
      <Article>
        <Abstract>
          <AbstractText>Example abstract text.</AbstractText>
        </Abstract>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
"""

    def fake_request_with_retry(
        session,
        method,
        url,
        *,
        params=None,
        timeout=None,
        max_attempts=None,
        **kwargs,
    ):
        if url.endswith("/esearch.fcgi"):
            return _FakeResponse(
                status_code=200,
                json_payload={"esearchresult": {"idlist": ["123"]}},
                url=url,
            )
        if url.endswith("/esummary.fcgi"):
            return _FakeResponse(status_code=200, text=pmc_xml_payload, url=url)
        if url.endswith("/efetch.fcgi"):
            assert params.get("db") == "pubmed"
            assert params.get("id") == "999"
            return _FakeResponse(status_code=200, text=pubmed_xml_payload, url=url)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(
        "tooluniverse.pmc_tool.request_with_retry", fake_request_with_retry
    )

    results = tool.run({"query": "x", "limit": 1, "include_abstract": True})

    assert len(results) == 1
    assert results[0]["pmid"] == "999"
    assert results[0]["abstract"] == "Example abstract text."
    assert results[0]["abstract_source"] == "PubMed"


@pytest.mark.unit
def test_pmc_search_include_abstract_handles_inline_xml_tags(monkeypatch):
    tool = PMCTool({"name": "PMC_search_papers"})

    pmc_xml_payload = """<?xml version="1.0" encoding="UTF-8"?>
<eSummaryResult>
  <DocSum>
    <Id>123</Id>
    <Item Name="Title" Type="String">Test PMC Title</Item>
    <Item Name="ArticleIds" Type="List">
      <Item Name="pubmed" Type="String">999</Item>
      <Item Name="pmc" Type="String">123</Item>
    </Item>
  </DocSum>
</eSummaryResult>
"""

    pubmed_xml_payload = """<?xml version="1.0" encoding="UTF-8"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>999</PMID>
      <Article>
        <Abstract>
          <AbstractText>Alpha <b>bold</b> omega.</AbstractText>
        </Abstract>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
"""

    def fake_request_with_retry(
        session,
        method,
        url,
        *,
        params=None,
        timeout=None,
        max_attempts=None,
        **kwargs,
    ):
        if url.endswith("/esearch.fcgi"):
            return _FakeResponse(
                status_code=200,
                json_payload={"esearchresult": {"idlist": ["123"]}},
                url=url,
            )
        if url.endswith("/esummary.fcgi"):
            return _FakeResponse(status_code=200, text=pmc_xml_payload, url=url)
        if url.endswith("/efetch.fcgi"):
            return _FakeResponse(status_code=200, text=pubmed_xml_payload, url=url)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(
        "tooluniverse.pmc_tool.request_with_retry", fake_request_with_retry
    )

    results = tool.run({"query": "x", "limit": 1, "include_abstract": True})

    assert results[0]["abstract"] == "Alpha bold omega."
