"""
Unit tests for OMIM tool.
"""

import pytest
import json
import os
from unittest.mock import patch, MagicMock


class TestOMIMToolDirect:
    """Test OMIM tool directly (Level 1)."""

    @pytest.fixture
    def tool_config(self):
        """Load tool config from JSON."""
        with open("src/tooluniverse/data/omim_tools.json") as f:
            tools = json.load(f)
            return next(t for t in tools if t["name"] == "OMIM_search")

    @pytest.fixture
    def tool(self, tool_config):
        """Create tool instance with mock API key."""
        with patch.dict(os.environ, {"OMIM_API_KEY": "test_key"}):
            from tooluniverse.omim_tool import OMIMTool
            return OMIMTool(tool_config)

    def test_missing_api_key(self, tool_config):
        """Test error when API key is missing."""
        with patch.dict(os.environ, {"OMIM_API_KEY": ""}, clear=True):
            from tooluniverse.omim_tool import OMIMTool
            tool = OMIMTool(tool_config)
            result = tool.run({"operation": "search", "query": "test"})
            assert result["status"] == "error"
            assert "API key" in result["error"]

    def test_search_missing_query(self, tool):
        """Test search with missing query parameter."""
        result = tool.run({"operation": "search"})
        assert result["status"] == "error"
        assert "query" in result["error"].lower()

    def test_get_entry_missing_mim(self, tool):
        """Test get_entry with missing MIM number."""
        result = tool.run({"operation": "get_entry"})
        assert result["status"] == "error"
        assert "mim_number" in result["error"].lower()

    def test_unknown_operation(self, tool):
        """Test unknown operation."""
        result = tool.run({"operation": "unknown"})
        assert result["status"] == "error"
        assert "unknown" in result["error"].lower()

    @patch("tooluniverse.omim_tool.requests.get")
    def test_search_success(self, mock_get, tool):
        """Test successful search."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "omim": {
                "searchResponse": {
                    "totalResults": 5,
                    "startIndex": 0,
                    "entryList": [
                        {"entry": {"mimNumber": 164730, "titles": {"preferredTitle": "BRAF"}}}
                    ],
                }
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = tool.run({"operation": "search", "query": "BRAF"})
        assert result["status"] == "success"
        assert result["data"]["total_results"] == 5

    @patch("tooluniverse.omim_tool.requests.get")
    def test_get_entry_success(self, mock_get, tool):
        """Test successful entry retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "omim": {
                "entryList": [
                    {"entry": {"mimNumber": 164730, "titles": {"preferredTitle": "BRAF"}}}
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = tool.run({"operation": "get_entry", "mim_number": "164730"})
        assert result["status"] == "success"
        assert result["data"]["mimNumber"] == 164730


class TestOMIMToolInterface:
    """Test OMIM tool via ToolUniverse interface (Level 2)."""

    @pytest.fixture
    def tu(self):
        """Create ToolUniverse instance."""
        from tooluniverse import ToolUniverse
        tu = ToolUniverse()
        tu.load_tools()
        return tu

    def test_tools_registered(self, tu):
        """Test that OMIM tools are registered."""
        # OMIM tools require API key - skip if not loaded
        import os
        if not os.environ.get("OMIM_API_KEY"):
            pytest.skip("OMIM_API_KEY not set")
        
        assert hasattr(tu.tools, "OMIM_search")
        assert hasattr(tu.tools, "OMIM_get_entry")
        assert hasattr(tu.tools, "OMIM_get_gene_map")
        assert hasattr(tu.tools, "OMIM_get_clinical_synopsis")


class TestOMIMToolReal:
    """Test OMIM tool with real API calls (Level 3).
    
    Requires OMIM_API_KEY environment variable.
    """

    @pytest.fixture
    def tu(self):
        """Create ToolUniverse instance."""
        from tooluniverse import ToolUniverse
        tu = ToolUniverse()
        tu.load_tools()
        return tu

    @pytest.mark.integration
    def test_real_search(self, tu):
        """Test real OMIM search."""
        if not os.environ.get("OMIM_API_KEY"):
            pytest.skip("OMIM_API_KEY not set")
        
        result = tu.tools.OMIM_search(
            operation="search",
            query="BRCA1",
            limit=5
        )
        if result["status"] == "success":
            print(f"Found {result['data']['total_results']} results")
        else:
            print(f"API error: {result.get('error')}")
