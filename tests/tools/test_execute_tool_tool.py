#!/usr/bin/env python3
"""
Unit tests for ExecuteToolTool argument normalization.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.tool_discovery_tools import ExecuteToolTool


class _DummyToolUniverse:
    def __init__(self):
        self.last_call = None

    def run_one_function(self, function_call):
        self.last_call = function_call
        return {"status": "success", "data": {"echo": function_call["arguments"]}}


@pytest.mark.unit
def test_execute_tool_accepts_object_arguments():
    dummy_tu = _DummyToolUniverse()
    tool = ExecuteToolTool({"name": "execute_tool"}, tooluniverse=dummy_tu)

    result = tool.run(
        {
            "tool_name": "UniProt_get_entry_by_accession",
            "arguments": {"accession": "P05067"},
        }
    )

    assert result["status"] == "success"
    assert dummy_tu.last_call == {
        "name": "UniProt_get_entry_by_accession",
        "arguments": {"accession": "P05067"},
    }


@pytest.mark.unit
def test_execute_tool_accepts_json_string_arguments():
    dummy_tu = _DummyToolUniverse()
    tool = ExecuteToolTool({"name": "execute_tool"}, tooluniverse=dummy_tu)

    result = tool.run(
        {
            "tool_name": "UniProt_get_entry_by_accession",
            "arguments": '{"accession": "P05067"}',
        }
    )

    assert result["status"] == "success"
    assert dummy_tu.last_call == {
        "name": "UniProt_get_entry_by_accession",
        "arguments": {"accession": "P05067"},
    }


@pytest.mark.unit
def test_execute_tool_rejects_invalid_json_string_arguments():
    dummy_tu = _DummyToolUniverse()
    tool = ExecuteToolTool({"name": "execute_tool"}, tooluniverse=dummy_tu)

    result = tool.run(
        {
            "tool_name": "UniProt_get_entry_by_accession",
            "arguments": '{"accession": "P05067"',
        }
    )

    assert result["error_type"] == "ValidationError"
    assert "valid JSON" in result["error"]


@pytest.mark.unit
def test_execute_tool_rejects_non_object_json_string_arguments():
    dummy_tu = _DummyToolUniverse()
    tool = ExecuteToolTool({"name": "execute_tool"}, tooluniverse=dummy_tu)

    result = tool.run(
        {
            "tool_name": "UniProt_get_entry_by_accession",
            "arguments": '["P05067"]',
        }
    )

    assert result["error_type"] == "ValidationError"
    assert "decode to an object" in result["error"]
