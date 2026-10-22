from unittest.mock import MagicMock, patch

from tooluniverse.alliance_genome_tool import AllianceGenomeTool


def _tool(endpoint="search_genes"):
    return AllianceGenomeTool({"fields": {"endpoint_type": endpoint}})


def _response(total=5):
    response = MagicMock()
    response.json.return_value = {
        "total": total,
        "results": [
            {
                "symbol": f"G{index}",
                "name": f"gene {index}",
                "curie": f"HGNC:{index}",
                "species": "Homo sapiens",
                "category": "gene_search_result",
            }
            for index in range(2, 4)
        ],
    }
    response.raise_for_status.return_value = None
    return response


@patch("tooluniverse.alliance_genome_tool.requests.get", return_value=_response())
def test_search_uses_real_upstream_offset_and_total(mock_get):
    result = _tool().run({"query": "TP53", "limit": 2, "offset": 2})

    assert [row["gene_id"] for row in result["data"]] == ["HGNC:2", "HGNC:3"]
    assert result["metadata"]["total_results"] == 5
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 4
    assert mock_get.call_args.kwargs["params"] == {
        "q": "TP53",
        "category": "gene_search_result",
        "limit": 2,
        "offset": 2,
    }


@patch("tooluniverse.alliance_genome_tool.requests.get", return_value=_response())
def test_species_search_filters_upstream_before_pagination(mock_get):
    result = _tool("zfin_search").run({"query": "tp53", "limit": 2, "offset": 2})

    assert result["metadata"]["species"] == "Danio rerio"
    assert mock_get.call_args.kwargs["params"]["species"] == "Danio rerio"


def test_search_rejects_invalid_pagination_without_request():
    with patch("tooluniverse.alliance_genome_tool.requests.get") as mock_get:
        assert "1 to 50" in _tool().run({"query": "TP53", "limit": 51})["error"]
        assert "non-negative" in _tool().run({"query": "TP53", "offset": -1})["error"]
    mock_get.assert_not_called()
