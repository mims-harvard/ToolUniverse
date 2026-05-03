#!/usr/bin/env python3
"""
Unit tests for PDF snippet extraction tools (Semantic Scholar and ArXiv).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.semantic_scholar_tool import SemanticScholarPDFSnippetsTool
from tooluniverse.arxiv_tool import ArXivPDFSnippetsTool


class _FakeResponse:
    def __init__(self, *, status_code=200, content=b"", text="", url="", json_data=None):
        self.status_code = status_code
        self.content = content
        self.text = text
        self.url = url or "https://example.test"
        self._json_data = json_data

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


# Semantic Scholar PDF Snippets Tests

@pytest.mark.unit
def test_semantic_scholar_pdf_snippets_basic(monkeypatch, tmp_path):
    """Test basic PDF snippet extraction from Semantic Scholar."""
    tool = SemanticScholarPDFSnippetsTool({"name": "SemanticScholar_get_pdf_snippets"})

    # Mock PDF content and markitdown conversion
    fake_markdown = """
# Introduction
Machine learning models using SHAP values and gradient-based attribution methods.

# Methods
We used SHAP (SHapley Additive exPlanations) for feature importance and gradient attribution for visualization.

# Results
The SHAP values showed high importance for features X and Y.
"""

    def mock_request(session, method, url, **kwargs):
        return _FakeResponse(status_code=200, content=b"fake pdf content", url=url)

    monkeypatch.setattr(
        "tooluniverse.semantic_scholar_tool.request_with_retry", mock_request
    )
    monkeypatch.setattr(
        "tooluniverse.semantic_scholar_tool.MARKITDOWN_AVAILABLE", True
    )
    tool.md_converter = _FakeMarkItDown(fake_markdown)

    # Run snippet extraction
    result = tool.run(
        {
            "open_access_pdf_url": "https://example.com/paper.pdf",
            "terms": ["SHAP", "gradient attribution"],
            "window_chars": 100,
        }
    )

    # Verify success
    assert result["status"] == "success"
    assert result["pdf_url"] == "https://example.com/paper.pdf"
    assert result["snippets_count"] > 0

    # Verify snippets contain terms
    snippets = result["snippets"]
    terms_found = {s["term"] for s in snippets}
    assert "SHAP" in terms_found
    assert any("SHAP" in s["snippet"] for s in snippets)


@pytest.mark.unit
def test_semantic_scholar_pdf_snippets_from_paper_id(monkeypatch):
    """Test PDF snippet extraction using paper_id."""
    tool = SemanticScholarPDFSnippetsTool({"name": "SemanticScholar_get_pdf_snippets"})

    fake_markdown = "This paper discusses SHAP values in detail."

    def mock_request(session, method, url, **kwargs):
        if "semanticscholar.org/graph" in url:
            # Mock paper details API response
            return _FakeResponse(
                status_code=200,
                json_data={
                    "openAccessPdf": {"url": "https://example.com/paper.pdf"}
                },
                url=url,
            )
        else:
            # Mock PDF download
            return _FakeResponse(status_code=200, content=b"pdf", url=url)

    monkeypatch.setattr(
        "tooluniverse.semantic_scholar_tool.request_with_retry", mock_request
    )
    monkeypatch.setattr(
        "tooluniverse.semantic_scholar_tool.MARKITDOWN_AVAILABLE", True
    )
    tool.md_converter = _FakeMarkItDown(fake_markdown)

    # Run with paper_id instead of URL
    result = tool.run({"paper_id": "abc123", "terms": ["SHAP"]})

    # Verify success
    assert result["status"] == "success"
    assert "example.com/paper.pdf" in result["pdf_url"]


@pytest.mark.unit
def test_semantic_scholar_pdf_snippets_no_markitdown(monkeypatch):
    """Test error when markitdown is not available."""
    tool = SemanticScholarPDFSnippetsTool({"name": "SemanticScholar_get_pdf_snippets"})

    monkeypatch.setattr(
        "tooluniverse.semantic_scholar_tool.MARKITDOWN_AVAILABLE", False
    )
    tool.md_converter = None

    # Run should return error
    result = tool.run(
        {
            "open_access_pdf_url": "https://example.com/paper.pdf",
            "terms": ["SHAP"],
        }
    )

    # Verify error
    assert result["status"] == "error"
    assert "markitdown" in result["error"].lower()


@pytest.mark.unit
def test_semantic_scholar_pdf_snippets_invalid_terms():
    """Test error handling for invalid terms."""
    tool = SemanticScholarPDFSnippetsTool({"name": "SemanticScholar_get_pdf_snippets"})

    # Missing terms
    result = tool.run({"open_access_pdf_url": "https://example.com/paper.pdf"})
    assert result["status"] == "error"
    assert "terms" in result["error"].lower()

    # Empty terms list
    result = tool.run(
        {"open_access_pdf_url": "https://example.com/paper.pdf", "terms": []}
    )
    assert result["status"] == "error"


# ArXiv PDF Snippets Tests

@pytest.mark.unit
def test_arxiv_pdf_snippets_basic(monkeypatch):
    """Test basic PDF snippet extraction from ArXiv."""
    tool = ArXivPDFSnippetsTool({"name": "ArXiv_get_pdf_snippets"})

    fake_markdown = """
# Attention Mechanisms in Transformers
We introduce self-attention layers with layer normalization.

