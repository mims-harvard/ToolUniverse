"""
Unit tests for Orphanet tool.
"""

import pytest
import json
from unittest.mock import patch, MagicMock


class TestOrphanetToolDirect:
    """Test Orphanet tool directly (Level 1)."""

    @pytest.fixture
    def tool_config(self):
        """Load tool config from JSON."""
        with open("src/tooluniverse/data/orphanet_tools.json") as f:
            tools = json.load(f)
            return next(t for t in tools if t["name"] == "Orphanet_search_diseases")

    @pytest.fixture
    def tool(self, tool_config):
        """Create tool instance."""
        from tooluniverse.orphanet_tool import OrphanetTool
        return OrphanetTool(tool_config)

    def test_search_missing_query(self, tool):
        """Test search with missing query parameter."""
        result = tool.run({"operation": "search_diseases"})
        assert result["status"] == "error"
        assert "query" in result["error"].lower()

    def test_get_disease_missing_orpha(self, tool):
        """Test get_disease with missing ORPHA code."""
        result = tool.run({"operation": "get_disease"})
        assert result["status"] == "error"
        assert "orpha_code" in result["error"].lower()

    def test_unknown_operation(self, tool):
        """Test unknown operation."""
        result = tool.run({"operation": "unknown"})
        assert result["status"] == "error"
        assert "unknown" in result["error"].lower()

    @patch("tooluniverse.orphanet_tool.requests.get")
    def test_search_success(self, mock_get, tool):
        """Test successful search."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"ORPHAcode": "558", "Preferred term": "Marfan syndrome"}
        ]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = tool.run({"operation": "search_diseases", "query": "Marfan"})
        assert result["status"] == "success"
        assert len(result["data"]["results"]) > 0

    @patch("tooluniverse.orphanet_tool.requests.get")
    def test_get_disease_success(self, mock_get, tool):
        """Test successful disease retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ORPHAcode": "558",
            "Preferred term": "Marfan syndrome",
            "Definition": "A systemic connective tissue disorder..."
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = tool.run({"operation": "get_disease", "orpha_code": "558"})
        assert result["status"] == "success"
        assert "ORPHAcode" in result["data"]


class TestOrphanetToolInterface:
    """Test Orphanet tool via ToolUniverse interface (Level 2)."""

    @pytest.fixture
    def tu(self):
        """Create ToolUniverse instance."""
        from tooluniverse import ToolUniverse
        tu = ToolUniverse()
        tu.load_tools()
        return tu

    def test_tools_registered(self, tu):
        """Test that Orphanet tools are registered."""
        assert hasattr(tu.tools, "Orphanet_search_diseases")
        assert hasattr(tu.tools, "Orphanet_get_disease")
        assert hasattr(tu.tools, "Orphanet_get_genes")
        assert hasattr(tu.tools, "Orphanet_get_classification")


class TestOrphanetToolReal:
    """Test Orphanet tool with real API calls (Level 3)."""

    @pytest.fixture
    def tu(self):
        """Create ToolUniverse instance."""
        from tooluniverse import ToolUniverse
        tu = ToolUniverse()
        tu.load_tools()
        return tu

    @pytest.mark.integration
    def test_real_search(self, tu):
        """Test real Orphanet search."""
        result = tu.tools.Orphanet_search_diseases(
            operation="search_diseases",
            query="Marfan"
        )
        if result["status"] == "success":
            print(f"Found {len(result['data']['results'])} diseases")
        else:
            print(f"API response: {result.get('error')}")

    @pytest.mark.integration
    def test_real_get_disease(self, tu):
        """Test real disease retrieval."""
        result = tu.tools.Orphanet_get_disease(
            operation="get_disease",
            orpha_code="558"
        )
        if result["status"] == "success":
            print(f"Disease: {result['data'].get('Preferred term', 'N/A')}")
        else:
            print(f"API response: {result.get('error')}")
