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


def test_idigbio_search_builds_rq_and_curates():
    body = {"itemCount": 130353, "items": [
        {"uuid": "abc", "indexTerms": {"scientificname": "quercus alba", "family": "Fagaceae",
                                       "genus": "quercus", "country": "united states"},
         "data": {"dwc:recordedBy": "J. Smith", "dwc:occurrenceID": "occ:1"}}]}
    captured = {}

    def fake_get(url, params=None, **kw):
        captured["params"] = params
        return _resp(200, body)

    with patch("tooluniverse.idigbio_tool.requests.get", side_effect=fake_get):
        out = iDigBioSearchTool(_cfg("iDigBio_search_records", "iDigBioSearchTool")).run(
            {"genus": "Quercus", "country": "United States", "limit": 5})
    assert out["status"] == "success"
    assert '"genus": "Quercus"' in captured["params"]["rq"]
    assert '"country": "United States"' in captured["params"]["rq"]
    rec = out["data"][0]
    assert rec["scientific_name"] == "quercus alba"
    assert rec["recorded_by"] == "J. Smith"
    assert out["metadata"]["total_available"] == 130353


def test_idigbio_get_requires_uuid():
    out = iDigBioRecordTool(_cfg("iDigBio_get_record", "iDigBioRecordTool")).run({})
    assert out["status"] == "error"


def test_idigbio_get_includes_full_data():
    body = {"uuid": "abc", "indexTerms": {"genus": "quercus"},
            "data": {"dwc:scientificName": "Quercus alba", "dwc:country": "United States"}}
    with patch("tooluniverse.idigbio_tool.requests.get", return_value=_resp(200, body)):
        out = iDigBioRecordTool(_cfg("iDigBio_get_record", "iDigBioRecordTool")).run({"uuid": "abc"})
    assert out["status"] == "success"
    assert out["data"]["uuid"] == "abc"
    assert out["data"]["data"]["dwc:scientificName"] == "Quercus alba"


def test_idigbio_get_404_empty():
    with patch("tooluniverse.idigbio_tool.requests.get", return_value=_resp(404)):
        out = iDigBioRecordTool(_cfg("iDigBio_get_record", "iDigBioRecordTool")).run({"uuid": "missing"})
    assert out["status"] == "success"
    assert out["data"] == {}
