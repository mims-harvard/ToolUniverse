"""Regression tests for Hugging Face Hub Link cursor pagination."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config(name):
    path = Path(__file__).parents[2] / "src/tooluniverse/data/huggingface_tools.json"
    return next(item for item in json.loads(path.read_text()) if item["name"] == name)


def _response(records, link=""):
    response = Mock(status_code=200, text="")
    response.json.return_value = records
    response.headers = {"Link": link}
    return response


@pytest.mark.parametrize(
    "name", ["HuggingFace_search_models", "HuggingFace_search_datasets"]
)
def test_link_next_cursor_is_exposed_and_input_cursor_is_forwarded(monkeypatch, name):
    requested = {}
    next_value = "eyJ0ZXN0IjoiY3Vyc29yIn0="

    def request(session, method, url, **kwargs):
        requested.update(kwargs["params"])
        return _response(
            [{"id": "a"}, {"id": "b"}],
            f'<https://huggingface.co/api/models?limit=2&cursor={next_value}>; rel="next"',
        )

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    result = BaseRESTTool(_config(name)).run(
        {"search": "biology", "limit": 2, "cursor": "previous"}
    )
    assert requested["cursor"] == "previous"
    assert requested["limit"] == 2
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_cursor"] == next_value
    assert result["metadata"]["total_results"] is None
    assert result["metadata"]["pagination_scope"] == "upstream_opaque_cursor"


def test_missing_link_marks_complete_first_page(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.base_rest_tool.request_with_retry",
        lambda *args, **kwargs: _response([{"id": "only"}]),
    )
    metadata = BaseRESTTool(_config("HuggingFace_search_models")).run(
        {"search": "unique", "limit": 20}
    )["metadata"]
    assert metadata["has_more"] is False
    assert metadata["next_cursor"] is None
    assert metadata["result_set_complete"] is True


@pytest.mark.parametrize(
    "arguments, parameter",
    [
        ({"search": "x", "limit": 0}, "limit"),
        ({"search": "x", "limit": 1001}, "limit"),
        ({"search": "x", "limit": True}, "limit"),
        ({"search": "x", "cursor": ""}, "cursor"),
        ({"search": "x", "cursor": 4}, "cursor"),
    ],
)
def test_invalid_pagination_is_explicit(arguments, parameter):
    result = BaseRESTTool(_config("HuggingFace_search_models")).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
