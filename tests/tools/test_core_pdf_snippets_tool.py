#!/usr/bin/env python3
"""
Unit tests for CORE_get_fulltext_snippets (PDF snippet extraction).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.core_tool import CorePDFSnippetsTool


class _FakeResponse:
    def __init__(self, *, status_code=200, content=b"", url="", headers=None, text=""):
        self.status_code = status_code
        self.content = content
        self.url = url or "https://example.test/paper.pdf"
        self.headers = headers or {"content-type": "application/pdf"}
        self.text = text or (content.decode("utf-8", "ignore") if isinstance(content, (bytes, bytearray)) else "")


class _FakeMarkItDownResult:
    def __init__(self, text_content):
        self.text_content = text_content


class _FakeMarkItDown:
    def __init__(self, text_content):
        self._text_content = text_content

    def convert(self, path):
        return _FakeMarkItDownResult(self._text_content)


@pytest.mark.unit
def test_core_pdf_snippets_basic(monkeypatch):
    tool = CorePDFSnippetsTool({"name": "CORE_get_fulltext_snippets"})

    fake_markdown = "This PDF mentions rs738409 and rs58542926 in the methods."

    def mock_request(session, method, url, **kwargs):
        return _FakeResponse(status_code=200, content=b"%PDF-1.4 fake", url=url)

    monkeypatch.setattr("tooluniverse.core_tool.request_with_retry", mock_request)
    monkeypatch.setattr("tooluniverse.core_tool.MARKITDOWN_AVAILABLE", True)
    tool.md_converter = _FakeMarkItDown(fake_markdown)

    result = tool.run(
        {
            "pdf_url": "https://core.ac.uk/download/123.pdf",
            "terms": ["rs738409", "rs58542926"],
            "window_chars": 80,
            "extractor": "markitdown",
        }
    )

    assert result["status"] == "success"
    assert result["pdf_url"] == "https://core.ac.uk/download/123.pdf"
    assert result["snippets_count"] >= 2
    assert any("rs738409" in s["snippet"].lower() for s in result["snippets"])


@pytest.mark.unit
def test_core_pdf_snippets_accepts_url_alias(monkeypatch):
    tool = CorePDFSnippetsTool({"name": "CORE_get_fulltext_snippets"})

    def mock_request(session, method, url, **kwargs):
        return _FakeResponse(status_code=200, content=b"%PDF-1.4 fake", url=url)

    monkeypatch.setattr("tooluniverse.core_tool.request_with_retry", mock_request)
    monkeypatch.setattr("tooluniverse.core_tool.MARKITDOWN_AVAILABLE", True)
    tool.md_converter = _FakeMarkItDown("mentions epistasis")

    result = tool.run(
        {
            "url": "https://core.ac.uk/download/abc.pdf",
            "terms": ["epistasis"],
            "extractor": "markitdown",
        }
    )
    assert result["status"] == "success"
    assert result["pdf_url"] == "https://core.ac.uk/download/abc.pdf"


@pytest.mark.unit
def test_core_pdf_snippets_follows_html_pdf_link(monkeypatch):
    tool = CorePDFSnippetsTool({"name": "CORE_get_fulltext_snippets"})

    calls = []

    html = '<html><body><a href="real.pdf">PDF</a></body></html>'

    def mock_request(session, method, url, **kwargs):
        calls.append((method, url))
        if method == "HEAD":
            return _FakeResponse(status_code=200, content=b"", url=url, headers={"content-type": "text/html"})
        if url.endswith("real.pdf"):
            return _FakeResponse(status_code=200, content=b"%PDF-1.4 fake", url=url, headers={"content-type": "application/pdf"})
        return _FakeResponse(status_code=200, content=html.encode("utf-8"), text=html, url=url, headers={"content-type": "text/html"})

    monkeypatch.setattr("tooluniverse.core_tool.request_with_retry", mock_request)
    monkeypatch.setattr("tooluniverse.core_tool.MARKITDOWN_AVAILABLE", True)
    tool.md_converter = _FakeMarkItDown("mentions hypertension and epistasis")

    result = tool.run(
        {
            "pdf_url": "https://example.test/landing",
            "terms": ["epistasis"],
            "extractor": "markitdown",
            "timeout": 5,
        }
    )

    assert result["status"] == "success"
    assert result["snippets_count"] >= 1
    assert any(c[1].endswith("real.pdf") for c in calls)


@pytest.mark.unit
def test_core_pdf_snippets_no_markitdown(monkeypatch):
    tool = CorePDFSnippetsTool({"name": "CORE_get_fulltext_snippets"})

    monkeypatch.setattr("tooluniverse.core_tool.MARKITDOWN_AVAILABLE", False)
    tool.md_converter = None

    result = tool.run(
        {
            "pdf_url": "https://core.ac.uk/download/123.pdf",
            "terms": ["rs738409"],
            "extractor": "markitdown",
        }
    )
    assert result["status"] == "error"
    assert "markitdown" in result["error"].lower()


@pytest.mark.unit
def test_core_pdf_snippets_invalid_terms():
    tool = CorePDFSnippetsTool({"name": "CORE_get_fulltext_snippets"})
    result = tool.run({"pdf_url": "https://core.ac.uk/download/123.pdf"})
    assert result["status"] == "error"
    assert "terms" in result["error"].lower()
