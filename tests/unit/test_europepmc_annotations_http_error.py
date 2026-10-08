"""Europe PMC HTTP failures must surface the status and upstream explanation."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from tooluniverse.europepmc_annotations_tool import EuroPMCAnnotationsTool

pytestmark = pytest.mark.unit


def _raising_get(response):
    error = requests.exceptions.HTTPError(response=response)
    return MagicMock(side_effect=error)


def _bad_request(payload=None, text=""):
    response = MagicMock()
    response.status_code = 400
    # A real requests.Response is falsy for 4xx/5xx; reproduce that here,
    # because `if e.response` is exactly what used to drop the detail.
    response.__bool__ = lambda self: False
    if payload is None:
        response.json.side_effect = ValueError("no json")
        response.text = text
    else:
        response.json.return_value = payload
    return response


def test_http_error_reports_status_and_upstream_message():
    upstream = (
        "The articleIds list parameter contains one or more wrongly formatted "
        "values (i.e. PMC4353746)."
    )
    response = _bad_request({"status": 400, "message": upstream})
    with patch(
        "tooluniverse.europepmc_annotations_tool.requests.get",
        _raising_get(response),
    ):
        result = EuroPMCAnnotationsTool({"name": "x"}).run({"article_id": "PMC4353746"})

    assert result["status"] == "error"
    # The status must be the real code, never the literal string "unknown".
    assert "400" in result["error"]
    assert "unknown" not in result["error"]
    assert upstream in result["error"]


def test_http_error_falls_back_to_body_when_not_json():
    response = _bad_request(text="Service Unavailable")
    with patch(
        "tooluniverse.europepmc_annotations_tool.requests.get",
        _raising_get(response),
    ):
        result = EuroPMCAnnotationsTool({"name": "x"}).run({"article_id": "PMC:PMC1"})

    assert result["status"] == "error"
    assert "400" in result["error"]
    assert "Service Unavailable" in result["error"]


def test_http_error_without_a_response_does_not_crash():
    error = requests.exceptions.HTTPError(response=None)
    with patch(
        "tooluniverse.europepmc_annotations_tool.requests.get",
        MagicMock(side_effect=error),
    ):
        result = EuroPMCAnnotationsTool({"name": "x"}).run({"article_id": "PMC:PMC1"})

    assert result["status"] == "error"
    assert "no response" in result["error"]
