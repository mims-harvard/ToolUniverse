"""Regression for reachable HuBMAP search pages."""

from unittest.mock import Mock

import pytest

from tooluniverse.hubmap_tool import HuBMAPTool

pytestmark = pytest.mark.unit


def test_search_sends_offset_and_reports_next_page(monkeypatch):
    response = Mock()
    response.json.return_value = {
        "hits": {
            "total": {"value": 957},
            "hits": [
                {"_source": {"hubmap_id": "HBM346.JMJX.867"}},
                {"_source": {"hubmap_id": "HBM757.KRNC.835"}},
                {"_source": {"hubmap_id": "HBM268.RGJT.587"}},
            ],
        }
    }
    response.raise_for_status.return_value = None
    requested = {}

    def post(url, json, headers, timeout):
        requested.update(
            {"url": url, "body": json, "headers": headers, "timeout": timeout}
        )
        return response

    monkeypatch.setattr("tooluniverse.hubmap_tool.requests.post", post)
    tool = HuBMAPTool(
        {
            "name": "HuBMAP_search_datasets",
            "fields": {"operation": "search_datasets"},
            "parameter": {"properties": {}},
        }
    )

    result = tool.run({"organ": "LK", "limit": 3, "offset": 3})

    assert requested["body"]["from"] == 3
    assert requested["body"]["size"] == 3
    assert [x["hubmap_id"] for x in result["data"]["datasets"]] == [
        "HBM346.JMJX.867",
        "HBM757.KRNC.835",
        "HBM268.RGJT.587",
    ]
    assert result["data"]["total"] == 957
    assert result["data"]["returned"] == 3
    assert result["data"]["offset"] == 3
    assert result["data"]["limit"] == 3
    assert result["data"]["has_more"] is True
    assert result["data"]["next_offset"] == 6
