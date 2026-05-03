#!/usr/bin/env python3
"""
Tests for clinical guideline tools.
"""

import pytest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tooluniverse.unified_guideline_tools import (
    NICEWebScrapingTool,
    PubMedGuidelinesTool,
    EuropePMCGuidelinesTool,
    TRIPDatabaseTool,
    WHOGuidelinesTool,
    OpenAlexGuidelinesTool
)


@pytest.mark.integration
@pytest.mark.network
class TestNICEGuidelinesTool:
    """Tests for NICE Clinical Guidelines Search tool."""
    
    def test_nice_tool_initialization(self):
        """Test NICE tool can be initialized."""
        config = {
            "name": "NICE_Clinical_Guidelines_Search",
            "type": "NICEWebScrapingTool"
        }
        tool = NICEWebScrapingTool(config)
        assert tool is not None
        assert tool.tool_config['name'] == "NICE_Clinical_Guidelines_Search"
    
    def test_nice_tool_run_basic(self):
        """Test NICE tool basic execution."""
        config = {
            "name": "NICE_Clinical_Guidelines_Search",
            "type": "NICEWebScrapingTool"
        }
        tool = NICEWebScrapingTool(config)
        result = tool.run({"query": "diabetes", "limit": 2})
        
        # Should return list or error dict
        assert isinstance(result, (list, dict))
        
        if isinstance(result, list):
            assert len(result) <= 2
            if result:
                # Check first result has expected fields
                assert 'title' in result[0]
                assert 'url' in result[0]
                assert 'source' in result[0]
                assert result[0]['source'] == 'NICE'
    
    def test_nice_tool_missing_query(self):
        """Test NICE tool handles missing query parameter."""
        config = {
            "name": "NICE_Clinical_Guidelines_Search",
            "type": "NICEWebScrapingTool"
        }
        tool = NICEWebScrapingTool(config)
        result = tool.run({})
        
        assert isinstance(result, dict)
        assert 'error' in result


@pytest.mark.integration
@pytest.mark.network
class TestPubMedGuidelinesTool:
    """Tests for PubMed Guidelines Search tool."""
    
    def test_pubmed_tool_initialization(self):
        """Test PubMed tool can be initialized."""
        config = {
            "name": "PubMed_Guidelines_Search",
            "type": "PubMedGuidelinesTool"
        }
        tool = PubMedGuidelinesTool(config)
        assert tool is not None
        assert tool.base_url == "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def test_pubmed_tool_run_basic(self):
        """Test PubMed tool basic execution."""
        config = {
            "name": "PubMed_Guidelines_Search",
            "type": "PubMedGuidelinesTool"
        }
        tool = PubMedGuidelinesTool(config)
        result = tool.run({"query": "diabetes", "limit": 3})
        
        # Should return list or error dict
        assert isinstance(result, (list, dict))
        
        if isinstance(result, list):
            assert len(result) <= 3
            
            if result:
                # Check first guideline structure
                guideline = result[0]
                assert 'pmid' in guideline
                assert 'title' in guideline
                assert 'abstract' in guideline  # Now includes abstract
                assert 'authors' in guideline
                assert 'journal' in guideline
                assert 'publication_date' in guideline
                assert 'url' in guideline
                assert 'is_guideline' in guideline
                assert 'source' in guideline
                assert guideline['source'] == 'PubMed'
        else:
            # Error case
            assert 'error' in result
    
    def test_pubmed_tool_missing_query(self):
        """Test PubMed tool handles missing query parameter."""
        config = {
            "name": "PubMed_Guidelines_Search",
            "type": "PubMedGuidelinesTool"
        }
        tool = PubMedGuidelinesTool(config)
        result = tool.run({})
        
        assert isinstance(result, dict)
        assert 'error' in result
    
    def test_pubmed_tool_with_limit(self):
        """Test PubMed tool respects limit parameter."""
        config = {
            "name": "PubMed_Guidelines_Search",
            "type": "PubMedGuidelinesTool"
        }
        tool = PubMedGuidelinesTool(config)
        result = tool.run({"query": "hypertension", "limit": 2})
        
        if isinstance(result, list):
            assert len(result) <= 2


