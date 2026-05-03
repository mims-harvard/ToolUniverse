#!/usr/bin/env python3
"""
Unit tests for Europe PMC auto-snippet mode (extract_terms_from_fulltext parameter).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.europe_pmc_tool import EuropePMCTool


class _FakeResponse:
    def __init__(self, *, status_code=200, text="", url="", json_data=None):
        self.status_code = status_code
        self.text = text
        self.url = url or "https://example.test"
        self._json_data = json_data

    def json(self):
        if self._json_data is not None:
            return self._json_data
        raise ValueError("No JSON data")


@pytest.mark.unit
def test_europe_pmc_auto_snippets_basic(monkeypatch):
    """Test basic auto-snippet extraction with OA articles."""
    tool = EuropePMCTool({"name": "EuropePMC_search_articles"})

    # Mock search response with 2 OA articles
    search_json = {
        "resultList": {
            "result": [
                {
                    "id": "12345",
                    "source": "MED",
                    "pmid": "12345",
                    "pmcid": "PMC12345",
                    "title": "Study on antibiotic resistance",
                    "abstractText": "We studied resistance evolution.",
                    "authorList": {"author": [{"fullName": "Smith J"}]},
                    "pubYear": "2023",
                    "doi": "10.1234/test",
                    "isOpenAccess": "Y",
                    "citedByCount": 10,
                },
                {
                    "id": "67890",
                    "source": "MED",
                    "pmid": "67890",
                    "pmcid": "PMC67890",
                    "title": "Another resistance study",
                    "abstractText": "We studied more resistance.",
                    "authorList": {"author": [{"fullName": "Jones A"}]},
                    "pubYear": "2024",
                    "doi": "10.1234/test2",
                    "isOpenAccess": "Y",
                    "citedByCount": 5,
                },
            ]
        }
    }

    fulltext_xml = """<?xml version="1.0" encoding="UTF-8"?>
<article>
  <front>
    <article-meta>
      <title-group>
        <article-title>Test Article</article-title>
      </title-group>
    </article-meta>
  </front>
  <body>
    <sec>
      <title>Methods</title>
      <p>We used ciprofloxacin at 5 μg/mL and meropenem at 8 μg/mL to select for resistance in A. baumannii cultures.</p>
    </sec>
    <sec>
      <title>Results</title>
      <p>Ciprofloxacin resistance emerged after 10 passages. Meropenem resistance took longer.</p>
    </sec>
  </body>
</article>
"""

    call_count = {"search": 0, "fulltext": 0}

    def mock_request(session, method, url, **kwargs):
        if "search" in url:
            call_count["search"] += 1
            return _FakeResponse(status_code=200, json_data=search_json, url=url)
        elif "fullTextXML" in url:
            call_count["fulltext"] += 1
            return _FakeResponse(status_code=200, text=fulltext_xml, url=url)
        return _FakeResponse(status_code=404, url=url)

    monkeypatch.setattr("tooluniverse.europe_pmc_tool.request_with_retry", mock_request)

    # Run search with auto-snippet mode
    results = tool.run(
        {
            "query": "antibiotic resistance",
            "limit": 5,
            "extract_terms_from_fulltext": ["ciprofloxacin", "meropenem", "A. baumannii"],
        }
    )

    # Verify results
    assert isinstance(results, list)
    assert len(results) == 2
    assert call_count["search"] == 2  # Core + lite mode
    assert call_count["fulltext"] >= 1  # At least one fulltext fetch

    # Check first article has snippets
    article1 = results[0]
    assert "fulltext_snippets" in article1
    assert article1["fulltext_snippets_count"] > 0

    # Verify snippets contain our terms
    snippets = article1["fulltext_snippets"]
    terms_found = {s["term"] for s in snippets}
    assert "ciprofloxacin" in terms_found
    assert any("ciprofloxacin" in s["snippet"].lower() for s in snippets)


@pytest.mark.unit
def test_europe_pmc_auto_snippets_no_oa(monkeypatch):
    """Test that non-OA articles don't get snippet extraction."""
    tool = EuropePMCTool({"name": "EuropePMC_search_articles"})

    # Mock search response with non-OA article
    search_json = {
        "resultList": {
            "result": [
                {
                    "id": "12345",
                    "source": "MED",
                    "pmid": "12345",
                    "title": "Paywalled study",
                    "abstractText": "Abstract only.",
                    "authorList": {"author": [{"fullName": "Smith J"}]},
                    "pubYear": "2023",
                    "doi": "10.1234/test",
                    "isOpenAccess": "N",  # Not OA
                    "citedByCount": 10,
                }
            ]
        }
    }

    call_count = {"search": 0, "fulltext": 0}

    def mock_request(session, method, url, **kwargs):
        if "search" in url:
            call_count["search"] += 1
            return _FakeResponse(status_code=200, json_data=search_json, url=url)
        elif "fullTextXML" in url:
            call_count["fulltext"] += 1
            return _FakeResponse(status_code=200, text="<article></article>", url=url)
        return _FakeResponse(status_code=404, url=url)

    monkeypatch.setattr("tooluniverse.europe_pmc_tool.request_with_retry", mock_request)

    # Run search with auto-snippet mode
    results = tool.run(
        {
            "query": "antibiotic resistance",
            "limit": 5,
            "extract_terms_from_fulltext": ["ciprofloxacin"],
        }
    )

    # Verify no fulltext was fetched (article not OA)
    assert isinstance(results, list)
    assert len(results) == 1
    assert call_count["fulltext"] == 0  # No fulltext fetch for non-OA
    assert "fulltext_snippets" not in results[0]


