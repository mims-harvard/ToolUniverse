"""Regression test for reachable Alliance gene cross-references."""

from unittest.mock import Mock

import pytest

from tooluniverse.alliance_genome_tool import AllianceGenomeTool

pytestmark = pytest.mark.unit


def test_gene_detail_pages_cross_references(monkeypatch):
    response = Mock()
    response.json.return_value = {
        "gene": {
            "primaryExternalId": "HGNC:11998",
            "geneSymbol": {"displayText": "TP53"},
            "crossReferences": [
                {
                    "displayName": f"Source {index}",
                    "referencedCurie": f"SRC:{index}",
                    "crossRefCompleteUrl": f"https://example.org/{index}",
                }
                for index in range(25)
            ],
        }
    }
    response.raise_for_status.return_value = None
    monkeypatch.setattr(
        "tooluniverse.alliance_genome_tool.requests.get",
        lambda *args, **kwargs: response,
    )
    tool = AllianceGenomeTool(
        {
            "name": "Alliance_get_gene",
            "fields": {"endpoint_type": "gene_detail"},
            "parameter": {"properties": {}},
        }
    )

    result = tool.run(
        {"gene_id": "HGNC:11998", "xref_offset": 10, "xref_limit": 3}
    )["data"]

    assert [item["curie"] for item in result["cross_references"]] == [
        "SRC:10",
        "SRC:11",
        "SRC:12",
    ]
    assert result["cross_references_total"] == 25
    assert result["cross_references_returned"] == 3
    assert result["cross_references_truncated"] is True
    assert result["next_xref_offset"] == 13

