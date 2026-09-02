#!/usr/bin/env python3
"""Compare the deployed OpenNIH MCP tool contract with local static configs."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from tooluniverse.opennih_tool import OpenNIHTool


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = (
    REPOSITORY_ROOT / "src" / "tooluniverse" / "data" / "opennih_tools.json"
)


def schema_types(schema: dict[str, Any]) -> set[str]:
    """Normalize JSON Schema type arrays and anyOf-null unions."""
    raw_type = schema.get("type")
    if isinstance(raw_type, str):
        types = {raw_type}
    elif isinstance(raw_type, list):
        types = {str(item) for item in raw_type}
    else:
        types = set()
    for option in schema.get("anyOf", []):
        if isinstance(option, dict):
            types.update(schema_types(option))
    return types


_NO_DEFAULT = object()


def effective_default(
    name: str, schema: dict[str, Any], required: set[str]
) -> Any:
    """Treat omitted defaults on optional nullable fields as semantic null."""
    if "default" in schema:
        return schema["default"]
    if name not in required and "null" in schema_types(schema):
        return None
    return _NO_DEFAULT


def compare_tool(local: dict[str, Any], remote: dict[str, Any]) -> list[str]:
    """Return actionable contract differences for one operation."""
    errors: list[str] = []
    local_schema = local.get("parameter", {})
    remote_schema = remote.get("inputSchema", {})
    local_properties = local_schema.get("properties", {})
    remote_properties = remote_schema.get("properties", {})
    local_required = set(local_schema.get("required", []))
    remote_required = set(remote_schema.get("required", []))

    if set(local_properties) != set(remote_properties):
        errors.append(
            "parameter names differ: "
            f"local_only={sorted(set(local_properties) - set(remote_properties))}, "
            f"remote_only={sorted(set(remote_properties) - set(local_properties))}"
        )
    if local_required != remote_required:
        errors.append(
            "required parameters differ: "
            f"local={sorted(local_schema.get('required', []))}, "
            f"remote={sorted(remote_schema.get('required', []))}"
        )
    if local_schema.get("additionalProperties") is not False:
        errors.append("local schema must reject unknown parameters")

    for name in sorted(set(local_properties) & set(remote_properties)):
        local_property = local_properties[name]
        remote_property = remote_properties[name]
        local_types = schema_types(local_property)
        remote_types = schema_types(remote_property)
        if local_types != remote_types:
            errors.append(
                f"{name} types differ: local={sorted(local_types)}, "
                f"remote={sorted(remote_types)}"
            )
        local_default = effective_default(name, local_property, local_required)
        remote_default = effective_default(name, remote_property, remote_required)
        if local_default != remote_default:
            local_display = (
                "<absent>" if local_default is _NO_DEFAULT else repr(local_default)
            )
            remote_display = (
                "<absent>" if remote_default is _NO_DEFAULT else repr(remote_default)
            )
            errors.append(
                f"{name} default differs: "
                f"local={local_display}, remote={remote_display}"
            )

    annotations = remote.get("annotations", {})
    expected_annotations = {
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
    for name, expected in expected_annotations.items():
        if annotations.get(name) is not expected:
            errors.append(
                f"annotation {name} differs: expected={expected!r}, "
                f"remote={annotations.get(name)!r}"
            )
    if remote.get("outputSchema", {}).get("type") != "object":
        errors.append("remote outputSchema is no longer an object")
    return errors


def main() -> int:
    local_configs = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    local_by_operation = {config["operation"]: config for config in local_configs}
    discovery_tool = OpenNIHTool(
        {
            "name": "OpenNIH_source_status",
            "type": "OpenNIHTool",
            "operation": "source_status",
        }
    )
    remote_result = discovery_tool._make_mcp_request("tools/list", {})
    remote_tools = remote_result.get("tools", [])
    remote_by_operation = {
        tool["name"]: tool for tool in remote_tools if isinstance(tool, dict)
    }

    local_operations = set(local_by_operation)
    remote_operations = set(remote_by_operation)
    missing_or_extra_operations = local_operations ^ remote_operations
    failed_operations = len(missing_or_extra_operations)
    passed_operations = 0
    if missing_or_extra_operations:
        print(
            "FAIL operation set: "
            f"local_only={sorted(local_operations - remote_operations)}, "
            f"remote_only={sorted(remote_operations - local_operations)}"
        )

    shared_operations = sorted(local_operations & remote_operations)
    for operation in shared_operations:
        errors = compare_tool(
            local_by_operation[operation], remote_by_operation[operation]
        )
        if errors:
            failed_operations += 1
            print(f"FAIL {operation}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"PASS {operation}")
            passed_operations += 1

    print(
        f"\nTotal operations: {len(local_operations | remote_operations)} | "
        f"PASS: {passed_operations} | "
        f"FAIL: {failed_operations}"
    )
    if any(
        tool.get("inputSchema", {}).get("additionalProperties") is not False
        for tool in remote_tools
        if isinstance(tool, dict)
    ):
        print(
            "NOTE deployed MCP schemas do not reject unknown arguments; keep local "
            "additionalProperties=false protection enabled."
        )
    return 0 if failed_operations == 0 else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FATAL contract verification error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
