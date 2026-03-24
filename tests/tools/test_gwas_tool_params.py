#!/usr/bin/env python3
"""
Unit tests for GWAS REST tools parameter normalization.

These tests focus on local behavior (param mapping), not on network calls.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.gwas_tool import GWASAssociationSearch, GWASStudySearch


@pytest.mark.unit
def test_gwas_association_search_normalizes_efo_uri_to_efo_id(monkeypatch):
    tool = GWASAssociationSearch({"name": "gwas_search_associations"})

    captured = {}

    def fake_make_request(endpoint, params=None):
        captured["endpoint"] = endpoint
        captured["params"] = params or {}
        return {"_embedded": {"associations": []}, "_links": {}, "page": {}}

    monkeypatch.setattr(tool, "_make_request", fake_make_request)

    out = tool.run(
        {
            "rs_id": "rs58542926",
            "efo_uri": "http://www.ebi.ac.uk/efo/OBA_2050062",
            "size": "5",
            "page": 0,
        }
    )

    assert out["data"] == []
    assert captured["endpoint"] == "/v2/associations"
    assert "efo_id" in captured["params"]
    assert captured["params"]["efo_id"] == "OBA_2050062"
    assert "efo_uri" not in captured["params"]
    assert captured["params"]["size"] == 5


@pytest.mark.unit
def test_gwas_association_search_converts_curie_to_efo_id(monkeypatch):
    tool = GWASAssociationSearch({"name": "gwas_search_associations"})

    captured = {}

    def fake_make_request(endpoint, params=None):
        captured["endpoint"] = endpoint
        captured["params"] = params or {}
        return {"_embedded": {"associations": []}, "_links": {}, "page": {}}

    monkeypatch.setattr(tool, "_make_request", fake_make_request)

    tool.run({"rs_id": "rs58542926", "efo_id": "OBA:2050062"})

    assert captured["endpoint"] == "/v2/associations"
    assert captured["params"]["efo_id"] == "OBA_2050062"


@pytest.mark.unit
def test_gwas_study_search_accepts_efo_id(monkeypatch):
    tool = GWASStudySearch({"name": "gwas_search_studies"})

    captured = {}

    def fake_make_request(endpoint, params=None):
        captured["endpoint"] = endpoint
        captured["params"] = params or {}
        return {"_embedded": {"studies": []}, "_links": {}, "page": {}}

    monkeypatch.setattr(tool, "_make_request", fake_make_request)

    out = tool.run({"efo_id": "EFO_0001421", "size": 10})

    assert out["data"] == []
    assert captured["endpoint"] == "/v2/studies"
    assert captured["params"]["efo_id"] == "EFO_0001421"
    assert captured["params"]["size"] == 10


@pytest.mark.unit
def test_gwas_search_ignores_empty_values(monkeypatch):
    """When all filter values are empty/None, the tool returns an error
    (Feature-81B-008: requires at least one filter to avoid returning 1M+ rows)."""
    tool = GWASAssociationSearch({"name": "gwas_search_associations"})

    def fake_make_request(endpoint, params=None):
        raise AssertionError("No network call should be made for all-empty inputs")

    monkeypatch.setattr(tool, "_make_request", fake_make_request)

    result = tool.run(
        {
            "disease_trait": None,
            "rs_id": "  ",
            "accession_id": "",
            "sort": None,
            "direction": "",
            "size": None,
            "page": None,
        }
    )

    assert result["status"] == "error"
    assert "filter" in result["error"].lower() or "required" in result["error"].lower()
