"""Regressions for NCI Drug Dictionary exact offset pagination."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config():
    path = Path(__file__).parents[2] / "src/tooluniverse/data/nci_drugdict_tools.json"
    return next(
        item
        for item in json.loads(path.read_text())
        if item["name"] == "NCIDrugDict_search"
    )


def _expand_config():
    path = (
        Path(__file__).parents[2]
        / "src/tooluniverse/data/clinical_guidelines_tools.json"
    )
    return next(
        item
        for item in json.loads(path.read_text())
        if item["name"] == "NCI_expand_drugs_by_letter"
    )


def _response(payload):
    response = Mock(status_code=200, text="")
    response.json.return_value = payload
    return response


def test_offset_maps_to_from_and_exact_total_drives_continuation(monkeypatch):
    requested = {}

    def request(session, method, url, **kwargs):
        requested.update(kwargs["params"])
        return _response(
            {
                "meta": {"totalResults": 8, "from": 3},
                "results": [{"termId": 4}, {"termId": 5}, {"termId": 6}],
            }
        )

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    result = BaseRESTTool(_config()).run(
        {"query": "kinase", "matchType": "Contains", "size": 3, "offset": 3}
    )
    assert requested == {
        "query": "kinase",
        "matchType": "Contains",
        "size": 3,
        "from": 3,
    }
    assert result["metadata"]["total_results"] == 8
    assert result["metadata"]["total_results_is_exact"] is True
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 6


def test_complete_first_page_is_marked_complete(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.base_rest_tool.request_with_retry",
        lambda *args, **kwargs: _response(
            {"meta": {"totalResults": 2, "from": 0}, "results": [{}, {}]}
        ),
    )
    metadata = BaseRESTTool(_config()).run({"query": "imatinib", "size": 10})[
        "metadata"
    ]
    assert metadata["has_more"] is False
    assert metadata["next_offset"] is None
    assert metadata["result_set_complete"] is True


def test_empty_page_before_reported_total_is_explicitly_stalled(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.base_rest_tool.request_with_retry",
        lambda *args, **kwargs: _response(
            {"meta": {"totalResults": 10, "from": 3}, "results": []}
        ),
    )
    metadata = BaseRESTTool(_config()).run({"query": "kinase", "size": 3, "offset": 3})[
        "metadata"
    ]
    assert metadata["pagination_stalled"] is True
    assert metadata["has_more"] is False
    assert metadata["warning"]


@pytest.mark.parametrize(
    "arguments, parameter",
    [
        ({"query": "x", "size": 0}, "size"),
        ({"query": "x", "size": True}, "size"),
        ({"query": "x", "offset": -1}, "offset"),
        ({"query": "x", "offset": 1.5}, "offset"),
    ],
)
def test_invalid_pagination_is_explicit(arguments, parameter):
    result = BaseRESTTool(_config()).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter


def test_alphabetical_expand_preserves_from_parameter_and_exact_navigation(monkeypatch):
    requested = {}

    def request(session, method, url, **kwargs):
        requested.update(kwargs["params"])
        return _response(
            {
                "meta": {"totalResults": 8688, "from": 3},
                "results": [{"termId": 4}, {"termId": 5}, {"termId": 6}],
            }
        )

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    result = BaseRESTTool(_expand_config()).run({"letter": "a", "size": 3, "from": 3})

    assert requested == {"size": 3, "from": 3}
    assert result["metadata"]["total_results"] == 8688
    assert result["metadata"]["offset"] == 3
    assert result["metadata"]["next_offset"] == 6


@pytest.mark.parametrize(
    "arguments,parameter",
    [
        ({"size": 0}, "size"),
        ({"size": 10001}, "size"),
        ({"size": True}, "size"),
        ({"from": -1}, "from"),
        ({"from": True}, "from"),
    ],
)
def test_alphabetical_expand_rejects_values_nci_silently_coerces(arguments, parameter):
    result = BaseRESTTool(_expand_config()).run({"letter": "a", **arguments})
    assert result["status"] == "error"
    assert result["parameter"] == parameter
