from unittest.mock import patch

import pytest

from tooluniverse.wikipathways_ext_tool import WikiPathwaysExtTool


def _binding(**values):
    return {key: {"value": value} for key, value in values.items()}


def _tool():
    return WikiPathwaysExtTool(
        {
            "name": "WikiPathways_find_pathways_by_gene",
            "fields": {"endpoint": "find_pathways_by_gene"},
        }
    )


def test_gene_search_exposes_exact_total_and_stable_offset_page():
    captured = []

    def fake_sparql(query, timeout=30):
        captured.append(query)
        if "COUNT(DISTINCT ?pathway)" in query:
            return {"results": {"bindings": [_binding(total="172")]}}
        return {
            "results": {
                "bindings": [
                    _binding(
                        pathway=f"https://identifiers.org/wikipathways/WP{i}_r1",
                        title=f"AKT pathway {i}",
                        organism="Homo sapiens",
                    )
                    for i in (51, 52, 53)
                ]
            }
        }

    with patch("tooluniverse.wikipathways_ext_tool._sparql", side_effect=fake_sparql):
        result = _tool().run(
            {"gene": "AKT1", "species": "Homo sapiens", "limit": 2, "offset": 50}
        )

    assert result["data"]["total_pathways"] == 172
    assert result["data"]["returned"] == 2
    assert [row["id"] for row in result["data"]["pathways"]] == ["WP51", "WP52"]
    assert result["metadata"]["total_pathways_is_exact"] is True
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 52
    page_query = next(q for q in captured if "COUNT(DISTINCT" not in q)
    assert "ORDER BY" in page_query
    assert "LIMIT 3" in page_query
    assert "OFFSET 50" in page_query


def test_gene_search_marks_empty_midstream_page_as_stalled():
    def fake_sparql(query, timeout=30):
        if "COUNT(DISTINCT ?pathway)" in query:
            return {"results": {"bindings": [_binding(total="172")]}}
        return {"results": {"bindings": []}}

    with patch("tooluniverse.wikipathways_ext_tool._sparql", side_effect=fake_sparql):
        result = _tool().run({"gene": "AKT1", "offset": 50})

    assert result["metadata"]["pagination_stalled"] is True
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_offset"] is None
    assert result["metadata"]["complete"] is False


def test_gene_and_species_are_safely_escaped_in_both_queries():
    queries = []

    def fake_sparql(query, timeout=30):
        queries.append(query)
        if "COUNT(DISTINCT ?pathway)" in query:
            return {"results": {"bindings": [_binding(total="0")]}}
        return {"results": {"bindings": []}}

    with patch("tooluniverse.wikipathways_ext_tool._sparql", side_effect=fake_sparql):
        _tool().run({"gene": 'A"\\B', "species": 'Homo "sapiens"'})

    assert all('A\\"\\\\B' in query for query in queries)
    assert all('homo \\"sapiens\\"' in query for query in queries)


@pytest.mark.parametrize(
    ("arguments", "field"),
    [
        ({"gene": ""}, "gene"),
        ({"gene": "AKT1", "species": []}, "species"),
        ({"gene": "AKT1", "limit": "50"}, "limit"),
        ({"gene": "AKT1", "limit": 101}, "limit"),
        ({"gene": "AKT1", "offset": -1}, "offset"),
    ],
)
def test_invalid_controls_are_rejected_before_sparql(arguments, field):
    with patch("tooluniverse.wikipathways_ext_tool._sparql") as sparql:
        result = _tool().run(arguments)

    assert result["status"] == "error"
    assert field in result["error"]
    sparql.assert_not_called()
