"""Offline, mocked unit tests for the AMPSphere modern-AMP-catalogue tools.

Covers all four AMPSphere tools — AMPSphere_search_amps (search + list_options),
AMPSphere_get_family, AMPSphere_get_amp_distributions, and
AMPSphere_get_amp_features — with a success-parse path and an error path each.
The HTTP layer (requests.get) is mocked so the tests are deterministic and run
without network access.
"""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

from tooluniverse.ampsphere_tool import (  # noqa: E402
    AMPSphereSearchAmpsTool,
    AMPSphereGetFamilyTool,
    AMPSphereGetAmpDistributionsTool,
    AMPSphereGetAmpFeaturesTool,
)


_AMPS_PAGE = {
    "info": {"currentPage": 0, "pageSize": 2, "totalPage": 55973, "totalItem": 111946},
    "data": [
        {
            "accession": "AMP10.000_000",
            "sequence": "KKVKSIFKKALAMMGENEVKAWGIGIK",
            "family": "SPHERE-III.001_493",
            "length": 27,
            "molecular_weight": 3005.685,
            "isoelectric_point": 10.13,
            "charge": 4.76,
            "Antifam": "Passed",
            "RNAcode": "Failed",
        }
    ],
}

_OPTIONS = {
    "quality": ["Passed", "Failed", "Not tested"],
    "habitat": ["human gut", "soil"],
    "microbial_source": ["Faecalibacterium"],
    "pep_length": {"min": 8, "max": 99},
}

_FAMILY = {
    "accession": "SPHERE-III.001_396",
    "consensus_sequence": "GDKLXXXXXVDXXXXGGLIVKXGSRMXDXSLXXKLXXLXXAMKXXG",
    "num_amps": 23,
    "downloads": {
        "alignment": "https://example/SPHERE-III.001_396.aln",
        "sequences": "https://example/SPHERE-III.001_396.faa",
    },
    "associated_amps": ["AMP10.072_299", "AMP10.085_907", "AMP10.810_114"],
    "feature_statistics": {"AMP10.072_299": {"length": 30}},
    "distributions": {"geo": {}, "habitat": {}, "microbial_source": {}},
}

_DISTRIBUTIONS = {
    "geo": {"type": "bubble map", "lat": [1.0, 2.0, 3.0], "lon": [4.0, 5.0, 6.0]},
    "habitat": {"type": "bar", "labels": ["human gut"], "values": [10]},
    "microbial_source": {"type": "bar", "labels": ["Prevotella"], "values": [5]},
}

_FEATURES = {
    "MW": 3005.685,
    "Length": 27.0,
    "Molar_extinction": {"cysteines_reduced": 0, "cystines_residues": 0},
    "Aromaticity": 0.074,
    "GRAVY": -0.111,
    "Instability_index": -18.348,
    "Isoelectric_point": 10.126,
    "Charge_at_pH_7": 4.759,
    "Secondary_structure": {"helix": 0.556, "turn": 0.185, "sheet": 0.296},
}


def _mock_response(
    json_value=None,
    status_code=200,
    raise_json=False,
    url="https://ampsphere-api.big-data-biology.org/v1/amps",
):
    resp = MagicMock()
    resp.status_code = status_code
    resp.url = url
    resp.text = (
        "" if json_value is not None else '{"detail": "invalid accession received."}'
    )
    if raise_json:
        resp.json.side_effect = ValueError("no json")
    elif status_code != 200 and json_value is None:
        resp.json.return_value = {"detail": "invalid accession received."}
    else:
        resp.json.return_value = json_value
    return resp


# --- AMPSphere_search_amps ------------------------------------------------


def test_search_amps_success():
    """Parses a paginated /v1/amps page and forwards filters + pagination."""
    tool = AMPSphereSearchAmpsTool({})
    with patch("tooluniverse.ampsphere_tool.requests.get") as get:
        get.return_value = _mock_response(_AMPS_PAGE)
        result = tool.run({"habitat": "human gut", "page_size": 2, "page": 0})
    assert result["status"] == "success"
    assert result["data"][0]["accession"] == "AMP10.000_000"
    assert result["metadata"]["total_item"] == 111946
    assert result["metadata"]["returned_count"] == 1
    assert result["metadata"]["filters"] == {"habitat": "human gut"}
    # filter + pagination params reach the API
    sent = get.call_args.kwargs["params"]
    assert sent["habitat"] == "human gut"
    assert sent["page_size"] == 2 and sent["page"] == 0


