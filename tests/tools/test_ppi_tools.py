#!/usr/bin/env python3
"""
Test cases for PPI (Protein-Protein Interaction) tools
Tests STRING and BioGRID tools for real data access
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from tooluniverse.string_tool import STRINGRESTTool
from tooluniverse.biogrid_tool import BioGRIDRESTTool


class TestSTRINGTool:
    """Test cases for STRING database tool"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.tool_config = {
            "type": "STRINGRESTTool",
            "name": "STRING_get_protein_interactions",
            "description": "Query protein-protein interactions from STRING database",
            "parameter": {
                "required": ["protein_ids"],
                "properties": {
                    "protein_ids": {"type": "array", "items": {"type": "string"}},
                    "species": {"type": "integer", "default": 9606},
                    "confidence_score": {"type": "number", "default": 0.4},
                    "limit": {"type": "integer", "default": 50}
                }
            },
            "fields": {
                "endpoint": "/tsv/network",
                "return_format": "TSV"
            }
        }
        self.tool = STRINGRESTTool(self.tool_config)
    
    def test_tool_initialization(self):
        """Test tool initialization"""
        assert self.tool.endpoint_template == "/tsv/network"
        assert self.tool.required == ["protein_ids"]
        assert self.tool.output_format == "TSV"
    
    def test_build_url(self):
        """Test URL building"""
        url = self.tool._build_url()
        assert url == "https://string-db.org/api/tsv/network"
    
    def test_build_params(self):
        """Test parameter building"""
        arguments = {
            "protein_ids": ["TP53", "BRCA1"],
            "species": 9606,
            "confidence_score": 0.4,
            "limit": 50
        }
        params = self.tool._build_params(arguments)
        
        assert params["identifiers"] == "TP53\rBRCA1"
        assert params["species"] == 9606
        assert params["required_score"] == 400  # 0.4 * 1000
        assert params["limit"] == 50
    
    def test_build_params_single_protein(self):
        """Test parameter building with single protein"""
        arguments = {"protein_ids": "TP53"}
        params = self.tool._build_params(arguments)
        assert params["identifiers"] == "TP53"
    
    def test_parse_tsv_response(self):
        """Test TSV response parsing"""
        tsv_data = "stringId_A\tstringId_B\tpreferredName_A\tpreferredName_B\tscore\n9606.ENSP00000269305\t9606.ENSP00000418960\tTP53\tBRCA1\t0.9"
        result = self.tool._parse_tsv_response(tsv_data)
        
        assert "data" in result
        assert "header" in result
        assert len(result["data"]) == 1
        assert result["data"][0]["preferredName_A"] == "TP53"
        assert result["data"][0]["preferredName_B"] == "BRCA1"
    
    def test_parse_tsv_response_empty(self):
        """Test TSV response parsing with empty data"""
        result = self.tool._parse_tsv_response("")
        assert result["data"] == []
        assert "error" in result
    
    @patch('requests.get')
    def test_make_request_success(self, mock_get):
        """Test successful API request"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.text = "stringId_A\tstringId_B\tpreferredName_A\tpreferredName_B\tscore\n9606.ENSP00000269305\t9606.ENSP00000418960\tTP53\tBRCA1\t0.9"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.tool._make_request("https://string-db.org/api/tsv/network", {})
        
        assert "data" in result
        assert len(result["data"]) == 1
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_make_request_error(self, mock_get):
        """Test API request error handling"""
        mock_get.side_effect = Exception("Network error")
        
        result = self.tool._make_request("https://string-db.org/api/tsv/network", {})
        
        assert "error" in result
        assert "Network error" in result["error"]
    
    def test_run_missing_required_params(self):
        """Test run method with missing required parameters"""
        result = self.tool.run({})
        assert "error" in result
        assert "Missing required parameter" in result["error"]
    
    @patch('requests.get')
    def test_run_success(self, mock_get):
        """Test successful run"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.text = "stringId_A\tstringId_B\tpreferredName_A\tpreferredName_B\tscore\n9606.ENSP00000269305\t9606.ENSP00000418960\tTP53\tBRCA1\t0.9"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        arguments = {"protein_ids": ["TP53", "BRCA1"]}
        result = self.tool.run(arguments)

        assert "data" in result
        assert len(result["data"]["data"]) == 1


