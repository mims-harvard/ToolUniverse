from typing import Any

from tooluniverse.veupathdb_tool import VEuPathDBTool


def test_gene_search_forwards_offset_and_reports_continuation(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_post(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        captured.update(body)
        return {
            "records": [{"attributes": {"primary_key": "PF3D7_1"}}],
            "meta": {"totalCount": 10},
        }

    monkeypatch.setattr(VEuPathDBTool, "_post_json", fake_post)
    tool = VEuPathDBTool({"fields": {"operation": "search_genes_by_organism"}})

    result = tool.run(
        {
            "organism": "Plasmodium falciparum 3D7",
            "project": "plasmodb",
            "limit": 3,
            "offset": 3,
        }
    )

    assert captured["reportConfig"]["pagination"] == {
        "offset": 3,
        "numRecords": 3,
    }
    assert result["status"] == "success"
    assert result["metadata"]["total_count"] == 10
    assert result["metadata"]["offset"] == 3
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 4
