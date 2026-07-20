"""Regression guard for Fix-R21D-1/2: NeuroMorphoTool and AllenBrainTool's
HTTPError handlers discarded the real upstream status code, always
reporting "unknown" instead.

Confirmed live for NeuroMorpho_get_neuron with a nonexistent neuron_id
(999999999): the real upstream response is HTTP 404 with a JSON body
{"status":404,"error":"Not Found","message":"Requested neuron not
found"}, but the tool reported {"status":"error","error":"NeuroMorpho API
HTTP error: unknown"}.

Root cause: `requests.Response.__bool__` returns `self.ok` (True only for
2xx/3xx), so `e.response.status_code if e.response else "unknown"` treats
every 4xx/5xx Response object as falsy and always falls through to
"unknown" -- the exact opposite of the intended check. The identical
pattern existed in AllenBrainTool (confirmed via source inspection and a
live 404 against a bad Allen Brain Atlas API path). Fixed by checking
`e.response is not None` instead of truthiness, and (for NeuroMorpho,
whose error responses are JSON) also surfacing the upstream "message"
field.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.neuromorpho_tool import NeuroMorphoTool
from tooluniverse.allen_brain_tool import AllenBrainTool

pytestmark = pytest.mark.unit


def _http_error_response(status_code, json_body=None, raise_on_json=False):
    # A real requests.Response (not a bare MagicMock) so `bool(r)` reflects
    # the actual `.ok` property (False for 4xx/5xx) -- a plain MagicMock's
    # __bool__ defaults to True regardless of status_code, which would let
    # the truthiness bug this test guards against (`e.response else
    # "unknown"`) pass silently even when reintroduced.
    r = requests.Response()
    r.status_code = status_code
    if raise_on_json:
        r.json = MagicMock(side_effect=ValueError("not json"))
    else:
        r.json = MagicMock(return_value=json_body or {})
    err = requests.exceptions.HTTPError(response=r)
    r.raise_for_status = MagicMock(side_effect=err)
    return r, err


def test_neuromorpho_404_reports_real_status_and_message():
    tool = NeuroMorphoTool(
        {"name": "nm_test", "fields": {"endpoint_type": "neuron", "query_mode": "id"}}
    )
    resp, err = _http_error_response(
        404, {"status": 404, "error": "Not Found", "message": "Requested neuron not found"}
    )

    def fake_get(url, **kwargs):
        raise err

    with patch("tooluniverse.neuromorpho_tool.requests.get", side_effect=fake_get):
        result = tool.run({"neuron_id": 999999999})

    assert result["status"] == "error"
    assert "404" in result["error"]
    assert "unknown" not in result["error"]
    assert "Requested neuron not found" in result["error"]


def test_neuromorpho_http_error_without_json_body_still_reports_status():
    tool = NeuroMorphoTool(
        {"name": "nm_test", "fields": {"endpoint_type": "neuron", "query_mode": "id"}}
    )
    resp, err = _http_error_response(500, raise_on_json=True)

    def fake_get(url, **kwargs):
        raise err

    with patch("tooluniverse.neuromorpho_tool.requests.get", side_effect=fake_get):
        result = tool.run({"neuron_id": 1})

    assert result["status"] == "error"
    assert "500" in result["error"]
    assert "unknown" not in result["error"]


def test_neuromorpho_no_response_object_falls_back_to_unknown():
    """A genuine HTTPError with no response attached (e.response is None)
    should still say 'unknown', not crash."""
    tool = NeuroMorphoTool(
        {"name": "nm_test", "fields": {"endpoint_type": "neuron", "query_mode": "id"}}
    )
    err = requests.exceptions.HTTPError("boom")
    err.response = None

    def fake_get(url, **kwargs):
        raise err

    with patch("tooluniverse.neuromorpho_tool.requests.get", side_effect=fake_get):
        result = tool.run({"neuron_id": 1})

    assert result["status"] == "error"
    assert "unknown" in result["error"]


def test_allenbrain_http_error_reports_real_status():
    tool = AllenBrainTool({"name": "allen_test", "fields": {"query_type": "gene_search"}})
    resp, err = _http_error_response(404)

    def fake_get(url, **kwargs):
        raise err

    with patch("tooluniverse.allen_brain_tool.requests.get", side_effect=fake_get):
        result = tool.run({"gene_acronym": "Bdnf"})

    assert result["status"] == "error"
    assert "404" in result["error"]
    assert "unknown" not in result["error"]


def test_allenbrain_success_case_unaffected():
    tool = AllenBrainTool({"name": "allen_test", "fields": {"query_type": "gene_search"}})
    r = MagicMock()
    r.status_code = 200
    r.raise_for_status = MagicMock()
    r.json.return_value = {"success": True, "msg": [{"id": 11850, "acronym": "Bdnf"}]}

    with patch("tooluniverse.allen_brain_tool.requests.get", return_value=r):
        result = tool.run({"gene_acronym": "Bdnf"})

    assert result["status"] == "success"
