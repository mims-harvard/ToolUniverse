"""Regression guard for Fix-R12A-1: SemanticScholar_search_papers with a
`sort` value switches to the /paper/search/bulk endpoint, which rejects the
"tldr" field with a 400 ("Unrecognized or unsupported fields: [tldr]") --
confirmed live via raw curl -- and has no server-side `limit` concept (only
token-based pagination over its full result set, so results must be sliced
client-side). Before the fix, every sorted search call failed outright.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.semantic_scholar_tool import SemanticScholarTool

pytestmark = pytest.mark.unit


class _FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.reason = ""
        self.headers = {}

    def json(self):
        return self._payload


def _tool():
    tool = SemanticScholarTool({"name": "SemanticScholar_search_papers"})
    return tool


def test_sorted_search_omits_tldr_from_bulk_request(monkeypatch):
    tool = _tool()
    monkeypatch.setattr(tool, "_enforce_rate_limit", lambda has_api_key: None)

    captured = {}

    def fake_request(session, method, url, **kwargs):
        captured["url"] = url
        captured["params"] = kwargs.get("params", {})
        return _FakeResponse(200, {"data": []})

    monkeypatch.setattr(
        "tooluniverse.semantic_scholar_tool.request_with_retry", fake_request
    )

    tool.run({"query": "CRISPR", "limit": 5, "sort": "citationCount:desc"})

    assert "/paper/search/bulk" in captured["url"]
    assert "tldr" not in captured["params"]["fields"].split(",")


def test_unsorted_search_still_requests_tldr(monkeypatch):
    tool = _tool()
    monkeypatch.setattr(tool, "_enforce_rate_limit", lambda has_api_key: None)

    captured = {}

    def fake_request(session, method, url, **kwargs):
        captured["url"] = url
        captured["params"] = kwargs.get("params", {})
        return _FakeResponse(200, {"data": []})

    monkeypatch.setattr(
        "tooluniverse.semantic_scholar_tool.request_with_retry", fake_request
    )

    tool.run({"query": "CRISPR", "limit": 5})

    assert "/paper/search/bulk" not in captured["url"]
    assert "tldr" in captured["params"]["fields"].split(",")


def test_sorted_search_results_sliced_to_requested_limit(monkeypatch):
    tool = _tool()
    monkeypatch.setattr(tool, "_enforce_rate_limit", lambda has_api_key: None)

    bulk_papers = [
        {"paperId": str(i), "title": f"Paper {i}", "citationCount": 100 - i}
        for i in range(50)
    ]

    def fake_request(session, method, url, **kwargs):
        return _FakeResponse(200, {"data": bulk_papers, "token": "next-page"})

    monkeypatch.setattr(
        "tooluniverse.semantic_scholar_tool.request_with_retry", fake_request
    )

    result = tool.run({"query": "CRISPR", "limit": 5, "sort": "citationCount:desc"})

    assert result["status"] == "success"
    assert len(result["data"]) == 5


def test_bulk_400_error_still_surfaced(monkeypatch):
    """If the bulk endpoint rejects the request for any other reason, the
    tool must still report the error rather than swallowing it."""
    tool = _tool()
    monkeypatch.setattr(tool, "_enforce_rate_limit", lambda has_api_key: None)

    def fake_request(session, method, url, **kwargs):
        return _FakeResponse(400, {})

    monkeypatch.setattr(
        "tooluniverse.semantic_scholar_tool.request_with_retry", fake_request
    )

    result = tool.run({"query": "CRISPR", "limit": 5, "sort": "citationCount:desc"})
    assert result["status"] == "error"
    assert result["error"] == "Semantic Scholar API error 400"
