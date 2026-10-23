"""Regression tests for complete STRING interaction-partner pagination."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config():
    path = Path(__file__).parents[2] / "src/tooluniverse/data/string_network_tools.json"
    return next(
        item
        for item in json.loads(path.read_text())
        if item["name"] == "STRING_get_interaction_partners"
    )


def _response(records):
    response = Mock(status_code=200, text="")
    response.json.return_value = records
    return response


def test_upstream_requests_all_and_local_page_keeps_rank_order(monkeypatch):
    requested = {}

    def request(session, method, url, **kwargs):
        requested.update(kwargs["params"])
        return _response(
            [{"preferredName_B": f"P{i}", "score": 1 - i / 100} for i in range(8)]
        )

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    result = BaseRESTTool(_config()).run(
        {"identifiers": "TP53", "species": 9606, "limit": 3, "offset": 3}
    )
    assert requested == {"limit": 0, "identifiers": "TP53", "species": 9606}
    assert [row["preferredName_B"] for row in result["data"]] == ["P3", "P4", "P5"]
    assert result["metadata"]["total_results"] == 8
    assert result["metadata"]["next_offset"] == 6


def test_score_filter_remains_upstream(monkeypatch):
    requested = {}

    def request(session, method, url, **kwargs):
        requested.update(kwargs["params"])
        return _response([])

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    BaseRESTTool(_config()).run(
        {"identifiers": "TP53", "required_score": 900, "limit": 5}
    )
    assert requested["required_score"] == 900
    assert requested["limit"] == 0
