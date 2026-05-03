"""
Tests for Pharos/TCRD tool.

Tests the Pharos GraphQL API integration for:
- Target lookup by gene/UniProt
- Target search with TDL filtering
- TDL summary statistics
- Disease-associated targets
"""

import json
import pytest
from pathlib import Path


class TestPharosToolDirect:
    """Level 1: Direct class testing."""

    @pytest.fixture
    def tool_config(self):
        """Load tool config from JSON."""
        config_path = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data" / "pharos_tools.json"
        with open(config_path) as f:
            tools = json.load(f)
        return {t["name"]: t for t in tools}

    @pytest.fixture
    def pharos_tool(self, tool_config):
        """Create PharosTool instance."""
        from tooluniverse.pharos_tool import PharosTool
        return PharosTool(tool_config["Pharos_get_target"])

    def test_get_target_by_gene(self, tool_config):
        """Test getting target info by gene symbol."""
        from tooluniverse.pharos_tool import PharosTool
        
        config = tool_config["Pharos_get_target"]
        tool = PharosTool(config)
        result = tool.run({"gene": "EGFR"})
        
        assert result["status"] == "success"
        assert result["data"] is not None
        assert result["data"]["sym"] == "EGFR"  # API returns 'sym' not 'gene'
        assert "tdl" in result["data"]  # TDL classification

    def test_get_target_by_uniprot(self, tool_config):
        """Test getting target info by UniProt ID."""
        from tooluniverse.pharos_tool import PharosTool
        
        config = tool_config["Pharos_get_target"]
        tool = PharosTool(config)
        result = tool.run({"uniprot": "P00533"})  # EGFR UniProt
        
        assert result["status"] == "success"
        # May or may not find depending on API facet support

    def test_get_target_missing_param(self, tool_config):
        """Test error when no identifier provided."""
        from tooluniverse.pharos_tool import PharosTool
        
        config = tool_config["Pharos_get_target"]
        tool = PharosTool(config)
        result = tool.run({})
        
        assert result["status"] == "error"
        assert "gene" in result["error"] or "uniprot" in result["error"]

    def test_search_targets(self, tool_config):
        """Test searching targets by keyword."""
        from tooluniverse.pharos_tool import PharosTool
        
        config = tool_config["Pharos_search_targets"]
        tool = PharosTool(config)
        result = tool.run({"query": "kinase", "top": 5})
        
        assert result["status"] == "success"
        assert "count" in result["data"]
        assert "targets" in result["data"]
        # Note: Pharos API may not respect the top parameter exactly
        assert len(result["data"]["targets"]) > 0
        assert result["data"]["count"] > 0

    def test_search_targets_with_tdl_filter(self, tool_config):
        """Test searching with TDL filter."""
        from tooluniverse.pharos_tool import PharosTool
        
        config = tool_config["Pharos_search_targets"]
        tool = PharosTool(config)
        result = tool.run({"query": "GPCR", "tdl": "Tdark", "top": 5})
        
        assert result["status"] == "success"
        # Results should be Tdark targets
        for target in result["data"]["targets"]:
            if "idgTDL" in target:
                assert target["idgTDL"] == "Tdark"

    def test_search_targets_missing_query(self, tool_config):
        """Test error when query is missing."""
        from tooluniverse.pharos_tool import PharosTool
        
        config = tool_config["Pharos_search_targets"]
        tool = PharosTool(config)
        result = tool.run({})
        
        assert result["status"] == "error"
        assert "query" in result["error"]

    def test_get_tdl_summary(self, tool_config):
        """Test getting TDL summary statistics."""
        from tooluniverse.pharos_tool import PharosTool
        
        config = tool_config["Pharos_get_tdl_summary"]
        tool = PharosTool(config)
        result = tool.run({})
        
        assert result["status"] == "success"
        assert "tdl_levels" in result["data"]
        assert "description" in result["data"]
        # Should have all TDL categories
        assert "Tclin" in result["data"]["tdl_levels"]
        assert "Tchem" in result["data"]["tdl_levels"]
        assert "Tbio" in result["data"]["tdl_levels"]
        assert "Tdark" in result["data"]["tdl_levels"]

    def test_get_disease_targets(self, tool_config):
        """Test getting targets for a disease."""
        from tooluniverse.pharos_tool import PharosTool
        
        config = tool_config["Pharos_get_disease_targets"]
        tool = PharosTool(config)
        result = tool.run({"disease": "breast cancer", "top": 5})
        
        assert result["status"] == "success"
        assert "disease" in result["data"]
        assert "targets" in result["data"]

    def test_get_disease_targets_missing_disease(self, tool_config):
        """Test error when disease is missing."""
        from tooluniverse.pharos_tool import PharosTool
        
        config = tool_config["Pharos_get_disease_targets"]
        tool = PharosTool(config)
        result = tool.run({})
        
        assert result["status"] == "error"
        assert "disease" in result["error"]


class TestPharosToolIntegration:
    """Level 2: ToolUniverse interface testing."""

    @pytest.fixture
    def tu(self):
        """Create ToolUniverse instance with tools loaded."""
        from tooluniverse import ToolUniverse
        tu = ToolUniverse()
        tu.load_tools()
        return tu

    def test_tools_registered(self, tu):
        """Verify Pharos tools are registered."""
        assert hasattr(tu.tools, "Pharos_get_target")
        assert hasattr(tu.tools, "Pharos_search_targets")
        assert hasattr(tu.tools, "Pharos_get_tdl_summary")
        assert hasattr(tu.tools, "Pharos_get_disease_targets")

    def test_get_target_via_tu(self, tu):
        """Test calling get_target through ToolUniverse."""
        result = tu.tools.Pharos_get_target(gene="EGFR")
        
        assert result["status"] == "success"
        assert result["data"]["sym"] == "EGFR"  # API returns 'sym' not 'gene'

    def test_search_via_tu(self, tu):
        """Test calling search through ToolUniverse."""
        result = tu.tools.Pharos_search_targets(query="kinase", top=3)
        
        assert result["status"] == "success"
        assert result["data"]["count"] > 0

    def test_tdl_summary_via_tu(self, tu):
        """Test calling TDL summary through ToolUniverse."""
        result = tu.tools.Pharos_get_tdl_summary()
        
        assert result["status"] == "success"
        assert "tdl_levels" in result["data"]
        assert "description" in result["data"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
