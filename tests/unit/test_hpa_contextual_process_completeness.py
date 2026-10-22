"""Regression guard for HPA contextual biological-process completeness."""

from unittest.mock import patch

from tooluniverse.hpa_tool import HPAGetContextualBiologicalProcessTool


def test_contextual_analysis_returns_every_biological_process():
    processes = [f"Process {i}" for i in range(11)]
    search_row = {
        "Gene": "BRCA1",
        "Gene synonym": "BRCC1",
        "Ensembl": "ENSG00000012048",
        "Biological process": processes,
    }
    expression = {"RNA tissue specific nTPM": {"breast": 2.5}}

    with (
        patch(
            "tooluniverse.hpa_tool.HPASearchApiTool._make_api_request",
            return_value=[search_row],
        ),
        patch(
            "tooluniverse.hpa_tool.HPAJsonApiTool._make_api_request",
            return_value=expression,
        ),
    ):
        result = HPAGetContextualBiologicalProcessTool({}).run(
            {"gene_name": "BRCA1", "context_name": "breast"}
        )

    data = result["data"]
    assert data["biological_processes"] == processes
    assert data["total_biological_processes"] == 11
    assert data["returned_biological_processes"] == 11
