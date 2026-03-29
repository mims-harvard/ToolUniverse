#!/usr/bin/env python3
"""
Unit tests for Semantic Scholar tool stability and error shaping.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.semantic_scholar_tool import SemanticScholarTool


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, reason=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.reason = reason
        self.headers = {}

    def json(self):
        return self._payload


@pytest.mark.unit
def test_semantic_scholar_returns_list_on_error(monkeypatch):
    tool = SemanticScholarTool({"name": "SemanticScholar_search_papers"})
    monkeypatch.setattr(tool, "_enforce_rate_limit", lambda has_api_key: None)

    def fake_request_with_retry(*args, **kwargs):
        return _FakeResponse(status_code=429, reason="Too Many Requests")

    monkeypatch.setattr(
        "tooluniverse.semantic_scholar_tool.request_with_retry", fake_request_with_retry
    )

    result = tool.run({"query": "x", "limit": 1})

    # run() returns envelope dict with status/error keys
    assert isinstance(result, dict)
    assert result["status"] == "error"
    assert "429" in result["error"]
    assert result["retryable"] is True


@pytest.mark.unit
def test_semantic_scholar_include_abstract_enriches_missing_abstract(monkeypatch):
    tool = SemanticScholarTool({"name": "SemanticScholar_search_papers"})
    monkeypatch.setattr(tool, "_enforce_rate_limit", lambda has_api_key: None)

    def fake_request_with_retry(session, method, url, *, params=None, **kwargs):
        if url.endswith("/paper/search"):
            return _FakeResponse(
                status_code=200,
                payload={
                    "data": [
                        {
                            "paperId": "abc",
                            "externalIds": {},
                            "title": "T",
                            "abstract": None,
                            "year": 2024,
                            "venue": "V",
                            "url": "https://example.test/paper",
                            "authors": [{"name": "A"}],
                            "citationCount": 1,
                            "referenceCount": 2,
                            "isOpenAccess": True,
                            "openAccessPdf": {},
                        }
                    ]
                },
            )
        if url.endswith("/paper/abc"):
            return _FakeResponse(
                status_code=200,
                payload={
                    "abstract": "Filled abstract.",
                    "externalIds": {"DOI": "10.1000/example"},
                    "openAccessPdf": {"url": "https://example.test/pdf"},
                },
            )
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(
        "tooluniverse.semantic_scholar_tool.request_with_retry", fake_request_with_retry
    )

    result = tool.run({"query": "x", "limit": 1, "include_abstract": True})

    # run() returns envelope dict with data list
    assert isinstance(result, dict)
    assert result["status"] == "success"
    papers = result["data"]
    assert len(papers) == 1
    assert papers[0]["abstract"] == "Filled abstract."
    assert papers[0]["doi"] == "10.1000/example"
    assert papers[0]["doi_url"] == "https://doi.org/10.1000/example"
    assert papers[0]["open_access_pdf_url"] == "https://example.test/pdf"
