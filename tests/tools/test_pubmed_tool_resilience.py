#!/usr/bin/env python3
"""
Unit tests for PubMed summary fetch resilience and partial results.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.pubmed_tool import PubMedRESTTool


class _FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}

    def json(self):
        return self._payload


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
def test_fetch_summaries_returns_partial_results_when_some_ids_fail(monkeypatch):
    tool = _make_tool()
    monkeypatch.setattr(tool, "_enforce_rate_limit", lambda has_api_key: None)

    article_payload = {
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

    def fake_request_with_retry(
        session,
        method,
        url,
        *,
        params=None,
        timeout=None,
        max_attempts=None,
        **kwargs,
    ):
        request_id = params.get("id", "")
        # Batch request fails, per-ID request recovers only PMID 1.
        if request_id == "1,2":
            return _FakeResponse(status_code=500)
        if request_id == "1":
            return _FakeResponse(status_code=200, payload=article_payload)
        if request_id == "2":
            return _FakeResponse(status_code=500)
        return _FakeResponse(status_code=500)

    monkeypatch.setattr(
        "tooluniverse.pubmed_tool.request_with_retry", fake_request_with_retry
    )

    result = tool._fetch_summaries(["1", "2"])

    assert result["status"] == "success"
    assert len(result["data"]) == 1
    assert result["data"][0]["pmid"] == "1"
    assert "warning" in result


@pytest.mark.unit
def test_fetch_summaries_returns_error_when_all_ids_fail(monkeypatch):
    tool = _make_tool()
    monkeypatch.setattr(tool, "_enforce_rate_limit", lambda has_api_key: None)

    def fake_request_with_retry(
        session,
        method,
        url,
        *,
        params=None,
        timeout=None,
        max_attempts=None,
        **kwargs,
    ):
        return _FakeResponse(status_code=500)

    monkeypatch.setattr(
        "tooluniverse.pubmed_tool.request_with_retry", fake_request_with_retry
    )

    result = tool._fetch_summaries(["10", "11"])

    assert result["status"] == "error"
    assert "Batch summary fetch failed" in result["error"]