@pytest.mark.unit
def test_europe_pmc_auto_snippets_max_articles(monkeypatch):
    """Test that auto-snippet mode respects max 3 articles limit."""
    tool = EuropePMCTool({"name": "EuropePMC_search_articles"})

    # Mock search response with 5 OA articles
    search_json = {
        "resultList": {
            "result": [
                {
                    "id": str(i),
                    "source": "MED",
                    "pmid": str(i),
                    "pmcid": f"PMC{i}",
                    "title": f"Study {i}",
                    "abstractText": f"Abstract {i}",
                    "authorList": {"author": [{"fullName": f"Author {i}"}]},
                    "pubYear": "2023",
                    "isOpenAccess": "Y",
                    "citedByCount": 1,
                }
                for i in range(1, 6)
            ]
        }
    }

    fulltext_xml = "<article><body><p>ciprofloxacin test</p></body></article>"
    call_count = {"search": 0, "fulltext": 0}

    def mock_request(session, method, url, **kwargs):
        if "search" in url:
            call_count["search"] += 1
            return _FakeResponse(status_code=200, json_data=search_json, url=url)
        elif "fullTextXML" in url:
            call_count["fulltext"] += 1
            return _FakeResponse(status_code=200, text=fulltext_xml, url=url)
        return _FakeResponse(status_code=404, url=url)

    monkeypatch.setattr("tooluniverse.europe_pmc_tool.request_with_retry", mock_request)

    # Run search with auto-snippet mode
    results = tool.run(
        {
            "query": "test",
            "limit": 10,
            "extract_terms_from_fulltext": ["ciprofloxacin"],
        }
    )

    # Verify only 3 fulltext fetches (max limit)
    assert isinstance(results, list)
    assert len(results) == 5
    assert call_count["fulltext"] <= 3  # Max 3 articles processed

    # Count how many articles got snippets
    with_snippets = [r for r in results if "fulltext_snippets" in r]
    assert len(with_snippets) <= 3


@pytest.mark.unit
def test_europe_pmc_auto_snippets_no_terms(monkeypatch):
    """Test that search works normally when no terms provided."""
    tool = EuropePMCTool({"name": "EuropePMC_search_articles"})

    search_json = {
        "resultList": {
            "result": [
                {
                    "id": "12345",
                    "source": "MED",
                    "pmid": "12345",
                    "title": "Test",
                    "abstractText": "Abstract",
                    "authorList": {"author": [{"fullName": "Author"}]},
                    "pubYear": "2023",
                    "isOpenAccess": "Y",
                }
            ]
        }
    }

    def mock_request(session, method, url, **kwargs):
        if "search" in url:
            return _FakeResponse(status_code=200, json_data=search_json, url=url)
        return _FakeResponse(status_code=404, url=url)

    monkeypatch.setattr("tooluniverse.europe_pmc_tool.request_with_retry", mock_request)

    # Run search WITHOUT extract_terms_from_fulltext
    results = tool.run({"query": "test", "limit": 5})

    # Should work normally, no snippets
    assert isinstance(results, list)
    assert len(results) == 1
    assert "fulltext_snippets" not in results[0]


