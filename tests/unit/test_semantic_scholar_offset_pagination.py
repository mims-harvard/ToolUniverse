"""Regression tests for Semantic Scholar author offset pagination."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config(name):
    path = (
        Path(__file__).parents[2]
        / "src/tooluniverse/data/semantic_scholar_ext_tools.json"
    )
    return next(item for item in json.loads(path.read_text()) if item["name"] == name)


def _response(payload):
    response = Mock(status_code=200, text="")
    response.json.return_value = payload
    return response


@pytest.mark.parametrize(
    "name,path_args",
    [
        ("SemanticScholar_search_authors", {"query": "Jennifer Doudna"}),
        ("SemanticScholar_get_author_papers", {"author_id": "1741101"}),
        (
            "SemanticScholar_get_paper_citations",
            {"paper_id": "204e3073870fae3d05bcbc2f6a8e263d9b72e776"},
        ),
        (
            "SemanticScholar_get_paper_references",
            {"paper_id": "204e3073870fae3d05bcbc2f6a8e263d9b72e776"},
        ),
    ],
)
def test_upstream_next_is_exposed(monkeypatch, name, path_args):
    requested = {}

    def request(session, method, url, **kwargs):
        requested.update(kwargs["params"])
        return _response({"total": 12, "offset": 3, "next": 6, "data": [{}, {}, {}]})

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    result = BaseRESTTool(_config(name)).run({**path_args, "limit": 3, "offset": 3})
    assert requested["limit"] == 3
    assert requested["offset"] == 3
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 6
    assert result["metadata"]["total_results"] == 12


def test_author_papers_without_total_is_honest(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.base_rest_tool.request_with_retry",
        lambda *args, **kwargs: _response({"offset": 0, "next": 2, "data": [{}, {}]}),
    )
    metadata = BaseRESTTool(_config("SemanticScholar_get_author_papers")).run(
        {"author_id": "1741101", "limit": 2}
    )["metadata"]
    assert metadata["total_results"] is None
    assert metadata["total_results_is_exact"] is False
    assert metadata["matches_lower_bound"] == 3


def test_terminal_page_without_upstream_total_derives_exact_total(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.base_rest_tool.request_with_retry",
        lambda *args, **kwargs: _response({"offset": 6, "data": [{}, {}]}),
    )
    metadata = BaseRESTTool(_config("SemanticScholar_get_paper_references")).run(
        {
            "paper_id": "204e3073870fae3d05bcbc2f6a8e263d9b72e776",
            "limit": 3,
            "offset": 6,
        }
    )["metadata"]
    assert metadata["total_results"] == 8
    assert metadata["total_results_is_exact"] is True
    assert metadata["has_more"] is False
    assert metadata["result_set_complete"] is False


@pytest.mark.parametrize(
    "arguments, parameter",
    [
        ({"query": "x", "limit": 0}, "limit"),
        ({"query": "x", "limit": 1001}, "limit"),
        ({"query": "x", "limit": True}, "limit"),
        ({"query": "x", "offset": -1}, "offset"),
        ({"query": "x", "offset": 1.5}, "offset"),
    ],
)
def test_invalid_pagination_is_explicit(arguments, parameter):
    result = BaseRESTTool(_config("SemanticScholar_search_authors")).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
