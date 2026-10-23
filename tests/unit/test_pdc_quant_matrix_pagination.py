from unittest.mock import patch

from tooluniverse.pdc_tool import PDCTool


@patch("tooluniverse.pdc_tool._execute_graphql")
def test_quant_matrix_gene_rows_are_paginated(mock_graphql):
    mock_graphql.return_value = {
        "ok": True,
        "data": {
            "quantDataMatrix": [
                ["gene", "sample-1"],
                ["A", 1.0],
                ["B", 2.0],
                ["C", 3.0],
                ["D", 4.0],
                ["E", 5.0],
            ]
        },
    }
    tool = PDCTool({})

    data = tool.run(
        {
            "operation": "get_quant_data_matrix",
            "pdc_study_id": "PDC000127",
            "max_genes": 2,
            "gene_offset": 2,
        }
    )["data"]

    assert [row[0] for row in data["matrix"]] == ["C", "D"]
    assert data["num_genes"] == 5
    assert data["has_more"] is True
    assert data["next_gene_offset"] == 4
