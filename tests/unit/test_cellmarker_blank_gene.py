"""Blank CellMarker gene symbols must fail locally without loading the table."""

from unittest.mock import patch

import pytest

from tooluniverse.cellmarker_tool import CellMarkerTool

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("gene_symbol", [None, "", "   ", "\t"])
def test_blank_gene_symbol_is_a_local_validation_error(gene_symbol):
    tool = CellMarkerTool({"name": "cellmarker_search_by_gene"})
    arguments = {"operation": "search_by_gene"}
    if gene_symbol is not None:
        arguments["gene_symbol"] = gene_symbol
    with patch("tooluniverse.cellmarker_tool._load_dataframe") as load:
        result = tool.run(arguments)

    load.assert_not_called()
    assert result["status"] == "error"
    assert "gene_symbol" in result["error"]
