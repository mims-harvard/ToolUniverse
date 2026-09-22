"""Rfam /family/{id}/structures needs ?content-type=..., not an Accept header.

With only an Accept header the endpoint answers HTTP 500, so
get_structure_mapping failed for every family. HTTP is mocked; no network.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.rfam_tool import RfamTool

pytestmark = pytest.mark.unit


def _tool():
    return RfamTool({"name": "Rfam_get_structure_mapping", "parameter": {}})


def _ok(payload):
    resp = Mock()
    resp.status_code = 200
    resp.json.return_value = payload
    resp.text = "<xml/>"
    return resp


def test_json_request_sends_content_type_query_parameter():
    with patch(
        "tooluniverse.rfam_tool.requests.get", return_value=_ok({"mapping": []})
    ) as get:
        result = _tool().run(
            {"operation": "get_structure_mapping", "family_id": "RF00002"}
        )
    assert result["status"] == "success"
    assert result["data"] == {"mapping": []}
    args, kwargs = get.call_args
    assert args[0] == "https://rfam.org/family/RF00002/structures"
    assert kwargs["params"] == {"content-type": "application/json"}


def test_xml_request_sends_text_xml_content_type():
    with patch("tooluniverse.rfam_tool.requests.get", return_value=_ok({})) as get:
        result = _tool().run(
            {
                "operation": "get_structure_mapping",
                "family_id": "RF00002",
                "format": "xml",
            }
        )
    assert result["status"] == "success"
    assert get.call_args.kwargs["params"] == {"content-type": "text/xml"}


def test_http_error_is_reported_not_raised():
    bad = Mock()
    bad.status_code = 500
    bad.text = "boom"
    with patch("tooluniverse.rfam_tool.requests.get", return_value=bad):
        result = _tool().run(
            {"operation": "get_structure_mapping", "family_id": "RF00002"}
        )
    assert result["status"] == "error"
    assert "RF00002" in result["error"]
