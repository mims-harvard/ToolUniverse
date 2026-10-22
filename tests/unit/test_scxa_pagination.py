from unittest.mock import MagicMock, patch

from tooluniverse.scxa_tool import SCExpressionAtlasTool


def _response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def test_experiment_catalog_supports_offset():
    experiments = [
        {
            "experimentAccession": f"E-TEST-{index}",
            "experimentDescription": "human atlas",
            "species": "Homo sapiens",
        }
        for index in range(7)
    ]
    tool = SCExpressionAtlasTool({"fields": {"operation": "list_experiments"}})
    with patch(
        "tooluniverse.scxa_tool.requests.get",
        return_value=_response({"experiments": experiments}),
    ):
        result = tool._list_experiments(
            {"species": "Homo sapiens", "limit": 3, "offset": 3}
        )

    assert [row["accession"] for row in result["data"]] == [
        "E-TEST-3",
        "E-TEST-4",
        "E-TEST-5",
    ]
    assert result["metadata"]["total_matching"] == 7
    assert result["metadata"]["next_offset"] == 6


def test_marker_rows_report_full_count_and_tail_page():
    rows = [
        {
            "geneName": f"GENE{index}",
            "cellGroupValue": str(index % 8),
            "value": float(index),
        }
        for index in range(8)
    ]
    tool = SCExpressionAtlasTool(
        {"fields": {"operation": "cluster_marker_genes"}}
    )
    with patch(
        "tooluniverse.scxa_tool.requests.get", return_value=_response(rows)
    ):
        result = tool._cluster_marker_genes(
            {
                "experiment_accession": "E-TEST-1",
                "marker_type": "clusters",
                "k": 8,
                "limit": 3,
                "offset": 6,
            }
        )

    assert [row["gene_name"] for row in result["data"]] == ["GENE6", "GENE7"]
    assert result["metadata"]["num_markers"] == 8
    assert result["metadata"]["returned"] == 2
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_offset"] is None


def test_marker_rows_without_limit_preserve_all_rows_behavior():
    rows = [{"geneName": f"GENE{index}"} for index in range(5)]
    tool = SCExpressionAtlasTool(
        {"fields": {"operation": "cluster_marker_genes"}}
    )
    with patch(
        "tooluniverse.scxa_tool.requests.get", return_value=_response(rows)
    ):
        result = tool._cluster_marker_genes(
            {"experiment_accession": "E-TEST-1", "k": 2}
        )

    assert len(result["data"]) == 5
    assert result["metadata"]["limit"] is None
    assert result["metadata"]["has_more"] is False
