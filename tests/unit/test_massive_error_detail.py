"""Regression guard for Fix-R20C-4: MassIVETool's ProXI error handler
discarded the upstream API's own JSON error body, showing only requests'
generic "404 Client Error: ..." string.

Confirmed live for MassIVE_get_protein_identifications with a sparse/
missing human protein accession: the real ProXI 404 body is
{"code":404,"title":"Not Found","message":"No data found for the
specified parameters."}, but the tool's error message dropped the
"message" field entirely. Fixed by parsing the HTTPError response body
and appending its "message" field when present.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.massive_tool import MassIVETool

pytestmark = pytest.mark.unit


def _tool():
    return MassIVETool(
        {"name": "massive_test", "fields": {"operation": "get_protein_identifications"}}
    )


def _http_error_resp(status_code, json_body):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_body
    err = requests.exceptions.HTTPError(response=r)
    r.raise_for_status = MagicMock(side_effect=err)
    return r


def test_404_error_includes_upstream_message():
    tool = _tool()
    resp = _http_error_resp(
        404, {"code": 404, "title": "Not Found", "message": "No data found for the specified parameters."}
    )

    with patch("tooluniverse.massive_tool.requests.get", return_value=resp):
        result = tool.run({"protein_accession": "HXK1_HUMAN"})

    assert result["status"] == "error"
    assert "No data found for the specified parameters." in result["error"]


def test_error_without_json_body_falls_back_gracefully():
    tool = _tool()
    r = MagicMock()
    r.status_code = 500
    r.json.side_effect = ValueError("not json")
    err = requests.exceptions.HTTPError(response=r)
    r.raise_for_status = MagicMock(side_effect=err)

    with patch("tooluniverse.massive_tool.requests.get", return_value=r):
        result = tool.run({"protein_accession": "HXK1_HUMAN"})

    assert result["status"] == "error"
    assert "MassIVE API error" in result["error"]


def test_success_case_unaffected():
    tool = _tool()
    r = MagicMock()
    r.status_code = 200
    r.raise_for_status = MagicMock()
    r.json.return_value = [
        {"proteinAccession": "A2M_MOUSE", "countPSM": 146131, "countPeptides": 106}
    ]

    with patch("tooluniverse.massive_tool.requests.get", return_value=r):
        result = tool.run({"protein_accession": "A2M_MOUSE"})

    assert result["status"] == "success"
    assert result["data"]["protein_accession"] == "A2M_MOUSE"
