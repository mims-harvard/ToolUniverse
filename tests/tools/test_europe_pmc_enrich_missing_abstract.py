#!/usr/bin/env python3
"""
Unit tests for Europe PMC enrich_missing_abstract (fullTextXML abstract fill).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.europe_pmc_tool import EuropePMCTool


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


@pytest.mark.unit
def test_europe_pmc_enrich_missing_abstract_fills_from_fulltext_xml(monkeypatch):
    tool = EuropePMCTool({"name": "EuropePMC_search_articles"})

    core_payload = {
        "resultList": {
            "result": [
                {
                    "title": "A title",
                    # abstractText intentionally missing
                    "pubYear": 2024,
                    "doi": "10.1000/example",
                    "source": "PMC",
                    "id": "123",
                    "pmcid": "PMC123",
                    "authorList": {"author": [{"fullName": "Author A"}]},
                }
            ]
        }
    }
    lite_payload = {"resultList": {"result": [{"id": "123", "journalTitle": "J"}]}}

    fulltext_xml = """<?xml version="1.0" encoding="UTF-8"?>
<article>
  <front>
    <abstract>
      <p>Filled abstract.</p>
    </abstract>
  </front>
</article>
"""

    def fake_request_with_retry(session, method, url, *, params=None, **kwargs):
        if url.endswith("/rest/search"):
            if params.get("resultType") == "core":
                return _FakeResponse(
                    status_code=200, json_payload=core_payload, url=url
                )
            if params.get("resultType") == "lite":
                return _FakeResponse(
                    status_code=200, json_payload=lite_payload, url=url
                )
        if url.endswith("/PMC123/fullTextXML"):
            return _FakeResponse(status_code=200, text=fulltext_xml, url=url)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(
        "tooluniverse.europe_pmc_tool.request_with_retry", fake_request_with_retry
    )

    result = tool.run({"query": "x", "limit": 1, "enrich_missing_abstract": True})

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["abstract"] == "Filled abstract."
    assert result[0]["abstract_source"] == "Europe PMC fullTextXML"
    assert result[0]["fulltext_xml_url"].endswith("/PMC123/fullTextXML")


@pytest.mark.unit
def test_europe_pmc_enrich_missing_abstract_falls_back_to_pmc_oai(monkeypatch):
    tool = EuropePMCTool({"name": "EuropePMC_search_articles"})

    core_payload = {
        "resultList": {
            "result": [
                {
                    "title": "A title",
                    # abstractText intentionally missing
                    "pubYear": 2024,
                    "doi": "10.1000/example",
                    "source": "PMC",
                    "id": "123",
                    "pmcid": "PMC123",
                    "authorList": {"author": [{"fullName": "Author A"}]},
                    "isOpenAccess": "Y",
                }
            ]
        }
    }
    lite_payload = {"resultList": {"result": [{"id": "123", "journalTitle": "J"}]}}

    oai_xml = """<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
  <GetRecord>
    <record>
      <metadata>
        <article>
          <front>
            <abstract><p>Filled abstract from OAI.</p></abstract>
          </front>
        </article>
      </metadata>
    </record>
  </GetRecord>
</OAI-PMH>
"""

    def fake_request_with_retry(session, method, url, *, params=None, **kwargs):
        if url.endswith("/rest/search"):
            if params.get("resultType") == "core":
                return _FakeResponse(status_code=200, json_payload=core_payload, url=url)
            if params.get("resultType") == "lite":
                return _FakeResponse(status_code=200, json_payload=lite_payload, url=url)
        # Europe PMC fullTextXML missing
        if url.endswith("/PMC123/fullTextXML"):
            return _FakeResponse(status_code=404, text="not found", url=url)
        # NCBI OAI fallback
        if "ncbi.nlm.nih.gov/pmc/oai/oai.cgi" in url:
            return _FakeResponse(status_code=200, text=oai_xml, url=url)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(
        "tooluniverse.europe_pmc_tool.request_with_retry", fake_request_with_retry
    )

    result = tool.run({"query": "x", "limit": 1, "enrich_missing_abstract": True})

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["abstract"] == "Filled abstract from OAI."
    assert result[0]["abstract_source"] == "NCBI PMC OAI (JATS)"
