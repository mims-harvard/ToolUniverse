"""Unit tests for EMoleculesTool."""

import pytest
from unittest.mock import patch, MagicMock

from tooluniverse.emolecules_tool import EMoleculesTool


class TestEMoleculesTool:
    """Test suite for EMoleculesTool."""

    @pytest.fixture
    def tool(self):
        """Create a tool instance with default config."""
        return EMoleculesTool({"timeout": 10})

    def test_missing_query(self, tool):
        """Test error when query is missing for search."""
        result = tool.run({"operation": "search"})
        assert result["status"] == "error"
        assert "query" in result["error"]

    def test_missing_smiles(self, tool):
        """Test error when smiles is missing for structure search."""
        result = tool.run({"operation": "search_smiles"})
        assert result["status"] == "error"
        assert "smiles" in result["error"]

    def test_missing_smiles_for_vendors(self, tool):
        """Test error when smiles is missing for get_vendors."""
        result = tool.run({"operation": "get_vendors"})
        assert result["status"] == "error"
        assert "smiles" in result["error"]

    def test_missing_emol_id(self, tool):
        """Test error when emol_id is missing."""
        result = tool.run({"operation": "get_compound"})
        assert result["status"] == "error"
        assert "emol_id" in result["error"]

    def test_unknown_operation(self, tool):
        """Test error for unknown operation."""
        result = tool.run({"operation": "invalid_op"})
        assert result["status"] == "error"
        assert "Unknown operation" in result["error"]

    def test_search_returns_url(self, tool):
        """Test search returns useful URL (no API call needed)."""
        result = tool.run({"operation": "search", "query": "caffeine"})

        assert result["status"] == "success"
        assert "search_url" in result["data"]
        assert "caffeine" in result["data"]["search_url"]

    def test_get_vendors_returns_info(self, tool):
        """Test get_vendors returns useful info (no API call needed)."""
        result = tool.run({"operation": "get_vendors", "smiles": "CC(=O)O"})

        assert result["status"] == "success"
        assert "vendor_info" in result["data"]
        assert "search_url" in result["data"]


class TestEMoleculesToolInterface:
    """Test EMoleculesTool through ToolUniverse interface."""

    def test_tool_registered(self):
        """Test that EMoleculesTool is properly registered."""
        from tooluniverse import ToolUniverse

        tu = ToolUniverse()
        tu.load_tools()

        assert hasattr(tu.tools, "eMolecules_search")
        assert hasattr(tu.tools, "eMolecules_search_smiles")
        assert hasattr(tu.tools, "eMolecules_get_vendors")
        assert hasattr(tu.tools, "eMolecules_get_compound")
