"""
Unit tests for DailyMed SPL Parser Tool.

Tests the new parsing functionality for extracting structured data from SPL XML.
"""

import pytest
import json
from unittest.mock import Mock, patch
from tooluniverse import ToolUniverse

# Check if lxml is available
try:
    from lxml import etree
    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False


class TestDailyMedSPLParser:
    """Test DailyMed SPL Parser operations."""
    
    @pytest.fixture
    def tu(self):
        """Initialize ToolUniverse with loaded tools."""
        tu = ToolUniverse()
        tu.load_tools()
        return tu
    
    def test_parser_tools_load(self, tu):
        """Verify all 5 parser operations are registered."""
        assert hasattr(tu.tools, 'DailyMed_parse_adverse_reactions')
        assert hasattr(tu.tools, 'DailyMed_parse_dosing')
        assert hasattr(tu.tools, 'DailyMed_parse_contraindications')
        assert hasattr(tu.tools, 'DailyMed_parse_drug_interactions')
        assert hasattr(tu.tools, 'DailyMed_parse_clinical_pharmacology')
    
    @pytest.mark.skipif(not LXML_AVAILABLE, reason="lxml not installed")
    def test_parse_adverse_reactions_real_api(self, tu):
        """Test parsing adverse reactions from real DailyMed API."""
        result = tu.tools.DailyMed_parse_adverse_reactions(
            operation="parse_adverse_reactions",
            setid="030d9bca-a934-6ef9-e063-6394a90a8277"  # Advil
        )
        
        assert result.get("status") == "success"
        assert isinstance(result.get("data"), dict)
        assert "adverse_reactions" in result
        assert "adverse_reactions" in result["data"]
        assert isinstance(result["adverse_reactions"], list)
        print(f"\n✅ Parsed {result.get('count', 0)} adverse reaction entries")
    
    @pytest.mark.skipif(not LXML_AVAILABLE, reason="lxml not installed")
    def test_parse_dosing_real_api(self, tu):
        """Test parsing dosing information from real DailyMed API."""
        result = tu.tools.DailyMed_parse_dosing(
            operation="parse_dosing",
            setid="030d9bca-a934-6ef9-e063-6394a90a8277"
        )
        
        assert result.get("status") == "success"
        assert isinstance(result.get("data"), dict)
        assert "dosing_info" in result
        assert "dosing_info" in result["data"]
        assert isinstance(result["dosing_info"], list)
        print(f"\n✅ Parsed {result.get('count', 0)} dosing entries")
    
    @pytest.mark.skipif(not LXML_AVAILABLE, reason="lxml not installed")
    def test_parse_contraindications_real_api(self, tu):
        """Test parsing contraindications from real DailyMed API."""
        result = tu.tools.DailyMed_parse_contraindications(
            operation="parse_contraindications",
            setid="030d9bca-a934-6ef9-e063-6394a90a8277"
        )
        
        assert result.get("status") == "success"
        assert isinstance(result.get("data"), dict)
        assert "contraindications" in result
        assert "contraindications" in result["data"]
        assert isinstance(result["contraindications"], list)
        print(f"\n✅ Parsed {result.get('count', 0)} contraindications")
    
    @pytest.mark.skipif(not LXML_AVAILABLE, reason="lxml not installed")
    def test_parse_drug_interactions_real_api(self, tu):
        """Test parsing drug interactions from real DailyMed API."""
        result = tu.tools.DailyMed_parse_drug_interactions(
            operation="parse_drug_interactions",
            setid="030d9bca-a934-6ef9-e063-6394a90a8277"
        )
        
        assert result.get("status") == "success"
        assert isinstance(result.get("data"), dict)
        assert "interactions" in result
        assert "interactions" in result["data"]
        assert isinstance(result["interactions"], list)
        print(f"\n✅ Parsed {result.get('count', 0)} drug interactions")
    
    @pytest.mark.skipif(not LXML_AVAILABLE, reason="lxml not installed")
    def test_parse_clinical_pharmacology_real_api(self, tu):
        """Test parsing clinical pharmacology from real DailyMed API."""
        result = tu.tools.DailyMed_parse_clinical_pharmacology(
            operation="parse_clinical_pharmacology",
            setid="030d9bca-a934-6ef9-e063-6394a90a8277"
        )
        
        assert result.get("status") == "success"
        assert isinstance(result.get("data"), dict)
        assert "pharmacology" in result
        assert "pharmacology" in result["data"]
        assert isinstance(result["pharmacology"], list)
        print(f"\n✅ Parsed {result.get('count', 0)} pharmacology entries")
    
    def test_error_handling_missing_setid(self, tu):
        """Test error handling when setid is missing."""
        result = tu.tools.DailyMed_parse_adverse_reactions(
            operation="parse_adverse_reactions"
            # Missing setid
        )
        
        assert result.get("status") == "error"
        assert "setid" in result.get("error", "").lower()
    
    def test_error_handling_invalid_setid(self, tu):
        """Test error handling with invalid setid."""
        result = tu.tools.DailyMed_parse_adverse_reactions(
            operation="parse_adverse_reactions",
            setid="00000000-0000-0000-0000-000000000000"  # Invalid
        )
        
        assert result.get("status") == "error"
        assert "not found" in result.get("error", "").lower() or "404" in result.get("error", "")
    
    def test_operation_autofill(self, tu):
        """Test that operation is auto-filled from schema const when not provided."""
        result = tu.tools.DailyMed_parse_adverse_reactions(
            # operation omitted — should be auto-filled from schema const
            setid="030d9bca-a934-6ef9-e063-6394a90a8277"
        )
        # Auto-fill means the call proceeds; it should not error on missing operation
        assert result.get("status") != "error" or "operation" not in result.get("error", "")


class TestDailyMedParserDirectClass:
    """Direct class testing for DailyMed Parser."""
    
    @pytest.fixture
    def parser_tool(self):
        """Initialize parser tool directly."""
        from tooluniverse.dailymed_tool import DailyMedSPLParserTool
        
        # Load tool config
        with open("src/tooluniverse/data/dailymed_tools.json") as f:
            tools = json.load(f)
            config = next(
                t for t in tools 
                if t["name"] == "DailyMed_parse_adverse_reactions"
            )
        
        return DailyMedSPLParserTool(config)
    
    def test_direct_class_instantiation(self, parser_tool):
        """Test that parser tool instantiates correctly."""
        assert parser_tool is not None
        assert hasattr(parser_tool, 'run')
        assert hasattr(parser_tool, '_parse_adverse_reactions')
        assert hasattr(parser_tool, '_extract_table_data')
    
    @pytest.mark.skipif(not LXML_AVAILABLE, reason="lxml not installed")
    def test_direct_class_execution(self, parser_tool):
        """Test direct class execution."""
        result = parser_tool.run({
            "operation": "parse_adverse_reactions",
            "setid": "030d9bca-a934-6ef9-e063-6394a90a8277"
        })
        
        assert result.get("status") == "success"
        assert isinstance(result.get("data"), dict)
        assert "adverse_reactions" in result
        assert "adverse_reactions" in result["data"]


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
