from unittest.mock import Mock, patch

import pytest

from tooluniverse.wikipathways_tool import (
    WikiPathwaysGetTool,
    WikiPathwaysSearchTool,
)


def _binding(**values):
    return {key: {"value": value} for key, value in values.items()}


def test_search_overfetches_with_stable_offset_navigation():
    captured = {}

    def fake_sparql(query, timeout=30):
        captured["query"] = query
        return {
            "results": {
                "bindings": [
                    _binding(
                        pathway=f"https://identifiers.org/wikipathways/WP{i}_r1",
                        title=f"Cancer {i}",
                        organism="Homo sapiens",
                    )
                    for i in (5, 6, 7)
                ]
            }
        }

    with patch("tooluniverse.wikipathways_tool._sparql", side_effect=fake_sparql):
        result = WikiPathwaysSearchTool().run(
            {"query": "cancer", "limit": 2, "offset": 4}
        )

    assert [row["wpid"] for row in result["data"]] == ["WP5", "WP6"]
    assert result["metadata"]["returned"] == 2
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 6
    assert result["metadata"]["total_hits_is_known"] is False
    assert "ORDER BY" in captured["query"]
    assert "LIMIT 3" in captured["query"]
    assert "OFFSET 4" in captured["query"]


@pytest.mark.parametrize(
    ("arguments", "field"),
    [
        ({"query": ""}, "query"),
        ({"query": "cancer", "limit": "2"}, "limit"),
        ({"query": "cancer", "limit": 201}, "limit"),
        ({"query": "cancer", "offset": -1}, "offset"),
        ({"query": "cancer", "organism": []}, "organism"),
    ],
)
def test_search_rejects_invalid_controls_without_network(arguments, field):
    with patch("tooluniverse.wikipathways_tool._sparql") as sparql:
        result = WikiPathwaysSearchTool().run(arguments)

    assert result["status"] == "error"
    assert field in result["error"]
    sparql.assert_not_called()


def test_search_escapes_sparql_literals():
    with patch(
        "tooluniverse.wikipathways_tool._sparql",
        return_value={"results": {"bindings": []}},
    ) as sparql:
        WikiPathwaysSearchTool().run(
            {"query": 'A"\\B\nC', "organism": 'Homo "sapiens"'}
        )

    query = sparql.call_args.args[0]
    assert 'a\\"\\\\b\\nc' in query
    assert 'homo \\"sapiens\\"' in query


def _pathway_side_effect(page_rows, total_rows=5, products=4):
    def fake_sparql(query, timeout=30):
        if "COUNT(*)" in query:
            return {
                "results": {
                    "bindings": [
                        _binding(
                            total_rows=str(total_rows), gene_products=str(products)
                        )
                    ]
                }
            }
        if "SELECT DISTINCT ?gene_id" in query:
            return {"results": {"bindings": page_rows}}
        return {
            "results": {
                "bindings": [
                    _binding(
                        pathway="https://identifiers.org/wikipathways/WP310_r1",
                        title="mRNA processing",
                        organism="Mus musculus",
                    )
                ]
            }
        }

    return fake_sparql


def test_get_pathway_exposes_exact_gene_totals_and_recoverable_pages():
    rows = [
        _binding(gene_id=f"id:{i}", gene_label=f"G{i}", datasource="Entrez Gene")
        for i in range(3)
    ]
    with patch(
        "tooluniverse.wikipathways_tool._sparql",
        side_effect=_pathway_side_effect(rows),
    ) as sparql:
        result = WikiPathwaysGetTool().run(
            {"wpid": "wp310", "gene_limit": 2, "gene_offset": 0}
        )

    assert result["data"]["gene_count"] == 5
    assert result["data"]["gene_product_count"] == 4
    assert [row["label"] for row in result["data"]["genes"]] == ["G0", "G1"]
    assert result["metadata"]["total_gene_rows"] == 5
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_gene_offset"] == 2
    gene_query = next(
        call.args[0]
        for call in sparql.call_args_list
        if "SELECT DISTINCT ?gene_id" in call.args[0]
    )
    assert "ORDER BY" in gene_query
    assert "LIMIT 3" in gene_query
    assert "OFFSET 0" in gene_query


def test_get_pathway_marks_upstream_pagination_stall_instead_of_complete():
    with patch(
        "tooluniverse.wikipathways_tool._sparql",
        side_effect=_pathway_side_effect([], total_rows=549, products=549),
    ):
        result = WikiPathwaysGetTool().run(
            {"wpid": "WP310", "gene_limit": 200, "gene_offset": 200}
        )

    assert result["metadata"]["pagination_stalled"] is True
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_gene_offset"] is None
    assert result["metadata"]["complete"] is False


def test_get_pathway_gpml_fetches_the_documented_static_asset():
    with patch(
        "tooluniverse.wikipathways_tool._fetch_gpml",
        return_value="<Pathway />",
    ) as fetch:
        result = WikiPathwaysGetTool().run({"wpid": "WP254", "format": "gpml"})

    assert result["status"] == "success"
    assert result["data"]["format"] == "gpml"
    assert result["data"]["gpml"] == "<Pathway />"
    assert result["metadata"]["complete"] is True
    assert result["data"]["source_url"].endswith("/WP254/WP254.gpml")
    fetch.assert_called_once_with("WP254", timeout=30)


@pytest.mark.parametrize(
    ("arguments", "field"),
    [
        ({"wpid": 310}, "wpid"),
        ({"wpid": "310"}, "wpid"),
        ({"wpid": "WP310", "format": "xml"}, "format"),
        ({"wpid": "WP310", "gene_limit": 0}, "gene_limit"),
        ({"wpid": "WP310", "gene_offset": "0"}, "gene_offset"),
    ],
)
def test_get_pathway_rejects_invalid_controls_without_network(arguments, field):
    with patch("tooluniverse.wikipathways_tool._sparql") as sparql:
        result = WikiPathwaysGetTool().run(arguments)

    assert result["status"] == "error"
    assert field in result["error"]
    sparql.assert_not_called()
