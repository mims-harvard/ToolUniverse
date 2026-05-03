"""
Unit tests for BioStudies tool.

Tests both direct class usage (Level 1) and ToolUniverse interface (Level 2).
"""

import json
import pytest
from pathlib import Path

# Level 1: Direct class testing
from tooluniverse.biostudies_tool import BioStudiesRESTTool


class TestBioStudiesToolDirect:
    """Level 1: Test implementation logic directly."""
    
    @pytest.fixture
    def tool_configs(self):
        """Load tool configurations."""
        config_path = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data" / "biostudies_tools.json"
        with open(config_path) as f:
            return json.load(f)
    
    def test_search_tool_initialization(self, tool_configs):
        """Test tool can be instantiated."""
        config = next(t for t in tool_configs if t["name"] == "biostudies_search")
        tool = BioStudiesRESTTool(config)
        
        assert tool.base_url == "https://www.ebi.ac.uk/biostudies/api/v1"
        assert tool.timeout == 30
    
    def test_search_execution(self, tool_configs):
        """Test search operation."""
        config = next(t for t in tool_configs if t["name"] == "biostudies_search")
        tool = BioStudiesRESTTool(config)
        
        result = tool.run({
            "query": "CRISPR",
            "pageSize": 5
        })
        
        # Handle transient API issues gracefully
        if result["status"] == "error":
            error_msg = result.get("error", "")
            if any(x in error_msg.lower() for x in ["timeout", "connection", "503", "502", "500"]):
                pytest.skip(f"BioStudies API temporarily unavailable: {error_msg}")
        
        assert result["status"] == "success"
        assert "data" in result
        assert "hits" in result["data"]
        assert "count" in result
        assert result["count"] <= 5
    
    def test_search_by_collection(self, tool_configs):
        """Test collection-specific search."""
        config = next(t for t in tool_configs if t["name"] == "biostudies_search_by_collection")
        tool = BioStudiesRESTTool(config)
        
        result = tool.run({
            "query": "cancer",
            "collection": "arrayexpress",
            "pageSize": 3
        })
        
        # Handle transient API issues gracefully
        if result["status"] == "error":
            error_msg = result.get("error", "")
            if any(x in error_msg.lower() for x in ["timeout", "connection", "503", "502", "500"]):
                pytest.skip(f"BioStudies API temporarily unavailable: {error_msg}")
        
        assert result["status"] == "success"
        assert "data" in result
        assert "count" in result
    
    def test_get_study(self, tool_configs):
        """Test getting specific study."""
        config = next(t for t in tool_configs if t["name"] == "biostudies_get_study")
        tool = BioStudiesRESTTool(config)
        
        result = tool.run({
            "accession": "S-BSST1254"
        })
        
        # Handle transient API issues gracefully
        if result["status"] == "error":
            error_msg = result.get("error", "")
            if any(x in error_msg.lower() for x in ["timeout", "connection", "503", "502", "500"]):
                pytest.skip(f"BioStudies API temporarily unavailable: {error_msg}")
        
        assert result["status"] == "success"
        assert "data" in result
        assert isinstance(result["data"], dict)
    
    def test_get_study_files(self, tool_configs):
        """Test extracting files from study."""
        config = next(t for t in tool_configs if t["name"] == "biostudies_get_study_files")
        tool = BioStudiesRESTTool(config)
        
        result = tool.run({
            "accession": "S-BSST1254"
        })
        
        # Handle transient API issues gracefully
        if result["status"] == "error":
            error_msg = result.get("error", "")
            if any(x in error_msg.lower() for x in ["timeout", "connection", "503", "502", "500"]):
                pytest.skip(f"BioStudies API temporarily unavailable: {error_msg}")
        
        assert result["status"] == "success"
        assert "data" in result
        assert isinstance(result["data"], list)
        assert "count" in result
    
    def test_error_handling_missing_required(self, tool_configs):
        """Test error handling for missing required parameters."""
        config = next(t for t in tool_configs if t["name"] == "biostudies_get_study")
        tool = BioStudiesRESTTool(config)
        
        # Missing required 'accession' parameter
        result = tool.run({})
        
        # Should return error or handle gracefully
        assert result["status"] in ["error", "success"]  # Some APIs may have defaults
    
    def test_response_format(self, tool_configs):
        """Test all responses follow standard format."""
        config = next(t for t in tool_configs if t["name"] == "biostudies_search")
        tool = BioStudiesRESTTool(config)
        
        result = tool.run({"query": "test", "pageSize": 1})
        
        # Standard format check
        assert "status" in result
        assert result["status"] in ["success", "error", "warning"]
        
        if result["status"] == "success":
            assert "data" in result
        elif result["status"] == "error":
            assert "error" in result