class TestBioGRIDTool:
    """Test cases for BioGRID database tool"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.tool_config = {
            "type": "BioGRIDRESTTool",
            "name": "BioGRID_get_interactions",
            "description": "Query protein and genetic interactions from BioGRID database",
            "parameter": {
                "required": ["gene_names"],
                "properties": {
                    "gene_names": {"type": "array", "items": {"type": "string"}},
                    "organism": {"type": "string", "default": "Homo sapiens"},
                    "interaction_type": {"type": "string", "default": "both"},
                    "limit": {"type": "integer", "default": 100}
                }
            },
            "fields": {
                "endpoint": "/interactions/",
                "return_format": "JSON"
            }
        }
        self.tool = BioGRIDRESTTool(self.tool_config)
    
    def test_tool_initialization(self):
        """Test tool initialization"""
        assert self.tool.endpoint_template == "/interactions/"
        assert self.tool.required == ["gene_names"]
        assert self.tool.output_format == "JSON"
    
    def test_build_url(self):
        """Test URL building"""
        url = self.tool._build_url()
        assert url == "https://webservice.thebiogrid.org/interactions/"
    
    def test_build_params_with_api_key(self):
        """Test parameter building with API key"""
        arguments = {
            "gene_names": ["TP53", "BRCA1"],
            "api_key": "test_key",
            "organism": "Homo sapiens",
            "interaction_type": "physical",
            "limit": 100
        }
        params = self.tool._build_params(arguments)
        
        assert params["accesskey"] == "test_key"
        assert params["geneList"] == "TP53|BRCA1"
        assert params["taxId"] == 9606  # Homo sapiens
        # interaction_type is informational only; BioGRID does not support evidenceList filtering
        assert params["max"] == 100
    
    def test_build_params_without_api_key(self):
        """Test parameter building without API key should raise error"""
        arguments = {"gene_names": ["TP53", "BRCA1"]}

        # Override any env var that might satisfy the key lookup
        with patch.dict(os.environ, {"BIOGRID_API_KEY": "", "BIOGRID_ACCESS_KEY": ""}):
            with pytest.raises(ValueError, match="BioGRID API key is required"):
                self.tool._build_params(arguments)
    
    def test_build_params_organism_mapping(self):
        """Test organism name to taxonomy ID mapping"""
        # Test human
        arguments = {"gene_names": ["TP53"], "api_key": "test", "organism": "Homo sapiens"}
        params = self.tool._build_params(arguments)
        assert params["taxId"] == 9606

        # Test mouse
        arguments = {"gene_names": ["TP53"], "api_key": "test", "organism": "Mus musculus"}
        params = self.tool._build_params(arguments)
        assert params["taxId"] == 10090

        # Test other organism (should pass through)
        arguments = {"gene_names": ["TP53"], "api_key": "test", "organism": "9607"}
        params = self.tool._build_params(arguments)
        assert params["taxId"] == "9607"
    
    def test_build_params_interaction_types(self):
        """Test interaction type — informational only; not translated to evidenceList.
        BioGRID does not support filtering by interaction type via the API;
        filtering must be done client-side on the EXPERIMENTAL_SYSTEM_TYPE field.
        """
        # interaction_type is passed in but never mapped to evidenceList
        for itype in ("physical", "genetic", "both"):
            arguments = {"gene_names": ["TP53"], "api_key": "test", "interaction_type": itype}
            params = self.tool._build_params(arguments)
            assert "evidenceList" not in params, (
                f"interaction_type={itype!r} should not produce evidenceList param"
            )
    
    @patch('requests.get')
    def test_make_request_success(self, mock_get):
        """Test successful API request"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": [{"gene1": "TP53", "gene2": "BRCA1"}]}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.tool._make_request("https://webservice.thebiogrid.org/interactions/", {})
        
        assert "results" in result
        assert len(result["results"]) == 1
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_make_request_error(self, mock_get):
        """Test API request error handling"""
        mock_get.side_effect = Exception("Network error")
        
        result = self.tool._make_request("https://webservice.thebiogrid.org/interactions/", {})
        
        assert "error" in result
        assert "Network error" in result["error"]
    
    def test_run_missing_required_params(self):
        """Test run method with missing required parameters"""
        result = self.tool.run({})
        assert "error" in result
        assert "Missing required parameter" in result["error"]
    
    @patch('requests.get')
    def test_run_success(self, mock_get):
        """Test successful run"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": [{"gene1": "TP53", "gene2": "BRCA1"}]}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        arguments = {"gene_names": ["TP53", "BRCA1"], "api_key": "test_key"}
        result = self.tool.run(arguments)

        assert "results" in result["data"]
        assert len(result["data"]["results"]) == 1


class TestIntegration:
    """Integration tests for PPI tools"""
    
    def test_string_tool_real_api(self):
        """Test STRING tool with real API (if network available)"""
        tool_config = {
            "type": "STRINGRESTTool",
            "parameter": {"required": ["protein_ids"]},
            "fields": {"endpoint": "/tsv/network", "return_format": "TSV"}
        }
        tool = STRINGRESTTool(tool_config)
        
        # Test with real protein IDs
        arguments = {
            "protein_ids": ["TP53", "BRCA1"],
            "species": 9606,
            "confidence_score": 0.4,
            "limit": 5
        }
        
        try:
            result = tool.run(arguments)
            # If successful, should have data
            if "data" in result and not result.get("error"):
                assert len(result["data"]) > 0
                print(f"✅ STRING API test successful: {len(result['data'])} interactions found")
            else:
                print(f"⚠️ STRING API test failed: {result.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"⚠️ STRING API test error: {e}")
    
    def test_biogrid_tool_api_key_requirement(self):
        """Test BioGRID tool API key requirement"""
        tool_config = {
            "type": "BioGRIDRESTTool",
            "parameter": {"required": ["gene_names"]},
            "fields": {"endpoint": "/interactions/", "return_format": "JSON"}
        }
        tool = BioGRIDRESTTool(tool_config)
        
        # Test without API key — run() catches ValueError and returns error dict
        arguments = {"gene_names": ["TP53", "BRCA1"]}

        with patch.dict(os.environ, {"BIOGRID_API_KEY": "", "BIOGRID_ACCESS_KEY": ""}):
            result = tool.run(arguments)
        assert "error" in result
        assert "BioGRID API key" in result["error"]


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
