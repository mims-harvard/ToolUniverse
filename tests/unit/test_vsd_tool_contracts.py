from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

from tooluniverse import ToolUniverse
from tooluniverse import vsd_tool

pytestmark = pytest.mark.unit


_VSD_TOOL_NAMES = (
    "VSDDiscoverSources",
    "VSDRegisterSource",
    "VSDListSources",
    "VSDQuerySource",
    "VSDRemoveSource",
)


def _loaded_vsd() -> ToolUniverse:
    tooluniverse = ToolUniverse()
    tooluniverse.load_tools(include_tools=list(_VSD_TOOL_NAMES), quiet=True)
    return tooluniverse


def test_loaded_vsd_tools_expose_safe_mcp_and_cache_contracts():
    """Loaded VSD tools expose cache and mutation hints matching behavior."""
    tooluniverse = _loaded_vsd()
    try:
        expected = {
            "VSDDiscoverSources": (True, True, False),
            "VSDRegisterSource": (False, False, True),
            "VSDListSources": (False, True, False),
            "VSDQuerySource": (False, True, False),
            "VSDRemoveSource": (False, False, True),
        }

        for name, (cacheable, read_only, destructive) in expected.items():
            config = tooluniverse.all_tool_dict[name]
            assert config["cacheable"] is cacheable
            assert config["mcp_annotations"] == {
                "readOnlyHint": read_only,
                "destructiveHint": destructive,
            }

            instance = tooluniverse._get_tool_instance(name, cache=True)
            assert instance is not None
            assert instance.supports_caching() is cacheable
    finally:
        tooluniverse.close()


def test_register_schema_requires_explicit_opt_in_for_replacement():
    """The public registration schema defaults replacement to false."""
    tooluniverse = _loaded_vsd()
    try:
        register_config = tooluniverse.all_tool_dict["VSDRegisterSource"]
        replace_schema = register_config["parameter"]["properties"]["replace"]

        assert replace_schema == {
            "type": "boolean",
            "default": False,
            "description": (
                "Replace an existing registration with the same source_id. "
                "Defaults to false, so duplicate registration is rejected."
            ),
        }
        assert "replace" not in register_config["parameter"]["required"]
    finally:
        tooluniverse.close()


def test_generated_wrapper_exposes_replace_contract_and_metadata():
    """Generated wrappers and metadata expose the new replacement control."""
    tools_path = Path(__file__).parents[2] / "src" / "tooluniverse" / "tools"
    wrapper = ast.parse(
        (tools_path / "VSDRegisterSource.py").read_text(encoding="utf-8")
    )
    function = next(
        node
        for node in wrapper.body
        if isinstance(node, ast.FunctionDef) and node.name == "VSDRegisterSource"
    )
    positional = [argument.arg for argument in function.args.args]
    defaults = dict(
        zip(positional[-len(function.args.defaults) :], function.args.defaults)
    )

    assert "replace" in positional
    assert isinstance(defaults["replace"], ast.Constant)
    assert defaults["replace"].value is False
    assert any(
        isinstance(node, ast.Dict)
        and any(
            isinstance(key, ast.Constant)
            and key.value == "replace"
            and isinstance(value, ast.Name)
            and value.id == "replace"
            for key, value in zip(node.keys, node.values)
        )
        for node in ast.walk(function)
    )

    metadata = json.loads(
        (tools_path / ".tool_metadata.json").read_text(encoding="utf-8")
    )
    for name in _VSD_TOOL_NAMES:
        assert re.fullmatch(r"[0-9a-f]{32}", metadata[name])


def test_catalog_operations_execute_even_when_cache_is_requested(monkeypatch, tmp_path):
    """Catalog reads and mutations never return stale cached results."""
    monkeypatch.setenv("TOOLUNIVERSE_VSD_DIR", str(tmp_path))
    calls = []

    def fake_safe_get(url, params=None, **kwargs):
        del kwargs
        calls.append((url, params or {}))
        return (
            {"endpoint": url, "call": len(calls)},
            {
                "url": url,
                "status_code": 200,
                "content_type": "application/json",
                "response_bytes": 20,
                "peer_ip": "93.184.216.34",
                "redirects": 0,
            },
        )

    monkeypatch.setattr(vsd_tool, "_safe_get_json", fake_safe_get)
    monkeypatch.setattr(
        vsd_tool,
        "_resolve_public_addresses",
        lambda host, port: ("93.184.216.34",),
    )
    tooluniverse = _loaded_vsd()
    register_call = {
        "name": "VSDRegisterSource",
        "arguments": {
            "source_id": "cache_case",
            "endpoint": "https://api.fda.gov/drug/label.json",
        },
    }
    remove_call = {
        "name": "VSDRemoveSource",
        "arguments": {"source_id": "cache_case"},
    }
    list_call = {"name": "VSDListSources", "arguments": {}}
    query_call = {
        "name": "VSDQuerySource",
        "arguments": {"source_id": "cache_case"},
    }

    try:
        tooluniverse.run_one_function(register_call, use_cache=True)
        assert (
            len(
                tooluniverse.run_one_function(list_call, use_cache=True)["data"][
                    "sources"
                ]
            )
            == 1
        )
        assert tooluniverse.run_one_function(remove_call, use_cache=True)["data"][
            "removed"
        ]

        tooluniverse.run_one_function(register_call, use_cache=True)
        assert (
            len(
                tooluniverse.run_one_function(list_call, use_cache=True)["data"][
                    "sources"
                ]
            )
            == 1
        )
        first_query = tooluniverse.run_one_function(query_call, use_cache=True)
        assert (
            first_query["data"]["result"]["endpoint"]
            == register_call["arguments"]["endpoint"]
        )

        tooluniverse.run_one_function(
            {
                "name": "VSDRegisterSource",
                "arguments": {
                    **register_call["arguments"],
                    "endpoint": "https://ghoapi.azureedge.net/api/Indicator",
                    "replace": True,
                },
            },
            use_cache=True,
        )
        second_query = tooluniverse.run_one_function(query_call, use_cache=True)
        assert second_query["data"]["result"]["endpoint"] == (
            "https://ghoapi.azureedge.net/api/Indicator"
        )

        assert tooluniverse.run_one_function(remove_call, use_cache=True)["data"][
            "removed"
        ]
        assert (
            tooluniverse.run_one_function(list_call, use_cache=True)["data"]["sources"]
            == []
        )
    finally:
        tooluniverse.close()
