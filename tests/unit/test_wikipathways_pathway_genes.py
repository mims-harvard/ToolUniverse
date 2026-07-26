"""WikiPathways_get_pathway_genes returned 0 genes for its own documented example.

``code`` defaulted to "H" (HGNC), which becomes a SPARQL filter on the
``dc:source`` database that annotated each gene product. WikiPathways rarely
records HGNC there: WP254's 87 gene products come from Entrez Gene (84) and
Ensembl (3), and none from HGNC. So the default answered "0 genes" -- with
status success -- for the pathway the tool's own description says returns 88.

Two smaller defects rode along: the "S" code mapped to the substring "Uniprot"
while the store writes "UniProtKB", and SPARQL CONTAINS is case-sensitive, so
that filter was permanently dead (WP3594 has 206 UniProt-sourced gene products
and returned 0). And gene_count deduplicated on rdfs:label, but one gene
product carries several alias labels (AKT, AKT1, Akt1), inflating WP254 from 87
genes to 134.
"""

from unittest.mock import patch

from tooluniverse.wikipathways_ext_tool import WikiPathwaysExtTool


def _make():
    return WikiPathwaysExtTool(
        {
            "name": "WikiPathways_get_pathway_genes",
            "type": "WikiPathwaysExtTool",
            "fields": {"endpoint": "get_pathway_genes"},
            "parameter": {"type": "object", "properties": {}},
        }
    )


def _bindings(rows):
    return {
        "results": {
            "bindings": [
                {"gene": {"value": g}, "gene_label": {"value": lbl}}
                for g, lbl in rows
            ]
        }
    }


# One gene product with three alias labels, plus two ordinary ones.
_ROWS = [
    ("http://identifiers.org/ncbigene/207", "AKT"),
    ("http://identifiers.org/ncbigene/207", "AKT1"),
    ("http://identifiers.org/ncbigene/207", "Akt1"),
    ("http://identifiers.org/ncbigene/317", "APAF1"),
    ("http://identifiers.org/ncbigene/7157", "TP53"),
]


def _run(arguments, rows=_ROWS):
    captured = {}

    def fake_sparql(query, timeout=30):
        captured["query"] = query
        return _bindings(rows)

    with patch(
        "tooluniverse.wikipathways_ext_tool._sparql", side_effect=fake_sparql
    ):
        result = _make().run(arguments)
    return result, captured.get("query", "")


def test_default_applies_no_source_filter():
    result, query = _run({"pathway_id": "WP254"})

    assert "FILTER(CONTAINS" not in query
    assert result["data"]["gene_count"] == 3
    assert result["data"]["identifier_type"] == "All sources"


def test_gene_count_counts_gene_products_not_alias_labels():
    result, _ = _run({"pathway_id": "WP254"})
    data = result["data"]

    # Five rows, three gene products, five distinct labels.
    assert data["gene_count"] == 3
    assert data["label_count"] == 5


def test_every_alias_is_still_reported_rather_than_one_being_guessed():
    # WikiPathways attaches unrelated symbols to a node (PIK3CA sits on the
    # AKT1 node), so picking a single label would fabricate a gene.
    result, _ = _run({"pathway_id": "WP254"})

    assert "AKT1" in result["data"]["genes"]
    assert "AKT" in result["data"]["genes"]


def test_gene_products_expose_node_level_truth():
    result, _ = _run({"pathway_id": "WP254"})
    products = result["data"]["gene_products"]

    assert len(products) == 3
    akt = next(p for p in products if p["identifier"].endswith("/207"))
    assert akt["labels"] == ["AKT", "AKT1", "Akt1"]


def test_uniprot_code_matches_the_stores_uniprotkb_spelling():
    _, query = _run({"pathway_id": "WP3594", "code": "S"})

    assert 'LCASE(STR(?src)), "uniprot"' in query


def test_source_filter_is_case_insensitive_for_every_code():
    for code in ("H", "En", "S", "L", "Ce"):
        _, query = _run({"pathway_id": "WP254", "code": code})
        assert "LCASE(STR(?src))" in query, code


def test_explicit_code_is_still_applied_and_labelled():
    result, query = _run({"pathway_id": "WP254", "code": "L"})

    assert 'LCASE(STR(?src)), "entrez gene"' in query
    assert result["data"]["identifier_type"] == "Entrez Gene"


def test_empty_result_stays_empty():
    result, _ = _run({"pathway_id": "WP254", "code": "S"}, rows=[])

    assert result["status"] == "success"
    assert result["data"]["gene_count"] == 0
    assert result["data"]["genes"] == []


def test_missing_pathway_id_is_an_error():
    assert _make().run({})["status"] == "error"