@pytest.mark.unit
def test_europe_pmc_auto_snippets_more_than_5_terms(monkeypatch):
    """Test that >5 terms are auto-chunked in batches of 5, not rejected or truncated."""
    tool = EuropePMCTool({"name": "EuropePMC_search_articles"})

    search_json = {
        "resultList": {
            "result": [
                {
                    "id": "12345",
                    "source": "MED",
                    "pmid": "12345",
                    "pmcid": "PMC12345",
                    "title": "Multi-drug resistance study",
                    "abstractText": "We studied multiple antibiotics.",
                    "authorList": {"author": [{"fullName": "Smith J"}]},
                    "pubYear": "2023",
                    "doi": "10.1234/test",
                    "isOpenAccess": "Y",
                    "citedByCount": 10,
                }
            ]
        }
    }

    fulltext_xml = """<?xml version="1.0" encoding="UTF-8"?>
<article>
  <body>
    <sec>
      <title>Methods</title>
      <p>We tested ciprofloxacin, meropenem, amoxicillin, tetracycline, and
      erythromycin. We also evaluated gentamicin, rifampicin, and vancomycin
      for synergistic effects.</p>
    </sec>
  </body>
</article>
"""

    def mock_request(session, method, url, **kwargs):
        if "search" in url:
            return _FakeResponse(status_code=200, json_data=search_json, url=url)
        elif "fullTextXML" in url:
            return _FakeResponse(status_code=200, text=fulltext_xml, url=url)
        return _FakeResponse(status_code=404, url=url)

    monkeypatch.setattr("tooluniverse.europe_pmc_tool.request_with_retry", mock_request)

    # Pass 8 terms -- more than the old max of 5
    eight_terms = [
        "ciprofloxacin",
        "meropenem",
        "amoxicillin",
        "tetracycline",
        "erythromycin",
        "gentamicin",
        "rifampicin",
        "vancomycin",
    ]
    results = tool.run(
        {
            "query": "multi-drug resistance",
            "limit": 5,
            "extract_terms_from_fulltext": eight_terms,
        }
    )

    assert isinstance(results, list)
    assert len(results) == 1

    article = results[0]
    assert "fulltext_snippets" in article
    assert article["fulltext_snippets_count"] > 0

    # Verify terms from BOTH batches (batch 1: first 5, batch 2: last 3) are found
    terms_found = {s["term"] for s in article["fulltext_snippets"]}
    # At minimum, terms from the second batch (beyond index 5) must appear
    assert "gentamicin" in terms_found, "Term from 2nd batch was not extracted"
    assert "rifampicin" in terms_found, "Term from 2nd batch was not extracted"
    assert "vancomycin" in terms_found, "Term from 2nd batch was not extracted"


@pytest.mark.unit
def test_europe_pmc_auto_snippets_empty_terms(monkeypatch):
    """Test handling of empty/invalid terms list."""
    tool = EuropePMCTool({"name": "EuropePMC_search_articles"})

    search_json = {
        "resultList": {
            "result": [
                {
                    "id": "12345",
                    "source": "MED",
                    "pmid": "12345",
                    "title": "Test",
                    "abstractText": "Abstract",
                    "authorList": {"author": [{"fullName": "Author"}]},
                    "pubYear": "2023",
                    "isOpenAccess": "Y",
                }
            ]
        }
    }

    def mock_request(session, method, url, **kwargs):
        if "search" in url:
            return _FakeResponse(status_code=200, json_data=search_json, url=url)
        return _FakeResponse(status_code=404, url=url)

    monkeypatch.setattr("tooluniverse.europe_pmc_tool.request_with_retry", mock_request)

    # Run with empty terms list
    results = tool.run(
        {"query": "test", "limit": 5, "extract_terms_from_fulltext": []}
    )

    # Should work normally, no snippet extraction attempted
    assert isinstance(results, list)
    assert len(results) == 1
    assert "fulltext_snippets" not in results[0]
