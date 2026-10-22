from tooluniverse.panglaodb_tool import PanglaoDBMarkerTool


def _row(index, *, gene="GENE", cell_type="T cells"):
    return {
        "gene_symbol": gene,
        "cell_type": cell_type,
        "organ": f"Organ {index}",
        "germ_layer": None,
        "species": "Hs",
        "species_tokens": ["Hs"],
        "canonical_marker": index % 2 == 0,
        "nicknames": None,
        "product_description": None,
        "gene_type": None,
        "ubiquitousness_index": None,
        "sensitivity_human": None,
        "sensitivity_mouse": None,
        "specificity_human": float(100 - index),
        "specificity_mouse": None,
    }


def _tool(operation):
    return PanglaoDBMarkerTool({"fields": {"operation": operation}})


def test_markers_for_cell_type_supports_adjacent_pages():
    rows = [_row(i) for i in range(7)]
    tool = _tool("markers_for_cell_type")

    first = tool._markers_for_cell_type(
        {"cell_type": "T cells", "limit": 3}, rows
    )
    second = tool._markers_for_cell_type(
        {"cell_type": "T cells", "limit": 3, "offset": 3}, rows
    )

    assert [row["organ"] for row in first["data"]] != [
        row["organ"] for row in second["data"]
    ]
    assert first["metadata"] == {
        "source": "PanglaoDB (panglaodb.se)",
        "cell_type": "T cells",
        "species_filter": None,
        "organ_filter": None,
        "canonical_only": False,
        "total_matching": 7,
        "returned": 3,
        "offset": 0,
        "limit": 3,
        "has_more": True,
        "next_offset": 3,
    }
    assert second["metadata"]["next_offset"] == 6


def test_markers_for_cell_type_tail_page_terminates():
    result = _tool("markers_for_cell_type")._markers_for_cell_type(
        {"cell_type": "T cells", "limit": 3, "offset": 6},
        [_row(i) for i in range(7)],
    )

    assert len(result["data"]) == 1
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_offset"] is None


def test_cell_types_for_gene_supports_offset():
    rows = [_row(i, gene="EPCAM", cell_type=f"Cell {i}") for i in range(5)]
    result = _tool("cell_types_for_gene")._cell_types_for_gene(
        {"gene": "EPCAM", "limit": 2, "offset": 2}, rows
    )

    assert [row["cell_type"] for row in result["data"]] == ["Cell 2", "Cell 3"]
    assert result["metadata"]["total_matching"] == 5
    assert result["metadata"]["next_offset"] == 4


def test_pagination_rejects_invalid_values():
    rows = [_row(0)]
    tool = _tool("markers_for_cell_type")

    bad_limit = tool._markers_for_cell_type(
        {"cell_type": "T cells", "limit": 0}, rows
    )
    bad_offset = tool._markers_for_cell_type(
        {"cell_type": "T cells", "offset": -1}, rows
    )

    assert bad_limit == {"status": "error", "error": "limit must be a positive integer"}
    assert bad_offset == {
        "status": "error",
        "error": "offset must be a non-negative integer",
    }
