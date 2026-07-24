"""Regression guard for Fix-R28-2 in stitch_tool.py: STITCH_BASE_URL pointed
at string-db.org (a genuinely different sister database, not a renamed/
merged STITCH) instead of STITCH's own host. Confirmed live: string-db.org's
own /resolve fuzzy-matched the chemical name "aspirin" to an unrelated
protein (SLC17A4), and its /interaction_partners rejected the real STITCH
chemical id "-1.CID100002244" as "not found" -- so every chemical-protein
query was silently returning wrong, mislabeled protein-protein data instead
of failing. stitch.embl.de (the API docs' old host) now redirects to
stitch-db.org, confirmed live as STITCH's current host, so queries now go
there instead.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.stitch_tool import STITCH_BASE_URL, STITCHTool

pytestmark = pytest.mark.unit


def _tool(operation):
    return STITCHTool({"fields": {"operation": operation}})


def _resp(status_code, json_body=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_body or {}
    r.raise_for_status = MagicMock()
    return r


class TestCorrectHost:
    def test_base_url_is_stitch_not_string(self):
        assert STITCH_BASE_URL == "https://stitch-db.org/api"
        assert "string-db.org" not in STITCH_BASE_URL

    def test_get_interactions_queries_stitch_host(self):
        tool = _tool("get_interactions")
        with patch(
            "tooluniverse.stitch_tool.requests.get", return_value=_resp(200, [])
        ) as mock_get:
            tool.run({"identifiers": ["CIDm00002244"]})

        called_url = mock_get.call_args.args[0]
        assert called_url.startswith("https://stitch-db.org/api")

    def test_get_interactors_queries_stitch_host(self):
        tool = _tool("get_interactors")
        with patch(
            "tooluniverse.stitch_tool.requests.get", return_value=_resp(200, [])
        ) as mock_get:
            tool.run({"identifiers": ["CIDm00002244"]})

        called_url = mock_get.call_args.args[0]
        assert called_url.startswith("https://stitch-db.org/api")

    def test_resolve_queries_stitch_host(self):
        tool = _tool("resolve")
        with patch(
            "tooluniverse.stitch_tool.requests.get", return_value=_resp(200, [])
        ) as mock_get:
            tool.run({"identifier": "aspirin"})

        called_url = mock_get.call_args.args[0]
        assert called_url.startswith("https://stitch-db.org/api")

    def test_404_reports_honest_error_not_wrong_data(self):
        # If the correct-database endpoint is unavailable, the tool must
        # fail honestly rather than fall back to a different database's
        # unrelated data.
        tool = _tool("get_interactions")
        with patch(
            "tooluniverse.stitch_tool.requests.get", return_value=_resp(404)
        ):
            result = tool.run({"identifiers": ["aspirin"]})

        assert result["status"] == "error"
        assert "stitch-db.org" in result["error"]
