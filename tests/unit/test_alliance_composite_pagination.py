from typing import Any

from tooluniverse.alliance_genome_tool import AllianceGenomeTool


def test_ortholog_paralog_tool_forwards_shared_page_and_reports_categories(
    monkeypatch,
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    def fake_get(self, gene_id: str, path: str, params: dict[str, Any]):
        calls.append((path, params))
        return {
            "results": [],
            "total": 19 if path == "orthologs" else 42,
        }

    monkeypatch.setattr(AllianceGenomeTool, "_alliance_get", fake_get)
    tool = AllianceGenomeTool({"fields": {"endpoint_type": "gene_orthologs_paralogs"}})

    result = tool.run(
        {"gene_id": "MGI:97490", "limit": 3, "page": 2, "stringency": "all"}
    )

    assert calls == [
        (
            "orthologs",
            {"limit": 3, "page": 2, "filter.stringency": "all"},
        ),
        ("paralogs", {"limit": 3, "page": 2}),
    ]
    assert result["metadata"]["page"] == 2
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_page"] == 3
    assert result["metadata"]["categories"]["orthologs"]["total"] == 19
    assert result["metadata"]["categories"]["paralogs"]["total"] == 42


def test_allele_model_tool_forwards_shared_page_and_reports_categories(
    monkeypatch,
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    def fake_get(self, gene_id: str, path: str, params: dict[str, Any]):
        calls.append((path, params))
        return {"results": [], "total": 675 if path == "alleles" else 183}

    monkeypatch.setattr(AllianceGenomeTool, "_alliance_get", fake_get)
    tool = AllianceGenomeTool({"fields": {"endpoint_type": "gene_alleles_and_models"}})

    result = tool.run({"gene_id": "MGI:97490", "limit": 3, "page": 2})

    assert calls == [
        ("alleles", {"limit": 3, "page": 2}),
        ("models", {"limit": 3, "page": 2}),
    ]
    assert result["metadata"]["page"] == 2
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_page"] == 3
    assert result["metadata"]["categories"]["alleles"]["total"] == 675
    assert result["metadata"]["categories"]["models"]["total"] == 183
