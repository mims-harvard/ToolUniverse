from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.hgnc_tool import HGNCTool


pytestmark = pytest.mark.unit


def _tool(endpoint="fetch", search_field="symbol"):
    return HGNCTool({"fields": {"endpoint": endpoint, "search_field": search_field}})


def _response(docs, num_found=None, start=0):
    response = MagicMock()
    response.json.return_value = {
        "response": {
            "docs": docs,
            "numFound": len(docs) if num_found is None else num_found,
            "start": start,
        }
    }
    return response


@pytest.mark.parametrize("value", [None, 1, " "])
def test_symbol_fetch_rejects_non_string_or_empty_values(value):
    with patch("tooluniverse.hgnc_tool.requests.get") as get:
        result = _tool().run({"symbol": value})
    assert result["status"] == "error"
    get.assert_not_called()


@pytest.mark.parametrize("value", ["HGNC:abc", "abc", 11998, True])
def test_hgnc_id_fetch_requires_a_numeric_string(value):
    with patch("tooluniverse.hgnc_tool.requests.get") as get:
        result = _tool(search_field="hgnc_id").run({"hgnc_id": value})
    assert result["status"] == "error"
    get.assert_not_called()


def test_hgnc_id_prefix_is_normalized_and_exact_result_verified():
    doc = {"hgnc_id": "HGNC:11998", "symbol": "TP53"}
    with patch(
        "tooluniverse.hgnc_tool.requests.get", return_value=_response([doc])
    ) as get:
        result = _tool(search_field="hgnc_id").run({"hgnc_id": "hgnc:11998"})
    assert "/fetch/hgnc_id/HGNC:11998" in get.call_args.args[0]
    assert result["data"]["symbol"] == "TP53"
    assert result["metadata"]["exact_identifier_verified"] is True
    assert result["metadata"]["result_set_complete"] is True


def test_exact_fetch_rejects_a_different_returned_symbol():
    doc = {"hgnc_id": "HGNC:1100", "symbol": "BRCA1"}
    with patch("tooluniverse.hgnc_tool.requests.get", return_value=_response([doc])):
        result = _tool().run({"symbol": "TP53"})
    assert result["status"] == "error"
    assert result["returned_value"] == "BRCA1"


@pytest.mark.parametrize(
    "response",
    [
        _response([{"symbol": "A"}], num_found=2),
        _response([{"symbol": "A"}], start=1),
    ],
)
def test_partial_upstream_response_is_an_error(response):
    with patch("tooluniverse.hgnc_tool.requests.get", return_value=response):
        result = _tool(endpoint="search", search_field=None).run({"query": "A"})
    assert result["status"] == "error"
    assert "partial result set" in result["error"]


def test_search_returns_full_unpaginated_count_and_encodes_path():
    docs = [{"symbol": "BRCA1"}, {"symbol": "BRCA2"}]
    with patch(
        "tooluniverse.hgnc_tool.requests.get", return_value=_response(docs)
    ) as get:
        result = _tool(endpoint="search", search_field=None).run(
            {"query": "BRCA*/test"}
        )
    assert "BRCA*%2Ftest" in get.call_args.args[0]
    assert result["metadata"]["total_results"] == 2
    assert result["metadata"]["returned"] == 2
    assert result["metadata"]["result_set_complete"] is True
    assert result["metadata"]["pagination_supported"] is False


@pytest.mark.parametrize(
    "arguments",
    [
        {"query": 1},
        {"query": "TP53", "search_field": "unsupported"},
        {"query": "TP53", "search_field": 1},
    ],
)
def test_search_rejects_invalid_query_controls_before_network(arguments):
    with patch("tooluniverse.hgnc_tool.requests.get") as get:
        result = _tool(endpoint="search", search_field=None).run(arguments)
    assert result["status"] == "error"
    get.assert_not_called()


def test_group_fetch_verifies_every_member_and_count():
    docs = [
        {"hgnc_id": "HGNC:1", "gene_group_id": [366]},
        {"hgnc_id": "HGNC:2", "gene_group_id": [100, 366]},
    ]
    with patch("tooluniverse.hgnc_tool.requests.get", return_value=_response(docs)):
        result = _tool(search_field="gene_group_id").run({"gene_group_id": 366})
    assert result["metadata"]["num_found"] == 2
    assert result["metadata"]["returned"] == 2
    assert result["metadata"]["result_set_complete"] is True


def test_group_fetch_rejects_out_of_group_record():
    docs = [{"hgnc_id": "HGNC:1", "gene_group_id": [100]}]
    with patch("tooluniverse.hgnc_tool.requests.get", return_value=_response(docs)):
        result = _tool(search_field="gene_group_id").run({"gene_group_id": "366"})
    assert result["status"] == "error"
    assert result["invalid_members"] == ["HGNC:1"]