@pytest.mark.integration
@pytest.mark.network
class TestEuropePMCGuidelinesTool:
    """Tests for Europe PMC Guidelines Search tool."""
    
    def test_europepmc_tool_initialization(self):
        """Test Europe PMC tool can be initialized."""
        config = {
            "name": "EuropePMC_Guidelines_Search",
            "type": "EuropePMCGuidelinesTool"
        }
        tool = EuropePMCGuidelinesTool(config)
        assert tool is not None
        assert tool.base_url == "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    
    def test_europepmc_tool_run_basic(self):
        """Test Europe PMC tool basic execution."""
        config = {
            "name": "EuropePMC_Guidelines_Search",
            "type": "EuropePMCGuidelinesTool"
        }
        tool = EuropePMCGuidelinesTool(config)
        result = tool.run({"query": "diabetes", "limit": 3})
        
        # Should return list or error dict
        assert isinstance(result, (list, dict))
        
        if isinstance(result, list):
            assert len(result) <= 3
            
            if result:
                # Check first guideline structure
                guideline = result[0]
                assert 'title' in guideline
                assert 'pmid' in guideline
                assert 'abstract' in guideline  # Includes abstract
                assert 'authors' in guideline
                assert 'journal' in guideline
                assert 'publication_date' in guideline
                assert 'url' in guideline
                assert 'is_guideline' in guideline
                assert 'source' in guideline
                assert guideline['source'] == 'Europe PMC'
        else:
            # Error case
            assert 'error' in result
    
    def test_europepmc_tool_missing_query(self):
        """Test Europe PMC tool handles missing query parameter."""
        config = {
            "name": "EuropePMC_Guidelines_Search",
            "type": "EuropePMCGuidelinesTool"
        }
        tool = EuropePMCGuidelinesTool(config)
        result = tool.run({})
        
        assert isinstance(result, dict)
        assert 'error' in result


@pytest.mark.integration
@pytest.mark.network
class TestTRIPDatabaseTool:
    """Tests for TRIP Database Guidelines Search tool."""
    
    def test_trip_tool_initialization(self):
        """Test TRIP Database tool can be initialized."""
        config = {
            "name": "TRIP_Database_Guidelines_Search",
            "type": "TRIPDatabaseTool"
        }
        tool = TRIPDatabaseTool(config)
        assert tool is not None
        assert tool.base_url == "https://www.tripdatabase.com/api/search"
    
    def test_trip_tool_run_basic(self):
        """Test TRIP Database tool basic execution."""
        config = {
            "name": "TRIP_Database_Guidelines_Search",
            "type": "TRIPDatabaseTool"
        }
        tool = TRIPDatabaseTool(config)
        result = tool.run({"query": "diabetes", "limit": 3})
        
        # Should return list or error dict
        assert isinstance(result, (list, dict))
        
        if isinstance(result, list):
            assert len(result) <= 3
            
            if result:
                # Check first guideline structure
                guideline = result[0]
                assert 'title' in guideline
                assert 'url' in guideline
                assert 'description' in guideline  # Now includes description
                assert 'publication' in guideline
                assert 'is_guideline' in guideline
                assert 'source' in guideline
                assert guideline['source'] == 'TRIP Database'
        else:
            # Error case
            assert 'error' in result
    
    def test_trip_tool_missing_query(self):
        """Test TRIP Database tool handles missing query parameter."""
        config = {
            "name": "TRIP_Database_Guidelines_Search",
            "type": "TRIPDatabaseTool"
        }
        tool = TRIPDatabaseTool(config)
        result = tool.run({})
        
        assert isinstance(result, dict)
        assert 'error' in result
    
    def test_trip_tool_custom_search_type(self):
        """Test TRIP Database tool with custom search type."""
        config = {
            "name": "TRIP_Database_Guidelines_Search",
            "type": "TRIPDatabaseTool"
        }
        tool = TRIPDatabaseTool(config)
        result = tool.run({"query": "cancer", "limit": 2, "search_type": "guideline"})
        
        # Just check it doesn't error
        assert isinstance(result, (list, dict))


@pytest.mark.integration
class TestGuidelineToolsIntegration:
    """Integration tests for all guideline tools."""
    
    def test_all_tools_return_consistent_format(self):
        """Test all tools return consistent guideline format."""
        tools = [
            (PubMedGuidelinesTool, "PubMed_Guidelines_Search", "PubMedGuidelinesTool"),
            (EuropePMCGuidelinesTool, "EuropePMC_Guidelines_Search", "EuropePMCGuidelinesTool"),
            (TRIPDatabaseTool, "TRIP_Database_Guidelines_Search", "TRIPDatabaseTool")
        ]
        
        for tool_class, name, type_name in tools:
            config = {"name": name, "type": type_name}
            tool = tool_class(config)
            result = tool.run({"query": "diabetes", "limit": 1})
            
            # All should return list (or error dict)
            assert isinstance(result, (list, dict))
            
            if isinstance(result, list):
                # Check it's a list of guidelines
                assert len(result) <= 1
                if result:
                    guideline = result[0]
                    assert 'title' in guideline
                    assert 'url' in guideline
                    assert 'source' in guideline
            else:
                # Error case
                assert 'error' in result
    
    def test_tools_handle_various_queries(self):
        """Test tools can handle various medical queries."""
        queries = ["diabetes", "hypertension", "covid-19"]
        
        config = {
            "name": "PubMed_Guidelines_Search",
            "type": "PubMedGuidelinesTool"
        }
        tool = PubMedGuidelinesTool(config)
        
        for query in queries:
            result = tool.run({"query": query, "limit": 1})
            assert isinstance(result, (list, dict))
            # Should either return results or error, not crash


