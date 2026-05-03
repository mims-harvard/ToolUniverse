#!/usr/bin/env python3
"""
Unit tests for PubMed search include_abstract enrichment.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.pubmed_tool import PubMedRESTTool


class _FakeResponse:
    def __init__(
        self, *, status_code=200, json_payload=None, text="", url="", reason=""
    ):
        self.status_code = status_code
        self._json_payload = json_payload
        self.text = text
        self.url = url or "https://example.test"
        self.reason = reason

    def json(self):
        if self._json_payload is None:
            raise ValueError("No JSON payload")
        return self._json_payload


def _make_tool():
    return PubMedRESTTool(
        {
            "name": "PubMed_search_articles",
            "fields": {
                "endpoint": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            },
        }
    )


@pytest.mark.unit
def test_pubmed_search_include_abstract_adds_abstract(monkeypatch):
    tool = _make_tool()
    monkeypatch.setattr(tool, "_enforce_rate_limit", lambda has_api_key: None)

    esearch_payload = {"esearchresult": {"idlist": ["1"]}}
    esummary_payload = {
        "result": {
            "1": {
                "title": "Example article",
                "authors": [{"name": "Author A"}],
                "pubdate": "2024 Jan 01",
                "elocationid": "doi: 10.1000/example",
                "fulljournalname": "Example Journal",
                "articleids": [{"idtype": "pmc", "value": "12345"}],
                "pubtype": ["Journal Article"],
            }
        }
    }

    efetch_xml = """<?xml version="1.0" encoding="UTF-8"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>1</PMID>
      <Article>
        <Abstract>
          <AbstractText>Abstract text.</AbstractText>
        </Abstract>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
"""

    def fake_request_with_retry(session, method, url, *, params=None, **kwargs):
        if url.endswith("/esearch.fcgi"):
            return _FakeResponse(status_code=200, json_payload=esearch_payload, url=url)
        if url.endswith("/esummary.fcgi"):
            return _FakeResponse(
                status_code=200, json_payload=esummary_payload, url=url
            )
        if url.endswith("/efetch.fcgi"):
            assert params.get("db") == "pubmed"
            assert params.get("id") == "1"
            return _FakeResponse(status_code=200, text=efetch_xml, url=url)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(
        "tooluniverse.pubmed_tool.request_with_retry", fake_request_with_retry
    )

    result = tool.run({"query": "x", "limit": 1, "include_abstract": True})

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["pmid"] == "1"
    assert result[0]["abstract"] == "Abstract text."
    assert result[0]["abstract_source"] == "PubMed"
    assert result[0]["doi_url"] == "https://doi.org/10.1000/example"
    assert result[0]["pmc_url"].endswith("/PMC12345/")


@pytest.mark.unit
def test_pubmed_search_include_abstract_handles_inline_xml_tags(monkeypatch):
    tool = _make_tool()
    monkeypatch.setattr(tool, "_enforce_rate_limit", lambda has_api_key: None)

    esearch_payload = {"esearchresult": {"idlist": ["1"]}}
    esummary_payload = {
        "result": {
            "1": {
                "title": "Example article",
                "authors": [{"name": "Author A"}],
                "pubdate": "2024 Jan 01",
                "elocationid": "doi: 10.1000/example",
                "fulljournalname": "Example Journal",
                "articleids": [],
                "pubtype": ["Journal Article"],
            }
        }
    }

    efetch_xml = """<?xml version="1.0" encoding="UTF-8"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>1</PMID>
      <Article>
        <Abstract>
          <AbstractText>First <i>italic</i> second.</AbstractText>
        </Abstract>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
"""

    def fake_request_with_retry(session, method, url, *, params=None, **kwargs):
        if url.endswith("/esearch.fcgi"):
            return _FakeResponse(status_code=200, json_payload=esearch_payload, url=url)
        if url.endswith("/esummary.fcgi"):
            return _FakeResponse(
                status_code=200, json_payload=esummary_payload, url=url
            )
        if url.endswith("/efetch.fcgi"):
            return _FakeResponse(status_code=200, text=efetch_xml, url=url)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(
        "tooluniverse.pubmed_tool.request_with_retry", fake_request_with_retry
    )

    result = tool.run({"query": "x", "limit": 1, "include_abstract": True})

    assert result[0]["abstract"] == "First italic second."
