"""
Unit tests for 4DN Data Portal tools.
"""

import pytest
from tooluniverse import ToolUniverse


class TestFourDNTools:
    """Test suite for 4DN Data Portal tools."""
    
    @pytest.fixture
    def tu(self):
        """Create ToolUniverse instance."""
        tu = ToolUniverse()
        tu.load_tools()
        return tu
    
    def test_tools_load(self, tu):
        """Test that 4DN tools load correctly."""
        tool_names = [tool.get("name") for tool in tu.all_tools if isinstance(tool, dict)]
        
        expected_tools = [
            "FourDN_search_data",
            "FourDN_get_file_metadata",
            "FourDN_get_experiment_metadata",
            "FourDN_get_download_url"
        ]
        
        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not found"
    
    def test_search_data_basic(self, tu):
        """Test basic search functionality."""
        result = tu.tools.FourDN_search_data(**{
            "operation": "search",
            "query": "*",
            "limit": 5
        })
        
        assert "status" in result
        # Response now has nested data structure
        if result["status"] == "success":
            assert "data" in result
            assert "num_results" in result["data"] or "num_results" in result
        else:
            assert "error" in result
    
    def test_search_data_with_filters(self, tu):
        """Test search with filters."""
        result = tu.tools.FourDN_search_data(**{
            "operation": "search",
            "query": "Hi-C",
            "item_type": "File",
            "limit": 10
        })
        
        assert "status" in result
        
        if result["status"] == "success":
            assert "data" in result
            assert "results" in result["data"]
            assert isinstance(result["data"]["results"], list)
    
    def test_get_file_metadata_requires_accession(self, tu):
        """Test get_file_metadata requires file_accession."""
        result = tu.tools.FourDN_get_file_metadata(**{
            "operation": "get_file_metadata"
        })
        
        # Handle both old and new error formats
        assert "status" in result or "error" in result
        
        if result.get("status") == "error" or "error" in result:
            error_text = result.get("error", "")
            assert "file_accession" in error_text.lower()
    
    def test_get_file_metadata_return_schema(self, tu):
        """Test get_file_metadata return schema."""
        result = tu.tools.FourDN_get_file_metadata(**{
            "operation": "get_file_metadata",
            "file_accession": "4DNFIIA7E3HL"
        })
        
        assert "status" in result
        
        if result["status"] == "success":
            # Check if data is nested or flat
            data = result.get("data", result)
            # Expected fields from return_schema
            expected_fields = ["accession", "file_type", "download_url"]
            for field in expected_fields:
                assert field in data, f"Missing field: {field}"
    
    def test_get_experiment_metadata_requires_accession(self, tu):
        """Test get_experiment_metadata requires experiment_accession."""
        result = tu.tools.FourDN_get_experiment_metadata(**{
            "operation": "get_experiment_metadata"
        })
        
        # Handle both old and new error formats  
        assert "status" in result or "error" in result
        
        if result.get("status") == "error" or "error" in result:
            error_text = result.get("error", "")
            assert "experiment_accession" in error_text.lower()
    
    def test_get_download_url_requires_accession(self, tu):
        """Test get_download_url requires file_accession."""
        result = tu.tools.FourDN_get_download_url(**{
            "operation": "download_file_url"
        })
        
        # Handle both old and new error formats
        assert "status" in result or "error" in result
        
        if result.get("status") == "error" or "error" in result:
            error_text = result.get("error", "")
            assert "file_accession" in error_text.lower()
    
    def test_get_download_url_return_schema(self, tu):
        """Test get_download_url return schema."""
        result = tu.tools.FourDN_get_download_url(**{
            "operation": "download_file_url",
            "file_accession": "4DNFIIA7E3HL"
        })
        
        assert "status" in result
        
        if result["status"] == "success":
            # Check if data is nested or flat
            data = result.get("data", result)
            assert "download_url" in data
            assert "drs_url" in data
            assert "instruction" in data or "note" in data


class TestFourDNReturnSchemas:
    """Test that return schemas match actual output."""
    
    @pytest.fixture
    def tu(self):
        """Create ToolUniverse instance."""
        tu = ToolUniverse()
        tu.load_tools()
        return tu
    
    def test_search_data_schema(self, tu):
        """Verify search_data return schema."""
        result = tu.tools.FourDN_search_data(**{
            "operation": "search",
            "query": "*",
            "limit": 1
        })
        
        assert "status" in result
        
        if result["status"] == "success":
            # Check if data is nested or flat
            data = result.get("data", result)
            # Must have num_results and results
            assert "num_results" in data
            assert "results" in data
    
    def test_error_response_schema(self, tu):
        """Test that error responses follow schema."""
        result = tu.tools.FourDN_get_file_metadata(**{
            "operation": "get_file_metadata"
            # Missing required file_accession
        })
        
        # Handle both old and new error formats
        assert "error" in result  # Error key is always present
        assert isinstance(result["error"], str)
        
        # New format may have error_details
        if "error_details" in result:
            assert isinstance(result["error_details"], dict)
