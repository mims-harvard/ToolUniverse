"""Explicit MCP registration support for externally generated JSON Schemas.

Most ToolUniverse tools should continue to use FastMCP's normal registration
path, which derives a schema from the generated Python signature.  This module
is only for tool configs that explicitly opt into ``mcp_schema_mode``
``"passthrough"`` because their authoritative schema contains nested unions or
discriminators that cannot be represented faithfully by that signature.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Awaitable, Callable

from jsonschema import Draft202012Validator


def _validate_local_refs(schema: dict[str, Any]) -> None:
    """Reject remote references and malformed local JSON Pointer references."""

    def resolve_pointer(ref: str) -> None:
        if not ref.startswith("#"):
            raise ValueError(
                "MCP passthrough schemas may only contain local $ref values"
            )
        fragment = ref[1:]
        if not fragment:
            return
        if not fragment.startswith("/"):
            raise ValueError(
                "MCP passthrough schemas only support local JSON Pointer $ref values"
            )

        target: Any = schema
        for raw_token in fragment[1:].split("/"):
            token = raw_token.replace("~1", "/").replace("~0", "~")
            if isinstance(target, dict) and token in target:
                target = target[token]
            elif isinstance(target, list) and token.isdigit():
                index = int(token)
                if index >= len(target):
                    raise ValueError(f"Unresolvable local $ref: {ref}")
                target = target[index]
            else:
                raise ValueError(f"Unresolvable local $ref: {ref}")

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            ref = value.get("$ref")
            if ref is not None:
                if not isinstance(ref, str):
                    raise ValueError(
                        "MCP passthrough schema $ref values must be strings"
                    )
                resolve_pointer(ref)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(schema)


def register_schema_passthrough_tool(
    server: Any,
    *,
    name: str,
    description: str,
    parameters: dict[str, Any],
    annotations: Any,
    fn: Callable[..., Awaitable[str]],
) -> None:
    """Register a tool using an explicit Draft 2020-12 input schema.

    FastMCP normally validates calls from the Python signature it inspects.  A
    passthrough tool instead advertises the supplied schema and delegates to the
    existing ToolUniverse wrapper.  ToolUniverse's ``run_one_function`` remains
    the runtime validation boundary before the underlying tool is dispatched.
    """

    if not isinstance(parameters, dict):
        raise TypeError("MCP passthrough parameters must be a JSON Schema object")

    schema = deepcopy(parameters)
    Draft202012Validator.check_schema(schema)
    _validate_local_refs(schema)

    from fastmcp.tools.function_tool import FunctionTool

    async def schema_passthrough_function(**kwargs: Any) -> str:
        return await fn(**kwargs)

    schema_passthrough_function.__name__ = name
    schema_passthrough_function.__doc__ = fn.__doc__
    server.add_tool(
        FunctionTool(
            name=name,
            description=description,
            parameters=schema,
            annotations=annotations,
            fn=schema_passthrough_function,
        )
    )