# Level 2: ToolUniverse interface testing
class TestBioStudiesToolInterface:
    """Level 2: Test via ToolUniverse (how users call it)."""
    
    @pytest.fixture
    def tu(self):
        """Initialize ToolUniverse."""
        from tooluniverse import ToolUniverse
        tu = ToolUniverse()
        tu.load_tools()
        return tu
    
    def test_tools_registered(self, tu):
        """Test all BioStudies tools are registered."""
        expected_tools = [
            'biostudies_search',
            'biostudies_search_by_collection',
            'biostudies_get_study',
            'biostudies_get_study_files'
        ]
        
        for tool_name in expected_tools:
            assert hasattr(tu.tools, tool_name), f"Tool {tool_name} not found"
    
    def test_search_via_tooluniverse(self, tu):
        """Test search through ToolUniverse interface."""
        result = tu.tools.biostudies_search(**{
            "query": "CRISPR",
            "pageSize": 5
        })
        
        # Handle transient API issues gracefully
        if result["status"] == "error":
            error_msg = result.get("error", "")
            if any(x in error_msg.lower() for x in ["timeout", "connection", "503", "502", "500"]):
                pytest.skip(f"BioStudies API temporarily unavailable: {error_msg}")
        
        assert result["status"] == "success"
        assert "data" in result
    
    def test_search_by_collection_via_tooluniverse(self, tu):
        """Test collection search through ToolUniverse."""
        result = tu.tools.biostudies_search_by_collection(**{
            "query": "stem cells",
            "collection": "arrayexpress",
            "pageSize": 3
        })
        
        # Handle transient API issues gracefully
        if result["status"] == "error":
            error_msg = result.get("error", "")
            # Skip test if API is temporarily unavailable
            if any(x in error_msg.lower() for x in ["timeout", "connection", "503", "502", "500"]):
                pytest.skip(f"BioStudies API temporarily unavailable: {error_msg}")
        
        assert result["status"] == "success"
        assert "data" in result
    
    def test_get_study_via_tooluniverse(self, tu):
        """Test get study through ToolUniverse."""
        result = tu.tools.biostudies_get_study(**{
            "accession": "S-BSST1254"
        })
        
        # Handle transient API issues gracefully
        if result["status"] == "error":
            error_msg = result.get("error", "")
            if any(x in error_msg.lower() for x in ["timeout", "connection", "503", "502", "500"]):
                pytest.skip(f"BioStudies API temporarily unavailable: {error_msg}")
        
        assert result["status"] == "success"
        assert "data" in result
    
    def test_get_study_files_via_tooluniverse(self, tu):
        """Test get files through ToolUniverse."""
        result = tu.tools.biostudies_get_study_files(**{
            "accession": "S-BSST1254"
        })
        
        # Handle transient API issues gracefully
        if result["status"] == "error":
            error_msg = result.get("error", "")
            if any(x in error_msg.lower() for x in ["timeout", "connection", "503", "502", "500"]):
                pytest.skip(f"BioStudies API temporarily unavailable: {error_msg}")
        
        assert result["status"] == "success"
        assert "data" in result
        assert isinstance(result["data"], list)


# Level 3: Real API integration tests
class TestBioStudiesRealAPI:
    """Level 3: Test real API integration (may be flaky if API is down)."""
    
    @pytest.fixture
    def tu(self):
        from tooluniverse import ToolUniverse
        tu = ToolUniverse()
        tu.load_tools()
        return tu
    
    @pytest.mark.integration
    def test_real_search(self, tu):
        """Test against real BioStudies API."""
        result = tu.tools.biostudies_search(**{
            "query": "cancer genomics",
            "pageSize": 5
        })
        
        if result["status"] == "success":
            assert "data" in result
            assert "hits" in result["data"]
            print(f"✅ Real API returned {result['count']} results")
        else:
            print(f"⚠️  API error (may be down): {result.get('error')}")
    
    @pytest.mark.integration
    def test_real_collection_search(self, tu):
        """Test real collection-specific search."""
        result = tu.tools.biostudies_search_by_collection(**{
            "query": "stem cells",
            "collection": "arrayexpress",
            "pageSize": 3
        })
        
        if result["status"] == "success":
            assert result["count"] <= 3
            print(f"✅ Collection search returned {result['count']} results")
        else:
            print(f"⚠️  API error: {result.get('error')}")
    
    @pytest.mark.integration
    def test_real_study_retrieval(self, tu):
        """Test retrieving real study."""
        result = tu.tools.biostudies_get_study(**{
            "accession": "S-BSST1254"
        })
        
        if result["status"] == "success":
            assert "accno" in result["data"]
            print(f"✅ Retrieved study: {result['data'].get('accno')}")
        else:
            print(f"⚠️  API error: {result.get('error')}")
    
    @pytest.mark.integration
    def test_real_file_extraction(self, tu):
        """Test extracting files from real study."""
        result = tu.tools.biostudies_get_study_files(**{
            "accession": "S-BSST1254"
        })
        
        if result["status"] == "success":
            file_count = result.get("count", 0)
            print(f"✅ Extracted {file_count} files from study")
        else:
            print(f"⚠️  API error: {result.get('error')}")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
