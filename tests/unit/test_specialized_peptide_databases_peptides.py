"""Offline unit tests for the AMPSphere single-record + sequence-match tools.

Covers ``AMPSphereGetAmpTool`` (AMPSphere_get_amp) and
``AMPSphereSequenceMatchTool`` (AMPSphere_sequence_match) with mocked HTTP, one
success path and one error path per tool, plus input-validation and the
case-insensitive sequence cleanup. No network access.
"""

from unittest.mock import patch

import pytest

from tooluniverse.ampsphere_record_tool import (
    AMPSphereGetAmpTool,
    AMPSphereSequenceMatchTool,
)

pytestmark = pytest.mark.unit


class _FakeResponse:
    """Minimal stand-in for ``requests.Response``."""

    def __init__(self, status_code=200, json_data=None, text="", raise_json=False):
        self.status_code = status_code
        self._json = json_data
        self.text = text
        self.url = "https://ampsphere-api.big-data-biology.org/v1/mock"
        self._raise_json = raise_json

    def json(self):
        if self._raise_json:
            raise ValueError("no json")
        return self._json


_AMP_RECORD = {
    "accession": "AMP10.000_000",
    "sequence": "KKVKSIFKKALAMMGENEVKAWGIGIK",
    "family": "SPHERE-III.001_493",
    "length": 27,
    "molecular_weight": 3005.685,
    "isoelectric_point": 10.125,
    "charge": 4.758,
    "aromaticity": 0.074,
    "instability_index": -18.34,
    "gravy": -0.111,
    "Antifam": "Passed",
    "RNAcode": "Failed",
    "metaproteomes": "Passed",
    "metatranscriptomes": "Passed",
    "coordinates": "Passed",
    "num_genes": None,
    "secondary_structure": {"helix": 0.555, "turn": 0.185, "sheet": 0.296},
    "metadata": {
        "data": [
            {
                "AMP": "AMP10.000_000",
                "GMSC_accession": "GMSC10.SMORF.x",
                "sample": "s1",
            },
            {
                "AMP": "AMP10.000_000",
                "GMSC_accession": "GMSC10.SMORF.y",
                "sample": "s2",
            },
        ]
    },
}


def _get_amp_tool():
    return AMPSphereGetAmpTool(tool_config={"name": "AMPSphere_get_amp"})


def _seqmatch_tool():
    return AMPSphereSequenceMatchTool(tool_config={"name": "AMPSphere_sequence_match"})


def test_get_amp_success():
    """get_amp returns the full record and a gene_count from metadata.data."""
    with patch(
        "tooluniverse.ampsphere_record_tool.requests.get",
        return_value=_FakeResponse(200, _AMP_RECORD),
    ):
        result = _get_amp_tool().run({"accession": "AMP10.000_000"})
    assert result["status"] == "success"
    assert result["data"]["sequence"] == "KKVKSIFKKALAMMGENEVKAWGIGIK"
    assert result["data"]["secondary_structure"]["helix"] == 0.555
    assert result["metadata"]["family"] == "SPHERE-III.001_493"
    assert result["metadata"]["gene_count"] == 2


def test_get_amp_invalid_accession_error():
    """An invalid-accession HTTP 500 maps to a clean not-found error result."""
    resp = _FakeResponse(500, {"detail": "invalid accession received."})
    with patch("tooluniverse.ampsphere_record_tool.requests.get", return_value=resp):
        result = _get_amp_tool().run({"accession": "AMP10.BAD"})
    assert result["status"] == "error"
    assert "no record" in result["error"].lower()


def test_get_amp_missing_accession_validation():
    """get_amp validates a missing accession without making a request."""
    result = _get_amp_tool().run({})
    assert result["status"] == "error"
    assert "accession is required" in result["error"]


def test_sequence_match_hit():
    """sequence_match reports matched=True and the accession on an exact hit."""
    payload = {"query": "KKVKSIFKKALAMMGENEVKAWGIGIK", "result": "AMP10.000_000"}
    with patch(
        "tooluniverse.ampsphere_record_tool.requests.get",
        return_value=_FakeResponse(200, payload),
    ):
        result = _seqmatch_tool().run({"query": "KKVKSIFKKALAMMGENEVKAWGIGIK"})
    assert result["status"] == "success"
    assert result["data"]["matched"] is True
    assert result["data"]["result"] == "AMP10.000_000"
    assert result["metadata"]["accession"] == "AMP10.000_000"


def test_sequence_match_no_hit():
    """A null result is reported as a successful matched=False membership test."""
    payload = {"query": "ACDEFGHIKLMNPQRST", "result": None}
    with patch(
        "tooluniverse.ampsphere_record_tool.requests.get",
        return_value=_FakeResponse(200, payload),
    ):
        result = _seqmatch_tool().run({"query": "ACDEFGHIKLMNPQRST"})
    assert result["status"] == "success"
    assert result["data"]["matched"] is False
    assert result["data"]["result"] is None


def test_sequence_match_uppercases_and_strips_query():
    """Lowercase / whitespace input is normalized to contiguous uppercase."""
    captured = {}

    def _fake_get(url, params=None, headers=None, timeout=None):
        captured["params"] = params
        return _FakeResponse(200, {"query": params["query"], "result": "AMP10.000_000"})

    with patch(
        "tooluniverse.ampsphere_record_tool.requests.get", side_effect=_fake_get
    ):
        result = _seqmatch_tool().run({"query": " kkvks ifkk "})
    assert captured["params"]["query"] == "KKVKSIFKK"
    assert result["status"] == "success"


def test_sequence_match_missing_query_validation():
    """sequence_match validates an empty query without making a request."""
    result = _seqmatch_tool().run({"query": "   "})
    assert result["status"] == "error"
    assert "required" in result["error"]


def test_sequence_match_request_exception():
    """A network exception is caught and returned as an error result."""
    import requests

    with patch(
        "tooluniverse.ampsphere_record_tool.requests.get",
        side_effect=requests.exceptions.ConnectionError("boom"),
    ):
        result = _seqmatch_tool().run({"query": "KKVK"})
    assert result["status"] == "error"
    assert "failed" in result["error"].lower()