# Architecture
The attention mechanism computes weighted sums using softmax. Layer normalization is applied after each sublayer.
"""

    def mock_request(session, method, url, **kwargs):
        return _FakeResponse(status_code=200, content=b"fake pdf", url=url)

    monkeypatch.setattr("tooluniverse.arxiv_tool.request_with_retry", mock_request)
    monkeypatch.setattr("tooluniverse.arxiv_tool.MARKITDOWN_AVAILABLE", True)
    tool.md_converter = _FakeMarkItDown(fake_markdown)

    # Run with arxiv_id
    result = tool.run(
        {
            "arxiv_id": "2301.12345",
            "terms": ["attention mechanism", "layer normalization"],
        }
    )

    # Verify success
    assert result["status"] == "success"
    assert "arxiv.org/pdf/2301.12345.pdf" in result["pdf_url"]
    assert result["snippets_count"] > 0

    # Verify snippets
    snippets = result["snippets"]
    terms_found = {s["term"] for s in snippets}
    assert "attention mechanism" in terms_found or "layer normalization" in terms_found


@pytest.mark.unit
def test_arxiv_pdf_snippets_with_prefix():
    """Test handling of arXiv ID with 'arXiv:' prefix."""
    tool = ArXivPDFSnippetsTool({"name": "ArXiv_get_pdf_snippets"})

    # Mock to capture the URL built
    captured_url = []

    def mock_request(session, method, url, **kwargs):
        captured_url.append(url)
        return _FakeResponse(status_code=200, content=b"pdf", url=url)

    import tooluniverse.arxiv_tool as arxiv_module

    original_request = arxiv_module.request_with_retry
    arxiv_module.request_with_retry = mock_request

    try:
        # Test with various ID formats
        tool.md_converter = _FakeMarkItDown("test content")
        arxiv_module.MARKITDOWN_AVAILABLE = True

        tool.run({"arxiv_id": "arXiv:2301.12345v1", "terms": ["test"]})

        # Verify URL built correctly (strips prefix and version)
        assert len(captured_url) > 0
        assert "2301.12345.pdf" in captured_url[0]
        assert "v1" not in captured_url[0]
    finally:
        arxiv_module.request_with_retry = original_request


@pytest.mark.unit
def test_arxiv_pdf_snippets_with_url(monkeypatch):
    """Test using direct PDF URL instead of arxiv_id."""
    tool = ArXivPDFSnippetsTool({"name": "ArXiv_get_pdf_snippets"})

    fake_markdown = "Test content with attention mechanism."

    def mock_request(session, method, url, **kwargs):
        return _FakeResponse(status_code=200, content=b"pdf", url=url)

    monkeypatch.setattr("tooluniverse.arxiv_tool.request_with_retry", mock_request)
    monkeypatch.setattr("tooluniverse.arxiv_tool.MARKITDOWN_AVAILABLE", True)
    tool.md_converter = _FakeMarkItDown(fake_markdown)

    # Run with direct URL
    result = tool.run(
        {
            "pdf_url": "https://arxiv.org/pdf/2301.12345.pdf",
            "terms": ["attention mechanism"],
        }
    )

    # Verify success
    assert result["status"] == "success"
    assert result["pdf_url"] == "https://arxiv.org/pdf/2301.12345.pdf"


@pytest.mark.unit
def test_arxiv_pdf_snippets_no_markitdown(monkeypatch):
    """Test error when markitdown is not available."""
    tool = ArXivPDFSnippetsTool({"name": "ArXiv_get_pdf_snippets"})

    monkeypatch.setattr("tooluniverse.arxiv_tool.MARKITDOWN_AVAILABLE", False)
    tool.md_converter = None

    # Run should return error
    result = tool.run({"arxiv_id": "2301.12345", "terms": ["test"]})

    # Verify error
    assert result["status"] == "error"
    assert "markitdown" in result["error"].lower()


@pytest.mark.unit
def test_arxiv_pdf_snippets_download_failure(monkeypatch):
    """Test handling of PDF download failure."""
    tool = ArXivPDFSnippetsTool({"name": "ArXiv_get_pdf_snippets"})

    def mock_request(session, method, url, **kwargs):
        return _FakeResponse(status_code=404, url=url)

    monkeypatch.setattr("tooluniverse.arxiv_tool.request_with_retry", mock_request)
    monkeypatch.setattr("tooluniverse.arxiv_tool.MARKITDOWN_AVAILABLE", True)
    tool.md_converter = _FakeMarkItDown("test")

    # Run should return error
    result = tool.run({"arxiv_id": "9999.99999", "terms": ["test"]})

    # Verify error
    assert result["status"] == "error"
    assert result["status_code"] == 404


@pytest.mark.unit
def test_pdf_snippets_window_size_limits():
    """Test that window_chars parameter is properly bounded."""
    tool = ArXivPDFSnippetsTool({"name": "ArXiv_get_pdf_snippets"})

    # Test with extreme values - too small
    tool.run(
        {
            "arxiv_id": "2301.12345",
            "terms": ["test"],
            "window_chars": 5,  # Too small
        }
    )
    # Should be clamped to minimum (20)

    # Test with extreme values - too large
    tool.run(
        {
            "arxiv_id": "2301.12345",
            "terms": ["test"],
            "window_chars": 10000,  # Too large
        }
    )
    # Should be clamped to maximum (2000)
