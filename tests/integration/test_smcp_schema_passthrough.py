"""Regression tests for explicit MCP JSON Schema passthrough registration."""

from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from unittest.mock import AsyncMock, patch

import pytest

from tooluniverse.mcp_schema_adapter import register_schema_passthrough_tool
from tooluniverse.smcp import SMCP


COMPLEX_SCHEMA = {
    "$defs": {
        "Choice": {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {"kind": {"const": "a"}},
                    "required": ["kind"],
                    "additionalProperties": False,
                },
                {
                    "type": "object",
                    "properties": {
                        "kind": {"const": "b"},
                        "count": {"type": "integer"},
                    },
                    "required": ["kind", "count"],
                    "additionalProperties": False,
                },
            ]
        }
    },
    "type": "object",
    "properties": {"choice": {"$ref": "#/$defs/Choice"}},
    "required": ["choice"],
    "additionalProperties": False,
}


def _config(*, passthrough: bool) -> dict:
    config = {
        "name": "test_complex_schema",
        "description": "Test a complex generated schema.",
        "parameter": deepcopy(COMPLEX_SCHEMA),
    }
    if passthrough:
        config["mcp_schema_mode"] = "passthrough"
    return config


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complex_schema_does_not_implicitly_change_registration_path():
    server = SMCP(name="default schema path", tool_categories=[], search_enabled=False)
    try:
        with patch(
            "tooluniverse.mcp_schema_adapter.register_schema_passthrough_tool"
        ) as register:
            server._create_mcp_tool_from_tooluniverse(_config(passthrough=False))
        register.assert_not_called()
    finally:
        await server.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_passthrough_is_explicit_and_uses_an_isolated_schema_copy():
    server = SMCP(
        name="passthrough schema path", tool_categories=[], search_enabled=False
    )
    config = _config(passthrough=True)
    original = deepcopy(config["parameter"])
    try:
        server._create_mcp_tool_from_tooluniverse(config)
        config["parameter"]["properties"].clear()

        tool = await server.get_tool("test_complex_schema")
        assert tool.parameters == original
        assert tool.fn is not None
    finally:
        await server.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_passthrough_wrapper_preserves_execution_and_control_arguments():
    server = SMCP(
        name="passthrough execution", tool_categories=[], search_enabled=False
    )
    try:
        server._create_mcp_tool_from_tooluniverse(_config(passthrough=True))
        tool = await server.get_tool("test_complex_schema")

        seen = {}

        def execute(call, stream_callback=None):
            seen["call"] = call
            seen["stream_callback"] = stream_callback
            return {"status": "success"}

        server.tooluniverse.run_one_function = execute
        result = json.loads(await tool.fn(choice={"kind": "a"}))
        assert result == {"status": "success"}
        assert seen["call"] == {
            "name": "test_complex_schema",
            "arguments": {"choice": {"kind": "a"}},
        }

        ctx = type("Context", (), {"info": AsyncMock()})()

        def execute_with_stream(call, stream_callback=None):
            assert stream_callback is not None
            stream_callback("partial result")
            return {"status": "success"}

        server.tooluniverse.run_one_function = execute_with_stream
        await tool.fn(choice={"kind": "a"}, ctx=ctx, _tooluniverse_stream=True)
        await asyncio.sleep(0)
        ctx.info.assert_awaited_once_with("partial result")

        task_result = json.loads(
            await tool.fn(choice={"kind": "a"}, _task={"ttl": 1_000})
        )
        assert "does not support task execution" in task_result["error"]

        def fail(call, stream_callback=None):
            raise RuntimeError("passthrough execution failed")

        server.tooluniverse.run_one_function = fail
        error_result = json.loads(await tool.fn(choice={"kind": "a"}))
        assert "passthrough execution failed" in error_result["error"]
    finally:
        await server.close()


@pytest.mark.unit
@pytest.mark.parametrize(
    "ref",
    [
        "https://example.org/schema.json#/Choice",
        "#missing-anchor",
        "#/$defs/Missing",
    ],
)
def test_passthrough_rejects_remote_or_unresolvable_refs(ref):
    schema = deepcopy(COMPLEX_SCHEMA)
    schema["properties"]["choice"]["$ref"] = ref

    async def execute(**kwargs):
        return str(kwargs)

    with pytest.raises(ValueError):
        register_schema_passthrough_tool(
            object(),
            name="unsafe_schema",
            description="Unsafe schema",
            parameters=schema,
            annotations=None,
            fn=execute,
        )
