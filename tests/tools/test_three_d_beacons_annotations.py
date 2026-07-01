"""
Unit tests for ThreeDBeaconsTool annotations 404 handling.

The 3D Beacons annotations endpoint returns HTTP 404 when a valid protein
simply has no annotations of the requested type (e.g. P04637 has DOMAIN
annotations but no BINDING annotations). That is an empty result, not a
failure — the tool must report it as a success with zero annotations rather
than the misleading "No structures found" error.
"""

import json
from unittest.mock import patch, MagicMock


def _tool():
    from tooluniverse.three_d_beacons_tool import ThreeDBeaconsTool

    cfg = next(
        t
        for t in json.load(open("src/tooluniverse/data/three_d_beacons_tools.json"))
        if t["name"] == "ThreeDBeacons_get_annotations"
    )
    return ThreeDBeaconsTool(cfg)


class TestAnnotations404:
    def test_404_is_empty_success_not_error(self):
        resp = MagicMock()
        resp.status_code = 404
        with patch(
            "tooluniverse.three_d_beacons_tool.requests.get", return_value=resp
        ):
            result = _tool().run({"accession": "P04637", "type": "BINDING"})
        assert result["status"] == "success"
        assert result["data"]["annotation_count"] == 0
        assert result["data"]["annotations"] == []
        # message must not claim "structures" for an annotations query
        assert "structure" not in result["data"]["note"].lower()

    def test_200_returns_annotations(self):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "accession": "P38398",
            "id": "P38398",
            "sequence": "MDL",
            "annotation": [
                {"type": "DOMAIN", "description": "BRCT", "residues": [1, 2, 3]}
            ],
        }
        resp.raise_for_status = MagicMock()
        with patch(
            "tooluniverse.three_d_beacons_tool.requests.get", return_value=resp
        ):
            result = _tool().run({"accession": "P38398", "type": "DOMAIN"})
        assert result["status"] == "success"
        assert result["data"]["annotation_count"] == 1
        assert result["data"]["annotations"][0]["type"] == "DOMAIN"

    def test_non_404_http_error_still_errors(self):
        import requests

        resp = MagicMock()
        resp.status_code = 500
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=resp
        )
        with patch(
            "tooluniverse.three_d_beacons_tool.requests.get", return_value=resp
        ):
            result = _tool().run({"accession": "P38398", "type": "DOMAIN"})
        assert result["status"] == "error"
