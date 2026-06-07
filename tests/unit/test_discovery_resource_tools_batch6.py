"""Unit tests for discovery-round batch 6 (EPA Envirofacts, USDA PLANTS). Network mocked."""

from unittest.mock import MagicMock, patch

from tooluniverse.epa_envirofacts_tool import EPATRIFacilitiesTool, EPAFRSFacilitiesTool
from tooluniverse.usda_plants_tool import USDAPlantsProfileTool, USDAPlantsCharacteristicsTool


def _resp(status=200, json_body=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_body
    r.raise_for_status.return_value = None
    return r


def _cfg(name, typ):
    return {"name": name, "type": typ, "parameter": {"type": "object", "properties": {}}}


# --------------------------- EPA --------------------------- #
def test_epa_tri_requires_state():
    out = EPATRIFacilitiesTool(_cfg("EPA_search_tri_facilities", "EPATRIFacilitiesTool")).run({})
    assert out["status"] == "error"
    assert "state" in out["error"]


def test_epa_tri_curates_and_builds_city_filter():
    rows = [{"tri_facility_id": "90001BCNCX935E5", "facility_name": "NEWARK CUSTOM PAPERBOARD",
             "city_name": "LOS ANGELES", "state_abbr": "CA", "zip_code": "90001", "region": "09"}]
    captured = {}

    def fake_get(url, **kw):
        captured["url"] = url
        return _resp(200, rows)

    with patch("tooluniverse.epa_envirofacts_tool.requests.get", side_effect=fake_get):
        out = EPATRIFacilitiesTool(_cfg("EPA_search_tri_facilities", "EPATRIFacilitiesTool")).run(
            {"state": "ca", "city": "Los Angeles", "limit": 5})
    assert out["status"] == "success"
    assert out["data"][0]["tri_facility_id"] == "90001BCNCX935E5"
    assert out["data"][0]["city"] == "LOS ANGELES"
    # URL includes uppercased state + city filter + row range
    assert "tri_facility/state_abbr/CA" in captured["url"]
    assert "city_name/LOS%20ANGELES" in captured["url"]
    assert "rows/0:4/JSON" in captured["url"]


def test_epa_frs_curates():
    rows = [{"std_name": "BOSTON COLLEGE", "std_full_address": "140 COMMONWEALTH AVE",
             "std_city_name": "CHESTNUT HILL", "state_name": "MA", "parent_registry_id": "110000123456"}]
    with patch("tooluniverse.epa_envirofacts_tool.requests.get", return_value=_resp(200, rows)):
        out = EPAFRSFacilitiesTool(_cfg("EPA_search_frs_facilities", "EPAFRSFacilitiesTool")).run({"state": "MA"})
    assert out["data"][0]["facility_name"] == "BOSTON COLLEGE"
    assert out["data"][0]["registry_id"] == "110000123456"


# --------------------------- USDA --------------------------- #
def test_usda_profile_requires_symbol():
    out = USDAPlantsProfileTool(_cfg("USDA_plants_get_profile", "USDAPlantsProfileTool")).run({})
    assert out["status"] == "error"


def test_usda_profile_curates():
    profile = {"Id": 15309, "Symbol": "ABBA", "ScientificNameWithoutAuthor": "Abies balsamea",
               "CommonName": "balsam fir", "GroupName": "Gymnosperm", "Rank": "Species",
               "Durations": ["Perennial"], "GrowthHabits": ["Tree"], "NativeStatuses": ["L48 (N)"]}
    with patch("tooluniverse.usda_plants_tool.requests.get", return_value=_resp(200, profile)):
        out = USDAPlantsProfileTool(_cfg("USDA_plants_get_profile", "USDAPlantsProfileTool")).run({"symbol": "abba"})
    assert out["data"]["scientific_name"] == "Abies balsamea"
    assert out["data"]["growth_habits"] == ["Tree"]
    assert out["data"]["id"] == 15309


def test_usda_profile_not_found():
    with patch("tooluniverse.usda_plants_tool.requests.get", return_value=_resp(200, {})):
        out = USDAPlantsProfileTool(_cfg("USDA_plants_get_profile", "USDAPlantsProfileTool")).run({"symbol": "ZZZZ"})
    assert out["status"] == "success"
    assert out["data"] == {}


def test_usda_characteristics_resolves_id_then_fetches():
    profile = {"Id": 15309, "Symbol": "ABBA"}
    chars = [{"PlantCharacteristicName": "Shade Tolerance", "PlantCharacteristicValue": "Tolerant",
              "PlantCharacteristicCategory": "Growth Requirements"}]
    # first call returns profile, second returns characteristics
    with patch("tooluniverse.usda_plants_tool.requests.get",
               side_effect=[_resp(200, profile), _resp(200, chars)]):
        out = USDAPlantsCharacteristicsTool(
            _cfg("USDA_plants_get_characteristics", "USDAPlantsCharacteristicsTool")).run({"symbol": "ABBA"})
    assert out["status"] == "success"
    assert out["metadata"]["plant_id"] == 15309
    assert out["data"][0]["name"] == "Shade Tolerance"
    assert out["data"][0]["value"] == "Tolerant"
