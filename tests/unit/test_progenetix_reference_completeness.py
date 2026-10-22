"""Regressions for Progenetix references and individual pagination."""

from unittest.mock import Mock

import pytest

from tooluniverse.progenetix_tool import ProgenetixTool

pytestmark = pytest.mark.unit


def _tool(endpoint):
    return ProgenetixTool(
        {
            "name": f"Progenetix_{endpoint}",
            "fields": {"endpoint": endpoint},
            "parameter": {"properties": {}},
        }
    )


def test_reference_formatter_preserves_live_beacon_fields_without_a_cap():
    references = [
        {
            "id": f"PMID:{index}",
            "description": f"Publication {index}",
            "reference": f"https://example.test/{index}",
            "notes": f"Study note {index}",
        }
        for index in range(7)
    ]

    result = ProgenetixTool._format_external_references(references)

    assert len(result) == 7
    assert result[-1] == {
        "id": "PMID:6",
        "label": None,
        "description": "Publication 6",
        "reference": "https://example.test/6",
        "notes": "Study note 6",
    }


def test_individual_search_sends_skip_and_reports_next_page(monkeypatch):
    response = Mock()
    response.json.return_value = {
        "response": {
            "resultSets": [
                {
                    "resultsCount": 421,
                    "results": [
                        {
                            "id": "pgxind-example",
                            "externalReferences": [
                                {
                                    "id": "PMID:28481359",
                                    "notes": "Complete study description",
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    }
    response.raise_for_status.return_value = None
    requested = {}

    def get(url, params, timeout):
        requested.update({"url": url, "params": params, "timeout": timeout})
        return response

    monkeypatch.setattr("tooluniverse.progenetix_tool.requests.get", get)

    result = _tool("individuals").run({"filters": "NCIT:C3058", "limit": 1, "skip": 3})

    assert requested["params"] == {
        "filters": "NCIT:C3058",
        "limit": 1,
        "skip": 3,
    }
    individual = result["data"]["individuals"][0]
    assert individual["external_references"][0]["notes"] == (
        "Complete study description"
    )
    assert individual["external_references_count"] == 1
    assert result["data"]["skip"] == 3
    assert result["data"]["has_more"] is True
    assert result["data"]["next_skip"] == 4
