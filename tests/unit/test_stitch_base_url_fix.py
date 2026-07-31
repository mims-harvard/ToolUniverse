"""Regression guard for Fix-R19E-3: STITCHTool pointed at string-db.org,
STRING's own PROTEIN-ONLY network API -- confirmed live it silently
returned real but entirely protein-protein data (e.g. resolving "aspirin"
returned the gene SLC17A4) with zero chemicals anywhere in the response.
stitch.embl.de (STITCH's real domain) 301-redirects to stitch-db.org, which
correctly resolves chemical names/CIDs to STITCH-format stringIds. The
network/interactions sub-endpoints still 404 on the new domain even for a
correctly-resolved identifier (confirmed live); those now give an honest
error instead of implying the identifier itself is the problem.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.stitch_tool import STITCHTool, STITCH_BASE_URL

pytestmark = pytest.mark.unit


def _tool(operation):
    return STITCHTool({"name": "stitch_test", "fields": {"operation": operation}})


def _resp(json_body=None, status_code=200):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_body
    r.raise_for_status = MagicMock()
    return r


def test_base_url_points_at_real_stitch_domain_not_string_db():
    assert "stitch-db.org" in STITCH_BASE_URL
    assert "string-db.org" not in STITCH_BASE_URL


def test_resolve_identifier_hits_correct_base_url():
    tool = _tool("resolve")
    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        return _resp([{"stringId": "-1.CID100002244", "preferredName": "aspirin", "taxonName": "small molecule"}])

    with patch("tooluniverse.stitch_tool.requests.get", side_effect=fake_get):
        result = tool.run({"identifier": "aspirin"})

    assert result["status"] == "success"
    assert captured["url"].startswith("https://stitch-db.org/api")
    assert result["data"][0]["taxonName"] == "small molecule"


def test_get_interactions_404_gives_honest_endpoint_unavailable_message():
    tool = _tool("get_interactions")

    with patch("tooluniverse.stitch_tool.requests.get", return_value=_resp(status_code=404)):
        result = tool.run({"identifiers": ["aspirin"]})

    assert result["status"] == "error"
    assert "endpoint appears unavailable" in result["error"]
    assert "not necessarily a bad identifier" in result["error"]


def test_get_interactors_404_gives_honest_endpoint_unavailable_message():
    tool = _tool("get_interactors")

    with patch("tooluniverse.stitch_tool.requests.get", return_value=_resp(status_code=404)):
        result = tool.run({"identifiers": ["aspirin"]})

    assert result["status"] == "error"
    assert "endpoint appears unavailable" in result["error"]


def test_get_interactions_success_still_works():
    tool = _tool("get_interactions")

    with patch(
        "tooluniverse.stitch_tool.requests.get",
        return_value=_resp([{"stringId_A": "CID1", "stringId_B": "P1"}]),
    ):
        result = tool.run({"identifiers": ["CIDm00002244"]})

    assert result["status"] == "success"
    assert result["data"][0]["stringId_A"] == "CID1"
