"""Regression guard for Fix-R76A-2: AlphaMissense_get_protein_scores's
per-residue fetch helper (_fetch_single_residue) treated every non-200
response identically, dropping the position from the output with zero
indication of what happened. Confirmed live: the API 404s with a clear
"no data for this residue" message for a position outside its real coverage
(e.g. resi=99999 on a real protein) -- a legitimate empty result, not a
failure -- while a genuine request failure (rate limit, timeout, 5xx) is a
different thing entirely. Also confirmed live during this fix's own testing:
1 of 20 real requests for a real protein failed, and previously would have
silently vanished from the response with no trace.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.alphamissense_tool import AlphaMissenseTool

pytestmark = pytest.mark.unit


def _tool():
    return AlphaMissenseTool({"name": "AlphaMissense_get_protein_scores"})


def _fasta_resp(length=5):
    r = MagicMock()
    r.status_code = 200
    r.text = ">sp|TEST|TEST\n" + "A" * length
    return r


def _score_resp(status_code, body=None):
    r = MagicMock()
    r.status_code = status_code
    if body is not None:
        r.json.return_value = body
    return r


def test_fetch_single_residue_404_is_not_marked_failed():
    """A 404 means "AlphaMissense has no data for this residue" -- a
    legitimate empty result, confirmed live, not a failure."""
    tool = _tool()
    with patch(
        "tooluniverse.alphamissense_tool.requests.get",
        return_value=_score_resp(404),
    ):
        data, failed = tool._fetch_single_residue("P05067", 99999)

    assert data is None
    assert failed is False


def test_fetch_single_residue_500_is_marked_failed():
    tool = _tool()
    with patch(
        "tooluniverse.alphamissense_tool.requests.get",
        return_value=_score_resp(500),
    ):
        data, failed = tool._fetch_single_residue("P05067", 100)

    assert data is None
    assert failed is True


def test_fetch_single_residue_request_exception_is_marked_failed():
    tool = _tool()
    with patch(
        "tooluniverse.alphamissense_tool.requests.get",
        side_effect=requests.exceptions.Timeout("timed out"),
    ):
        data, failed = tool._fetch_single_residue("P05067", 100)

    assert data is None
    assert failed is True


def test_partial_failure_is_surfaced_not_silently_dropped():
    """The core confirmed-live bug: some positions failing (not 404 -- a
    real request failure) must not silently vanish from the response."""
    tool = _tool()

    def fake_get(url, params=None, timeout=None):
        if "uniprot.org" in url or "fasta" in url.lower():
            return _fasta_resp(length=3)
        resi = params.get("resi") if params else None
        if resi == 2:
            return _score_resp(500)
        return _score_resp(200, {"uid": "TEST", "resi": resi, "mean_all": 0.1})

    with patch.object(tool, "_fetch_protein_length", return_value=3), patch(
        "tooluniverse.alphamissense_tool.requests.get", side_effect=fake_get
    ):
        result = tool.run({"uniprot_id": "TEST"})

    assert result["status"] == "success"
    assert result["data"]["n_positions_failed"] == 1
    assert "note" in result["data"]
    assert len(result["data"]["scores"]) == 2


def test_all_positions_genuinely_no_data_reports_database_absence():
    """All-404 (genuinely no AlphaMissense coverage) keeps the existing,
    correct "may not be in the database" message -- not the new
    all-requests-failed message."""
    tool = _tool()

    def fake_get(url, params=None, timeout=None):
        if "resi" not in (params or {}):
            return _fasta_resp(length=2)
        return _score_resp(404)

    with patch.object(tool, "_fetch_protein_length", return_value=2), patch(
        "tooluniverse.alphamissense_tool.requests.get", side_effect=fake_get
    ):
        result = tool.run({"uniprot_id": "TEST"})

    assert result["status"] == "error"
    assert "may not be in the AlphaMissense database" in result["error"]


def test_all_positions_genuinely_failed_reports_failure_not_absence():
    """All-500 (every request genuinely failed) must not use the same
    "may not be in the database" message as all-404 -- that's misleading
    when the real cause is a request failure, not missing coverage."""
    tool = _tool()

    def fake_get(url, params=None, timeout=None):
        if "resi" not in (params or {}):
            return _fasta_resp(length=2)
        return _score_resp(503)

    with patch.object(tool, "_fetch_protein_length", return_value=2), patch(
        "tooluniverse.alphamissense_tool.requests.get", side_effect=fake_get
    ):
        result = tool.run({"uniprot_id": "TEST"})

    assert result["status"] == "error"
    assert "may not be in the AlphaMissense database" not in result["error"]
    assert "failed" in result["error"].lower()


def test_no_failures_omits_failure_fields():
    """Backward compatibility: when nothing fails, the response must not
    gain the new n_positions_failed/note keys."""
    tool = _tool()

    def fake_get(url, params=None, timeout=None):
        if "resi" not in (params or {}):
            return _fasta_resp(length=2)
        resi = params.get("resi")
        return _score_resp(200, {"uid": "TEST", "resi": resi, "mean_all": 0.1})

    with patch.object(tool, "_fetch_protein_length", return_value=2), patch(
        "tooluniverse.alphamissense_tool.requests.get", side_effect=fake_get
    ):
        result = tool.run({"uniprot_id": "TEST"})

    assert result["status"] == "success"
    assert "n_positions_failed" not in result["data"]
    assert "note" not in result["data"]
