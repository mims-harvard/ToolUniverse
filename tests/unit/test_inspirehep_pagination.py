"""Regression tests for INSPIRE-HEP page/size pagination."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config():
    path = Path(__file__).parents[2] / "src/tooluniverse/data/inspirehep_tools.json"
    return json.loads(path.read_text())[0]


def _response(records, total=8):
    response = Mock(status_code=200, text="")
    response.json.return_value = {"hits": {"total": total, "hits": records}}
    return response


def test_page_is_forwarded_and_exact_total_drives_next(monkeypatch):
    requested = {}

    def request(session, method, url, **kwargs):
        requested.update(kwargs["params"])
        return _response([{"id": "4"}, {"id": "5"}, {"id": "6"}])

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    result = BaseRESTTool(_config()).run(
        {"q": "quantum gravity", "size": 3, "page": 2}
    )
    assert requested["size"] == 3
    assert requested["page"] == 2
    assert result["metadata"]["total_results"] == 8
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_page"] == 3


@pytest.mark.parametrize(
    "arguments, parameter",
    [
        ({"q": "x", "size": 0}, "size"),
        ({"q": "x", "size": 26}, "size"),
        ({"q": "x", "size": True}, "size"),
        ({"q": "x", "page": 0}, "page"),
        ({"q": "x", "page": 1.5}, "page"),
    ],
)
def test_invalid_pagination_is_explicit(arguments, parameter):
    result = BaseRESTTool(_config()).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
