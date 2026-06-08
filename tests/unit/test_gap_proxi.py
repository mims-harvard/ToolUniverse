"""Unit tests for ProteomeXchange_get_spectrum_by_usi.

Closes the spectrum/PSM-level gap: the existing ProteomeXchange tools are
dataset-level only (GetDataset metadata + dataset search). This tool wraps
the PROXI v0.1 /spectra endpoint, which resolves a Universal Spectrum
Identifier (USI) to a single spectrum, parsing CV-term attributes (scan
number, charge, precursor m/z, peptide) and the m/z + intensity peak arrays
(capped to the first MAX_PEAKS peaks).
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from tooluniverse.proteomexchange_tool import ProteomeXchangeTool, MAX_PEAKS


_USI = (
    "mzspec:PXD000561:Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555:VLHPLEGAVVIIFK/2"
)


def _make_spectrum_tool():
    return ProteomeXchangeTool(
        {
            "name": "ProteomeXchange_get_spectrum_by_usi",
            "type": "ProteomeXchangeTool",
            "fields": {"endpoint_type": "get_spectrum_by_usi"},
            "parameter": {"type": "object", "properties": {}},
        }
    )


# Trimmed slice of the live /spectra response for the USI above.
_SPECTRUM = {
    "attributes": [
        {"accession": "MS:1008025", "name": "scan number", "value": "17555"},
        {"accession": "MS:1000744", "name": "selected ion m/z", "value": "767.9739"},
        {"accession": "MS:1000041", "name": "charge state", "value": "2"},
        {
            "accession": "MS:1000888",
            "name": "unmodified peptide sequence",
            "value": "VLHPLEGAVVIIFK",
        },
    ],
    "mzs": [110.0712, 111.0682, 111.0745],
    "intensities": [39316.4648, 319.6931, 1509.0269],
}


@pytest.mark.unit
@patch("tooluniverse.proteomexchange_tool.requests.get")
def test_spectrum_parses_attributes_and_peaks(mock_get):
    resp = MagicMock()
    resp.json.return_value = [_SPECTRUM]
    resp.raise_for_status.return_value = None
    mock_get.return_value = resp

    result = _make_spectrum_tool().run({"usi": _USI})

    # Correct PROXI endpoint hit with the USI + default resultType.
    called_url = mock_get.call_args[0][0]
    assert "/api/proxi/v0.1/spectra" in called_url
    sent_params = mock_get.call_args[1]["params"]
    assert sent_params["usi"] == _USI
    assert sent_params["resultType"] == "full"

    assert result["status"] == "success"
    data = result["data"]
    assert data["usi"] == _USI
    assert data["scan_number"] == "17555"
    assert data["charge"] == "2"
    assert data["precursor_mz"] == "767.9739"
    assert data["peptide_sequence"] == "VLHPLEGAVVIIFK"
    assert len(data["attributes"]) == 4

    # Peaks pair m/z with intensity; nothing truncated here.
    assert data["total_peaks"] == 3
    assert data["returned_peaks"] == 3
    assert data["peaks_truncated"] is False
    assert "note" not in data
    assert data["peaks"][0] == {"mz": 110.0712, "intensity": 39316.4648}

    assert result["metadata"]["endpoint"] == "get_spectrum_by_usi"
    assert result["metadata"]["source"] == "ProteomeXchange/PROXI"


@pytest.mark.unit
@patch("tooluniverse.proteomexchange_tool.requests.get")
def test_spectrum_caps_peak_list(mock_get):
    n = MAX_PEAKS + 50
    big_spectrum = {
        "attributes": [],
        "mzs": [100.0 + i for i in range(n)],
        "intensities": [float(i) for i in range(n)],
    }
    resp = MagicMock()
    resp.json.return_value = [big_spectrum]
    resp.raise_for_status.return_value = None
    mock_get.return_value = resp

    result = _make_spectrum_tool().run({"usi": _USI})

    data = result["data"]
    assert result["status"] == "success"
    assert data["total_peaks"] == n
    assert data["returned_peaks"] == MAX_PEAKS
    assert len(data["peaks"]) == MAX_PEAKS
    assert data["peaks_truncated"] is True
    assert str(MAX_PEAKS) in data["note"]


@pytest.mark.unit
def test_spectrum_missing_usi():
    result = _make_spectrum_tool().run({})
    assert result["status"] == "error"
    assert "usi" in result["error"]


@pytest.mark.unit
@patch("tooluniverse.proteomexchange_tool.requests.get")
def test_spectrum_empty_list(mock_get):
    resp = MagicMock()
    resp.json.return_value = []
    resp.raise_for_status.return_value = None
    mock_get.return_value = resp

    result = _make_spectrum_tool().run({"usi": _USI})
    assert result["status"] == "error"
    assert "No spectrum found" in result["error"]


@pytest.mark.unit
@patch("tooluniverse.proteomexchange_tool.requests.get")
def test_spectrum_error_dict_payload(mock_get):
    # PROXI returns an error-shaped dict (e.g. 404 with a 'detail' field).
    resp = MagicMock()
    resp.json.return_value = {
        "detail": "USI not found in any repository",
        "title": "Not Found",
        "status": 404,
    }
    resp.raise_for_status.return_value = None
    mock_get.return_value = resp

    result = _make_spectrum_tool().run({"usi": _USI})
    assert result["status"] == "error"
    assert "USI not found in any repository" in result["error"]


@pytest.mark.unit
@patch("tooluniverse.proteomexchange_tool.requests.get")
def test_spectrum_http_error(mock_get):
    err = requests.exceptions.HTTPError()
    err.response = MagicMock(status_code=500)
    resp = MagicMock()
    resp.raise_for_status.side_effect = err
    mock_get.return_value = resp

    result = _make_spectrum_tool().run({"usi": _USI})
    assert result["status"] == "error"
    assert "500" in result["error"]
