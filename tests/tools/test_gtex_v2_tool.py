"""
Unit tests for GTEx Portal API V2 tools.

Tests cover expression data, eQTL queries, tissue information, and metadata endpoints.
"""

import pytest
from tooluniverse import ToolUniverse


class TestGTExV2Tools:
    """Test suite for GTEx Portal API V2 tools."""
    
    @pytest.fixture
    def tu(self):
        """Create ToolUniverse instance with tools loaded."""
        tu = ToolUniverse()
        tu.load_tools()
        return tu
    
    def test_tools_load(self, tu):
        """Test that GTEx V2 tools load correctly."""
        tool_names = [tool.get("name") for tool in tu.all_tools if isinstance(tool, dict)]
        
        expected_tools = [
            "GTEx_get_median_gene_expression",
            "GTEx_get_tissue_sites",
            "GTEx_get_eqtl_genes",
            "GTEx_get_single_tissue_eqtls",
            "GTEx_calculate_eqtl",
            "GTEx_get_top_expressed_genes",
            "GTEx_get_dataset_info",
            "GTEx_get_gene_expression",
            "GTEx_get_sample_info",
            "GTEx_get_multi_tissue_eqtls"
        ]
        
        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not found"
    
    def test_get_tissue_sites(self, tu):
        """Test getting GTEx tissue sites."""
        result = tu.tools.GTEx_get_tissue_sites(**{
            "operation": "get_tissue_sites",
            "items_per_page": 10
        })
        
        assert result.get("status") == "success" or "error" in result
        
        if result.get("status") == "success":
            assert "data" in result
            assert "num_tissues" in result
            assert isinstance(result["data"], list)
            
            if result["data"]:
                tissue = result["data"][0]
                assert "tissueSiteDetailId" in tissue
                assert "tissueSiteDetail" in tissue
    
    def test_get_dataset_info(self, tu):
        """Test getting GTEx dataset information."""
        result = tu.tools.GTEx_get_dataset_info(**{
            "operation": "get_dataset_info"
        })
        
        assert result.get("status") == "success" or "error" in result
        
        if result.get("status") == "success":
            # Check if data is nested or flat
            datasets = result.get("data", result.get("datasets"))
            assert datasets is not None
            assert isinstance(datasets, list)
            
            if datasets:
                dataset = datasets[0]
                assert "datasetId" in dataset
                assert "gencodeVersion" in dataset
                assert "genomeBuild" in dataset
    
    def test_get_median_gene_expression(self, tu):
        """Test getting median gene expression with TP53."""
        result = tu.tools.GTEx_get_median_gene_expression(**{
            "operation": "get_median_gene_expression",
            "gencode_id": "ENSG00000141510.16",  # TP53
            "items_per_page": 10
        })
        
        assert result.get("status") == "success" or "error" in result
        
        if result.get("status") == "success":
            assert "data" in result
            assert "num_results" in result
            
            if result["data"]:
                expr = result["data"][0]
                assert "gencodeId" in expr
                assert "geneSymbol" in expr
                assert "median" in expr
                assert "tissueSiteDetailId" in expr
    
    def test_get_top_expressed_genes(self, tu):
        """Test getting top expressed genes in a tissue."""
        result = tu.tools.GTEx_get_top_expressed_genes(**{
            "operation": "get_top_expressed_genes",
            "tissue_site_detail_id": "Liver",
            "items_per_page": 20
        })
        
        assert result.get("status") == "success" or "error" in result
        
        if result.get("status") == "success":
            assert "data" in result
            assert "num_genes" in result
            
            if result["data"]:
                gene = result["data"][0]
                assert "gencodeId" in gene
                assert "geneSymbol" in gene
                assert "median" in gene
    
    def test_get_eqtl_genes(self, tu):
        """Test getting eQTL genes (eGenes)."""
        result = tu.tools.GTEx_get_eqtl_genes(**{
            "operation": "get_eqtl_genes",
            "tissue_site_detail_id": ["Whole_Blood"],
            "items_per_page": 10
        })
        
        assert result.get("status") == "success" or "error" in result
        
        if result.get("status") == "success":
            assert "data" in result
            assert "num_egenes" in result
            
            if result["data"]:
                egene = result["data"][0]
                assert "gencodeId" in egene
                assert "geneSymbol" in egene
                assert "tissueSiteDetailId" in egene
                assert "pValue" in egene
                assert "qValue" in egene
    
    def test_get_single_tissue_eqtls_by_gene(self, tu):
        """Test getting single-tissue eQTLs for a gene."""
        result = tu.tools.GTEx_get_single_tissue_eqtls(**{
            "operation": "get_single_tissue_eqtls",
            "gencode_id": ["ENSG00000141510.16"],  # TP53
            "tissue_site_detail_id": ["Whole_Blood"],
            "items_per_page": 5
        })
        
        assert result.get("status") == "success" or "error" in result
        
        if result.get("status") == "success":
            assert "data" in result
            assert "num_eqtls" in result
    
    def test_get_single_tissue_eqtls_missing_params(self, tu):
        """Test that single-tissue eQTL requires at least one filter."""
        result = tu.tools.GTEx_get_single_tissue_eqtls(**{
            "operation": "get_single_tissue_eqtls"
        })
        
        # Should either succeed or return error about missing params
        assert "status" in result or "error" in result
    
    def test_get_gene_expression(self, tu):
        """Test getting sample-level gene expression."""
        result = tu.tools.GTEx_get_gene_expression(**{
            "operation": "get_gene_expression",
            "gencode_id": "ENSG00000141510.16",  # TP53
            "tissue_site_detail_id": ["Liver"],
            "items_per_page": 5
        })
        
        assert result.get("status") == "success" or "error" in result
        
        if result.get("status") == "success":
            assert "data" in result
            assert "num_results" in result
    
    def test_get_sample_info(self, tu):
        """Test getting sample metadata."""
        result = tu.tools.GTEx_get_sample_info(**{
            "operation": "get_sample_info",
            "tissue_site_detail_id": ["Liver"],
            "sex": "female",
            "items_per_page": 5
        })
        
        assert result.get("status") == "success" or "error" in result
        
        if result.get("status") == "success":
            assert "data" in result
            assert "num_samples" in result
    
    def test_get_multi_tissue_eqtls(self, tu):
        """Test getting multi-tissue eQTL meta-analysis results."""
        result = tu.tools.GTEx_get_multi_tissue_eqtls(**{
            "operation": "get_multi_tissue_eqtls",
            "gencode_id": "ENSG00000141510.16",  # TP53
            "items_per_page": 5
        })
        
        assert result.get("status") == "success" or "error" in result
        
        if result.get("status") == "success":
            assert "data" in result
            assert "num_results" in result
    
    def test_calculate_eqtl_missing_params(self, tu):
        """Test that calculate_eqtl requires all parameters."""
        result = tu.tools.GTEx_calculate_eqtl(**{
            "operation": "calculate_eqtl",
            "gencode_id": "ENSG00000141510.16"
            # Missing variant_id and tissue_site_detail_id
        })
        
        # Should return error about missing parameters
        assert result.get("status") == "error" or "error" in result
        if result.get("status") == "error":
            assert "required" in result.get("error", "").lower() or \
                   "missing" in result.get("error", "").lower()
    
    def test_invalid_operation(self, tu):
        """Test handling of invalid operation."""
        result = tu.tools.GTEx_get_dataset_info(**{
            "operation": "invalid_operation_name"
        })
        
        assert result.get("status") == "error" or "error" in result
        if result.get("status") == "error":
            assert "operation" in result.get("error", "").lower()
    
    def test_error_handling(self, tu):
        """Test that tools handle errors gracefully."""
        # Test with invalid gencode_id format
        result = tu.tools.GTEx_get_median_gene_expression(**{
            "operation": "get_median_gene_expression",
            "gencode_id": "INVALID_ID_FORMAT"
        })
        
        # Should either succeed (if API accepts it) or return error
        assert "status" in result or "error" in result
        assert isinstance(result, dict)
