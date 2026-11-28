"""Unit tests for discovery-round batch 8 (Allen Cell Types, iDigBio). Network mocked."""

from unittest.mock import MagicMock, patch

from tooluniverse.allen_cell_types_tool import AllenCellTypesSpecimensTool
from tooluniverse.idigbio_tool import iDigBioSearchTool, iDigBioRecordTool


def _resp(status=200, json_body=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_body
    r.raise_for_status.return_value = None
    return r


def _cfg(name, typ):
    return {"name": name, "type": typ, "parameter": {"type": "object", "properties": {}}}


# --------------------------- Allen Cell Types --------------------------- #
def test_allen_builds_species_criteria_and_curates():
    body = {"success": True, "total_rows": 2333, "msg": [
        {"name": "H16.03.001", "donor__species": "Homo Sapiens", "donor__sex": "Male",
         "structure__name": '"inferior frontal gyrus"', "ef__avg_firing_rate": 8.73,
         "ef__ri": 120.5, "line_name": "", "nr__reconstruction_type": "full"}]}
    captured = {}

    def fake_get(url, params=None, **kw):
        captured["params"] = params
        return _resp(200, body)

    with patch("tooluniverse.allen_cell_types_tool.requests.get", side_effect=fake_get):
        out = AllenCellTypesSpecimensTool(
            _cfg("AllenCellTypes_search_specimens", "AllenCellTypesSpecimensTool")).run(
            {"species": "Homo Sapiens", "limit": 5})
    assert out["status"] == "success"
    assert "donor__species$eq'Homo Sapiens'" in captured["params"]["criteria"]
    rec = out["data"][0]
    assert rec["species"] == "Homo Sapiens"
    assert rec["brain_structure"] == "inferior frontal gyrus"  # quotes stripped
    assert rec["avg_firing_rate"] == 8.73
    assert rec["has_reconstruction"] is True
    assert out["metadata"]["total_available"] == 2333


def test_allen_query_failure_is_error():
    with patch("tooluniverse.allen_cell_types_tool.requests.get",
               return_value=_resp(200, {"success": False, "msg": "bad criteria"})):
        out = AllenCellTypesSpecimensTool(
            _cfg("AllenCellTypes_search_specimens", "AllenCellTypesSpecimensTool")).run({"species": "X"})
    assert out["status"] == "error"
    assert "query error" in out["error"]


# --------------------------- iDigBio --------------------------- #
def test_idigbio_search_requires_a_field():
    out = iDigBioSearchTool(_cfg("iDigBio_search_records", "iDigBioSearchTool")).run({})
    assert out["status"] == "error"


def test_idigbio_search_builds_a_gbif_query_and_curates():
    """The retired iDigBio API is reached through GBIF's iDigBio network now.

    `genus` is not a GBIF occurrence filter -- GBIF would ignore it and answer
    with the whole network -- so it arrives as a taxonKey, and `country` arrives
    as the ISO code GBIF filters on rather than the name iDigBio accepted.
    """
    match = {"usageKey": 2877951, "canonicalName": "Quercus", "rank": "GENUS",
             "matchType": "EXACT", "familyKey": 4689}
    countries = [{"iso2": "US", "iso3": "USA", "title": "United States",
                  "enumName": "UNITED_STATES"}]
    body = {"count": 130353, "results": [
        {"key": 11, "scientificName": "Quercus alba L.", "family": "Fagaceae",
         "genus": "Quercus", "country": "United States of America",
         "recordedBy": "J. Smith", "occurrenceID": "occ:1"}]}
    captured = {}

    def fake_get(url, params=None, **kw):
        if url.endswith("/enumeration/country"):
            return _resp(200, countries)
        if url.endswith("/species/match"):
            return _resp(200, match)
        captured["params"] = params
        return _resp(200, body)

    import tooluniverse.idigbio_tool as mod

    with patch("tooluniverse.idigbio_tool.requests.get", side_effect=fake_get), \
            patch.object(mod, "_countries_cache", None):
        out = iDigBioSearchTool(_cfg("iDigBio_search_records", "iDigBioSearchTool")).run(
            {"genus": "Quercus", "country": "United States", "limit": 5})
    assert out["status"] == "success"
    assert captured["params"]["taxonKey"] == 2877951
    assert "genus" not in captured["params"]
    assert captured["params"]["country"] == "US"
    assert captured["params"]["networkKey"] == mod.IDIGBIO_NETWORK_KEY
    rec = out["data"][0]
    assert rec["scientific_name"] == "Quercus alba L."
    assert rec["recorded_by"] == "J. Smith"
    assert out["metadata"]["total_available"] == 130353


def test_idigbio_get_requires_an_occurrence_key():
    out = iDigBioRecordTool(_cfg("iDigBio_get_record", "iDigBioRecordTool")).run({})
    assert out["status"] == "error"


def test_idigbio_get_includes_the_full_upstream_record():
    body = {"key": 6158969750, "scientificName": "Quercus alba L.",
            "country": "United States of America", "genus": "Quercus"}
    with patch("tooluniverse.idigbio_tool.requests.get", return_value=_resp(200, body)):
        out = iDigBioRecordTool(_cfg("iDigBio_get_record", "iDigBioRecordTool")).run(
            {"occurrence_key": "6158969750"})
    assert out["status"] == "success"
    assert out["data"]["gbif_id"] == 6158969750
    assert out["data"]["data"]["scientificName"] == "Quercus alba L."


def test_idigbio_get_refuses_a_legacy_uuid():
    """Those ids existed only in the retired API; GBIF resolves none of them."""
    out = iDigBioRecordTool(_cfg("iDigBio_get_record", "iDigBioRecordTool")).run(
        {"occurrence_key": "b659bd7f-7fa7-434b-80e7-2be10d1c4e80"})
    assert out["status"] == "error"
    assert "legacy iDigBio record UUID" in out["error"]


def test_idigbio_get_404_empty():
    with patch("tooluniverse.idigbio_tool.requests.get", return_value=_resp(404)):
        out = iDigBioRecordTool(_cfg("iDigBio_get_record", "iDigBioRecordTool")).run(
            {"occurrence_key": "999999999"})
    assert out["status"] == "success"
    assert out["data"] == {}
