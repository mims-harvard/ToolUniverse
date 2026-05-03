"""
Tests for CADD tool.

Tests the CADD API integration for:
- Single variant deleteriousness scores
- Position-level scores (all substitutions)
- Range-based scoring
"""

import json
import pytest
from pathlib import Path


class TestCADDToolDirect:
    """Level 1: Direct class testing."""

    @pytest.fixture
    def tool_config(self):
        """Load tool config from JSON."""
        config_path = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data" / "cadd_tools.json"
        with open(config_path) as f:
            tools = json.load(f)
        return {t["name"]: t for t in tools}

    def test_get_variant_score(self, tool_config):
        """Test getting score for a specific variant."""
        from tooluniverse.cadd_tool import CADDTool
        
        config = tool_config["CADD_get_variant_score"]
        tool = CADDTool(config)
        # Test with a known variant location
        result = tool.run({
            "chrom": "7",
            "pos": 140753336,
            "ref": "A",
            "alt": "T"
        })
        
        assert result["status"] == "success"

    def test_get_variant_score_with_chr_prefix(self, tool_config):
        """Test that chr prefix is handled correctly."""
        from tooluniverse.cadd_tool import CADDTool
        
        config = tool_config["CADD_get_variant_score"]
        tool = CADDTool(config)
        result = tool.run({
            "chrom": "chr7",  # With chr prefix
            "pos": 140753336,
            "ref": "A",
            "alt": "T"
        })
        
        assert result["status"] == "success"

    def test_get_variant_score_missing_params(self, tool_config):
        """Test error when parameters are missing."""
        from tooluniverse.cadd_tool import CADDTool
        
        config = tool_config["CADD_get_variant_score"]
        tool = CADDTool(config)
        
        # Missing chrom
        result = tool.run({"pos": 100, "ref": "A", "alt": "T"})
        assert result["status"] == "error"
        assert "chrom" in result["error"]
        
        # Missing pos
        result = tool.run({"chrom": "7", "ref": "A", "alt": "T"})
        assert result["status"] == "error"
        assert "pos" in result["error"]

    def test_get_position_scores(self, tool_config):
        """Test getting all scores at a position."""
        from tooluniverse.cadd_tool import CADDTool
        
        config = tool_config["CADD_get_position_scores"]
        tool = CADDTool(config)
        result = tool.run({
            "chrom": "7",
            "pos": 140753336
        })
        
        assert result["status"] == "success"
        if result["data"]:
            assert "variants" in result["data"]

    def test_get_range_scores(self, tool_config):
        """Test getting scores for a range."""
        from tooluniverse.cadd_tool import CADDTool

        config = tool_config["CADD_get_range_scores"]
        tool = CADDTool(config)
        result = tool.run({
            "chrom": "7",
            "start": 140753330,
            "end": 140753340  # 10bp range in BRAF region
        })

        assert result["status"] == "success"
        if result["data"]:
            assert "variants" in result["data"]
            assert "count" in result["data"]

    def test_get_range_scores_too_large(self, tool_config):
        """Test error when range exceeds 100bp limit."""
        from tooluniverse.cadd_tool import CADDTool
        
        config = tool_config["CADD_get_range_scores"]
        tool = CADDTool(config)
        result = tool.run({
            "chrom": "7",
            "start": 140753000,
            "end": 140753200  # 200bp - too large
        })
        
        assert result["status"] == "error"
        assert "100bp" in result["error"] or "too large" in result["error"].lower()

    def test_interpret_phred(self, tool_config):
        """Test PHRED score interpretation."""
        from tooluniverse.cadd_tool import CADDTool
        
        config = tool_config["CADD_get_variant_score"]
        tool = CADDTool(config)
        
        assert "highly_deleterious" in tool._interpret_phred(35)
        assert "deleterious" in tool._interpret_phred(25)
        assert "likely_deleterious" in tool._interpret_phred(17)
        assert "possibly_deleterious" in tool._interpret_phred(12)
        assert "benign" in tool._interpret_phred(5)


class TestCADDToolIntegration:
    """Level 2: ToolUniverse interface testing."""

    @pytest.fixture
    def tu(self):
        """Create ToolUniverse instance with tools loaded."""
        from tooluniverse import ToolUniverse
        tu = ToolUniverse()
        tu.load_tools()
        return tu

    def test_tools_registered(self, tu):
        """Verify CADD tools are registered."""
        assert hasattr(tu.tools, "CADD_get_variant_score")
        assert hasattr(tu.tools, "CADD_get_position_scores")
        assert hasattr(tu.tools, "CADD_get_range_scores")

    def test_get_variant_via_tu(self, tu):
        """Test calling get_variant through ToolUniverse."""
        result = tu.tools.CADD_get_variant_score(
            chrom="7",
            pos=140753336,
            ref="A",
            alt="T"
        )
        
        assert result["status"] == "success"

    def test_get_position_via_tu(self, tu):
        """Test calling get_position through ToolUniverse."""
        result = tu.tools.CADD_get_position_scores(
            chrom="7",
            pos=140753336
        )
        
        assert result["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