@pytest.mark.integration
@pytest.mark.network
class TestWHOGuidelinesTool:
    """Tests for WHO Guidelines Search tool."""
    
    def test_who_tool_initialization(self):
        """Test WHO tool can be initialized."""
        config = {
            "name": "WHO_Guidelines_Search",
            "type": "WHOGuidelinesTool"
        }
        tool = WHOGuidelinesTool(config)
        assert tool is not None
        assert tool.base_url == "https://www.who.int"
    
    def test_who_tool_run_basic(self):
        """Test WHO tool basic execution."""
        config = {
            "name": "WHO_Guidelines_Search",
            "type": "WHOGuidelinesTool"
        }
        tool = WHOGuidelinesTool(config)
        result = tool.run({"query": "HIV", "limit": 3})
        
        # Should return list or error dict
        assert isinstance(result, (list, dict))
        
        if isinstance(result, list):
            assert len(result) <= 3
            
            if result:
                # Check first guideline structure
                guideline = result[0]
                assert 'title' in guideline
                assert 'url' in guideline
                assert 'description' in guideline  # Now includes description
                assert 'source' in guideline
                assert 'organization' in guideline
                assert 'is_guideline' in guideline
                assert 'official' in guideline
                assert guideline['source'] == 'WHO'
                assert guideline['official'] is True
        else:
            # Error case
            assert 'error' in result
    
    def test_who_tool_missing_query(self):
        """Test WHO tool handles missing query parameter."""
        config = {
            "name": "WHO_Guidelines_Search",
            "type": "WHOGuidelinesTool"
        }
        tool = WHOGuidelinesTool(config)
        result = tool.run({})
        
        assert isinstance(result, dict)
        assert 'error' in result


@pytest.mark.integration
@pytest.mark.network
class TestOpenAlexGuidelinesTool:
    """Tests for OpenAlex Guidelines Search tool."""
    
    def test_openalex_tool_initialization(self):
        """Test OpenAlex tool can be initialized."""
        config = {
            "name": "OpenAlex_Guidelines_Search",
            "type": "OpenAlexGuidelinesTool"
        }
        tool = OpenAlexGuidelinesTool(config)
        assert tool is not None
        assert tool.base_url == "https://api.openalex.org/works"
    
    def test_openalex_tool_run_basic(self):
        """Test OpenAlex tool basic execution."""
        config = {
            "name": "OpenAlex_Guidelines_Search",
            "type": "OpenAlexGuidelinesTool"
        }
        tool = OpenAlexGuidelinesTool(config)
        result = tool.run({"query": "diabetes", "limit": 3})
        
        # Should return list or error dict
        assert isinstance(result, (list, dict))
        
        if isinstance(result, list):
            assert len(result) <= 3
            
            if result:
                # Check first guideline structure
                guideline = result[0]
                assert 'title' in guideline
                assert 'authors' in guideline
                assert 'year' in guideline
                assert 'url' in guideline
                assert 'cited_by_count' in guideline
                assert 'is_guideline' in guideline
                assert 'abstract' in guideline  # Now includes abstract
                assert 'source' in guideline
                assert guideline['source'] == 'OpenAlex'
        else:
            # Error case
            assert 'error' in result
    
    def test_openalex_tool_missing_query(self):
        """Test OpenAlex tool handles missing query parameter."""
        config = {
            "name": "OpenAlex_Guidelines_Search",
            "type": "OpenAlexGuidelinesTool"
        }
        tool = OpenAlexGuidelinesTool(config)
        result = tool.run({})
        
        assert isinstance(result, dict)
        assert 'error' in result
    
    def test_openalex_tool_with_year_filter(self):
        """Test OpenAlex tool with year filters."""
        config = {
            "name": "OpenAlex_Guidelines_Search",
            "type": "OpenAlexGuidelinesTool"
        }
        tool = OpenAlexGuidelinesTool(config)
        result = tool.run({"query": "hypertension", "limit": 2, "year_from": 2020})
        
        if isinstance(result, list):
            # All results should be from 2020 or later
            for guideline in result:
                year = guideline.get('year')
                if year and year != 'N/A':
                    assert year >= 2020


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
