"""Regression guard for Fix-R17C-2: every Rfam_* tool config constrains
`operation` to a single-value enum (each ToolUniverse tool name maps to
exactly one Rfam operation, e.g. Rfam_get_family -> "get_family"), yet
`operation` was still required on every call -- forcing a caller to look
up and pass back a fixed value the tool config itself already pins.
RfamTool.run() now falls back to that sole enum value when the caller
omits `operation`, and the JSON configs no longer list it in `required`.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.rfam_tool import RfamTool

pytestmark = pytest.mark.unit


def _tool(operation_enum, required):
    return RfamTool(
        {
            "name": "Rfam_get_family",
            "parameter": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": operation_enum},
                    "family_id": {"type": "string"},
                },
                "required": required,
            },
        }
    )


def test_operation_omitted_falls_back_to_sole_enum_value(monkeypatch):
    tool = _tool(["get_family"], ["family_id"])
    captured = {"called": False}

    def fake_get_family(arguments):
        captured["called"] = True
        return {"status": "success"}

    monkeypatch.setattr(tool, "_get_family", fake_get_family)

    result = tool.run({"family_id": "RF01871"})

    assert result["status"] == "success"
    assert captured["called"] is True


def test_operation_explicitly_provided_still_works(monkeypatch):
    tool = _tool(["get_family"], ["family_id"])
    monkeypatch.setattr(
        tool, "_get_family", lambda arguments: {"status": "success"}
    )

    result = tool.run({"operation": "get_family", "family_id": "RF01871"})

    assert result["status"] == "success"


def test_missing_family_id_still_rejected():
    tool = _tool(["get_family"], ["family_id"])

    result = tool.run({})

    assert result["status"] == "error"
    assert "family_id" in result["error"]


def test_multi_value_enum_does_not_fall_back():
    # A hypothetical tool with more than one legal operation value should
    # not silently guess -- fallback only applies when there's exactly one
    # possible value.
    tool = _tool(["get_family", "get_alignment"], ["family_id"])

    result = tool.run({"family_id": "RF01871"})

    assert result["status"] == "error"
    assert "operation" in result["error"]
