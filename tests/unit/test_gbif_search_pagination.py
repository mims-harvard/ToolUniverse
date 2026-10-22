from unittest.mock import patch

from tooluniverse.gbif_tool import GBIFOccurrenceTool, GBIFTool


def page(count=913, offset=0, limit=3, end=False):
    return {
        "offset": offset,
        "limit": limit,
        "endOfRecords": end,
        "count": count,
        "results": [{"key": offset + i} for i in range(limit)],
    }


def test_species_search_exposes_exact_offset_continuation():
    with patch("tooluniverse.gbif_tool._http_get", return_value=page()) as request:
        result = GBIFTool().run({"query": "Homo", "limit": 3, "offset": 0})

    assert result["metadata"]["total_results"] == 913
    assert result["metadata"]["accessible_results"] == 913
    assert result["metadata"]["next_offset"] == 3
    assert result["metadata"]["upstream_truncated"] is False
    assert "limit=3" in request.call_args.args[0]


def test_occurrence_search_reports_finite_window():
    payload = page(count=500000, offset=3, limit=3)
    with patch("tooluniverse.gbif_tool._http_get", return_value=payload):
        result = GBIFOccurrenceTool().run(
            {"taxonKey": 2435099, "country": "us", "limit": 3, "offset": 3}
        )

    metadata = result["metadata"]
    assert result["query"]["country"] == "US"
    assert metadata["total_results"] == 500000
    assert metadata["accessible_results"] == 100001
    assert metadata["upstream_truncated"] is True
    assert metadata["next_offset"] == 6
    assert metadata["warning"]


def test_gbif_rejects_values_upstream_coerces_or_clamps():
    species = GBIFTool()
    occurrence = GBIFOccurrenceTool()
    with patch("tooluniverse.gbif_tool._http_get") as request:
        assert species.run({"query": "x", "offset": -1})["parameter"] == "offset"
        assert species.run({"query": "x", "limit": 1001})["parameter"] == "limit"
        assert species.run({"query": "x", "offset": 99999, "limit": 2})["parameter"] == "offset"
        assert occurrence.run({"offset": -1})["parameter"] == "offset"
        assert occurrence.run({"limit": 301})["parameter"] == "limit"
        assert occurrence.run({"offset": 100000, "limit": 2})["parameter"] == "offset"
        assert occurrence.run({"country": "USA"})["parameter"] == "country"
        assert occurrence.run({"hasCoordinate": "true"})["parameter"] == "hasCoordinate"
    request.assert_not_called()
