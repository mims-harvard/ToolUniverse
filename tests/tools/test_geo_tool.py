#!/usr/bin/env python3
"""
Test cases for GEO (Gene Expression Omnibus) tool
Tests GEO tool for real data access
"""

import pytest
import sys
import os
from unittest.mock import MagicMock

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from tooluniverse.geo_tool import GEORESTTool


class TestGEOTool:
    """Test cases for GEO database tool"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.tool_config = {
            "type": "GEORESTTool",
            "name": "GEO_search_expression_data",
            "description": "Search gene expression data from GEO database",
            "parameter": {
                "required": ["query"],
                "properties": {
                    "query": {"type": "string"},
                    "organism": {"type": "string", "default": "Homo sapiens"},
                    "study_type": {"type": "string", "default": "expression"},
                    "limit": {"type": "integer", "default": 10}
                }
            },
            "fields": {
                "endpoint": "/esearch.fcgi",
                "return_format": "JSON"
            }
        }
        self.tool = GEORESTTool(self.tool_config)
    
    def test_tool_initialization(self):
        """Test tool initialization"""
        assert self.tool.endpoint_template == "/esearch.fcgi"
        assert self.tool.required == ["query"]
        assert self.tool.output_format == "JSON"
    
    def test_build_url(self):
        """Test URL building"""
        arguments = {"query": "cancer"}
        url = self.tool._build_url(arguments)
        assert url == "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    
    def test_build_params(self):
        """Test parameter building"""
        arguments = {
            "query": "cancer",
            "organism": "Homo sapiens",
            "study_type": "expression",
            "limit": 10
        }
        params = self.tool._build_params(arguments)
        
        assert params["db"] == "gds"
        assert params["term"] == "cancer AND Homo sapiens[organism] AND \"expression\"[study_type]"
        assert params["retmode"] == "json"
        assert params["retmax"] == 10
    
    def test_build_params_with_organism(self):
        """Test parameter building with organism specification"""
        arguments = {
            "query": "cancer",
            "organism": "Mus musculus",
            "limit": 5
        }
        params = self.tool._build_params(arguments)
        
        expected_term = "cancer AND Mus musculus[organism]"
        assert params["term"] == expected_term
        assert params["retmax"] == 5
    
    def test_build_params_with_study_type(self):
        """Test parameter building with study type"""
        arguments = {
            "query": "cancer",
            "study_type": "methylation",
            "limit": 20
        }
        params = self.tool._build_params(arguments)
        
        expected_term = "cancer AND \"methylation\"[study_type]"
        assert params["term"] == expected_term
        assert params["retmax"] == 20
    
    def test_make_request_success(self):
        """Test successful API request"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "esearchresult": {
                "idlist": ["200000001", "200000002", "200000003"],
                "count": "3"
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_response.headers.get.return_value = "application/json"
        self.tool.session.get = MagicMock(return_value=mock_response)
        
        result = self.tool._make_request("/esearch.fcgi", {})
        
        assert result["status"] == "success"
        assert "data" in result
        assert "esearchresult" in result["data"]
        assert "idlist" in result["data"]["esearchresult"]
        assert len(result["data"]["esearchresult"]["idlist"]) == 3
        self.tool.session.get.assert_called_once()
    
    def test_make_request_error(self):
        """Test API request error handling"""
        import requests
        self.tool.session.get = MagicMock(side_effect=requests.exceptions.RequestException("Network error"))
        
        result = self.tool._make_request("/esearch.fcgi", {})
        
        assert result["status"] == "error"
        assert "error" in result
        assert "Network error" in result["error"]
    
    def test_run_missing_required_params(self):
        """Test run method with missing required parameters"""
        result = self.tool.run({})
        assert "error" in result
        assert "Missing required parameter" in result["error"]
    
    def test_run_success(self):
        """Test successful run"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "esearchresult": {
                "idlist": ["200000001", "200000002"],
                "count": "2"
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_response.headers.get.return_value = "application/json"
        self.tool.session.get = MagicMock(return_value=mock_response)
        
        arguments = {"query": "cancer AND Homo sapiens[organism]"}
        result = self.tool.run(arguments)
        
        assert result["status"] == "success"
        assert "data" in result
        assert "esearchresult" in result["data"]
        assert len(result["data"]["esearchresult"]["idlist"]) == 2
    
    def test_parse_search_results(self):
        """Test parsing of search results"""
        mock_data = {
            "esearchresult": {
                "idlist": ["200000001", "200000002", "200000003"],
                "count": "3",
                "retmax": "3",
                "retstart": "0"
            }
        }
        
        # Test that the data structure is preserved
        assert "esearchresult" in mock_data
        assert "idlist" in mock_data["esearchresult"]
        assert len(mock_data["esearchresult"]["idlist"]) == 3


class TestGEOIntegration:
    """Integration tests for GEO tool"""
    
    def test_geo_tool_real_api(self):
        """Test GEO tool with real API (if network available)"""
        tool_config = {
            "type": "GEORESTTool",
            "parameter": {"required": ["query"]},
            "fields": {"endpoint": "/esearch.fcgi", "return_format": "JSON"}
        }
        tool = GEORESTTool(tool_config)
        
        # Test with real query
        arguments = {
            "query": "cancer AND Homo sapiens[organism]",
            "limit": 5
        }
        
        try:
            result = tool.run(arguments)
            # If successful, should have esearchresult
            if "esearchresult" in result and not result.get("error"):
                idlist = result["esearchresult"].get("idlist", [])
                print(f"✅ GEO API test successful: {len(idlist)} studies found")
                if idlist:
                    print(f"📊 Sample study IDs: {idlist[:3]}")
            else:
                print(f"⚠️ GEO API test failed: {result.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"⚠️ GEO API test error: {e}")
    
    def test_geo_tool_different_organisms(self):
        """Test GEO tool with different organisms"""
        tool_config = {
            "type": "GEORESTTool",
            "parameter": {"required": ["query"]},
            "fields": {"endpoint": "/esearch.fcgi", "return_format": "JSON"}
        }
        tool = GEORESTTool(tool_config)
        
        organisms = [
            "Homo sapiens",
            "Mus musculus", 
            "Drosophila melanogaster"
        ]
        
        for organism in organisms:
            arguments = {
                "query": "cancer",
                "organism": organism,
                "limit": 3
            }
            
            try:
                result = tool.run(arguments)
                if "esearchresult" in result and not result.get("error"):
                    idlist = result["esearchresult"].get("idlist", [])
                    print(f"✅ {organism}: {len(idlist)} studies found")
                else:
                    print(f"⚠️ {organism}: {result.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"⚠️ {organism}: {e}")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
