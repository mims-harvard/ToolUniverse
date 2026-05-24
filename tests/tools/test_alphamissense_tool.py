"""
Tests for AlphaMissense tool.

Tests the AlphaMissense API integration for:
- Protein-level pathogenicity scores
- Specific variant scores
- Residue-level saturation data
"""

import json
import pytest
from pathlib import Path


class TestAlphaMissenseToolDirect:
    """Level 1: Direct class testing."""

    @pytest.fixture
    def tool_config(self):
        """Load tool config from JSON."""
        config_path = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data" / "alphamissense_tools.json"
        with open(config_path) as f:
            tools = json.load(f)
        return {t["name"]: t for t in tools}

    def test_get_protein_scores(self, tool_config):
        """Test getting scores for a protein."""
        from tooluniverse.alphamissense_tool import AlphaMissenseTool

        config = tool_config["AlphaMissense_get_protein_scores"]
        tool = AlphaMissenseTool(config)
        # KRAS with small cap — fast diagnostic, no live network volume
        result = tool.run({"uniprot_id": "P01116", "max_residues": 5})

        assert result["status"] == "success"
        assert "data" in result

    def test_get_protein_scores_returns_per_residue_list(self, tool_config):
        """Whole-protein call now returns one record per residue, not a sample.

        Pins the iter-3 fix: previously the tool returned only sample_residue +
        sample_data (one position); now it returns the full scores list. Skill
        5 (variant-predictor-dms-benchmarking) iterates `data['scores']` keyed
        by `resi`, so this shape contract is load-bearing.
        """
        from tooluniverse.alphamissense_tool import AlphaMissenseTool

        config = tool_config["AlphaMissense_get_protein_scores"]
        tool = AlphaMissenseTool(config)
        result = tool.run({"uniprot_id": "P01116", "max_residues": 10})

        assert result["status"] == "success"
        d = result["data"]
        # New contract: scores is a list, NOT a sample_data dict
        assert "scores" in d, f"missing 'scores' field: {list(d)}"
        assert isinstance(d["scores"], list), f"scores must be a list, got {type(d['scores'])}"
        assert d["n_positions_returned"] > 1, "should return many residues, not just a sample"
        assert d["protein_length"] == 189, f"KRAS canonical = 189 aa, got {d['protein_length']}"
        # Each record has position + uid + aa + resi + bin strings + mean_all
        if d["scores"]:
            first = d["scores"][0]
            assert "position" in first
            assert "uid" in first
            assert "aa" in first
            assert "resi" in first
            assert "mean_all" in first
        # Old fields that confirmed the sampling-only behavior must NOT be present
        assert "sample_residue" not in d
        assert "sample_data" not in d

    def test_get_protein_scores_max_residues_cap(self, tool_config):
        """max_residues caps the loop to first N positions."""
        from tooluniverse.alphamissense_tool import AlphaMissenseTool

        config = tool_config["AlphaMissense_get_protein_scores"]
        tool = AlphaMissenseTool(config)
        result = tool.run({"uniprot_id": "P01116", "max_residues": 3})

        assert result["status"] == "success"
        d = result["data"]
        assert d["n_positions_attempted"] == 3
        assert d["max_residues_cap"] == 3
        positions_returned = [s["position"] for s in d["scores"]]
        # First 3 residues attempted — even if some fail, positions are bounded
        for p in positions_returned:
            assert 1 <= p <= 3, f"position {p} exceeds the cap of 3"

    def test_get_protein_scores_missing_id(self, tool_config):
        """Test error when UniProt ID is missing."""
        from tooluniverse.alphamissense_tool import AlphaMissenseTool
        
        config = tool_config["AlphaMissense_get_protein_scores"]
        tool = AlphaMissenseTool(config)
        result = tool.run({})
        
        assert result["status"] == "error"
        assert "uniprot_id" in result["error"]

    def test_get_variant_score(self, tool_config):
        """Test getting score for a specific variant."""
        from tooluniverse.alphamissense_tool import AlphaMissenseTool
        
        config = tool_config["AlphaMissense_get_variant_score"]
        tool = AlphaMissenseTool(config)
        # BRAF V600E - famous oncogenic mutation
        result = tool.run({"uniprot_id": "P15056", "variant": "V600E"})
        
        assert result["status"] == "success"
        assert "data" in result

    def test_get_variant_score_with_p_notation(self, tool_config):
        """Test variant with p. notation."""
        from tooluniverse.alphamissense_tool import AlphaMissenseTool
        
        config = tool_config["AlphaMissense_get_variant_score"]
        tool = AlphaMissenseTool(config)
        result = tool.run({"uniprot_id": "P00533", "variant": "p.L858R"})  # EGFR L858R
        
        assert result["status"] == "success"

    def test_get_variant_score_missing_params(self, tool_config):
        """Test error when parameters are missing."""
        from tooluniverse.alphamissense_tool import AlphaMissenseTool
        
        config = tool_config["AlphaMissense_get_variant_score"]
        tool = AlphaMissenseTool(config)
        
        # Missing variant
        result = tool.run({"uniprot_id": "P00533"})
        assert result["status"] == "error"
        assert "variant" in result["error"]
        
        # Missing uniprot_id
        result = tool.run({"variant": "V600E"})
        assert result["status"] == "error"
        assert "uniprot_id" in result["error"]

    def test_get_variant_score_invalid_format(self, tool_config):
        """Test error with invalid variant format."""
        from tooluniverse.alphamissense_tool import AlphaMissenseTool
        
        config = tool_config["AlphaMissense_get_variant_score"]
        tool = AlphaMissenseTool(config)
        result = tool.run({"uniprot_id": "P00533", "variant": "invalid"})
        
        assert result["status"] == "error"
        assert "format" in result["error"].lower()

    def test_get_residue_scores(self, tool_config):
        """Test getting all scores at a position."""
        from tooluniverse.alphamissense_tool import AlphaMissenseTool
        
        config = tool_config["AlphaMissense_get_residue_scores"]
        tool = AlphaMissenseTool(config)
        result = tool.run({"uniprot_id": "P15056", "position": 600})  # BRAF position 600
        
        assert result["status"] == "success"
        assert "data" in result
        if result["data"]:
            assert result["data"]["position"] == 600

    def test_get_residue_scores_invalid_position(self, tool_config):
        """Test error with invalid position."""
        from tooluniverse.alphamissense_tool import AlphaMissenseTool
        
        config = tool_config["AlphaMissense_get_residue_scores"]
        tool = AlphaMissenseTool(config)
        result = tool.run({"uniprot_id": "P00533", "position": "abc"})
        
        assert result["status"] == "error"
        assert "integer" in result["error"].lower()

    def test_classification_thresholds(self, tool_config):
        """Test that classification thresholds are correct."""
        from tooluniverse.alphamissense_tool import AlphaMissenseTool
        
        config = tool_config["AlphaMissense_get_variant_score"]
        tool = AlphaMissenseTool(config)
        
        # Test classification logic
        assert tool._classify_score(0.7) == "pathogenic"
        assert tool._classify_score(0.5) == "ambiguous"
        assert tool._classify_score(0.2) == "benign"


class TestAlphaMissenseToolIntegration:
    """Level 2: ToolUniverse interface testing."""

    @pytest.fixture
    def tu(self):
        """Create ToolUniverse instance with tools loaded."""
        from tooluniverse import ToolUniverse
        tu = ToolUniverse()
        tu.load_tools()
        return tu

    def test_tools_registered(self, tu):
        """Verify AlphaMissense tools are registered."""
        assert hasattr(tu.tools, "AlphaMissense_get_protein_scores")
        assert hasattr(tu.tools, "AlphaMissense_get_variant_score")
        assert hasattr(tu.tools, "AlphaMissense_get_residue_scores")

    def test_get_variant_via_tu(self, tu):
        """Test calling get_variant through ToolUniverse."""
        result = tu.tools.AlphaMissense_get_variant_score(
            uniprot_id="P15056",
            variant="V600E"
        )
        
        assert result["status"] == "success"

    def test_get_residue_via_tu(self, tu):
        """Test calling get_residue through ToolUniverse."""
        result = tu.tools.AlphaMissense_get_residue_scores(
            uniprot_id="P15056",
            position=600
        )
        
        assert result["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
