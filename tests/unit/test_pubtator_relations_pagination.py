"""Regression tests for recoverable PubTator relation pagination."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config():
    path = Path(__file__).parents[2] / "src/tooluniverse/data/pubtator3_ext_tools.json"
    return next(
        item
        for item in json.loads(path.read_text())
        if item["name"] == "PubTator3_GetEntityRelations"
    )


def _response(records):
    response = Mock(status_code=200, text="")
    response.json.return_value = records
    return response


def test_later_ranked_edges_are_reachable_without_sending_fake_paging(monkeypatch):
    requested = {}

    def request(session, method, url, **kwargs):
        requested.update(kwargs["params"])
        return _response(
            [{"type": "associate", "publications": 100 - i} for i in range(8)]
        )

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    result = BaseRESTTool(_config()).run({"e1": "@GENE_BRAF", "limit": 3, "offset": 3})
    assert requested == {"e1": "@GENE_BRAF"}
    assert [row["publications"] for row in result["data"]] == [97, 96, 95]
    assert result["metadata"]["total_results"] == 8
    assert result["metadata"]["next_offset"] == 6
    assert result["metadata"]["pagination_scope"] == "client_side_full_response"


def test_relation_filters_remain_upstream(monkeypatch):
    requested = {}

    def request(session, method, url, **kwargs):
        requested.update(kwargs["params"])
        return _response([])

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    BaseRESTTool(_config()).run(
        {
            "e1": "@CHEMICAL_Doxorubicin",
            "type": "treat",
            "e2": "@DISEASE_Neoplasms",
            "limit": 5,
        }
    )
    assert requested == {
        "e1": "@CHEMICAL_Doxorubicin",
        "type": "treat",
        "e2": "@DISEASE_Neoplasms",
    }
