"""
Unit tests for DisGeNET tool.
"""

import pytest
import json
import os
from unittest.mock import patch, MagicMock


class TestDisGeNETToolDirect:
    """Test DisGeNET tool directly (Level 1)."""

    @pytest.fixture
    def tool_config(self):
        """Load tool config from JSON."""
        with open("src/tooluniverse/data/disgenet_tools.json") as f:
            tools = json.load(f)
            return next(t for t in tools if t["name"] == "DisGeNET_search_gene")

    @pytest.fixture
    def tool(self, tool_config):
        """Create tool instance with mock API key."""
        with patch.dict(os.environ, {"DISGENET_API_KEY": "test_key"}):
            from tooluniverse.disgenet_tool import DisGeNETTool
            return DisGeNETTool(tool_config)

    def test_missing_api_key(self, tool_config):
        """Test error when API key is missing."""
        with patch.dict(os.environ, {"DISGENET_API_KEY": ""}, clear=True):
            from tooluniverse.disgenet_tool import DisGeNETTool
            tool = DisGeNETTool(tool_config)
            result = tool.run({"operation": "search_gene", "gene": "BRCA1"})
            assert result["status"] == "error"
            assert "API key" in result["error"]

    def test_search_gene_missing_param(self, tool):
        """Test search_gene with missing gene parameter."""
        result = tool.run({"operation": "search_gene"})
        assert result["status"] == "error"
        assert "gene" in result["error"].lower()

    def test_unknown_operation(self, tool):
        """Test unknown operation."""
        result = tool.run({"operation": "unknown"})
        assert result["status"] == "error"
        assert "unknown" in result["error"].lower()

    @patch("tooluniverse.disgenet_tool.requests.get")
    def test_search_gene_success(self, mock_get, tool):
        """Test successful gene search."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"gene_symbol": "BRCA1", "disease_name": "Breast cancer", "score": 0.8}
        ]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = tool.run({"operation": "search_gene", "gene": "BRCA1"})
        assert result["status"] == "success"
        assert len(result["data"]["associations"]) > 0


class TestDisGeNETToolInterface:
    """Test DisGeNET tool via ToolUniverse interface (Level 2)."""

    @pytest.fixture
    def tu(self):
        """Create ToolUniverse instance."""
        from tooluniverse import ToolUniverse
        tu = ToolUniverse()
        tu.load_tools()
        return tu

    def test_tools_registered(self, tu):
        """Test that DisGeNET tools are registered."""
        # DisGeNET tools require API key - skip if not loaded
        import os
        if not os.environ.get("DISGENET_API_KEY"):
            pytest.skip("DISGENET_API_KEY not set")
        
        assert hasattr(tu.tools, "DisGeNET_search_gene")
        assert hasattr(tu.tools, "DisGeNET_search_disease")
        assert hasattr(tu.tools, "DisGeNET_get_gda")
        assert hasattr(tu.tools, "DisGeNET_get_vda")
        assert hasattr(tu.tools, "DisGeNET_get_disease_genes")
