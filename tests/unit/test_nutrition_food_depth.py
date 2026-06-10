"""Depth coverage for the nutrition-food cluster: Open Food Facts faceted /
tag-based product filtering and USDA PLANTS wetland / invasive / wildlife
endpoints.

Each test mocks the upstream HTTP call so it runs offline, covering both the
parse (success) path and the failure path. Every tool must always return a
{status: ...} envelope and never raise.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

pytestmark = pytest.mark.unit

_DATA = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"


def _load_config(filename, tool_name):
    cfgs = json.load(open(_DATA / filename))
    for cfg in cfgs:
        if cfg.get("name") == tool_name:
            return cfg
    raise AssertionError(f"{tool_name} not found in {filename}")


# ---------------------------------------------------------------------------
# Open Food Facts faceted / tag filter (BaseRESTTool, config-driven)
# ---------------------------------------------------------------------------


def _make_off_filter():
    from tooluniverse.base_rest_tool import BaseRESTTool

    return BaseRESTTool(
        _load_config(
            "openfoodfacts_tools.json", "OpenFoodFacts_filter_products_by_tags"
        )
    )


class TestOpenFoodFactsFilter:
    OFF_PAYLOAD = {
        "count": 37562,
        "page": 1,
        "page_count": 2,
        "page_size": 2,
        "skip": 0,
        "products": [
            {
                "code": "3760020507350",
                "product_name": "Pur beurre de cacahuete",
                "brands": "Jardin Bio etic",
                "allergens_tags": ["en:peanuts"],
                "nutrition_grades": "b",
            },
            {
                "code": "0000000",
                "product_name": "Menguy's Peanut 100%",
                "allergens_tags": ["en:peanuts"],
            },
        ],
    }

    def _mock_resp(self, payload, status=200):
        resp = MagicMock()
        resp.status_code = status
        resp.json.return_value = payload
        resp.headers = {"content-type": "application/json"}
        resp.text = json.dumps(payload)
        return resp

    def test_config_present_and_valid(self):
        """Config is a valid BaseRESTTool entry with a oneOf return schema."""
        cfg = _load_config(
            "openfoodfacts_tools.json", "OpenFoodFacts_filter_products_by_tags"
        )
        assert cfg["type"] == "BaseRESTTool"
        assert cfg["fields"]["endpoint"].endswith("/api/v2/search")
        assert len(cfg["name"]) <= 55
        # oneOf with success + error branches
        assert "oneOf" in cfg["return_schema"]
        assert len(cfg["return_schema"]["oneOf"]) == 2

    def test_tag_filters_forwarded_as_query_params(self):
        """Tag fields are sent verbatim to the v2 search endpoint."""
        tool = _make_off_filter()
        captured = {}

        def fake_request(session, method, url, **kwargs):
            captured["url"] = url
            captured["params"] = kwargs.get("params")
            return self._mock_resp(self.OFF_PAYLOAD)

        with patch(
            "tooluniverse.base_rest_tool.request_with_retry", side_effect=fake_request
        ):
            out = tool.run(
                {
                    "additives_tags": "en:e322",
                    "nutrition_grades_tags": "a",
                    "page_size": 2,
                }
            )

        assert out["status"] == "success"
        # The controlled-vocabulary tags reach the API unchanged.
        assert captured["params"]["additives_tags"] == "en:e322"
        assert captured["params"]["nutrition_grades_tags"] == "a"
        assert captured["params"]["page_size"] == 2
        # Default fields list from config is still present.
        assert "product_name" in captured["params"]["fields"]

    def test_parse_success_envelope(self):
        tool = _make_off_filter()
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry",
            return_value=self._mock_resp(self.OFF_PAYLOAD),
        ):
            out = tool.run({"allergens_tags": "en:peanuts", "page_size": 2})

        assert out["status"] == "success"
        assert out["data"]["count"] == 37562
        names = [p["product_name"] for p in out["data"]["products"]]
        assert "Pur beurre de cacahuete" in names

    def test_http_error_path_does_not_raise(self):
        tool = _make_off_filter()
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry",
            return_value=self._mock_resp("<html>503</html>", status=503),
        ):
            out = tool.run({"allergens_tags": "en:peanuts"})
        assert out["status"] == "error"
        assert out["status_code"] == 503

    def test_exception_path_does_not_raise(self):
        tool = _make_off_filter()
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry",
            side_effect=requests.exceptions.ConnectionError("boom"),
        ):
            out = tool.run({"allergens_tags": "en:peanuts"})
        assert out["status"] == "error"
        assert "error" in out


# ---------------------------------------------------------------------------
# USDA PLANTS wetland / invasive / wildlife (USDAPlantsProfileTool, new actions)
# ---------------------------------------------------------------------------


def _make_usda(tool_name):
    from tooluniverse.usda_plants_tool import USDAPlantsProfileTool

    return USDAPlantsProfileTool(_load_config("usda_plants_tools.json", tool_name))


def _profile_resp():
    """Symbol->Id resolution profile payload."""
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"Id": 27001, "Symbol": "TYLA"}
    return resp


class TestUSDAWetland:
    WETLAND = [
        {
            "Id": 27001,
            "ScientificName": "<i>Typha latifolia</i> L.",
            "WetlandDesignations": [
                {"Region": "Great Plains", "SubRegion": None, "WetlandCode": "OBL"},
                {"Region": "Midwest", "SubRegion": None, "WetlandCode": "OBL"},
            ],
        }
    ]

    def test_config(self):
        """Config wires the right action and a <=55-char name."""
        cfg = _load_config("usda_plants_tools.json", "USDA_plants_get_wetland_status")
        assert cfg["type"] == "USDAPlantsProfileTool"
        assert cfg["fields"]["action"] == "wetland"
        assert len(cfg["name"]) <= 55

    def test_parse_success_by_symbol(self):
        tool = _make_usda("USDA_plants_get_wetland_status")
        wet = MagicMock()
        wet.raise_for_status.return_value = None
        wet.json.return_value = self.WETLAND
        with patch("tooluniverse.usda_plants_tool.requests.get") as get:
            # First call resolves symbol->Id, second fetches wetland data.
            get.side_effect = [_profile_resp(), wet]
            out = tool.run({"symbol": "TYLA"})

        assert out["status"] == "success"
        assert out["metadata"]["plant_id"] == 27001
        designations = out["data"][0]["wetland_designations"]
        assert designations[0]["wetland_code"] == "OBL"
        # HTML stripped from scientific name.
        assert out["data"][0]["scientific_name"] == "Typha latifolia L."

    def test_parse_success_by_id_skips_resolution(self):
        tool = _make_usda("USDA_plants_get_wetland_status")
        wet = MagicMock()
        wet.raise_for_status.return_value = None
        wet.json.return_value = self.WETLAND
        with patch("tooluniverse.usda_plants_tool.requests.get") as get:
            # Only one call (no symbol->Id profile lookup needed).
            get.return_value = wet
            out = tool.run({"id": 27001})
        assert out["status"] == "success"
        assert out["metadata"]["plant_id"] == 27001
        assert get.call_count == 1

    def test_missing_input_returns_error(self):
        tool = _make_usda("USDA_plants_get_wetland_status")
        out = tool.run({})
        assert out["status"] == "error"
        assert "symbol" in out["error"]

    def test_error_path_does_not_raise(self):
        """A network failure returns status=error, never raises."""
        tool = _make_usda("USDA_plants_get_wetland_status")
        with patch("tooluniverse.usda_plants_tool.requests.get") as get:
            get.side_effect = requests.exceptions.ConnectionError("boom")
            out = tool.run({"id": 27001})
        assert out["status"] == "error"
        assert "USDA PLANTS request failed" in out["error"]


class TestUSDAInvasive:
    INVASIVE = [
        {
            "LocalityName": "Connecticut",
            "CommonNames": ["kudzu"],
            "InvasiveStatuses": ["Potentially Invasive", "Prohibited"],
        },
        {
            "LocalityName": "Missouri",
            "CommonNames": ["kudzu"],
            "InvasiveStatuses": ["Invasive (DOC)"],
        },
    ]

    def test_config(self):
        """Config wires the right action and a <=55-char name."""
        cfg = _load_config("usda_plants_tools.json", "USDA_plants_get_invasive_status")
        assert cfg["fields"]["action"] == "invasive"
        assert len(cfg["name"]) <= 55

    def test_parse_success(self):
        """Parse the mocked upstream payload into the tool envelope."""
        tool = _make_usda("USDA_plants_get_invasive_status")
        inv = MagicMock()
        inv.raise_for_status.return_value = None
        inv.json.return_value = self.INVASIVE
        nox = MagicMock()
        nox.raise_for_status.return_value = None
        nox.json.return_value = []
        with patch("tooluniverse.usda_plants_tool.requests.get") as get:
            # invasive endpoint, then noxious endpoint (id provided -> no profile).
            get.side_effect = [inv, nox]
            out = tool.run({"id": 82047})

        assert out["status"] == "success"
        assert out["metadata"]["invasive_count"] == 2
        assert out["metadata"]["noxious_count"] == 0
        ct = out["data"]["invasive"][0]
        assert ct["locality_name"] == "Connecticut"
        assert "Prohibited" in ct["statuses"]

    def test_error_path_does_not_raise(self):
        """A network failure returns status=error, never raises."""
        tool = _make_usda("USDA_plants_get_invasive_status")
        with patch("tooluniverse.usda_plants_tool.requests.get") as get:
            get.side_effect = requests.exceptions.Timeout()
            out = tool.run({"id": 82047})
        assert out["status"] == "error"
        assert "timed out" in out["error"]


class TestUSDAWildlife:
    WILDLIFE = {
        "Food": [
            {
                "Source": "Miller",
                "LargeMammals": "Minor",
                "SmallMammals": "",
                "WaterBirds": "",
                "TerrestrialBirds": "Low",
            }
        ],
        "Cover": [
            {
                "Source": "Yarrow",
                "LargeMammals": "",
                "SmallMammals": "",
                "WaterBirds": "",
                "TerrestrialBirds": "Moderate",
            }
        ],
        "Sources": [
            {
                "AuthorName": "Miller, J.H.",
                "Title": "Forest plants of the southeast",
                "PublisherName": "SWSS",
                "PublicationYear": 1999,
            }
        ],
    }

    def test_config(self):
        """Config wires the right action and a <=55-char name."""
        cfg = _load_config("usda_plants_tools.json", "USDA_plants_get_wildlife_value")
        assert cfg["fields"]["action"] == "wildlife"
        assert len(cfg["name"]) <= 55

    def test_parse_success(self):
        """Parse the mocked upstream payload into the tool envelope."""
        tool = _make_usda("USDA_plants_get_wildlife_value")
        wl = MagicMock()
        wl.raise_for_status.return_value = None
        wl.json.return_value = self.WILDLIFE
        with patch("tooluniverse.usda_plants_tool.requests.get") as get:
            get.return_value = wl
            out = tool.run({"id": 42834})

        assert out["status"] == "success"
        assert out["metadata"]["food_count"] == 1
        assert out["metadata"]["cover_count"] == 1
        food = out["data"]["food"][0]
        assert food["large_mammals"] == "Minor"
        # Empty-string ratings normalized to None.
        assert food["small_mammals"] is None
        assert out["data"]["sources"][0]["year"] == 1999

    def test_error_path_does_not_raise(self):
        """A network failure returns status=error, never raises."""
        tool = _make_usda("USDA_plants_get_wildlife_value")
        with patch("tooluniverse.usda_plants_tool.requests.get") as get:
            get.side_effect = requests.exceptions.ConnectionError("boom")
            out = tool.run({"id": 42834})
        assert out["status"] == "error"
        assert "USDA PLANTS request failed" in out["error"]


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-q"]))
