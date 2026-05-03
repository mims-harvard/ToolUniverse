#!/usr/bin/env python3
"""
Tests for Semantic Scholar TLDR and fields_of_study support.
Covers both SemanticScholar_search_papers and SemanticScholar_get_paper.
"""

import json
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


# ---------------------------------------------------------------------------
# SemanticScholar_search_papers: TLDR + fieldsOfStudy extraction
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_search_includes_tldr_in_api_fields(monkeypatch):
    """The search API request must include 'tldr' and 'fieldsOfStudy' in the fields parameter."""
    tool = SemanticScholarTool({"name": "SemanticScholar_search_papers"})
    monkeypatch.setattr(tool, "_enforce_rate_limit", lambda has_api_key: None)

    captured_params = {}

    def fake_request(session, method, url, **kwargs):
        captured_params.update(kwargs.get("params", {}))
        return _FakeResponse(
            200, {"data": [{"paperId": "abc", "title": "Test"}]}
        )

    monkeypatch.setattr(
        "tooluniverse.semantic_scholar_tool.request_with_retry", fake_request
    )

    tool.run({"query": "test", "limit": 1})

    fields_str = captured_params.get("fields", "")
    assert "tldr" in fields_str, f"'tldr' not in API fields: {fields_str}"
    assert (
        "fieldsOfStudy" in fields_str
    ), f"'fieldsOfStudy' not in API fields: {fields_str}"


@pytest.mark.unit
def test_search_extracts_tldr_text(monkeypatch):
    """When API returns tldr object, search tool extracts the text string."""
    tool = SemanticScholarTool({"name": "SemanticScholar_search_papers"})
    monkeypatch.setattr(tool, "_enforce_rate_limit", lambda has_api_key: None)

    api_paper = {
        "paperId": "abc123",
        "title": "CRISPR-Cas9 Review",
        "abstract": "A review of CRISPR...",
        "tldr": {"model": "tldr@v2.0.0", "text": "CRISPR enables precise genome editing."},
        "fieldsOfStudy": ["Biology", "Medicine"],
        "year": 2023,
        "venue": "Nature",
        "url": "https://example.com",
        "authors": [{"name": "Jane Doe"}],
        "externalIds": {"DOI": "10.1234/test"},
        "citationCount": 100,
        "referenceCount": 50,
        "isOpenAccess": True,
        "openAccessPdf": {"url": "https://pdf.example.com/paper.pdf"},
    }

    def fake_request(session, method, url, **kwargs):
        return _FakeResponse(200, {"data": [api_paper]})

    monkeypatch.setattr(
        "tooluniverse.semantic_scholar_tool.request_with_retry", fake_request
    )

    result = tool.run({"query": "crispr", "limit": 1})
    assert result["status"] == "success"
    papers = result["data"]
    assert len(papers) == 1

    paper = papers[0]
    assert paper["tldr"] == "CRISPR enables precise genome editing."
    assert paper["fields_of_study"] == ["Biology", "Medicine"]
    assert paper["data_quality"]["has_tldr"] is True


@pytest.mark.unit
def test_search_handles_null_tldr(monkeypatch):
    """When tldr is null/missing, the field should be None."""
    tool = SemanticScholarTool({"name": "SemanticScholar_search_papers"})
    monkeypatch.setattr(tool, "_enforce_rate_limit", lambda has_api_key: None)

    api_paper = {
        "paperId": "def456",
        "title": "Some Paper",
        "abstract": None,
        "tldr": None,
        "fieldsOfStudy": None,
        "year": 2020,
        "venue": None,
        "url": None,
        "authors": [],
        "externalIds": {},
        "citationCount": 0,
        "referenceCount": 0,
        "isOpenAccess": False,
        "openAccessPdf": None,
    }

    def fake_request(session, method, url, **kwargs):
        return _FakeResponse(200, {"data": [api_paper]})

    monkeypatch.setattr(
        "tooluniverse.semantic_scholar_tool.request_with_retry", fake_request
    )

    result = tool.run({"query": "test", "limit": 1})
    paper = result["data"][0]
    assert paper["tldr"] is None
    assert paper["fields_of_study"] is None
    assert paper["data_quality"]["has_tldr"] is False


@pytest.mark.unit
def test_search_handles_missing_tldr_key(monkeypatch):
    """When tldr key is entirely absent from API response, field should be None."""
    tool = SemanticScholarTool({"name": "SemanticScholar_search_papers"})
    monkeypatch.setattr(tool, "_enforce_rate_limit", lambda has_api_key: None)

    api_paper = {
        "paperId": "ghi789",
        "title": "Old Paper",
        "year": 2010,
        "authors": [],
        "externalIds": {},
    }

    def fake_request(session, method, url, **kwargs):
        return _FakeResponse(200, {"data": [api_paper]})

    monkeypatch.setattr(
        "tooluniverse.semantic_scholar_tool.request_with_retry", fake_request
    )

    result = tool.run({"query": "test", "limit": 1})
    paper = result["data"][0]
    assert paper["tldr"] is None
    assert paper["fields_of_study"] is None


# ---------------------------------------------------------------------------
# JSON config: return_schema includes tldr and fields_of_study
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_search_json_schema_includes_tldr():
    """The search tool JSON config return_schema must include tldr and fields_of_study."""
    config_path = (
        Path(__file__).parent.parent.parent
        / "src/tooluniverse/data/semantic_scholar_tools.json"
    )
    configs = json.loads(config_path.read_text())
    search_config = next(c for c in configs if c["name"] == "SemanticScholar_search_papers")

    # Check success schema (first oneOf)
    success_schema = search_config["return_schema"]["oneOf"][0]
    item_props = success_schema["items"]["properties"]

    assert "tldr" in item_props, "tldr missing from search return_schema"
    assert "fields_of_study" in item_props, "fields_of_study missing from search return_schema"


@pytest.mark.unit
def test_get_paper_json_schema_includes_tldr():
    """The get_paper JSON config return_schema must include tldr."""
    config_path = (
        Path(__file__).parent.parent.parent
        / "src/tooluniverse/data/semantic_scholar_ext_tools.json"
    )
    configs = json.loads(config_path.read_text())
    paper_config = next(c for c in configs if c["name"] == "SemanticScholar_get_paper")

    # Check success schema (first oneOf)
    success_schema = paper_config["return_schema"]["oneOf"][0]
    props = success_schema["properties"]

    assert "tldr" in props, "tldr missing from get_paper return_schema"
    assert props["tldr"]["properties"]["text"]["type"] == "string"
    assert props["tldr"]["properties"]["model"]["type"] == "string"


@pytest.mark.unit
def test_get_paper_default_fields_include_tldr():
    """The get_paper default fields param must include tldr."""
    config_path = (
        Path(__file__).parent.parent.parent
        / "src/tooluniverse/data/semantic_scholar_ext_tools.json"
    )
    configs = json.loads(config_path.read_text())
    paper_config = next(c for c in configs if c["name"] == "SemanticScholar_get_paper")

    default_fields = paper_config["parameter"]["properties"]["fields"]["default"]
    assert "tldr" in default_fields, f"tldr not in default fields: {default_fields}"
