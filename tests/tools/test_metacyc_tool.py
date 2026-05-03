"""Unit tests for MetaCycTool."""

import pytest
from unittest.mock import patch, MagicMock

from tooluniverse.metacyc_tool import MetaCycTool


class TestMetaCycTool:
    """Test suite for MetaCycTool."""

    @pytest.fixture
    def tool(self):
        """Create a tool instance with default config."""
        return MetaCycTool({"timeout": 10})

    def test_missing_query(self, tool):
        """Test error when query is missing for search."""
        result = tool.run({"operation": "search_pathways"})
        assert result["status"] == "error"
        assert "query" in result["error"]

    def test_missing_pathway_id(self, tool):
        """Test error when pathway_id is missing."""
        result = tool.run({"operation": "get_pathway"})
        assert result["status"] == "error"
        assert "pathway_id" in result["error"]

    def test_missing_compound_id(self, tool):
        """Test error when compound_id is missing."""
        result = tool.run({"operation": "get_compound"})
        assert result["status"] == "error"
        assert "compound_id" in result["error"]

    def test_missing_reaction_id(self, tool):
        """Test error when reaction_id is missing."""
        result = tool.run({"operation": "get_reaction"})
        assert result["status"] == "error"
        assert "reaction_id" in result["error"]

    def test_unknown_operation(self, tool):
        """Test error for unknown operation."""
        result = tool.run({"operation": "invalid_op"})
        assert result["status"] == "error"
        assert "Unknown operation" in result["error"]

    @patch("tooluniverse.metacyc_tool.requests.get")
    def test_get_pathway_success(self, mock_get, tool):
        """Test successful pathway retrieval."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<pathway>...</pathway>"
        mock_get.return_value = mock_response

        result = tool.run({"operation": "get_pathway", "pathway_id": "GLYCOLYSIS"})

        assert result["status"] == "success"
        assert result["data"]["pathway_id"] == "GLYCOLYSIS"
        assert "url" in result["data"]


class TestMetaCycToolInterface:
    """Test MetaCycTool through ToolUniverse interface."""

    def test_tool_registered(self):
        """Test that MetaCycTool is properly registered."""
        from tooluniverse import ToolUniverse

        tu = ToolUniverse()
        tu.load_tools()

        assert hasattr(tu.tools, "MetaCyc_search_pathways")
        assert hasattr(tu.tools, "MetaCyc_get_pathway")
        assert hasattr(tu.tools, "MetaCyc_get_compound")
        assert hasattr(tu.tools, "MetaCyc_get_reaction")
