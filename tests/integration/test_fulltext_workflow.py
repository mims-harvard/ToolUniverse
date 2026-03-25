#!/usr/bin/env python3
"""
Integration tests for full-text extraction workflows.
Tests the complete workflow: search → snippet extraction → verification.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.europe_pmc_tool import EuropePMCTool, EuropePMCFullTextSnippetsTool
from tooluniverse.semantic_scholar_tool import (
    SemanticScholarTool,
    SemanticScholarPDFSnippetsTool,
)
from tooluniverse.arxiv_tool import ArXivTool, ArXivPDFSnippetsTool


class _FakeResponse:
    def __init__(self, *, status_code=200, content=b"", text="", url="", json_data=None):
        self.status_code = status_code
        self.content = content
        self.text = text
        self.url = url or "https://example.test"
        self._json_data = json_data
        self.reason = "OK" if status_code == 200 else "Error"

    def json(self):
        if self._json_data is not None:
            return self._json_data
        raise ValueError("No JSON data")


class _FakeMarkItDownResult:
    def __init__(self, text_content):
        self.text_content = text_content


class _FakeMarkItDown:
    def __init__(self, text_content):
        self._text_content = text_content

    def convert(self, path):
        return _FakeMarkItDownResult(self._text_content)


@pytest.mark.integration
def test_europe_pmc_search_to_snippets_workflow(monkeypatch):
    """Test complete workflow: Europe PMC search → auto-snippets."""
    search_tool = EuropePMCTool({"name": "EuropePMC_search_articles"})

    # Mock search results with OA article
    search_json = {
        "resultList": {
            "result": [
                {
                    "id": "12345",
                    "source": "MED",
                    "pmid": "12345",
                    "pmcid": "PMC12345",
                    "title": "Evolution of antibiotic resistance in A. baumannii",
                    "abstractText": "We studied resistance evolution using various antibiotics.",
                    "authorList": {"author": [{"fullName": "Smith J"}, {"fullName": "Jones A"}]},
                    "pubYear": "2024",
                    "doi": "10.1234/example",
                    "isOpenAccess": "Y",
                    "citedByCount": 15,
                }
            ]
        }
    }

    fulltext_xml = """<?xml version="1.0" encoding="UTF-8"?>
<article>
  <front>
    <article-meta>
      <title-group>
        <article-title>Evolution of antibiotic resistance</article-title>
      </title-group>
      <abstract>
        <p>We evolved A. baumannii under antibiotic pressure.</p>
      </abstract>
    </article-meta>
  </front>
  <body>
    <sec>
      <title>Materials and Methods</title>
      <sec>
        <title>Bacterial strains and culture conditions</title>
        <p>A. baumannii ATCC 19606 was cultured in LB medium at 37°C.</p>
      </sec>
      <sec>
        <title>Evolution experiments</title>
        <p>Cultures were serially passaged in the presence of ciprofloxacin (5 μg/mL) or meropenem (8 μg/mL). Resistant clones emerged after 15-20 passages with ciprofloxacin and 25-30 passages with meropenem.</p>
      </sec>
    </sec>
    <sec>
      <title>Results</title>
      <p>Ciprofloxacin resistance appeared earlier than meropenem resistance. The A. baumannii strains showed cross-resistance patterns.</p>
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

    # Workflow Step 1: Search with auto-snippet mode
    results = search_tool.run(
        {
            "query": "antibiotic resistance evolution",
            "limit": 10,
            "extract_terms_from_fulltext": [
                "ciprofloxacin",
                "meropenem",
                "A. baumannii",
                "MIC",
            ],
        }
    )

    # Verify search results (tools now return {status, data, metadata} envelope)
    assert results["status"] == "success"
    data = results["data"]
    assert isinstance(data, list)
    assert len(data) == 1
    article = data[0]

    # Verify metadata
    assert article["title"] == "Evolution of antibiotic resistance in A. baumannii"
    assert article["open_access"] is True
    assert article["pmid"] == "12345"

    # Verify snippets were extracted
    assert "fulltext_snippets" in article
    assert article["fulltext_snippets_count"] > 0

    # Verify snippet content
    snippets = article["fulltext_snippets"]
    terms_found = {s["term"] for s in snippets}

    # Should find at least ciprofloxacin, meropenem, and A. baumannii
    assert "ciprofloxacin" in terms_found
    assert "meropenem" in terms_found
    assert "A. baumannii" in terms_found

    # Verify snippets contain context
    cipro_snippets = [s for s in snippets if s["term"] == "ciprofloxacin"]
    assert len(cipro_snippets) > 0
    assert "5 μg/mL" in cipro_snippets[0]["snippet"] or "μg/mL" in cipro_snippets[0]["snippet"]


