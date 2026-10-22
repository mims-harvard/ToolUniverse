"""Regressions for reachable HOCOMOCO search pagination."""

from unittest.mock import Mock

import pytest

from tooluniverse.hocomoco_tool import HocomocoTool

pytestmark = pytest.mark.unit


def _tool():
    return HocomocoTool(
        {
            "name": "HOCOMOCO_search_motifs",
            "fields": {"endpoint_type": "search_motifs"},
            "parameter": {"properties": {}},
        }
    )


def test_search_pages_all_ids_and_reports_failed_detail_fetches(monkeypatch):
    motif_ids = [f"FOX{i}.H14CORE.0.P.A" for i in range(15)]
    response = Mock()
    response.json.return_value = motif_ids
    response.raise_for_status.return_value = None
    monkeypatch.setattr(
        "tooluniverse.hocomoco_tool.requests.get", lambda *a, **k: response
    )

    tool = _tool()
    requested = []

    def fetch(motif_id):
        requested.append(motif_id)
        if motif_id == motif_ids[7]:
            return None
        return {"motif_id": motif_id}

    monkeypatch.setattr(tool, "_fetch_motif_summary", fetch)

    result = tool.run({"query": "FOX", "offset": 5, "limit": 5})

    assert requested == motif_ids[5:10]
    assert [item["motif_id"] for item in result["data"]] == [
        motif_ids[5],
        motif_ids[6],
        motif_ids[8],
        motif_ids[9],
    ]
    assert result["metadata"] == {
        "query": "FOX",
        "total": 15,
        "returned": 4,
        "offset": 5,
        "limit": 5,
        "has_more": True,
        "next_offset": 10,
        "failed_motif_ids": [motif_ids[7]],
    }


def test_search_offset_beyond_total_returns_valid_empty_final_page(monkeypatch):
    response = Mock()
    response.json.return_value = ["P53.H14CORE.0.P.B"]
    response.raise_for_status.return_value = None
    monkeypatch.setattr(
        "tooluniverse.hocomoco_tool.requests.get", lambda *a, **k: response
    )

    result = _tool().run({"query": "TP53", "offset": 10, "limit": 5})

    assert result["status"] == "success"
    assert result["data"] == []
    assert result["metadata"]["total"] == 1
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_offset"] is None
