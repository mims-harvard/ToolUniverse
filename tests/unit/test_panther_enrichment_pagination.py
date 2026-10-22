from unittest.mock import Mock

from tooluniverse.panther_tool import PANTHERTool


def _row(term_id: str, fdr: float, fold: float) -> dict:
    return {
        "term": {"id": term_id, "label": term_id},
        "number_in_list": 2,
        "number_in_reference": 10,
        "expected": 0.1,
        "fold_enrichment": fold,
        "pValue": fdr / 2,
        "fdr": fdr,
        "plus_minus": "+",
    }


def test_enrichment_filters_by_fdr_and_paginates_true_significant_total(
    monkeypatch,
) -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "results": {
            "result": [
                _row("GO:3", 0.03, 30),
                _row("GO:1", 0.01, 10),
                _row("GO:4", 0.20, 40),
                _row("GO:2", 0.02, 20),
            ]
        }
    }
    monkeypatch.setattr("tooluniverse.panther_tool.requests.get", Mock(return_value=response))
    tool = PANTHERTool({"fields": {"endpoint_type": "enrichment"}})

    result = tool.run(
        {
            "gene_list": "TP53,BRCA1",
            "limit": 1,
            "offset": 1,
        }
    )

    assert result["status"] == "success"
    assert result["data"]["total_enriched_terms"] == 3
    assert result["data"]["result_count"] == 1
    assert [row["term_id"] for row in result["data"]["enriched_terms"]] == [
        "GO:2"
    ]
    assert result["data"]["has_more"] is True
    assert result["data"]["next_offset"] == 2
    assert result["metadata"]["raw_term_count"] == 4
    assert result["metadata"]["significance_threshold"] == "FDR < 0.05"
