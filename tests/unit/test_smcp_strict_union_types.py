"""Strict SMCP must accept the union-typed schemas the project generates.

``@remote_tool`` turns ``Optional[int]`` into ``{"type": ["integer", "null"]}``
and ``tu serve`` builds the server with ``strict_input_schemas=True``, so a
union-typed parameter has to survive strict registration.
"""

import asyncio

import pytest

from tooluniverse import mcp_tool_registry as registry
from tooluniverse.smcp import SMCP

pytestmark = pytest.mark.unit


@pytest.fixture
def clean_remote_registry():
    saved_tools = dict(registry._mcp_tool_registry)
    saved_unported = list(registry._unported_tools)
    registry._mcp_tool_registry.clear()
    registry._unported_tools.clear()
    yield
    registry._mcp_tool_registry.clear()
    registry._mcp_tool_registry.update(saved_tools)
    registry._unported_tools[:] = saved_unported


def test_strict_field_constraints_reads_union_typed_parameter():
    assert SMCP._strict_field_constraints(
        {"type": ["integer", "null"], "minimum": 2, "maximum": 200}
    ) == {"ge": 2, "le": 200}
    assert SMCP._strict_field_constraints(
        {"type": ["string", "null"], "minLength": 1, "maxLength": 8}
    ) == {"min_length": 1, "max_length": 8}
    assert SMCP._strict_field_constraints({"type": ["null"], "minimum": 2}) == {}


def test_strict_smcp_exposes_remote_tool_with_optional_parameter(
    tmp_path, monkeypatch, clean_remote_registry
):
    from typing import Optional

    monkeypatch.setenv("TOOLUNIVERSE_CACHE_DIR", str(tmp_path / "cache"))

    @registry.remote_tool
    def gene_report(gene: str, count: Optional[int] = None) -> dict:
        """Return a short report for one gene."""
        return {"gene": gene, "count": count}

    schema = registry._mcp_tool_registry["gene_report"]["parameter_schema"]
    assert schema["properties"]["count"]["type"] == ["integer", "null"]

    server = SMCP(
        name="strict union schema",
        tooluniverse_config={},
        auto_expose_tools=False,
        search_enabled=False,
        strict_input_schemas=True,
    )
    server._create_mcp_tool_from_tooluniverse(
        {
            "name": "gene_report",
            "description": "Return a short report for one gene.",
            "parameter": schema,
        }
    )

    tool = asyncio.run(server.get_tool("gene_report"))
    assert tool is not None, "strict registration dropped the tool"
    assert tool.parameters == schema


def test_strict_smcp_enforces_limits_on_a_union_typed_parameter(tmp_path, monkeypatch):
    monkeypatch.setenv("TOOLUNIVERSE_CACHE_DIR", str(tmp_path / "cache"))
    schema = {
        "type": "object",
        "properties": {
            "gene": {"type": "string"},
            "count": {
                "type": ["integer", "null"],
                "minimum": 2,
                "maximum": 200,
                "default": None,
            },
        },
        "required": ["gene"],
        "additionalProperties": False,
    }
    server = SMCP(
        name="strict union limits",
        tooluniverse_config={},
        auto_expose_tools=False,
        search_enabled=False,
        strict_input_schemas=True,
    )
    server._create_mcp_tool_from_tooluniverse(
        {"name": "bounded_report", "description": "bounded", "parameter": schema}
    )

    tool = asyncio.run(server.get_tool("bounded_report"))
    assert tool is not None, "strict registration dropped the tool"
    with pytest.raises(Exception, match="validation error"):
        asyncio.run(tool.run({"gene": "TP53", "count": 1}))
