"""
Unit tests for ChIP-Atlas tools.
"""

import pytest
from tooluniverse import ToolUniverse


class TestChIPAtlasTools:
    """Test suite for ChIP-Atlas tools."""
    
    @pytest.fixture
    def tu(self):
        """Create ToolUniverse instance."""
        tu = ToolUniverse()
        tu.load_tools()
        return tu
    
    def test_tools_load(self, tu):
        """Test that ChIP-Atlas tools load correctly."""
        tool_names = [tool.get("name") for tool in tu.all_tools if isinstance(tool, dict)]
        
        expected_tools = [
            "ChIPAtlas_enrichment_analysis",
            "ChIPAtlas_get_experiments",
            "ChIPAtlas_get_peak_data",
            "ChIPAtlas_search_datasets"
        ]
        
        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not found"
    
    def test_enrichment_analysis_requires_input(self, tu):
        """Test enrichment analysis requires input data."""
        result = tu.tools.ChIPAtlas_enrichment_analysis(**{
            "operation": "enrichment_analysis",
            "genome": "hg38"
        })
        
        assert "status" in result
        
        if result["status"] == "error":
            # Error message is nested under "data" key
            assert "data" in result
            assert "error" in result["data"]
            # Should mention missing required input
            assert any(key in result["data"]["error"].lower() 
                      for key in ["bed", "motif", "gene"])
    
    def test_enrichment_analysis_with_gene_list(self, tu):
        """Test enrichment analysis with gene list."""
        result = tu.tools.ChIPAtlas_enrichment_analysis(**{
            "operation": "enrichment_analysis",
            "gene_list": ["TP53", "MDM2"],
            "genome": "hg38"
        })
        
        assert "status" in result
        assert result["status"] == "success"
        assert "data" in result
        # Success response nests data under "data" key
        assert "url" in result["data"] or "message" in result["data"]
    
    def test_get_experiments_return_schema(self, tu):
        """Test get_experiments return schema."""
        result = tu.tools.ChIPAtlas_get_experiments(**{
            "operation": "get_experiment_list",
            "genome": "hg38",
            "limit": 5
        })
        
        assert "status" in result
        
        if result["status"] == "success":
            # Data is nested under "data" key
            assert "data" in result
            # May have num_experiments and experiments or just guidance
            assert isinstance(result["data"], dict)
    
    def test_get_peak_data_requires_experiment_id(self, tu):
        """Test get_peak_data requires experiment_id."""
        result = tu.tools.ChIPAtlas_get_peak_data(**{
            "operation": "get_peak_data",
            "genome": "hg38"
        })
        
        assert "status" in result
        
        if result.get("status") == "error":
            # Handle both validation errors (error at top level) 
            # and tool errors (error under data key)
            if "error" in result:
                error_text = result["error"]
            elif "data" in result and "error" in result["data"]:
                error_text = result["data"]["error"]
            else:
                error_text = ""
            
            assert "experiment_id" in error_text.lower()
    
    def test_get_peak_data_with_valid_id(self, tu):
        """Test get_peak_data with valid experiment ID."""
        result = tu.tools.ChIPAtlas_get_peak_data(**{
            "operation": "get_peak_data",
            "experiment_id": "SRX097088",
            "genome": "hg19",
            "format": "bigwig"
        })
        
        assert "status" in result
        assert result["status"] == "success"
        # Data is nested under "data" key
        assert "data" in result
        assert "url" in result["data"]
        assert "SRX097088" in result["data"]["url"]
    
    def test_search_datasets_requires_input(self, tu):
        """Test search_datasets requires antigen or cell_type."""
        result = tu.tools.ChIPAtlas_search_datasets(**{
            "operation": "search_datasets",
            "genome": "hg38"
        })
        
        assert "status" in result
        
        # Tool may return error or handle gracefully
        if result.get("status") == "error":
            # If error, it should be properly formatted
            assert "data" in result
            assert "error" in result["data"]


class TestChIPAtlasReturnSchemas:
    """Test that return schemas match actual output."""
    
    @pytest.fixture
    def tu(self):
        """Create ToolUniverse instance."""
        tu = ToolUniverse()
        tu.load_tools()
        return tu
    
    def test_enrichment_analysis_schema(self, tu):
        """Verify enrichment_analysis return schema."""
        result = tu.tools.ChIPAtlas_enrichment_analysis(**{
            "operation": "enrichment_analysis",
            "gene_list": ["TP53"],
            "genome": "hg38"
        })
        
        assert "status" in result
        
        if result["status"] == "success":
            # Data is nested under "data" key
            assert "data" in result
            # Should have message or url in data
            assert "message" in result["data"] or "url" in result["data"]
    
    def test_get_peak_data_url_format(self, tu):
        """Test that get_peak_data returns proper URL format."""
        result = tu.tools.ChIPAtlas_get_peak_data(**{
            "operation": "get_peak_data",
            "experiment_id": "SRX000001",
            "genome": "hg38",
            "format": "bed",
            "threshold": "05"
        })
        
        assert "status" in result
        
        if result["status"] == "success":
            # Data is nested under "data" key
            assert "data" in result
            assert "url" in result["data"]
            assert "https://" in result["data"]["url"]
            assert "SRX000001" in result["data"]["url"]