def test_search_amps_list_options_success():
    """list_options=true returns the /v1/all_available_options enum object."""
    tool = AMPSphereSearchAmpsTool({})
    with patch("tooluniverse.ampsphere_tool.requests.get") as get:
        get.return_value = _mock_response(_OPTIONS)
        result = tool.run({"list_options": True})
    assert result["status"] == "success"
    assert result["metadata"]["mode"] == "options"
    assert "Passed" in result["data"]["quality"]
    # options route is hit, not the search route
    assert get.call_args.args[0].endswith("/all_available_options")


def test_search_amps_http_error():
    """A non-200 from /v1/amps yields a structured error with the API detail."""
    tool = AMPSphereSearchAmpsTool({})
    with patch("tooluniverse.ampsphere_tool.requests.get") as get:
        get.return_value = _mock_response(None, status_code=422)
        result = tool.run({"pep_length_interval": "bad"})
    assert result["status"] == "error"
    assert "HTTP 422" in result["error"]
    assert result["response_snippet"] == "invalid accession received."


# --- AMPSphere_get_family -------------------------------------------------


def test_get_family_success():
    """Parses a /v1/families/{accession} record and counts its members."""
    tool = AMPSphereGetFamilyTool({})
    with patch("tooluniverse.ampsphere_tool.requests.get") as get:
        get.return_value = _mock_response(_FAMILY)
        result = tool.run({"accession": "SPHERE-III.001_396"})
    assert result["status"] == "success"
    assert result["data"]["consensus_sequence"].startswith("GDKL")
    assert result["metadata"]["num_amps"] == 23
    assert result["metadata"]["member_count"] == 3
    assert "alignment" in result["data"]["downloads"]


def test_get_family_missing_accession_error():
    """A missing accession returns an error without any HTTP call."""
    tool = AMPSphereGetFamilyTool({})
    with patch("tooluniverse.ampsphere_tool.requests.get") as get:
        result = tool.run({})
    assert result["status"] == "error"
    assert "accession is required" in result["error"]
    get.assert_not_called()


# --- AMPSphere_get_amp_distributions --------------------------------------


def test_get_amp_distributions_success():
    """Parses geo/habitat/source blocks and counts geo bubble-map points."""
    tool = AMPSphereGetAmpDistributionsTool({})
    with patch("tooluniverse.ampsphere_tool.requests.get") as get:
        get.return_value = _mock_response(_DISTRIBUTIONS)
        result = tool.run({"accession": "AMP10.000_000"})
    assert result["status"] == "success"
    assert result["data"]["geo"]["type"] == "bubble map"
    assert result["metadata"]["geo_point_count"] == 3


def test_get_amp_distributions_bad_accession_error():
    """An invalid accession (HTTP 400) yields a structured error result."""
    tool = AMPSphereGetAmpDistributionsTool({})
    with patch("tooluniverse.ampsphere_tool.requests.get") as get:
        get.return_value = _mock_response(None, status_code=400)
        result = tool.run({"accession": "AMP99.999_999"})
    assert result["status"] == "error"
    assert "HTTP 400" in result["error"]


# --- AMPSphere_get_amp_features -------------------------------------------


def test_get_amp_features_success():
    """Parses the physicochemical + secondary-structure feature profile."""
    tool = AMPSphereGetAmpFeaturesTool({})
    with patch("tooluniverse.ampsphere_tool.requests.get") as get:
        get.return_value = _mock_response(_FEATURES)
        result = tool.run({"accession": "AMP10.000_000"})
    assert result["status"] == "success"
    assert result["data"]["MW"] == 3005.685
    assert result["data"]["Secondary_structure"]["helix"] == 0.556
    assert result["metadata"]["accession"] == "AMP10.000_000"


def test_get_amp_features_unexpected_payload_error():
    """A payload without the expected MW field is reported as an error."""
    tool = AMPSphereGetAmpFeaturesTool({})
    with patch("tooluniverse.ampsphere_tool.requests.get") as get:
        get.return_value = _mock_response({"unexpected": "shape"})
        result = tool.run({"accession": "AMP10.000_000"})
    assert result["status"] == "error"
    assert "feature profile" in result["error"]
