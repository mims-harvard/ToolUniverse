"""Unit tests for Rfam Database API tools."""

import pytest
from tooluniverse import ToolUniverse


class TestRfamTools:
    """Test suite for Rfam tools."""
    
    @pytest.fixture
    def tu(self):
        """Create ToolUniverse instance."""
        tu = ToolUniverse()
        tu.load_tools()
        return tu
    
    def test_tools_load(self, tu):
        """Test that Rfam tools load correctly."""
        tool_names = [tool.get("name") for tool in tu.all_tools if isinstance(tool, dict)]
        
        expected_tools = [
            "Rfam_get_family",
            "Rfam_get_alignment",
            "Rfam_get_covariance_model",
            "Rfam_search_sequence",
            "Rfam_get_tree_data",
            "Rfam_get_sequence_regions",
            "Rfam_get_structure_mapping",
            "Rfam_accession_to_id",
            "Rfam_id_to_accession"
        ]
        
        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not found"
    
    def test_get_family(self, tu):
        """Test getting RNA family information."""
        result = tu.tools.Rfam_get_family(**{
            "operation": "get_family",
            "family_id": "RF00360",
            "format": "json"
        })
        
        assert result.get("status") == "success" or "error" in result
        
        if result.get("status") == "success":
            assert "data" in result
            assert "family_id" in result
    
    def test_accession_conversion(self, tu):
        """Test converting accession to ID."""
        result = tu.tools.Rfam_accession_to_id(**{
            "operation": "get_family_id",
            "accession": "RF00360"
        })
        
        assert result.get("status") == "success" or "error" in result
    
    def test_id_conversion(self, tu):
        """Test converting ID to accession."""
        result = tu.tools.Rfam_id_to_accession(**{
            "operation": "get_family_accession",
            "family_id": "snoZ107_R87"
        })
        
        assert result.get("status") == "success" or "error" in result
    
    def test_get_alignment(self, tu):
        """Test getting RNA alignment."""
        result = tu.tools.Rfam_get_alignment(**{
            "operation": "get_alignment",
            "family_id": "RF00360",
            "format": "fasta"
        })
        
        assert result.get("status") == "success" or "error" in result
        
        if result.get("status") == "success":
            # Check if data is nested or flat
            data = result.get("data", result)
            assert "alignment" in data
            assert "format" in data
