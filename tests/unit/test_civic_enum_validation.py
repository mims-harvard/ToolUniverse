"""Unit test: civic_search_evidence_items validates enum filters up front.

Regression: an invalid enum value (e.g. evidence_type="BANANA",
significance="GARBAGEXYZ") was passed straight to the CIViC GraphQL API and came
back as an opaque "Error: GraphQL query errors" with no hint of what was wrong or
what is valid. The tool now validates evidence_type / significance /
evidence_direction client-side and names the allowed values.
"""
import glob
import json
from unittest.mock import patch

import pytest

from tooluniverse.civic_tool import CIViCTool


def _load(name):
    for f in glob.glob("src/tooluniverse/data/*.json"):
        try:
            data = json.load(open(f))
        except ValueError:
            continue
        if isinstance(data, list):
            for tool in data:
                if isinstance(tool, dict) and tool.get("name") == name:
                    return tool
    raise AssertionError(f"tool config not found: {name}")


def _tool():
    return CIViCTool(_load("civic_search_evidence_items"))


@pytest.mark.unit
def test_invalid_evidence_type_rejected_with_valid_list():
    result = _tool().run(
        {"molecular_profile": "CTNNB1 S45F", "evidence_type": "BANANA"}
    )
    assert result["status"] == "error"
    assert "Invalid evidence_type 'BANANA'" in result["error"]
    assert "PREDICTIVE" in result["error"]


@pytest.mark.unit
def test_invalid_significance_rejected():
    result = _tool().run(
        {"molecular_profile": "ERBB2 V777L", "significance": "GARBAGEXYZ"}
    )
    assert result["status"] == "error"
    assert "Invalid significance 'GARBAGEXYZ'" in result["error"]
    assert "RESISTANCE" in result["error"]


@pytest.mark.unit
def test_valid_enum_passes_validation():
    """A valid enum must NOT trip the guard (proceeds to the API layer)."""

    class _Resp:
        status_code = 200

        def json(self):
            return {"data": {"evidenceItems": {"nodes": []}}}

        def raise_for_status(self):
            pass

    with patch("tooluniverse.civic_tool.requests.post", return_value=_Resp()):
        result = _tool().run(
            {"molecular_profile": "CTNNB1 S45F", "evidence_type": "PREDICTIVE"}
        )
    assert not (
        result.get("status") == "error"
        and "Invalid evidence_type" in result.get("error", "")
    )


@pytest.mark.unit
def test_enum_check_is_case_insensitive():
    class _Resp:
        status_code = 200

        def json(self):
            return {"data": {"evidenceItems": {"nodes": []}}}

        def raise_for_status(self):
            pass

    with patch("tooluniverse.civic_tool.requests.post", return_value=_Resp()):
        result = _tool().run(
            {"molecular_profile": "x", "significance": "resistance"}
        )
    assert not (
        result.get("status") == "error"
        and "Invalid significance" in result.get("error", "")
    )
