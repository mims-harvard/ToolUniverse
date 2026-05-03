"""
Unit tests for OncoKB tool.
"""

import pytest
import json
import os
from unittest.mock import patch, MagicMock


class TestOncoKBToolDirect:
    """Test OncoKB tool directly (Level 1)."""

    @pytest.fixture
    def tool_config(self):
        """Load tool config from JSON."""
        with open("src/tooluniverse/data/oncokb_tools.json") as f:
            tools = json.load(f)
            return next(t for t in tools if t["name"] == "OncoKB_annotate_variant")

    @pytest.fixture
    def tool(self, tool_config):
        """Create tool instance."""
        from tooluniverse.oncokb_tool import OncoKBTool

        return OncoKBTool(tool_config)

    def test_annotate_variant_missing_gene(self, tool):
        """Test annotate_variant with missing gene parameter."""
        result = tool.run({"operation": "annotate_variant", "variant": "V600E"})
        assert result["status"] == "error"
        assert "gene" in result["error"].lower()

    def test_annotate_variant_missing_variant(self, tool):
        """Test annotate_variant with missing variant parameter."""
        result = tool.run({"operation": "annotate_variant", "gene": "BRAF"})
        assert result["status"] == "error"
        assert "variant" in result["error"].lower()

    def test_unknown_operation(self, tool):
        """Test unknown operation."""
        result = tool.run({"operation": "unknown"})
        assert result["status"] == "error"
        assert "unknown" in result["error"].lower()

    def test_copy_number_invalid_type(self, tool):
        """Test copy number with invalid type."""
        result = tool.run({
            "operation": "annotate_copy_number",
            "gene": "ERBB2",
            "copy_number_type": "INVALID"
        })
        assert result["status"] == "error"
        assert "AMPLIFICATION" in result["error"] or "DELETION" in result["error"]

    @patch("tooluniverse.oncokb_tool.requests.get")
    def test_annotate_variant_success(self, mock_get, tool):
        """Test successful variant annotation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "oncogenic": "Oncogenic",
            "mutationEffect": {"knownEffect": "Gain-of-function"},
            "highestSensitiveLevel": "LEVEL_1",
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = tool.run({
            "operation": "annotate_variant",
            "gene": "BRAF",
            "variant": "V600E"
        })
        assert result["status"] == "success"
        assert result["data"]["oncogenic"] == "Oncogenic"

    @patch("tooluniverse.oncokb_tool.requests.get")
    def test_get_gene_info_success(self, mock_get, tool):
        """Test successful gene info retrieval.
        
        Note: In demo mode (no ONCOKB_API_TOKEN), the tool calls /utils/allCuratedGenes
        which returns a list of genes, then searches for the specific gene.
        """
        mock_response = MagicMock()
        # Demo mode returns a list of genes from /utils/allCuratedGenes
        mock_response.json.return_value = [
            {
                "hugoSymbol": "BRAF",
                "oncogene": True,
                "tsg": False,
            },
            {
                "hugoSymbol": "TP53",
                "oncogene": False,
                "tsg": True,
            },
        ]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = tool.run({"operation": "get_gene_info", "gene": "BRAF"})
        assert result["status"] == "success"
        assert result["data"]["oncogene"] is True


class TestOncoKBToolInterface:
    """Test OncoKB tool via ToolUniverse interface (Level 2)."""

    @pytest.fixture
    def tu(self):
        """Create ToolUniverse instance."""
        from tooluniverse import ToolUniverse

        tu = ToolUniverse()
        tu.load_tools()
        return tu

    def test_tools_registered(self, tu):
        """Test that OncoKB tools are registered."""
        assert hasattr(tu.tools, "OncoKB_annotate_variant")
        assert hasattr(tu.tools, "OncoKB_get_gene_info")
        assert hasattr(tu.tools, "OncoKB_get_cancer_genes")
        assert hasattr(tu.tools, "OncoKB_get_levels")
        assert hasattr(tu.tools, "OncoKB_annotate_copy_number")


class TestOncoKBToolReal:
    """Test OncoKB tool with real API calls (Level 3).
    
    These tests use the demo API (limited genes: BRAF, TP53, ROS1).
    """

    @pytest.fixture
    def tu(self):
        """Create ToolUniverse instance."""
        from tooluniverse import ToolUniverse

        tu = ToolUniverse()
        tu.load_tools()
        return tu

    @pytest.mark.integration
    def test_real_annotate_variant(self, tu):
        """Test real variant annotation with demo API."""
        result = tu.tools.OncoKB_annotate_variant(
            operation="annotate_variant",
            gene="BRAF",
            variant="V600E"
        )
        # Demo API should work for BRAF
        if result["status"] == "success":
            print(f"Oncogenic: {result['data'].get('oncogenic')}")
        else:
            print(f"API response: {result.get('error')}")

    @pytest.mark.integration
    def test_real_get_levels(self, tu):
        """Test real evidence levels retrieval."""
        result = tu.tools.OncoKB_get_levels(operation="get_levels")
        if result["status"] == "success":
            print(f"Retrieved {len(result['data'])} evidence levels")
        else:
            print(f"API response: {result.get('error')}")
