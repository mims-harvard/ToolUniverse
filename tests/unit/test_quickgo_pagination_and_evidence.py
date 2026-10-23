from typing import Any

import pytest

from tooluniverse.quickgo_tool import QuickGOTool


class _Response:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {
            "numberOfHits": 10,
            "pageInfo": {"resultsPerPage": 3, "current": 2, "total": 4},
            "results": [
                {
                    "geneProductId": "UniProtKB:P04637",
                    "goId": "GO:0006974",
                    "goName": "DNA damage response",
                    "goEvidence": "IDA",
                    "evidenceCode": "ECO:0000314",
                }
            ],
        }


@pytest.mark.parametrize(
    ("endpoint", "arguments", "query_key"),
    [
        (
            "annotation_gene",
            {
                "gene_product_id": "UniProtKB:P04637",
                "page": 2,
                "limit": 3,
                "evidence_code": "ECO:0000314",
            },
            "geneProductId",
        ),
        (
            "annotation_goterm",
            {
                "go_id": "GO:0006974",
                "page": 2,
                "limit": 3,
                "evidence_code": "ECO:0000314",
            },
            "goId",
        ),
    ],
)
def test_annotation_endpoints_forward_page_and_exact_eco_filter(
    monkeypatch,
    endpoint: str,
    arguments: dict[str, Any],
    query_key: str,
) -> None:
    captured: dict[str, Any] = {}

    def fake_get(url: str, **kwargs: Any) -> _Response:
        captured.update(kwargs)
        return _Response()

    monkeypatch.setattr("tooluniverse.quickgo_tool.requests.get", fake_get)
    tool = QuickGOTool({"fields": {"endpoint": endpoint}})

    result = tool.run(arguments)

    assert result["status"] == "success"
    assert query_key in captured["params"]
    assert captured["params"]["page"] == 2
    assert captured["params"]["limit"] == 3
    assert captured["params"]["evidenceCode"] == "ECO:0000314"
    assert "goUsage" not in captured["params"]
    assert result["data"][0]["go_evidence"] == "IDA"
    assert result["data"][0]["evidence_code"] == "ECO:0000314"
    assert result["metadata"]["total_annotations"] == 10
    assert result["metadata"]["page"] == 2
    assert result["metadata"]["total_pages"] == 4
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_page"] == 3
