"""
Tests for tool name shortening functionality.

This module tests the automatic tool name shortening feature added for
MCP 64-character limit compatibility.
"""

import pytest
from tooluniverse.tool_name_utils import shorten_tool_name, ToolNameMapper


class TestShortenToolName:
    """Tests for the shorten_tool_name function."""
    
    def test_short_name_unchanged(self):
        """Test that short names are not modified."""
        name = "FDA_get_drug_name"
        shortened = shorten_tool_name(name, max_length=55)
        assert shortened == name
        assert len(shortened) <= 55
    
    def test_long_name_shortened(self):
        """Test that long names are shortened."""
        name = "FDA_get_info_on_conditions_for_doctor_consultation_by_drug_name"
        shortened = shorten_tool_name(name, max_length=55)
        
        assert len(shortened) <= 55
        assert shortened.startswith("FDA_")
        assert shortened != name
    
    def test_preserves_category_prefix(self):
        """Test that category prefix (first word) is preserved."""
        names = [
            "FDA_get_very_long_information_about_something",
            "UniProt_get_extremely_detailed_function_information",
        ]
        
        for name in names:
            shortened = shorten_tool_name(name, max_length=55)
            category = name.split('_')[0]
            assert shortened.startswith(category + "_")
    
    def test_fits_within_limit(self):
        """Test that shortened names always fit within the limit."""
        long_names = [
            "FDA_get_info_on_conditions_for_doctor_consultation_by_drug_name",
            "euhealthinfo_search_diabetes_mellitus_epidemiology_registry",
        ]
        
        for name in long_names:
            shortened = shorten_tool_name(name, max_length=55)
            assert len(shortened) <= 55


class TestToolNameMapper:
    """Tests for the ToolNameMapper class."""
    
    def test_bidirectional_mapping(self):
        """Test that names can be mapped both directions."""
        mapper = ToolNameMapper()
        original = "FDA_get_info_on_conditions_for_doctor_consultation_by_drug_name"
        
        # Shorten
        shortened = mapper.get_shortened(original, max_length=55)
        assert len(shortened) <= 55
        
        # Resolve back
        resolved = mapper.get_original(shortened)
        assert resolved == original
    
    def test_collision_handling(self):
        """Test that collisions are handled with counters."""
        mapper = ToolNameMapper()
        
        # Create two names that might shorten to the same thing
        name1 = "test_get_info"
        name2 = "test_get_information"
        
        short1 = mapper.get_shortened(name1, max_length=20)
        short2 = mapper.get_shortened(name2, max_length=20)
        
        # If they collide, second should have suffix
        if short1 == short2[:len(short1)]:
            assert "_2" in short2 or short2 != short1
        
        # Both should resolve correctly
        assert mapper.get_original(short1) == name1
        assert mapper.get_original(short2) == name2
    
    def test_caching(self):
        """Test that repeated calls return the same shortened name."""
        mapper = ToolNameMapper()
        name = "FDA_get_info_on_conditions_for_doctor_consultation_by_drug_name"
        
        short1 = mapper.get_shortened(name, max_length=55)
        short2 = mapper.get_shortened(name, max_length=55)
        
        assert short1 == short2


class TestMCPCompatibility:
    """Tests for MCP 64-character limit compatibility."""
    
    def test_smcp_integration(self):
        """Test that SMCP automatically enables name shortening."""
        try:
            from tooluniverse.smcp import SMCP
        except Exception as e:
            pytest.skip(f"SMCP not available: {e}")
        
        server = SMCP(
            name='tu',
            tool_categories=['fda_drug_label'],
            auto_expose_tools=False,
            search_enabled=False
        )
        
        # SMCP should automatically enable name shortening
        assert server.tooluniverse.name_mapper is not None
