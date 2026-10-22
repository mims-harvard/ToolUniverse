"""Unit tests for EnamineTool."""

import pytest
from unittest.mock import patch, MagicMock

from tooluniverse.enamine_tool import EnamineTool


class TestEnamineTool:
    """Test suite for EnamineTool."""

    @pytest.fixture
    def tool(self):
        """Create a tool instance with default config."""
        return EnamineTool({"timeout": 10})

    def test_missing_query(self, tool):
        """Test error when query is missing for catalog search."""
        result = tool.run({"operation": "search_catalog"})
        assert result["status"] == "error"
        assert "query" in result["error"]

    def test_missing_enamine_id(self, tool):
        """Test error when enamine_id is missing."""
        result = tool.run({"operation": "get_compound"})
        assert result["status"] == "error"
        assert "enamine_id" in result["error"]

    def test_missing_smiles(self, tool):
        """Test error when smiles is missing for structure search."""
        result = tool.run({"operation": "search_smiles"})
        assert result["status"] == "error"
        assert "smiles" in result["error"]

    def test_unknown_operation(self, tool):
        """Test error for unknown operation."""
        result = tool.run({"operation": "invalid_op"})
        assert result["status"] == "error"
        assert "Unknown operation" in result["error"]

    @patch("tooluniverse.enamine_tool.requests.get")
    def test_search_catalog_returns_url(self, mock_get, tool):
        """Test search catalog returns useful URL."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = tool.run({"operation": "search_catalog", "query": "pyridine"})

        assert result["status"] == "error"
        assert "no catalog data was retrieved" in result["error"]
        assert "search_url" in result

    @patch("tooluniverse.enamine_tool.requests.get")
    def test_get_libraries_success(self, mock_get, tool):
        """Test getting libraries returns useful info."""
        mock_response = MagicMock()
        mock_response.status_code = 404  # Will use fallback
        mock_get.return_value = mock_response

        result = tool.run({"operation": "get_libraries"})

        assert result["status"] == "error"
        assert "no live library data was retrieved" in result["error"]

    @patch("tooluniverse.enamine_tool.requests.get")
    def test_search_catalog_pages_json_payload_without_fixed_twenty(self, mock_get, tool):
        response = MagicMock(status_code=200)
        response.headers = {"Content-Type": "application/json"}
        response.json.return_value = {"results": [{"id": i} for i in range(25)]}
        mock_get.return_value = response

        result = tool.run(
            {"operation": "search_catalog", "query": "amine", "limit": 3, "offset": 20}
        )

        assert [row["id"] for row in result["data"]["results"]] == [20, 21, 22]
        assert result["metadata"]["next_offset"] == 23
        assert result["metadata"]["upstream_result_set_complete"] is None

    @patch("tooluniverse.enamine_tool.requests.get")
    def test_search_catalog_rejects_malformed_pagination(self, mock_get, tool):
        for pagination in ({"limit": "2"}, {"limit": 0}, {"offset": -1}, {"offset": False}):
            result = tool.run({"operation": "search_catalog", "query": "amine", **pagination})
            assert result["status"] == "error"
        mock_get.assert_not_called()


class TestEnamineToolInterface:
    """Test EnamineTool through ToolUniverse interface."""

    def test_tool_registered(self):
        """Test that EnamineTool is properly registered."""
        from tooluniverse import ToolUniverse

        tu = ToolUniverse()
        tu.load_tools()

        assert hasattr(tu.tools, "Enamine_search_catalog")
        assert hasattr(tu.tools, "Enamine_get_compound")
        assert hasattr(tu.tools, "Enamine_search_smiles")
        assert hasattr(tu.tools, "Enamine_get_libraries")
