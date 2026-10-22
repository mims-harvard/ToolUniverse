"""Round 227: mixed Harmonizome suggestions must not hide resolution failures."""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.harmonizome_tool import HarmonizomeTool

pytestmark = pytest.mark.unit


def _tool():
    return HarmonizomeTool({"fields": {"endpoint": "search"}, "timeout": 30})


def _response(payload=None, status=200):
    response = MagicMock(status_code=status)
    response.json.return_value = payload
    return response


def _gene(symbol):
    return {"symbol": symbol, "name": f"name-{symbol}", "ncbiEntrezGeneId": 1}


def test_mixed_suggestions_count_non_genes_and_page_only_resolved_genes():
    """404 suggestion candidates are expected mixed entities, not gene records."""
    responses = [
        _response(_gene("TP53")),
        _response(["TP53TG3B", "TP53 pathway", "TP53TG3C", "unused"]),
        _response(_gene("TP53TG3B")),
        _response({"status": 400, "message": "Bad request."}),
        _response(_gene("TP53TG3C")),
        _response(status=404),
    ]
    with patch("tooluniverse.harmonizome_tool.requests.get", side_effect=responses):
        result = _tool().run(
            {"query": "TP53", "entity_type": "gene", "limit": 2, "offset": 1}
        )

    assert result["status"] == "success"
    assert [row["symbol"] for row in result["data"]] == ["TP53TG3B", "TP53TG3C"]
    metadata = result["metadata"]
    assert metadata["suggestions_examined"] == 4
    assert metadata["rejected_non_gene_suggestions"] == 2
    assert metadata["has_more"] is False
    assert metadata["suggestions_exhausted"] is True
    assert metadata["total_results_known"] is True
    assert metadata["total_results"] == 3


@pytest.mark.parametrize("failure", [Exception("timeout"), _response(status=503)])
def test_suggestion_resolution_failure_cannot_become_short_success(failure):
    """An unresolved candidate can change the page, so the search must fail closed."""
    responses = [
        _response(_gene("TP53")),
        _response(["TP53TG3B"]),
        failure,
    ]
    with patch("tooluniverse.harmonizome_tool.requests.get", side_effect=responses):
        result = _tool().run(
            {"query": "TP53", "entity_type": "gene", "limit": 2}
        )

    assert result["status"] == "error"
    assert result["search_stage"] == "suggestion_gene_resolution"
    assert result["candidate"] == "TP53TG3B"
    assert "data" not in result


def test_suggestion_lookup_failure_does_not_return_exact_only_success():
    """Exact lookup success is not a complete search if suggestions are unavailable."""
    with patch(
        "tooluniverse.harmonizome_tool.requests.get",
        side_effect=[_response(_gene("TP53")), _response(status=503)],
    ):
        result = _tool().run({"query": "TP53", "entity_type": "gene"})
    assert result["status"] == "error"
    assert result["search_stage"] == "suggestion_lookup"


@pytest.mark.parametrize(
    "arguments,fragment",
    [
        ({"query": "TP53", "entity_type": "gene", "limit": 0}, "limit"),
        ({"query": "TP53", "entity_type": "gene", "limit": True}, "limit"),
        ({"query": "TP53", "entity_type": "gene", "offset": -1}, "offset"),
    ],
)
def test_invalid_pagination_fails_before_network(arguments, fragment):
    """Paging values cannot be silently clamped into another request."""
    with patch("tooluniverse.harmonizome_tool.requests.get") as request:
        result = _tool().run(arguments)
    assert result["status"] == "error"
    assert fragment in result["error"]
    request.assert_not_called()
