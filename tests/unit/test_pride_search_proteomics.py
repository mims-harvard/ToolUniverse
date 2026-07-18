"""Regression guard for Fix-R12C-1 and Fix-R12C-3.

Fix-R12C-1: PRIDE_search_proteomics's `query` and `page_size` params were
completely ignored -- confirmed live that a real query ("TP53") and a
nonsense query returned byte-identical 100-row results. Root cause: the
config pointed at PRIDE's `/projects?query={query}` endpoint, which (via raw
curl) turns out to ignore `query` entirely; the real keyword-filtering
endpoint is `/search/projects?keyword={query}&pageSize=N`. `page_size` was
also never wired into any request param anywhere in the code.

Fix-R12C-3: any PRIDE 404 (e.g. a gene symbol passed where a UniProt/PXD
accession is expected) returned a bare "PRIDE API error" with no hint that
the identifier itself was the problem, even though PRIDE's own 404 body is
empty and has nothing more to surface.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.pride_tool import PRIDERESTTool

pytestmark = pytest.mark.unit


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else []
        self.text = text

    def json(self):
        return self._payload


def _search_tool():
    return PRIDERESTTool(
        {
            "name": "PRIDE_search_proteomics",
            "parameter": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "page_size": {"type": "integer", "default": 20},
                },
            },
            "fields": {
                "endpoint": "https://www.ebi.ac.uk/pride/ws/archive/v2/search/projects?keyword={query}",
                "return_format": "JSON",
            },
        }
    )


def _protein_tool():
    return PRIDERESTTool(
        {
            "name": "PRIDE_get_projects_for_protein",
            "parameter": {
                "type": "object",
                "properties": {"accession": {"type": "string"}},
            },
            "fields": {
                "endpoint": "https://www.ebi.ac.uk/pride/ws/archive/v2/proteins/{accession}",
                "return_format": "JSON",
            },
        }
    )


def test_search_url_uses_keyword_search_endpoint():
    tool = _search_tool()
    url = tool._build_url({"query": "TP53", "page_size": 5})
    assert url.startswith(
        "https://www.ebi.ac.uk/pride/ws/archive/v2/search/projects?keyword=TP53"
    )
    assert "pageSize=5" in url


def test_search_page_size_defaults_to_20_when_omitted():
    tool = _search_tool()
    url = tool._build_url({"query": "cancer"})
    assert "pageSize=20" in url


def test_search_run_returns_data_from_correct_endpoint(monkeypatch):
    tool = _search_tool()
    captured = {}

    def fake_request(session, method, url, **kwargs):
        captured["url"] = url
        return _FakeResponse(200, [{"accession": "PXD073999"}])

    monkeypatch.setattr("tooluniverse.pride_tool.request_with_retry", fake_request)

    result = tool.run({"query": "TP53", "page_size": 5})

    assert result["status"] == "success"
    assert "search/projects?keyword=TP53" in captured["url"]
    assert "pageSize=5" in captured["url"]


def test_url_build_does_not_add_page_size_for_tools_without_that_param():
    tool = _protein_tool()
    url = tool._build_url({"accession": "P04637"})
    assert url == "https://www.ebi.ac.uk/pride/ws/archive/v2/proteins/P04637"
    assert "pageSize" not in url


def test_404_error_message_hints_at_identifier_mismatch(monkeypatch):
    tool = _protein_tool()

    def fake_request(session, method, url, **kwargs):
        return _FakeResponse(404, {}, text="")

    monkeypatch.setattr("tooluniverse.pride_tool.request_with_retry", fake_request)

    result = tool.run({"accession": "TP53"})

    assert result["status"] == "error"
    assert result["status_code"] == 404
    assert "404" in result["error"]
    assert "identifier" in result["error"]


def test_non_404_errors_keep_generic_message(monkeypatch):
    tool = _protein_tool()

    def fake_request(session, method, url, **kwargs):
        return _FakeResponse(500, {}, text="internal error")

    monkeypatch.setattr("tooluniverse.pride_tool.request_with_retry", fake_request)

    result = tool.run({"accession": "P04637"})

    assert result["status"] == "error"
    assert result["error"] == "PRIDE API error"
    assert result["status_code"] == 500
