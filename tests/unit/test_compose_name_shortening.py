"""
A ComposeTool must find its dependencies under shortened names, and auto-loading
a dependency must not unload everything else.

The MCP server turns on name shortening, so a tool whose name is longer than
MAX_TOOL_NAME_LENGTH is registered under a shortened form. BiomarkerDiscoveryWorkflow
names two such HPA tools in full. Before the fix, its pre-flight check missed them,
the auto-load called load_tools(tool_type=[category]) -- which clears the registry
by default -- and the server was left with the HPA tools alone: every later
execute_tool call answered "Tool 'execute_tool' not found even after loading tools".

Offline: only local tool configs are read.
"""

import pytest

from tooluniverse import ToolUniverse
from tooluniverse.compose_tool import ComposeTool

LONG_NAME = "HPA_get_comprehensive_gene_details_by_ensembl_id"


@pytest.fixture
def universe():
    tu = ToolUniverse(enable_name_shortening=True)
    tu.load_tools(categories=["hpa", "compose", "pubmed"])
    return tu


@pytest.fixture
def workflow(universe):
    return ComposeTool(
        universe.all_tool_dict["BiomarkerDiscoveryWorkflow"], tooluniverse=universe
    )


def test_long_dependency_name_is_registered_shortened(universe):
    """Positive control: the case below only exists if the name was shortened."""
    assert len(LONG_NAME) > universe.MAX_TOOL_NAME_LENGTH
    assert LONG_NAME not in universe.all_tool_dict


def test_dependency_is_found_under_its_shortened_name(workflow):
    assert LONG_NAME in set(workflow.required_tools) | workflow.discovered_dependencies
    assert workflow._is_available(LONG_NAME)


def test_auto_load_keeps_tools_already_loaded(universe, workflow):
    before = set(universe.all_tool_dict)
    assert any(name.startswith("PubMed_") for name in before)

    loaded, missing = workflow._load_missing_dependencies({LONG_NAME})

    assert set(universe.all_tool_dict) == before
    assert loaded == {LONG_NAME} and not missing


def test_unknown_tool_is_still_unavailable(workflow):
    assert not workflow._is_available("NoSuchTool_anywhere")
