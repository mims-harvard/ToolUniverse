"""Regression tests for EVA variant skip pagination."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config(name):
    path = Path(__file__).parents[2] / "src/tooluniverse/data/eva_tools.json"
    return next(item for item in json.loads(path.read_text()) if item["name"] == name)


def _response(payload):
    response = Mock(status_code=200, text="")
    response.json.return_value = payload
    return response


@pytest.mark.parametrize(
    "name,path_arg",
    [
        ("EVA_get_variants_by_gene", {"gene": "BRCA1"}),
        ("EVA_get_variants_by_region", {"region": "17:43000000-43100000"}),
    ],
)
def test_offset_maps_to_skip_and_total_drives_continuation(monkeypatch, name, path_arg):
    requested = {}

    def request(session, method, url, **kwargs):
        requested.update(kwargs["params"])
        return _response(
            {
                "response": [
                    {
                        "numResults": 3,
                        "numTotalResults": 10,
                        "result": [{"start": 4}, {"start": 5}, {"start": 6}],
                    }
                ]
            }
        )

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    result = BaseRESTTool(_config(name)).run(
        {**path_arg, "species": "hsapiens_grch38", "limit": 3, "offset": 3}
    )
    assert requested == {"species": "hsapiens_grch38", "limit": 3, "skip": 3}
    assert result["metadata"]["total_results"] == 10
    assert result["metadata"]["upstream_total_results"] == 10
    assert result["metadata"]["upstream_total_inconsistent"] is False
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 6
    assert result["metadata"]["offset_must_align_to_limit"] is True


def test_complete_first_page_is_marked_complete(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.base_rest_tool.request_with_retry",
        lambda *args, **kwargs: _response(
            {"response": [{"numResults": 1, "numTotalResults": 1, "result": [{}]}]}
        ),
    )
    metadata = BaseRESTTool(_config("EVA_get_variants_by_gene")).run(
        {"gene": "TP53", "limit": 20}
    )["metadata"]
    assert metadata["result_set_complete"] is True
    assert metadata["has_more"] is False


def test_conflicting_region_total_is_rejected_and_full_page_continues(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.base_rest_tool.request_with_retry",
        lambda *args, **kwargs: _response(
            {
                "response": [
                    {
                        "numResults": 3,
                        "numTotalResults": 0,
                        "result": [{"start": 1}, {"start": 2}, {"start": 3}],
                    }
                ]
            }
        ),
    )
    metadata = BaseRESTTool(_config("EVA_get_variants_by_region")).run(
        {"region": "17:1-100", "limit": 3, "offset": 0}
    )["metadata"]
    assert metadata["upstream_total_results"] == 0
    assert metadata["upstream_total_inconsistent"] is True
    assert metadata["total_results"] is None
    assert metadata["total_results_is_exact"] is False
    assert metadata["has_more"] is True
    assert metadata["next_offset"] == 3
    assert metadata["warning"]


@pytest.mark.parametrize(
    "arguments, parameter",
    [
        ({"gene": "TP53", "limit": 0}, "limit"),
        ({"gene": "TP53", "limit": 1001}, "limit"),
        ({"gene": "TP53", "limit": True}, "limit"),
        ({"gene": "TP53", "offset": -1}, "offset"),
        ({"gene": "TP53", "offset": 1.5}, "offset"),
        ({"gene": "TP53", "limit": 3, "offset": 4}, "offset"),
    ],
)
def test_invalid_or_unaligned_pagination_is_explicit(arguments, parameter):
    result = BaseRESTTool(_config("EVA_get_variants_by_gene")).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