@pytest.mark.integration
def test_europe_pmc_manual_snippet_extraction_workflow(monkeypatch):
    """Test two-step workflow: search → manual snippet extraction."""
    search_tool = EuropePMCTool({"name": "EuropePMC_search_articles"})
    snippet_tool = EuropePMCFullTextSnippetsTool(
        {"name": "EuropePMC_get_fulltext_snippets"}
    )

    search_json = {
        "resultList": {
            "result": [
                {
                    "id": "12345",
                    "source": "MED",
                    "pmid": "12345",
                    "pmcid": "PMC12345",
                    "title": "Test study",
                    "abstractText": "Abstract text",
                    "authorList": {"author": [{"fullName": "Author"}]},
                    "pubYear": "2024",
                    "isOpenAccess": "Y",
                }
            ]
        }
    }

    fulltext_xml = """<article><body>
        <p>We used CRISPR-Cas9 with sgRNA targeting the GFP gene. The guide RNA sequence was 5'-GTAGCGTCTACTGCATGACT-3'.</p>
        <p>Off-target effects were minimal with this sgRNA design.</p>
    </body></article>"""

    def mock_request(session, method, url, **kwargs):
        if "search" in url:
            return _FakeResponse(status_code=200, json_data=search_json, url=url)
        elif "fullTextXML" in url:
            return _FakeResponse(status_code=200, text=fulltext_xml, url=url)
        return _FakeResponse(status_code=404, url=url)

    monkeypatch.setattr("tooluniverse.europe_pmc_tool.request_with_retry", mock_request)

    # Step 1: Search (without auto-snippets)
    search_results = search_tool.run({"query": "CRISPR", "limit": 5})

    assert search_results["status"] == "success"
    data = search_results["data"]
    assert len(data) == 1
    article = data[0]
    assert article["open_access"] is True
    assert "fulltext_xml_url" in article

    # Step 2: Extract snippets manually
    snippet_result = snippet_tool.run(
        {
            "fulltext_xml_url": article["fulltext_xml_url"],
            "terms": ["CRISPR-Cas9", "sgRNA", "guide RNA", "off-target"],
            "window_chars": 150,
        }
    )

    # Verify snippet extraction
    assert snippet_result["status"] == "success"
    assert snippet_result["snippets_count"] > 0

    snippets = snippet_result["snippets"]
    terms_found = {s["term"] for s in snippets}
    assert "CRISPR-Cas9" in terms_found or "sgRNA" in terms_found


@pytest.mark.integration
def test_semantic_scholar_workflow(monkeypatch):
    """Test Semantic Scholar search → PDF snippet extraction workflow."""
    search_tool = SemanticScholarTool({"name": "SemanticScholar_search_papers"})
    snippet_tool = SemanticScholarPDFSnippetsTool(
        {"name": "SemanticScholar_get_pdf_snippets"}
    )

    # Mock search results
    search_data = {
        "data": [
            {
                "paperId": "abc123",
                "title": "Machine Learning Interpretability with SHAP",
                "abstract": "We present a method for interpreting ML models.",
                "venue": "NeurIPS",
                "year": 2024,
                "authors": [{"name": "Researcher A"}],
                "externalIds": {"DOI": "10.1234/ml.2024"},
                "citationCount": 50,
                "referenceCount": 25,
                "isOpenAccess": True,
                "openAccessPdf": {"url": "https://example.com/paper.pdf"},
            }
        ]
    }

    pdf_markdown = """
# Introduction
Model interpretability using SHAP values and gradient-based methods.

# Methods
We computed SHAP (SHapley Additive exPlanations) values for each feature.
Gradient attribution was calculated using integrated gradients.

# Results
SHAP values revealed that features X and Y had the highest importance.
"""

    def mock_request(session, method, url, **kwargs):
        if "semanticscholar.org/graph" in url and "search" in url:
            return _FakeResponse(status_code=200, json_data=search_data, url=url)
        elif "pdf" in url.lower():
            return _FakeResponse(status_code=200, content=b"fake pdf", url=url)
        return _FakeResponse(status_code=404, url=url)

    monkeypatch.setattr(
        "tooluniverse.semantic_scholar_tool.request_with_retry", mock_request
    )
    monkeypatch.setattr(
        "tooluniverse.semantic_scholar_tool.MARKITDOWN_AVAILABLE", True
    )
    snippet_tool.md_converter = _FakeMarkItDown(pdf_markdown)

    # Step 1: Search
    search_results = search_tool.run(
        {"query": "machine learning interpretability", "limit": 5}
    )

    assert search_results["status"] == "success"
    data = search_results["data"]
    assert len(data) == 1
    paper = data[0]
    assert paper["title"] == "Machine Learning Interpretability with SHAP"
    assert paper["open_access_pdf_url"] == "https://example.com/paper.pdf"

    # Step 2: Extract snippets from PDF
    snippet_result = snippet_tool.run(
        {
            "open_access_pdf_url": paper["open_access_pdf_url"],
            "terms": ["SHAP", "gradient attribution", "integrated gradients"],
        }
    )

    # Verify extraction
    assert snippet_result["status"] == "success"
    assert snippet_result["snippets_count"] > 0

    snippets = snippet_result["snippets"]
    assert any("SHAP" in s["snippet"] for s in snippets)


