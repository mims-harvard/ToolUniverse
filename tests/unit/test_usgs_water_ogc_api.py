"""USGS water tools read the Water Data OGC API, not WaterServices (#787).

WaterServices (waterservices.usgs.gov) is slowed from 2026-11-16 and shut
down on 2027-02-22. The replacement "continuous" collection names sites
``USGS-<number>``, pages at 10 values unless asked, returns string values,
and can hold several sensor series for one site and parameter.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.usgs_water_tool import USGSWaterTool

pytestmark = pytest.mark.unit

CONFIG_PATH = Path(__file__).parents[2] / "src/tooluniverse/data/usgs_water_tools.json"
CONFIGS = {t["name"]: t for t in json.loads(CONFIG_PATH.read_text())}


def _response(payload, status=200):
    response = MagicMock()
    response.status_code = status
    response.json.return_value = payload
    response.text = json.dumps(payload) if isinstance(payload, dict) else payload
    return response


LOCATIONS = {
    "features": [
        {
            "id": "USGS-01646500",
            "properties": {
                "monitoring_location_name": "POTOMAC RIVER NEAR WASH, DC",
                "state_name": "Maryland",
                "site_type": "Stream",
            },
            "geometry": {"coordinates": [-77.13, 38.95]},
        }
    ]
}


def _values(series_id, values):
    # Newest first, as sortby=-time returns them.
    return [
        {
            "properties": {
                "time_series_id": series_id,
                "time": f"2026-10-10T15:{50 - 5 * i:02d}:00+00:00",
                "value": str(v),
                "unit_of_measure": "ft^3/s",
                "approval_status": "Provisional",
                "qualifier": None,
            }
        }
        for i, v in enumerate(values)
    ]


def _router(continuous, metadata=None):
    calls = []

    def fake_get(url, params, headers, timeout):
        calls.append((url, params, headers))
        if url.endswith("monitoring-locations/items"):
            return _response(LOCATIONS)
        if url.endswith("time-series-metadata/items"):
            return _response(metadata or {"features": []})
        return _response(continuous)

    return fake_get, calls


def test_no_tool_still_points_at_waterservices():
    for config in CONFIGS.values():
        assert config["type"] == "USGSWaterTool"
        assert "waterservices.usgs.gov" not in json.dumps(config.get("fields", {}))


def test_streamflow_request_and_flattened_series():
    fake, calls = _router({"features": _values("ts1", [1560, 1550, 1540])})
    with patch("tooluniverse.usgs_water_tool.requests.get", side_effect=fake):
        result = USGSWaterTool(CONFIGS["USGSWater_get_streamflow"]).run(
            {"sites": "01646500", "period": "pt2h"}
        )

    assert result["status"] == "success"
    continuous = [c for c in calls if c[0].endswith("continuous/items")][0][1]
    assert continuous["monitoring_location_id"] == "USGS-01646500"
    assert continuous["parameter_code"] == "00060"
    assert continuous["time"] == "PT2H"
    assert continuous["sortby"] == "-time"
    assert continuous["limit"] == 500

    (series,) = result["data"]
    assert series["site_number"] == "01646500"
    assert series["site_name"] == "POTOMAC RIVER NEAR WASH, DC"
    assert (series["latitude"], series["longitude"]) == (38.95, -77.13)
    assert [v["value"] for v in series["values"]] == [1540.0, 1550.0, 1560.0]
    assert series["latest"]["value"] == 1560.0
    assert series["sensor"] is None
    # One site, one series: no metadata lookup needed.
    assert not any(c[0].endswith("time-series-metadata/items") for c in calls)


def test_several_sensors_at_one_site_stay_separate_and_labelled():
    features = _values("lower", [18.2, 18.2]) + _values("upper", [18.1, 18.0])
    metadata = {
        "features": [
            {"id": "lower", "properties": {"sublocation_identifier": "LOWER"}},
            {"id": "upper", "properties": {"sublocation_identifier": "UPPER"}},
        ]
    }
    fake, _ = _router({"features": features}, metadata)
    with patch("tooluniverse.usgs_water_tool.requests.get", side_effect=fake):
        result = USGSWaterTool(CONFIGS["USGSWater_get_water_temperature"]).run(
            {"sites": "USGS-01646500"}
        )

    by_sensor = {s["sensor"]: s for s in result["data"]}
    assert set(by_sensor) == {"LOWER", "UPPER"}
    assert [v["value"] for v in by_sensor["UPPER"]["values"]] == [18.0, 18.1]
    assert by_sensor["LOWER"]["value_count"] == 2


def test_site_without_data_is_reported_not_dropped_silently():
    fake, _ = _router({"features": []})
    with patch("tooluniverse.usgs_water_tool.requests.get", side_effect=fake):
        result = USGSWaterTool(CONFIGS["USGSWater_get_water_temperature"]).run(
            {"sites": "01578310", "period": "PT6H"}
        )

    assert result["status"] == "success"
    assert result["data"] == []
    assert result["metadata"]["sites_without_data"] == ["01578310"]


def test_truncation_is_disclosed():
    page = {"features": _values("ts1", [1, 2]), "links": [{"rel": "next"}]}
    fake, calls = _router(page)
    with patch("tooluniverse.usgs_water_tool.requests.get", side_effect=fake):
        result = USGSWaterTool(CONFIGS["USGSWater_get_streamflow"]).run(
            {"sites": "01646500", "period": "P30D", "max_values": 2}
        )

    assert result["data"][0]["truncated"] is True
    assert "truncation_note" in result["metadata"]
    assert [c for c in calls if c[0].endswith("continuous/items")][0][1]["limit"] == 2


@pytest.mark.parametrize(
    "arguments",
    [{"sites": "Potomac"}, {"sites": ""}, {"sites": "01646500", "period": "2 hours"}],
)
def test_bad_input_is_rejected_without_a_request(arguments):
    with patch("tooluniverse.usgs_water_tool.requests.get") as get:
        result = USGSWaterTool(CONFIGS["USGSWater_get_streamflow"]).run(arguments)

    assert result["status"] == "error"
    get.assert_not_called()


def test_api_key_is_sent_only_when_configured(monkeypatch):
    fake, calls = _router({"features": []})
    monkeypatch.delenv("USGS_WATER_API_KEY", raising=False)
    with patch("tooluniverse.usgs_water_tool.requests.get", side_effect=fake):
        USGSWaterTool(CONFIGS["USGSWater_get_streamflow"]).run({"sites": "01646500"})
    assert all("X-Api-Key" not in headers for _, _, headers in calls)

    calls.clear()
    monkeypatch.setenv("USGS_WATER_API_KEY", "k123")
    with patch("tooluniverse.usgs_water_tool.requests.get", side_effect=fake):
        USGSWaterTool(CONFIGS["USGSWater_get_streamflow"]).run({"sites": "01646500"})
    assert all(headers.get("X-Api-Key") == "k123" for _, _, headers in calls)


def test_server_error_is_retryable_and_has_no_html():
    with patch(
        "tooluniverse.usgs_water_tool.requests.get",
        return_value=_response("<html><body>Service Unavailable</body></html>", 503),
    ) as get:
        get.return_value.json.side_effect = ValueError("no json")
        result = USGSWaterTool(CONFIGS["USGSWater_get_streamflow"]).run(
            {"sites": "01646500"}
        )

    assert result["status"] == "error"
    assert result["retryable"] is True
    assert "HTTP 503" in result["error"]
    assert "<" not in result["error"]


@pytest.mark.network
def test_live_streamflow():
    result = USGSWaterTool(CONFIGS["USGSWater_get_streamflow"]).run(
        {"sites": "01646500", "period": "P1D", "max_values": 5}
    )
    assert result["status"] == "success", result
    assert result["data"][0]["unit"] == "ft^3/s"
    assert result["data"][0]["value_count"] == 5
