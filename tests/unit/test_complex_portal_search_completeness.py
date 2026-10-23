"""Regressions for Complex Portal search pagination and descriptions."""

from unittest.mock import Mock

import pytest

from tooluniverse.complex_portal_tool import ComplexPortalTool

pytestmark = pytest.mark.unit


def _tool():
    return ComplexPortalTool(
        {
            "name": "ComplexPortal_search_complexes",
            "fields": {"operation": "search_complexes"},
            "parameter": {"properties": {}},
        }
    )


def test_search_sends_first_and_keeps_complete_descriptions(monkeypatch):
    long_description = "Complete curated complex function. " * 30
    response = Mock()
    response.json.return_value = {
        "totalNumberOfResults": 12,
        "elements": [
            {
                "complexAC": "CPX-4",
                "complexName": "Complex four",
                "organismName": "Homo sapiens; 9606",
                "description": long_description,
                "interactors": [],
            },
            {
                "complexAC": "CPX-5",
                "complexName": "Complex five",
                "organismName": "Homo sapiens; 9606",
                "description": None,
                "interactors": [],
            },
        ],
    }
    response.raise_for_status.return_value = None
    requested = {}

    def get(url, params, timeout):
        requested.update({"url": url, "params": params, "timeout": timeout})
        return response

    monkeypatch.setattr("tooluniverse.complex_portal_tool.requests.get", get)

    result = _tool().run(
        {"query": "proteasome", "species": "9606", "first": 3, "number": 2}
    )

    assert requested["params"]["first"] == 3
    assert requested["params"]["number"] == 2
    assert len(long_description) > 500
    assert result["data"]["complexes"][0]["description"] == long_description
    assert result["data"]["complexes"][0]["description_length"] == len(long_description)
    assert result["data"]["complexes"][1]["description"] is None
    assert result["data"]["complexes"][1]["description_length"] == 0
    assert result["data"]["first"] == 3
    assert result["data"]["number"] == 2
    assert result["data"]["total_found"] == 12
    assert result["data"]["has_more"] is True
    assert result["data"]["next_first"] == 5
