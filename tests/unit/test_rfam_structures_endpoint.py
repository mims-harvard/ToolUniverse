"""Rfam's /structures endpoint needs a query parameter, not a header.

Rfam's /structures endpoint ignores the Accept header and answers HTTP 500
without ?content-type=application/json. Measured against RF00002: every other
family route -- /family/{id}, /acc, /id, /regions, /tree/ -- returns 200 with
the header alone, and only /structures needs the query parameter. With it the
endpoint returns the mapping (798 rows for RF00002).
"""

from unittest.mock import patch

import pytest

from tooluniverse.rfam_tool import RfamTool

pytestmark = pytest.mark.unit


class _Response:
    status_code = 200
    text = "{}"

    @staticmethod
    def json():
        return {"mapping": [{"pdb_id": "6ftg", "chain": "w"}]}


def test_the_structures_request_carries_the_query_parameter():
    """Without it Rfam answers 500, and the Accept header does not substitute."""
    tool = RfamTool({"name": "Rfam_get_structure_mapping", "type": "RfamTool",
                     "fields": {}, "parameter": {"type": "object", "properties": {}}})
    seen = {}

    def fake_get(url, headers=None, params=None, timeout=None):
        seen.update(url=url, headers=headers or {}, params=params or {})
        return _Response()

    with patch("tooluniverse.rfam_tool.requests.get", fake_get):
        result = tool.run(
            {"operation": "get_structure_mapping", "family_id": "RF00002"}
        )

    assert result["status"] == "success"
    assert seen["url"].endswith("/family/RF00002/structures")
    assert seen["params"].get("content-type") == "application/json", (
        "Rfam's /structures endpoint returns HTTP 500 without this parameter; "
        "the Accept header alone is not enough"
    )


def test_xml_asks_for_xml_in_the_parameter_too():
    """The parameter carries the format, so it has to track format_type."""
    tool = RfamTool({"name": "Rfam_get_structure_mapping", "type": "RfamTool",
                     "fields": {}, "parameter": {"type": "object", "properties": {}}})
    seen = {}

    def fake_get(url, headers=None, params=None, timeout=None):
        seen.update(params=params or {})
        response = _Response()
        response.text = "<xml/>"
        return response

    with patch("tooluniverse.rfam_tool.requests.get", fake_get):
        tool.run(
            {
                "operation": "get_structure_mapping",
                "family_id": "RF00002",
                "format": "xml",
            }
        )

    assert seen["params"].get("content-type") == "text/xml"
