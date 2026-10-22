from typing import Any

import pytest

from tooluniverse.gbif_taxonomy_tool import GBIFTaxonomyTool


@pytest.mark.parametrize("operation", ["get_children", "get_synonyms"])
def test_paged_taxon_usages_forward_offset_and_return_continuation(
    monkeypatch, operation: str
) -> None:
    captured: dict[str, Any] = {}

    def fake_get(url: str, params: dict[str, Any], timeout: int):
        captured.update(params)
        return True, {"endOfRecords": False, "results": [{"key": 1}]}, None

    monkeypatch.setattr("tooluniverse.gbif_taxonomy_tool._http_get", fake_get)
    tool = GBIFTaxonomyTool(
        {"fields": {"operation": operation, "base_url": "https://example.test"}}
    )

    result = tool.run({"taxon_key": 2435194, "limit": 3, "offset": 3})

    assert captured == {"limit": 3, "offset": 3}
    assert result["status"] == "success"
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 4


def test_vernacular_language_filter_keeps_raw_page_continuation(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    payload = {
        "endOfRecords": False,
        "results": [
            {"vernacularName": "Lion", "language": "eng"},
            {"vernacularName": "Löwe", "language": "deu"},
        ],
    }

    def fake_get(url: str, params: dict[str, Any], timeout: int):
        captured.update(params)
        return True, payload, None

    monkeypatch.setattr("tooluniverse.gbif_taxonomy_tool._http_get", fake_get)
    tool = GBIFTaxonomyTool(
        {
            "fields": {
                "operation": "get_vernacular_names",
                "base_url": "https://example.test",
            }
        }
    )

    result = tool.run(
        {"taxon_key": 5219404, "language": "spa", "limit": 2, "offset": 5}
    )

    assert captured == {"limit": 2, "offset": 5}
    assert result["data"] == []
    assert result["metadata"]["raw_returned"] == 2
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 7
