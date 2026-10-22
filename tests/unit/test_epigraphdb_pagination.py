from unittest.mock import MagicMock, patch

from tooluniverse.epigraphdb_tool import EpiGraphDBTool


def _tool(operation):
    return EpiGraphDBTool(
        {"name": f"EpiGraphDB_{operation}", "fields": {"operation": operation}}
    )


def _response(results):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"results": results}
    return response


@patch("tooluniverse.epigraphdb_tool.requests.get")
def test_genetic_correlations_are_recoverably_paged(mock_get):
    results = [
        {
            "trait": {"id": "source", "trait": "Waist circumference"},
            "assoc_trait": {"id": f"trait-{i}", "trait": f"Trait {i}"},
            "gc": {"rg": 0.9, "rg_SE": 0.01, "p": 1e-10},
        }
        for i in range(7)
    ]
    mock_get.return_value = _response(results)

    data = _tool("genetic_cor").run(
        {"trait": "Waist circumference", "limit": 3, "offset": 3}
    )["data"]

    assert data["total_count"] == 7
    assert data["returned"] == 3
    assert data["has_more"] is True
    assert data["next_offset"] == 6
    assert [row["trait2_id"] for row in data["correlations"]] == [
        "trait-3", "trait-4", "trait-5"
    ]


@patch("tooluniverse.epigraphdb_tool.requests.get")
def test_trait_drugs_are_recoverably_paged_after_deduplication(mock_get):
    results = [
        {"drug": {"label": f"Drug {i}"}, "gene": {"name": f"Gene {i}"}, "variant": {}}
        for i in range(7)
    ]
    results.append(results[0])
    mock_get.return_value = _response(results)

    data = _tool("drugs_risk_factors").run(
        {"trait": "LDL cholesterol", "limit": 3, "offset": 3}
    )["data"]

    assert data["total_evidence_count"] == 8
    assert data["unique_drug_count"] == 7
    assert data["returned"] == 3
    assert data["has_more"] is True
    assert data["next_offset"] == 6


@patch("tooluniverse.epigraphdb_tool.requests.get")
def test_literature_evidence_forwards_recoverable_upstream_page(mock_get):
    results = [
        {
            "triple": {
                "name": f"Subject {i} TREATS Object {i}",
                "predicate": "TREATS",
            },
            "gwas": {"trait": "Body mass index"},
            "lit": {"id": str(1000 + i)},
        }
        for i in range(3)
    ]
    mock_get.return_value = _response(results)

    data = _tool("literature_evidence").run(
        {
            "trait": "body mass index",
            "pval_threshold": 1e-4,
            "limit": 3,
            "offset": 6,
        }
    )["data"]

    assert mock_get.call_args.kwargs["params"] == {
        "trait": "body mass index",
        "pval_threshold": 1e-4,
        "limit": 3,
        "skip": 6,
    }
    assert data["returned_count"] == 3
    assert data["total_count"] is None
    assert data["has_more"] is True
    assert data["next_offset"] == 9
    assert data["result_set_complete"] is False


@patch("tooluniverse.epigraphdb_tool.requests.get")
def test_literature_final_page_exposes_exact_total(mock_get):
    mock_get.return_value = _response(
        [
            {
                "triple": {"name": "A TREATS B", "predicate": "TREATS"},
                "gwas": {"trait": "Trait"},
                "lit": {"id": "123"},
            }
        ]
    )

    data = _tool("literature_evidence").run(
        {"trait": "Trait", "limit": 3, "offset": 6}
    )["data"]

    assert data["returned_count"] == 1
    assert data["total_count"] == 7
    assert data["has_more"] is False
    assert data["next_offset"] is None
    assert data["result_set_complete"] is False


@patch("tooluniverse.epigraphdb_tool.requests.get")
def test_mr_single_trait_query_is_recoverably_paged(mock_get):
    results = [
        {
            "exposure": {"id": "exp", "trait": "Body mass index"},
            "outcome": {"id": f"out-{i}", "trait": f"Outcome {i}"},
            "mr": {"b": i / 10, "se": 0.01, "pval": 1e-8, "method": "IVW"},
        }
        for i in range(7)
    ]
    mock_get.return_value = _response(results)

    data = _tool("mr").run(
        {"exposure_trait": "Body mass index", "limit": 3, "offset": 3}
    )["data"]

    assert mock_get.call_args.kwargs["params"] == {
        "pval_threshold": 1e-5,
        "exposure_trait": "Body mass index",
    }
    assert data["total_count"] == 7
    assert data["returned_count"] == 3
    assert [row["outcome_id"] for row in data["mr_results"]] == [
        "out-3",
        "out-4",
        "out-5",
    ]
    assert data["has_more"] is True
    assert data["next_offset"] == 6


def test_mr_rejects_query_without_either_trait():
    result = _tool("mr").run({})
    assert result["status"] == "error"
    assert "At least one" in result["error"]


@patch("tooluniverse.epigraphdb_tool.requests.get")
def test_gene_search_full_page_is_not_misreported_as_total(mock_get):
    results = [
        {
            "node": {
                "ensembl_id": f"ENSG{i:011d}",
                "_name": f"A{i}",
                "description": "test gene",
            }
        }
        for i in range(200)
    ]
    mock_get.return_value = _response(results)

    result = _tool("gene_search").run({"gene_name": "A", "limit": 500})
    data = result["data"]

    assert mock_get.call_args.kwargs["params"]["limit"] == 200
    assert data["returned_count"] == 200
    assert data["total_found"] is None
    assert data["truncated"] is True
    assert data["result_set_complete"] is False
    assert "no offset" in result["metadata"]["note"]


@patch("tooluniverse.epigraphdb_tool.requests.get")
def test_exact_gene_id_result_is_complete(mock_get):
    mock_get.return_value = _response(
        [{"node": {"ensembl_id": "ENSG00000141510", "_name": "TP53"}}]
    )

    data = _tool("gene_search").run(
        {"gene_id": "ENSG00000141510", "limit": 1}
    )["data"]

    assert data["total_found"] == 1
    assert data["truncated"] is False
    assert data["result_set_complete"] is True
