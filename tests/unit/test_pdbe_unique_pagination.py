"""Regression tests for PDBe entity deduplication and reachable unique pages."""

import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.pdbe_search_tool import PDBeSearchTool
from tooluniverse.tools.PDBeSearch_search_structures import (
    PDBeSearch_search_structures,
)


def _tool(endpoint="search_structures"):
    return PDBeSearchTool(
        {"name": f"PDBe_{endpoint}", "fields": {"endpoint_type": endpoint}}
    )


def _response(docs, total):
    response = MagicMock()
    response.json.return_value = {"response": {"numFound": total, "docs": docs}}
    response.raise_for_status.return_value = None
    return response


def test_offset_is_applied_after_pdb_id_deduplication():
    docs = [
        {"pdb_id": "1aaa", "title": "first entity"},
        {"pdb_id": "1aaa", "title": "duplicate entity"},
        {"pdb_id": "2bbb"},
        {"pdb_id": "3ccc"},
        {"pdb_id": "4ddd"},
        {"pdb_id": "5eee"},
    ]
    with patch(
        "tooluniverse.pdbe_search_tool.requests.get",
        return_value=_response(docs, total=6),
    ) as get:
        result = _tool().run(
            {"query": "kinase", "limit": 2, "offset": 2, "max_rows_scanned": 20}
        )

    assert [item["pdb_id"] for item in result["data"]] == ["3ccc", "4ddd"]
    assert (
        get.call_args.kwargs["params"]["sort"] == "score desc,resolution asc,pdb_id asc"
    )
    assert result["metadata"]["next_offset"] == 4
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["page_complete"] is True


def test_scan_budget_exhaustion_is_explicit_instead_of_silent_short_page():
    duplicate_docs = [{"pdb_id": "1aaa"}, {"pdb_id": "1aaa"}, {"pdb_id": "1aaa"}]
    with patch(
        "tooluniverse.pdbe_search_tool.requests.get",
        return_value=_response(duplicate_docs, total=10),
    ):
        result = _tool().run({"query": "ribosome", "limit": 2, "max_rows_scanned": 3})

    assert len(result["data"]) == 1
    assert result["metadata"]["page_complete"] is False
    assert result["metadata"]["scan_limit_reached"] is True
    assert "Increase max_rows_scanned" in result["metadata"]["warning"]


def test_organism_search_forwards_rows_above_old_fifty_cap():
    with patch(
        "tooluniverse.pdbe_search_tool.requests.get",
        return_value=_response([{"pdb_id": "1aaa"}], total=100),
    ) as get:
        result = _tool("search_by_organism").run(
            {"organism": "Homo sapiens", "limit": 51, "start": 0}
        )

    assert result["status"] == "success"
    assert get.call_args.kwargs["params"]["rows"] == 51


@pytest.mark.parametrize(
    "arguments",
    [
        {"query": "kinase", "limit": 0},
        {"query": "kinase", "limit": 1001},
        {"query": "kinase", "offset": -1},
        {"query": "kinase", "max_rows_scanned": 0},
        {"query": "kinase", "max_rows_scanned": 200001},
    ],
)
def test_invalid_unique_pagination_is_rejected(arguments):
    with patch("tooluniverse.pdbe_search_tool.requests.get") as get:
        result = _tool().run(arguments)

    assert result["status"] == "error"
    get.assert_not_called()


def test_config_and_wrapper_expose_unique_offset_and_scan_budget():
    config_path = (
        Path(__file__).parents[2]
        / "src"
        / "tooluniverse"
        / "data"
        / "pdbe_search_tools.json"
    )
    configs = {item["name"]: item for item in json.loads(config_path.read_text())}
    properties = configs["PDBeSearch_search_structures"]["parameter"]["properties"]

    assert properties["limit"]["maximum"] == 1000
    assert "offset" in properties
    assert "max_rows_scanned" in properties
    signature = inspect.signature(PDBeSearch_search_structures).parameters
    assert "offset" in signature
    assert "max_rows_scanned" in signature
