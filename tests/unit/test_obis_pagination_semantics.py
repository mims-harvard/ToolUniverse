from unittest.mock import patch

from tooluniverse.obis_tool import OBISOccurrenceTool, OBISTaxaTool


def test_taxa_uses_real_exact_name_endpoint_and_local_offset():
    payload = {
        "total": 2,
        "results": [
            {"scientificName": "Gadus", "taxonID": 125732, "taxonRank": "Genus"},
            {"scientificName": "Gadus", "taxonID": 990530, "taxonRank": "Genus"},
        ],
    }
    with patch("tooluniverse.obis_tool._http_get", return_value=payload) as request:
        result = OBISTaxaTool().run({"scientificname": "Gadus", "size": 1, "offset": 1})

    assert request.call_args.args[0].endswith("/taxon/Gadus")
    assert result["endpoint"] == "taxon/{scientificname}"
    assert result["data"]["total"] == 2
    assert result["data"]["results"][0]["aphiaID"] == 990530
    assert result["data"]["results"][0]["rank"] == "Genus"
    assert result["metadata"]["returned"] == 1
    assert result["metadata"]["has_more"] is False


def test_occurrence_uses_internal_uuid_cursor_and_lookahead():
    payload = {
        "total": 3116253,
        "results": [
            {"id": "uuid-1", "occurrenceID": "catalog-1"},
            {"id": "uuid-2", "occurrenceID": "catalog-2"},
            {"id": "uuid-3", "occurrenceID": "catalog-3"},
            {"id": "uuid-4", "occurrenceID": "catalog-4"},
        ],
    }
    with patch("tooluniverse.obis_tool._http_get", return_value=payload) as request:
        result = OBISOccurrenceTool().run(
            {"scientificname": "Gadus morhua", "size": 3, "after": "previous"}
        )

    assert "size=4" in request.call_args.args[0]
    assert "after=previous" in request.call_args.args[0]
    assert len(result["data"]["results"]) == 3
    assert result["metadata"]["next_after"] == "uuid-3"
    assert result["metadata"]["cursor_field"] == "id"
    assert result["metadata"]["cursor_is_not_occurrenceID"] is True


def test_obis_rejects_invalid_pagination_without_network():
    with patch("tooluniverse.obis_tool._http_get") as request:
        assert (
            OBISTaxaTool().run({"scientificname": "Gadus", "offset": -1})["parameter"]
            == "offset"
        )
        assert (
            OBISTaxaTool().run({"scientificname": "Gadus", "size": 0})["parameter"]
            == "size"
        )
        assert OBISOccurrenceTool().run({"size": 101})["parameter"] == "size"
        assert OBISOccurrenceTool().run({"after": ""})["parameter"] == "after"
    request.assert_not_called()
