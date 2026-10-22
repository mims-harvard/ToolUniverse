from unittest.mock import Mock, patch

import pytest

from tooluniverse.alliance_genome_tool import AllianceGenomeTool


@pytest.mark.parametrize(
    ("endpoint_type", "arguments", "payload"),
    [
        (
            "gene_phenotypes",
            {"gene_id": "HGNC:11998"},
            {"total": 5, "results": [{"subject": {}}] * 2},
        ),
        (
            "disease_genes",
            {"disease_id": "DOID:162"},
            {"total": 5, "results": [{"subject": {}, "object": {}}] * 2},
        ),
        (
            "gene_molecular_interactions",
            {"gene_id": "MGI:97490"},
            {"total": 5, "results": [{"geneMolecularInteraction": {}}] * 2},
        ),
    ],
)
def test_alliance_paginated_operations_expose_exact_continuation(
    endpoint_type, arguments, payload
):
    tool = AllianceGenomeTool(
        {"name": "test", "fields": {"endpoint_type": endpoint_type}}
    )
    response = Mock(status_code=200)
    response.json.return_value = payload
    response.raise_for_status.return_value = None

    with patch("tooluniverse.alliance_genome_tool.requests.get", return_value=response):
        if endpoint_type == "gene_molecular_interactions":
            tool._alliance_get = Mock(return_value=payload)
        result = tool.run({**arguments, "limit": 2, "page": 1})

    metadata = result["metadata"]
    assert metadata["total_results"] == 5
    assert metadata["returned"] == 2
    assert metadata["limit"] == 2
    assert metadata["page"] == 1
    assert metadata["total_pages"] == 3
    assert metadata["has_more"] is True
    assert metadata["next_page"] == 2
    assert metadata["result_set_complete"] is False


@pytest.mark.parametrize(
    "arguments",
    [
        {"limit": 0},
        {"limit": 101},
        {"limit": "2"},
        {"page": 0},
        {"page": True},
    ],
)
def test_alliance_rejects_invalid_pages_before_network(arguments):
    tool = AllianceGenomeTool(
        {"name": "test", "fields": {"endpoint_type": "gene_phenotypes"}}
    )
    with patch(
        "tooluniverse.alliance_genome_tool.requests.get",
        side_effect=AssertionError("invalid page must not hit API"),
    ):
        result = tool.run({"gene_id": "HGNC:11998", **arguments})

    assert result["status"] == "error"
    assert "limit" in result["error"] or "page" in result["error"]