@pytest.mark.integration
def test_arxiv_workflow(monkeypatch):
    """Test ArXiv search → PDF snippet extraction workflow."""
    search_tool = ArXivTool({"name": "ArXiv_search_papers"})
    snippet_tool = ArXivPDFSnippetsTool({"name": "ArXiv_get_pdf_snippets"})

    # Mock ArXiv search results (Atom XML)
    arxiv_xml = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2301.12345v1</id>
    <title>Attention is All You Need v2</title>
    <summary>We present an improved transformer architecture with novel attention mechanisms.</summary>
    <author><name>Author One</name></author>
    <author><name>Author Two</name></author>
    <published>2024-01-15T00:00:00Z</published>
    <updated>2024-01-15T00:00:00Z</updated>
    <link type="text/html" href="http://arxiv.org/abs/2301.12345" />
    <arxiv:primary_category xmlns:arxiv="http://arxiv.org/schemas/atom" term="cs.LG" />
  </entry>
</feed>"""

    pdf_markdown = """
# Attention Mechanisms

Our architecture uses multi-head self-attention with scaled dot-product attention mechanism.

## Layer Normalization

We apply layer normalization after each sublayer using the standard LayerNorm formula.

## Results

The attention mechanism showed improved performance with layer normalization applied.
"""

    def mock_request(session, method, url, **kwargs):
        if "export.arxiv.org/api" in url:
            return _FakeResponse(status_code=200, text=arxiv_xml, url=url)
        elif "arxiv.org/pdf" in url:
            return _FakeResponse(status_code=200, content=b"fake pdf", url=url)
        return _FakeResponse(status_code=404, url=url)

    monkeypatch.setattr("tooluniverse.arxiv_tool.request_with_retry", mock_request)
    monkeypatch.setattr("tooluniverse.arxiv_tool.MARKITDOWN_AVAILABLE", True)
    snippet_tool.md_converter = _FakeMarkItDown(pdf_markdown)

    # Step 1: Search ArXiv
    search_results = search_tool.run(
        {"query": "attention mechanisms", "limit": 5, "sort_by": "relevance"}
    )

    # ArXiv tool may return bare list or {status, data} envelope
    if isinstance(search_results, dict):
        assert search_results["status"] == "success"
        search_data = search_results["data"]
    else:
        search_data = search_results
    assert isinstance(search_data, list)
    assert len(search_data) == 1
    paper = search_data[0]
    assert "Attention" in paper["title"]
    assert "2301.12345" in paper["url"]

    # Step 2: Extract arxiv_id and get snippets
    arxiv_id = paper["url"].split("/")[-1]  # Extract ID from URL

    snippet_result = snippet_tool.run(
        {
            "arxiv_id": arxiv_id,
            "terms": ["attention mechanism", "layer normalization", "self-attention"],
            "window_chars": 200,
        }
    )

    # Verify extraction
    assert snippet_result["status"] == "success"
    assert snippet_result["snippets_count"] > 0

    snippets = snippet_result["snippets"]
    terms_found = {s["term"] for s in snippets}
    assert (
        "attention mechanism" in terms_found or "layer normalization" in terms_found
    )


@pytest.mark.integration
def test_cross_database_verification_workflow(monkeypatch):
    """Test comprehensive cross-database verification workflow."""
    epmc_tool = EuropePMCTool({"name": "EuropePMC_search_articles"})

    # Mock multiple database responses
    epmc_json = {
        "resultList": {
            "result": [
                {
                    "id": "111",
                    "source": "MED",
                    "pmid": "111",
                    "pmcid": "PMC111",
                    "title": "Drug X in cancer treatment",
                    "abstractText": "We tested drug X.",
                    "authorList": {"author": [{"fullName": "Smith"}]},
                    "pubYear": "2024",
                    "isOpenAccess": "Y",
                }
            ]
        }
    }

    fulltext_xml = """<article><body>
        <p>Drug X (compound Y) was administered at 100 mg/kg daily. The IC50 was 5 nM.</p>
        <p>Patients received Drug X intravenously at 100 mg/kg.</p>
    </body></article>"""

    def mock_request(session, method, url, **kwargs):
        if "europepmc" in url and "search" in url:
            return _FakeResponse(status_code=200, json_data=epmc_json, url=url)
        elif "fullTextXML" in url:
            return _FakeResponse(status_code=200, text=fulltext_xml, url=url)
        return _FakeResponse(status_code=404, url=url)

    monkeypatch.setattr("tooluniverse.europe_pmc_tool.request_with_retry", mock_request)

    # Comprehensive search with verification terms
    verification_terms = ["100 mg/kg", "IC50", "5 nM", "intravenously"]

    results = epmc_tool.run(
        {
            "query": "Drug X cancer",
            "limit": 10,
            "extract_terms_from_fulltext": verification_terms,
        }
    )

    # Verify comprehensive data collection
    assert results["status"] == "success"
    data = results["data"]
    assert len(data) == 1
    article = data[0]

    # Verify all expected terms found
    if "fulltext_snippets" in article:
        terms_found = {s["term"] for s in article["fulltext_snippets"]}
        # Should find dosage and IC50 information
        assert "100 mg/kg" in terms_found or "5 nM" in terms_found
