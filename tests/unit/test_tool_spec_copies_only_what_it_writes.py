"""Preparing tool specifications must copy what it writes, and no more.

``tool_specification`` deep-copied the whole tool configuration so it could stamp a
``required`` flag onto each property, and ``prepare_tool_prompts`` deep-copied every
tool and then deleted all but four keys. Both ran on every tool the finders return,
and most of the copying was of data that is either never written or thrown away.

These tests pin the two halves of the contract that callers actually depend on: the
returned specification carries the same content as before, and writing to the parts a
caller is handed does not reach the loaded catalogue.
"""

import pytest

from tooluniverse import ToolUniverse

pytestmark = pytest.mark.unit


def _engine():
    tu = ToolUniverse()
    tu.all_tool_dict = {
        "alpha": {
            "name": "alpha",
            "description": "first tool",
            "type": "RESTTool",
            "test_examples": [{"query": "x"}],
            "return_schema": {"type": "object", "properties": {"out": {"type": "string"}}},
            "parameter": {
                "type": "object",
                "required": ["gene"],
                "properties": {
                    "gene": {"type": "string", "description": "gene symbol"},
                    "limit": {"type": "integer"},
                },
            },
        }
    }
    tu.all_tools = list(tu.all_tool_dict.values())
    return tu


def test_specification_marks_required_properties():
    spec = _engine().tool_specification("alpha")

    properties = spec["parameter"]["properties"]
    assert properties["gene"]["required"] is True
    assert properties["limit"]["required"] is False
    # Fields outside the parameter schema are still reported.
    assert spec["description"] == "first tool"
    assert spec["return_schema"]["properties"]["out"]["type"] == "string"


def test_specification_does_not_write_into_the_loaded_catalogue():
    tu = _engine()
    spec = tu.tool_specification("alpha")

    spec["parameter"]["properties"]["gene"]["required"] = "tampered"
    spec["parameter"]["properties"]["injected"] = {"type": "string"}
    spec["parameter"]["required"] = ["everything"]

    live = tu.all_tool_dict["alpha"]["parameter"]
    assert "required" not in live["properties"]["gene"]
    assert "injected" not in live["properties"]
    assert live["required"] == ["gene"]


def test_openai_format_does_not_write_into_the_loaded_catalogue():
    tu = _engine()
    spec = tu.tool_specification("alpha", format="openai")

    assert set(spec) == {"name", "description", "parameters"}
    spec["parameters"]["properties"]["gene"]["type"] = "tampered"
    assert tu.all_tool_dict["alpha"]["parameter"]["properties"]["gene"]["type"] == "string"


def test_prepare_tool_prompts_keeps_four_keys_and_isolates_them():
    tu = _engine()
    tools = list(tu.all_tool_dict.values())

    prepared = tu.prepare_tool_prompts(tools)

    assert set(prepared[0]) == {"name", "description", "parameter"}
    prepared[0]["parameter"]["properties"]["gene"]["description"] = "tampered"
    assert (
        tools[0]["parameter"]["properties"]["gene"]["description"] == "gene symbol"
    )


def test_prepare_one_tool_prompt_matches_prepare_tool_prompts():
    tu = _engine()
    tool = tu.all_tool_dict["alpha"]

    assert tu.prepare_one_tool_prompt(tool) == tu.prepare_tool_prompts([tool])[0]
