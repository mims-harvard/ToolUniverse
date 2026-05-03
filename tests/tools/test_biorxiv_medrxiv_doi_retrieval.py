#!/usr/bin/env python3
"""
Unit tests for bioRxiv/medRxiv DOI-based retrieval.

Note: The old BioRxiv_search_preprints and MedRxiv_search_preprints tools have been removed
because the bioRxiv API does not support text search. For searching preprints, use:
- EuropePMC_search_articles with 'SRC:PPR' filter
- web_search with 'site:biorxiv.org' or 'site:medrxiv.org'

These tests validate the new BioRxiv_get_preprint and MedRxiv_get_preprint tools.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.biorxiv_tool import BioRxivTool


class _FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.reason = "OK" if status_code == 200 else "Error"
        self._payload = payload if payload is not None else {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@pytest.mark.unit
def test_biorxiv_get_preprint_success(monkeypatch):
    """Test successful DOI retrieval for bioRxiv"""
    tool = BioRxivTool({"name": "BioRxiv_get_preprint"})

    def fake_request_with_retry(session, method, url, *, timeout=None, **kwargs):
        # Should be called with details API endpoint
        assert "/details/biorxiv/" in url
        assert "/na/json" in url
        
        return _FakeResponse(
            payload={
                "collection": [
                    {
                        "doi": "10.1101/2023.12.01.569554",
                        "title": "Test bioRxiv preprint",
                        "authors": "Smith, J.; Doe, A.",
                        "abstract": "This is a test abstract.",
                        "date": "2023-12-01",
                        "version": "1",
                        "type": "new results",
                        "license": "cc_by",
                        "category": "microbiology",
                        "author_corresponding": "Smith, J.",
                        "author_corresponding_institution": "Test University",
                        "published": None,
                        "jatsxml": "https://www.biorxiv.org/content/...",
                    }
                ]
            }
        )

    monkeypatch.setattr(
        "tooluniverse.biorxiv_tool.request_with_retry", fake_request_with_retry
    )

    result = tool.run({"doi": "2023.12.01.569554"})

    assert result["status"] == "success"
    data = result["data"]
    assert data["doi"] == "10.1101/2023.12.01.569554"
    assert data["title"] == "Test bioRxiv preprint"
    assert len(data["authors"]) == 2
    assert data["authors"][0] == "Smith, J."
    assert data["abstract"] == "This is a test abstract."
    assert data["url"] == "https://www.biorxiv.org/content/10.1101/2023.12.01.569554"
    assert data["pdf_url"] == "https://www.biorxiv.org/content/10.1101/2023.12.01.569554.full.pdf"
    assert data["server"] == "biorxiv"


@pytest.mark.unit
def test_medrxiv_get_preprint_success(monkeypatch):
    """Test successful DOI retrieval for medRxiv"""
    tool = BioRxivTool({"name": "MedRxiv_get_preprint"})

    def fake_request_with_retry(session, method, url, *, timeout=None, **kwargs):
        # Should be called with medRxiv server
        assert "/details/medrxiv/" in url
        assert "/na/json" in url
        
        return _FakeResponse(
            payload={
                "collection": [
                    {
                        "doi": "10.1101/2021.04.29.21256344",
                        "title": "Test medRxiv preprint",
                        "authors": "Jones, A.; Brown, B.",
                        "abstract": "Clinical study abstract.",
                        "date": "2021-04-29",
                        "version": "2",
                        "type": "new results",
                        "license": "cc0",
                        "category": "infectious diseases",
                        "author_corresponding": "Jones, A.",
                        "author_corresponding_institution": "Medical Center",
                        "published": "10.1128/journal.00123-21",
                        "jatsxml": "https://www.medrxiv.org/content/...",
                    }
                ]
            }
        )

    monkeypatch.setattr(
        "tooluniverse.biorxiv_tool.request_with_retry", fake_request_with_retry
    )

    result = tool.run({"doi": "2021.04.29.21256344", "server": "medrxiv"})

    assert result["status"] == "success"
    data = result["data"]
    assert data["doi"] == "10.1101/2021.04.29.21256344"
    assert data["title"] == "Test medRxiv preprint"
    assert len(data["authors"]) == 2
    assert data["published"] == "10.1128/journal.00123-21"
    assert data["url"] == "https://www.medrxiv.org/content/10.1101/2021.04.29.21256344"
    assert data["server"] == "medrxiv"


@pytest.mark.unit
def test_biorxiv_doi_normalization(monkeypatch):
    """Test that partial DOIs are normalized correctly"""
    tool = BioRxivTool({"name": "BioRxiv_get_preprint"})

    called_urls = []

    def fake_request_with_retry(session, method, url, *, timeout=None, **kwargs):
        called_urls.append(url)
        return _FakeResponse(
            payload={
                "collection": [
                    {
                        "doi": "10.1101/2023.12.01.569554",
                        "title": "Test",
                        "authors": "A",
                        "abstract": "Test",
                        "date": "2023-12-01",
                        "version": "1",
                        "type": "new results",
                        "license": "cc_by",
                        "category": "test",
                    }
                ]
            }
        )

    monkeypatch.setattr(
        "tooluniverse.biorxiv_tool.request_with_retry", fake_request_with_retry
    )

    # Test with partial DOI (without 10.1101/ prefix)
    result = tool.run({"doi": "2023.12.01.569554"})
    
    assert result["status"] == "success"
    # Should have normalized to full DOI in URL
    assert "/10.1101/2023.12.01.569554/" in called_urls[0]


@pytest.mark.unit
def test_biorxiv_not_found(monkeypatch):
    """Test handling of non-existent DOI"""
    tool = BioRxivTool({"name": "BioRxiv_get_preprint"})

    def fake_request_with_retry(session, method, url, *, timeout=None, **kwargs):
        resp = _FakeResponse(status_code=404)
        resp.reason = "Not Found"
        return resp

    monkeypatch.setattr(
        "tooluniverse.biorxiv_tool.request_with_retry", fake_request_with_retry
    )

    result = tool.run({"doi": "9999.99.99.999999"})

    assert result["status"] == "error"
    assert "not found" in result["error"].lower()


@pytest.mark.unit
def test_biorxiv_missing_doi_parameter():
    """Test error when DOI parameter is missing"""
    tool = BioRxivTool({"name": "BioRxiv_get_preprint"})

    result = tool.run({})

    assert result["status"] == "error"
    assert "doi" in result["error"].lower()
    assert "required" in result["error"].lower()


@pytest.mark.unit
def test_biorxiv_invalid_server_parameter():
    """Test error when invalid server is specified"""
    tool = BioRxivTool({"name": "BioRxiv_get_preprint"})

    result = tool.run({"doi": "2023.12.01.569554", "server": "arxiv"})

    assert result["status"] == "error"
    assert "server" in result["error"].lower()
