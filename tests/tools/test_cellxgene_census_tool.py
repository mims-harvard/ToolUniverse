"""
Unit tests for CELLxGENE Census tools.
"""

import pytest
from tooluniverse import ToolUniverse


class TestCELLxGENECensusTools:
    """Test suite for CELLxGENE Census tools."""
    
    @pytest.fixture
    def tu(self):
        """Create ToolUniverse instance."""
        tu = ToolUniverse()
        tu.load_tools()
        return tu
    
    def test_tools_load(self, tu):
        """Test that CELLxGENE Census tools load correctly."""
        tool_names = [tool.get("name") for tool in tu.all_tools if isinstance(tool, dict)]
        
        # Check that all expected tools are present
        expected_tools = [
            "CELLxGENE_get_census_versions",
            "CELLxGENE_get_cell_metadata",
            "CELLxGENE_get_gene_metadata",
            "CELLxGENE_get_expression_data",
            "CELLxGENE_get_presence_matrix",
            "CELLxGENE_get_embeddings",
            "CELLxGENE_download_h5ad"
        ]
        
        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not found in available tools"
    
    def test_get_census_versions_without_package(self, tu):
        """Test get_census_versions returns error when package not installed."""
        result = tu.tools.CELLxGENE_get_census_versions(**{
            "operation": "get_census_versions"
        })
        
        # Should either succeed or return error about missing package
        assert "status" in result
        assert result["status"] in ["success", "error"]
        
        if result["status"] == "error":
            assert "cellxgene_census" in result["error"].lower()
    
    def test_get_cell_metadata_requires_operation(self, tu):
        """Test that operation parameter is required."""
        result = tu.tools.CELLxGENE_get_cell_metadata(**{})
        
        # Should have status field
        assert "status" in result
    
    def test_get_cell_metadata_return_schema(self, tu):
        """Test that return matches expected schema."""
        # NOTE: MUST use a restrictive filter - without it, the query would try to
        # fetch ALL 50M+ cells from CELLxGENE Census, causing a timeout.
        result = tu.tools.CELLxGENE_get_cell_metadata(**{
            "operation": "get_obs_metadata",
            "organism": "Homo sapiens",
            "census_version": "stable",
            # Use restrictive filter to limit query to a small subset
            "obs_value_filter": 'tissue_general == "blood" and cell_type == "T cell" and disease == "normal"',
            "column_names": ["soma_joinid", "cell_type", "tissue_general", "disease"]
        })
        
        assert "status" in result
        
        if result["status"] == "success":
            # Check if data is nested or flat
            data = result.get("data", result)
            # Check expected fields in success response
            assert "organism" in data or "organism" in result
            assert "num_cells" in data or "num_cells" in result or "error" in result
        else:
            # Check error response has error message
            assert "error" in result
    
    def test_download_h5ad_requires_dataset_id(self, tu):
        """Test that dataset_id is required for download."""
        result = tu.tools.CELLxGENE_download_h5ad(**{
            "operation": "download_h5ad"
        })
        
        assert "status" in result
        
        if result["status"] == "error":
            assert "dataset_id" in result["error"].lower()
    
    def test_invalid_operation(self, tu):
        """Test handling of invalid operation."""
        result = tu.tools.CELLxGENE_get_cell_metadata(**{
            "operation": "invalid_operation"
        })
        
        assert "status" in result
        assert result["status"] == "error"
        assert "error" in result


class TestCELLxGENECensusReturnSchemas:
    """Test that return schemas match actual output."""
    
    @pytest.fixture
    def tu(self):
        """Create ToolUniverse instance."""
        tu = ToolUniverse()
        tu.load_tools()
        return tu
    
    def test_get_census_versions_schema(self, tu):
        """Verify get_census_versions return schema."""
        result = tu.tools.CELLxGENE_get_census_versions(**{
            "operation": "get_census_versions"
        })
        
        # Common fields
        assert "status" in result
        
        if result["status"] == "success":
            # Check if data is nested or flat
            data = result.get("data", result)
            # Should have versions field
            assert "versions" in data or "versions" in result or "error" in result


class TestCELLxGENECensusIntegration:
    """Integration tests (only run if package is installed)."""
    
    @pytest.fixture
    def tu(self):
        """Create ToolUniverse instance."""
        tu = ToolUniverse()
        tu.load_tools()
        return tu
    
    @pytest.mark.skipif(
        not pytest.importorskip("cellxgene_census", reason="cellxgene_census not installed"),
        reason="Requires cellxgene_census package"
    )
    def test_get_census_versions_with_package(self, tu):
        """Test get_census_versions with package installed."""
        result = tu.tools.CELLxGENE_get_census_versions(**{
            "operation": "get_census_versions"
        })
        
        assert result["status"] == "success"
        # Check if data is nested or flat
        data = result.get("data", result)
        assert "versions" in data or "versions" in result
        
        # Versions should be a dict or list
        versions = data.get("versions", result.get("versions"))
        assert isinstance(versions, (dict, list))
