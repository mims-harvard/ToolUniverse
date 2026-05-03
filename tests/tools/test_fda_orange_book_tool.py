"""
Unit tests for FDA Orange Book Tool.

Tests drug approval information, patent data, exclusivity, and TE codes.
"""

import pytest
import json
from tooluniverse import ToolUniverse


class TestFDAOrangeBookTool:
    """Test FDA Orange Book operations."""
    
    @pytest.fixture
    def tu(self):
        """Initialize ToolUniverse with loaded tools."""
        tu = ToolUniverse()
        tu.load_tools()
        return tu
    
    def test_orange_book_tools_load(self, tu):
        """Verify all 6 Orange Book operations are registered."""
        assert hasattr(tu.tools, 'FDA_OrangeBook_search_drug')
        assert hasattr(tu.tools, 'FDA_OrangeBook_get_approval_history')
        assert hasattr(tu.tools, 'FDA_OrangeBook_get_patent_info')
        assert hasattr(tu.tools, 'FDA_OrangeBook_get_exclusivity')
        assert hasattr(tu.tools, 'FDA_OrangeBook_check_generic_availability')
        assert hasattr(tu.tools, 'FDA_OrangeBook_get_te_code')
    
    def test_search_drug_by_brand_name(self, tu):
        """Test searching for drug by brand name."""
        result = tu.tools.FDA_OrangeBook_search_drug(
            operation="search_drug",
            brand_name="ADVIL",
            limit=5
        )
        
        assert result.get("status") == "success"
        assert isinstance(result.get("data"), dict)
        assert "drugs" in result
        assert "drugs" in result["data"]
        assert isinstance(result["drugs"], list)
        assert result["count"] > 0
        print(f"\n✅ Found {result['count']} products for ADVIL")
    
    def test_search_drug_by_application_number(self, tu):
        """Test searching by application number."""
        result = tu.tools.FDA_OrangeBook_search_drug(
            operation="search_drug",
            application_number="NDA020402",
            limit=5
        )
        
        assert result.get("status") == "success"
        assert isinstance(result.get("data"), dict)
        assert "drugs" in result
        if result["count"] > 0:
            print(f"\n✅ Found application NDA020402")
    
    def test_get_approval_history(self, tu):
        """Test getting approval history for an application."""
        result = tu.tools.FDA_OrangeBook_get_approval_history(
            operation="get_approval_history",
            application_number="NDA020402"
        )
        
        assert result.get("status") == "success"
        assert isinstance(result.get("data"), dict)
        assert "application_number" in result
        assert "application_number" in result["data"]
        assert "submissions" in result
        assert isinstance(result["submissions"], list)
        print(f"\n✅ Retrieved {result.get('submission_count', 0)} submissions")
        if result.get("original_approval_date"):
            print(f"   Original approval: {result['original_approval_date']}")
    
    def test_check_generic_availability(self, tu):
        """Test checking for generic versions."""
        result = tu.tools.FDA_OrangeBook_check_generic_availability(
            operation="check_generic_availability",
            brand_name="ADVIL"
        )
        
        assert result.get("status") == "success"
        assert isinstance(result.get("data"), dict)
        assert "generics_available" in result
        assert "generics_available" in result["data"]
        assert "reference_count" in result
        assert "generic_count" in result
        print(f"\n✅ Reference drugs: {result['reference_count']}")
        print(f"   Generic drugs: {result['generic_count']}")
        print(f"   Generics available: {result['generics_available']}")
    
    def test_get_te_code(self, tu):
        """Test getting therapeutic equivalence codes."""
        result = tu.tools.FDA_OrangeBook_get_te_code(
            operation="get_te_code",
            brand_name="ADVIL"
        )
        
        assert result.get("status") == "success"
        assert isinstance(result.get("data"), dict)
        assert "te_codes" in result
        assert "te_codes" in result["data"]
        assert "te_code_guide" in result
        print(f"\n✅ Found {result.get('count', 0)} TE codes")
        for te in result.get("te_codes", [])[:3]:
            print(f"   {te.get('brand_name')}: {te.get('te_code')} - {te.get('interpretation')}")
    
    def test_get_patent_info(self, tu):
        """Test getting patent information."""
        result = tu.tools.FDA_OrangeBook_get_patent_info(
            operation="get_patent_info",
            brand_name="ADVIL"
        )
        
        assert result.get("status") == "success"
        assert isinstance(result.get("data"), dict)
        assert "download_url" in result
        assert "download_url" in result["data"]
        print(f"\n✅ Patent info guidance provided")
        print(f"   Download URL: {result.get('download_url')}")
    
    def test_get_exclusivity(self, tu):
        """Test getting exclusivity information."""
        result = tu.tools.FDA_OrangeBook_get_exclusivity(
            operation="get_exclusivity",
            brand_name="ADVIL"
        )
        
        assert result.get("status") == "success"
        assert isinstance(result.get("data"), dict)
        assert "exclusivity_types" in result
        assert "exclusivity_types" in result["data"]
        print(f"\n✅ Exclusivity types:")
        for exc_type in result.get("exclusivity_types", []):
            print(f"   - {exc_type}")
    
    def test_error_handling_missing_params(self, tu):
        """Test error handling when parameters are missing."""
        result = tu.tools.FDA_OrangeBook_search_drug(
            operation="search_drug"
            # Missing brand_name, generic_name, and application_number
        )
        
        assert result.get("status") == "error"
        assert "brand_name" in result.get("error", "").lower() or \
               "generic_name" in result.get("error", "").lower() or \
               "application_number" in result.get("error", "").lower()
    
    def test_error_handling_invalid_application(self, tu):
        """Test error handling with invalid application number."""
        result = tu.tools.FDA_OrangeBook_get_approval_history(
            operation="get_approval_history",
            application_number="NDA000000"  # Invalid
        )
        
        assert result.get("status") == "error"
        assert "not found" in result.get("error", "").lower() or "no application" in result.get("error", "").lower()


class TestFDAOrangeBookDirectClass:
    """Direct class testing for FDA Orange Book."""
    
    @pytest.fixture
    def orange_book_tool(self):
        """Initialize Orange Book tool directly."""
        from tooluniverse.fda_orange_book_tool import FDAOrangeBookTool
        
        # Load tool config
        with open("src/tooluniverse/data/fda_orange_book_tools.json") as f:
            tools = json.load(f)
            config = next(
                t for t in tools 
                if t["name"] == "FDA_OrangeBook_search_drug"
            )
        
        return FDAOrangeBookTool(config)
    
    def test_direct_class_instantiation(self, orange_book_tool):
        """Test that Orange Book tool instantiates correctly."""
        assert orange_book_tool is not None
        assert hasattr(orange_book_tool, 'run')
        assert hasattr(orange_book_tool, '_search_drug')
        assert hasattr(orange_book_tool, '_get_approval_history')
        assert hasattr(orange_book_tool, '_interpret_te_code')
    
    def test_direct_class_execution(self, orange_book_tool):
        """Test direct class execution."""
        result = orange_book_tool.run({
            "operation": "search_drug",
            "brand_name": "ADVIL",
            "limit": 5
        })
        
        assert result.get("status") == "success"
        assert isinstance(result.get("data"), dict)
        assert "drugs" in result
        assert "drugs" in result["data"]
    
    def test_te_code_interpretation(self, orange_book_tool):
        """Test TE code interpretation helper."""
        assert "therapeutically equivalent" in orange_book_tool._interpret_te_code("AB").lower()
        assert "not therapeutically equivalent" in orange_book_tool._interpret_te_code("BX").lower()
        assert "no te code" in orange_book_tool._interpret_te_code("").lower()


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
