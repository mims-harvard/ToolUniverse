"""
Unit tests for COSMIC tool.
"""

import pytest
import json
from unittest.mock import patch, MagicMock


class TestCOSMICToolDirect:
    """Test COSMIC tool directly (Level 1)."""

    @pytest.fixture
    def tool_config(self):
        """Load tool config from JSON."""
        with open("src/tooluniverse/data/cosmic_tools.json") as f:
            tools = json.load(f)
            return next(t for t in tools if t["name"] == "COSMIC_search_mutations")

    @pytest.fixture
    def tool(self, tool_config):
        """Create tool instance."""
        from tooluniverse.cosmic_tool import COSMICTool

        return COSMICTool(tool_config)

    def test_search_missing_terms(self, tool):
        """Test search with missing terms parameter."""
        result = tool.run({"operation": "search"})
        assert result["status"] == "error"
        assert "terms" in result["error"].lower()

    def test_get_by_gene_missing_gene(self, tool):
        """Test get_by_gene with missing gene parameter."""
        result = tool.run({"operation": "get_by_gene"})
        assert result["status"] == "error"
        assert "gene" in result["error"].lower()

    def test_unknown_operation(self, tool):
        """Test unknown operation."""
        result = tool.run({"operation": "unknown"})
        assert result["status"] == "error"
        assert "unknown" in result["error"].lower()

    @patch("tooluniverse.cosmic_tool.requests.get")
    def test_search_success(self, mock_get, tool):
        """Test successful search."""
        # Mock NLM API response format: [total, codes, extra_data, display_strings]
        mock_response = MagicMock()
        # NLM API: [total, codes, {field_name: [values_by_index]}, display_strings]
        mock_response.json.return_value = [
            5,
            ["COSM476", "COSM477"],
            {
                "GeneName": ["BRAF", "BRAF"],
                "MutationAA": ["p.V600E", "p.V600K"],
                "MutationCDS": ["c.1799T>A", "c.1798_1799GT>AA"],
                "PrimarySite": ["skin", "skin"],
                "PrimaryHistology": ["malignant_melanoma", "malignant_melanoma"],
            },
            ["BRAF V600E", "BRAF V600K"],
        ]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = tool.run({"operation": "search", "terms": "BRAF V600E"})
        assert result["status"] == "success"
        assert "data" in result
        assert result["data"]["total_count"] == 5
        assert len(result["data"]["results"]) == 2

    @patch("tooluniverse.cosmic_tool.requests.get")
    def test_search_timeout(self, mock_get, tool):
        """Test timeout handling."""
        import requests

        mock_get.side_effect = requests.exceptions.Timeout()
        result = tool.run({"operation": "search", "terms": "BRAF"})
        assert result["status"] == "error"
        # The error message is "Request timeout after 30 seconds"
        assert "timeout" in result["error"].lower()


class TestCOSMICToolInterface:
    """Test COSMIC tool via ToolUniverse interface (Level 2)."""

    @pytest.fixture
    def tu(self):
        """Create ToolUniverse instance."""
        from tooluniverse import ToolUniverse

        tu = ToolUniverse()
        tu.load_tools()
        return tu

    def test_tools_registered(self, tu):
        """Test that COSMIC tools are registered."""
        assert hasattr(tu.tools, "COSMIC_search_mutations")
        assert hasattr(tu.tools, "COSMIC_get_mutations_by_gene")

    @patch("tooluniverse.cosmic_tool.requests.get")
    def test_search_via_interface(self, mock_get, tu):
        """Test search via ToolUniverse interface."""
        mock_response = MagicMock()
        mock_response.json.return_value = [1, ["COSM476"], {}, ["BRAF V600E"]]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = tu.tools.COSMIC_search_mutations(
            operation="search", terms="BRAF V600E", max_results=10
        )
        assert result["status"] == "success"


class TestCOSMICToolReal:
    """Test COSMIC tool with real API calls (Level 3).
    
    These tests make actual API calls and may be skipped in CI.
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
        """Test real COSMIC search."""
        result = tu.tools.COSMIC_search_mutations(
            operation="search", terms="BRAF", max_results=5
        )
        # API may succeed or fail depending on availability
        if result["status"] == "success":
            assert "data" in result
            print(f"Found {result['data']['total_count']} mutations")
        else:
            print(f"API error (may be expected): {result.get('error')}")

    @pytest.mark.integration
    def test_real_get_by_gene(self, tu):
        """Test real get mutations by gene."""
        result = tu.tools.COSMIC_get_mutations_by_gene(
            operation="get_by_gene", gene="TP53", max_results=10
        )
        if result["status"] == "success":
            assert "data" in result
            print(f"Found {result['data']['total_count']} TP53 mutations")
        else:
            print(f"API error (may be expected): {result.get('error')}")
