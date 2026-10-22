"""Regressions for LINCS signature and library pagination."""

from unittest.mock import Mock

import pytest

from tooluniverse.lincs_tool import LINCSSignatureTool

pytestmark = pytest.mark.unit


def _tool(endpoint):
    return LINCSSignatureTool({"name": endpoint, "fields": {"endpoint_type": endpoint}})


def _response(payload):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


def test_signature_search_forwards_skip_and_uses_lookahead(monkeypatch):
    requested = {}
    signatures = [{"id": str(index), "meta": {}} for index in range(102)]

    def post(url, json, timeout):
        requested.update({"url": url, "json": json, "timeout": timeout})
        return _response(signatures)

    monkeypatch.setattr("tooluniverse.lincs_tool.requests.post", post)
    result = _tool("search_signatures").run(
        {"drug_name": "vorinostat", "limit": 101, "offset": 101}
    )
    assert requested["json"]["filter"]["limit"] == 102
    assert requested["json"]["filter"]["skip"] == 101
    assert len(result["data"]) == 101
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 202
    assert result["metadata"]["total_results"] is None


def test_library_filter_is_complete_before_pagination(monkeypatch):
    libraries = [
        {"id": str(index), "dataset": f"L1000 dataset {index}", "meta": {}}
        for index in range(5)
    ]
    monkeypatch.setattr(
        "tooluniverse.lincs_tool.requests.get",
        lambda *args, **kwargs: _response(libraries),
    )
    result = _tool("list_libraries").run(
        {"keyword": "L1000", "limit": 2, "offset": 2}
    )
    assert [row["library_id"] for row in result["data"]] == ["2", "3"]
    assert result["metadata"]["total_matches"] == 5
    assert result["metadata"]["next_offset"] == 4


@pytest.mark.parametrize(
    "arguments",
    [
        {"drug_name": "x", "limit": 0},
        {"drug_name": "x", "limit": 1001},
        {"drug_name": "x", "offset": -1},
        {"drug_name": "x", "offset": True},
    ],
)
def test_invalid_signature_pagination_is_explicit(arguments):
    result = _tool("search_signatures").run(arguments)
    assert result["status"] == "error"
