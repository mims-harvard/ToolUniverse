"""Regression for complete Bioregistry publication metadata."""

from unittest.mock import Mock

import pytest

from tooluniverse.bioregistry_tool import BioregistryTool

pytestmark = pytest.mark.unit


def test_get_registry_keeps_all_publications(monkeypatch):
    publications = [
        {"pubmed": str(index), "title": f"Registry paper {index}"} for index in range(7)
    ]
    response = Mock(status_code=200)
    response.json.return_value = {
        "prefix": "example",
        "name": "Example Registry",
        "publications": publications,
    }
    monkeypatch.setattr(
        "tooluniverse.bioregistry_tool.requests.get", lambda *args, **kwargs: response
    )
    tool = BioregistryTool(
        {
            "name": "Bioregistry_get_registry",
            "fields": {"operation": "get_registry"},
            "parameter": {"properties": {}},
        }
    )

    result = tool.run({"operation": "get_registry", "prefix": "example"})

    assert len(publications) > 5
    assert result["data"]["publications"] == publications
    assert result["data"]["publications_count"] == len(publications)


def test_search_offset_pages_the_hits_and_resolves_their_names(monkeypatch):
    def fake_get(url, *args, **kwargs):
        response = Mock(status_code=200)
        if url.endswith("/search"):
            response.json.return_value = [[f"p{index}", ""] for index in range(5)]
        else:
            prefix = url.rsplit("/", 1)[-1]
            response.json.return_value = {"name": f"Name {prefix}"}
        return response

    monkeypatch.setattr("tooluniverse.bioregistry_tool.requests.get", fake_get)
    tool = BioregistryTool(
        {
            "name": "Bioregistry_search_registries",
            "fields": {"operation": "search_registries"},
            "parameter": {"properties": {}},
        }
    )

    result = tool.run(
        {"operation": "search_registries", "query": "x", "limit": 2, "offset": 2}
    )

    data = result["data"]
    assert [row["prefix"] for row in data["results"]] == ["p2", "p3"]
    assert data["results"][0]["name"] == "Name p2"
    assert data["total"] == 5
    assert data["has_more"] is True
    assert data["next_offset"] == 4
