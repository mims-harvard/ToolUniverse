from __future__ import annotations

import pytest

from tooluniverse import vsd_tool

pytestmark = pytest.mark.unit


def _request(endpoint):
    return {
        "url": endpoint,
        "status_code": 200,
        "content_type": "application/json",
        "response_bytes": 100,
        "peer_ip": "93.184.216.34",
        "redirects": 0,
    }


def test_cdc_adapter_constrains_geography_and_normalizes_records(monkeypatch):
    """CDC CHD calls use a fixed query shape and reject unrequested geography."""
    observed = {}

    def fake_safe_get(endpoint, params):
        observed.update(params)
        return (
            [
                {
                    "year": "2023",
                    "stateabbr": "AL",
                    "countyname": "Autauga",
                    "locationname": "01001020100",
                    "measure": "Coronary heart disease among adults",
                    "data_value": "7.2",
                    "low_confidence_limit": "6.2",
                    "high_confidence_limit": "8.1",
                }
            ],
            _request(endpoint),
        )

    monkeypatch.setattr(vsd_tool, "_safe_get_json", fake_safe_get)
    result = vsd_tool.VSDCDCPlacesCoronaryHeartDisease({}).run(
        {"state_abbr": "al", "county_name": "Autauga", "limit": 20}
    )

    assert result["data"]["tracts"][0]["data_value"] == "7.2"
    assert result["data"]["possibly_truncated"] is False
    assert "stateabbr='AL'" in observed["$where"]
    assert "countyname='Autauga'" in observed["$where"]
    assert observed["$limit"] == 20


def test_cdc_adapter_rejects_wrong_returned_county(monkeypatch):
    """A provider response cannot escape the requested county contract."""
    monkeypatch.setattr(
        vsd_tool,
        "_safe_get_json",
        lambda endpoint, params: (
            [
                {
                    "year": "2023",
                    "stateabbr": "AL",
                    "countyname": "Jefferson",
                    "locationname": "01073000100",
                    "measure": "Coronary heart disease among adults",
                    "data_value": "8.0",
                    "low_confidence_limit": "7.0",
                    "high_confidence_limit": "9.0",
                }
            ],
            _request(endpoint),
        ),
    )

    with pytest.raises(vsd_tool.VSDPolicyError, match="escaped"):
        vsd_tool.VSDCDCPlacesCoronaryHeartDisease({}).run(
            {"state_abbr": "AL", "county_name": "Autauga"}
        )


def test_openfda_adapter_normalizes_one_label(monkeypatch):
    """The openFDA adapter returns a typed subset for an exact set UUID."""
    set_id = "0058175f-3474-40c3-a046-6cfaec86d84b"
    monkeypatch.setattr(
        vsd_tool,
        "_safe_get_json",
        lambda endpoint, params: (
            {
                "results": [
                    {
                        "set_id": set_id,
                        "effective_time": "20240416",
                        "warnings": ["Ask a doctor before use."],
                        "openfda": {
                            "brand_name": ["Low Dose Aspirin"],
                            "generic_name": ["ASPIRIN"],
                            "route": ["ORAL"],
                        },
                    }
                ]
            },
            _request(endpoint),
        ),
    )

    result = vsd_tool.VSDOpenFDALabelBySetId({}).run({"set_id": set_id})
    assert result["data"]["label"] == {
        "set_id": set_id,
        "effective_time": "20240416",
        "brand_name": "Low Dose Aspirin",
        "generic_name": "ASPIRIN",
        "route": "ORAL",
        "warnings": ["Ask a doctor before use."],
    }


def test_ensembl_adapter_rejects_unexpected_schema(monkeypatch):
    """The reviewed Ensembl adapter fails closed on schema drift."""
    monkeypatch.setattr(
        vsd_tool,
        "_safe_get_json",
        lambda endpoint: ({"status": "ok"}, _request(endpoint)),
    )
    with pytest.raises(vsd_tool.VSDPolicyError, match="ping schema"):
        vsd_tool.VSDEnsemblServiceStatus({}).run({})
