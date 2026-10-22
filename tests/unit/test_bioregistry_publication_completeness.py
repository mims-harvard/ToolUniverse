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
