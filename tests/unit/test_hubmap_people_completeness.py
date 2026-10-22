"""Regression for complete HuBMAP contacts and contributors."""

from unittest.mock import Mock

import pytest

from tooluniverse.hubmap_tool import HuBMAPTool

pytestmark = pytest.mark.unit


def test_dataset_keeps_all_people_and_maps_live_display_name(monkeypatch):
    contributors = [
        {
            "display_name": f"Contributor {index}",
            "first_name": "Contributor",
            "last_name": str(index),
            "email": f"person{index}@example.test",
            "affiliation": "Example Center",
            "orcid": f"0000-0000-0000-{index:04d}",
            "is_contact": "No",
            "is_operator": "Yes",
            "is_principal_investigator": "No",
        }
        for index in range(12)
    ]
    response = Mock(status_code=200)
    response.json.return_value = {
        "hubmap_id": "HBM.EXAMPLE.001",
        "entity_type": "Dataset",
        "contacts": [
            {
                "display_name": "Contact Person",
                "email": "contact@example.test",
                "orcid": "0000-0001-0002-0003",
            }
        ],
        "contributors": contributors,
    }
    response.raise_for_status.return_value = None
    monkeypatch.setattr(
        "tooluniverse.hubmap_tool.requests.get", lambda *args, **kwargs: response
    )

    tool = HuBMAPTool(
        {
            "name": "HuBMAP_get_dataset",
            "fields": {"operation": "get_dataset"},
            "parameter": {"properties": {}},
        }
    )
    result = tool.run({"hubmap_id": "HBM.EXAMPLE.001"})

    assert result["data"]["contacts"][0]["name"] == "Contact Person"
    assert result["data"]["contacts_count"] == 1
    assert len(contributors) > 10
    assert result["data"]["contributors_count"] == 12
    assert len(result["data"]["contributors"]) == 12
    assert result["data"]["contributors"][-1]["name"] == "Contributor 11"
    assert result["data"]["contributors"][-1]["orcid"] == "0000-0000-0000-0011"
