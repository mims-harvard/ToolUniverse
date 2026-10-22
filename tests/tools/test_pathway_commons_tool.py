"""Compatibility coverage for the historical Pathway Commons import path."""

from tooluniverse.pathway_commons_tool import PathwayCommonsTool as LegacyImport
from tooluniverse.pathwaycommons_tool import PathwayCommonsTool
from tooluniverse.tool_registry import get_tool_registry


def test_historical_module_reexports_canonical_class_without_reregistering():
    assert LegacyImport is PathwayCommonsTool
    assert get_tool_registry()["PathwayCommonsTool"] is PathwayCommonsTool
