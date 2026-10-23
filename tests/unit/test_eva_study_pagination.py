"""Regression tests for EVA study-list ordering and local pagination."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config():
    path = Path(__file__).parents[2] / "src/tooluniverse/data/eva_tools.json"
    return next(
        item
        for item in json.loads(path.read_text())
        if item["name"] == "EVA_list_studies"
    )


def test_upstream_order_is_sorted_before_local_page(monkeypatch):
    requested = {}
    response = Mock(status_code=200, text="")
    response.json.return_value = {
        "response": [
            {
                "numResults": 5,
                "numTotalResults": 5,
                "result": [
                    {"studyId": "S5"},
                    {"studyId": "S2"},
                    {"studyId": "S4"},
                    {"studyId": "S1"},
                    {"studyId": "S3"},
                ],
            }
        ]
    }

    def request(session, method, url, **kwargs):
        requested.update(kwargs["params"])
        return response

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    result = BaseRESTTool(_config()).run(
        {"species": "hsapiens_grch38", "limit": 2, "offset": 2}
    )

    assert requested == {"species": "hsapiens_grch38"}
    page = result["data"]["response"][0]
    assert [item["studyId"] for item in page["result"]] == ["S3", "S4"]
    assert page["numResults"] == 2
    assert result["metadata"]["next_offset"] == 4
    assert result["metadata"]["total_results"] == 5
    assert result["metadata"]["upstream_total_consistent"] is True


@pytest.mark.parametrize(
    "arguments, parameter",
    [
        ({"limit": 0}, "limit"),
        ({"limit": 1001}, "limit"),
        ({"offset": -1}, "offset"),
        ({"offset": 1.5}, "offset"),
    ],
)
def test_invalid_pagination_is_explicit(arguments, parameter):
    result = BaseRESTTool(_config()).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
