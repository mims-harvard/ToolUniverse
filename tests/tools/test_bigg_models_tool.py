"""Unit tests for BiGG Models API tools."""

import pytest
from tooluniverse import ToolUniverse


class TestBiGGModelsTools:
    """Test suite for BiGG Models tools."""
    
    @pytest.fixture
    def tu(self):
        """Create ToolUniverse instance."""
        tu = ToolUniverse()
        tu.load_tools()
        return tu
    
    def test_tools_load(self, tu):
        """Test that BiGG tools load correctly."""
        tool_names = [tool.get("name") for tool in tu.all_tools if isinstance(tool, dict)]
        
        expected_tools = [
            "BiGG_list_models",
            "BiGG_get_model",
            "BiGG_get_model_reactions",
            "BiGG_get_reaction",
            "BiGG_get_metabolite",
            "BiGG_search",
            "BiGG_get_database_version"
        ]
        
        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not found"
    
    def test_get_database_version(self, tu):
        """Test getting BiGG database version."""
        result = tu.tools.BiGG_get_database_version(**{
            "operation": "get_database_version"
        })
        
        assert result.get("status") == "success" or "error" in result
        
        if result.get("status") == "success":
            assert "data" in result
            data = result["data"]
            assert "bigg_models_version" in data or "api_version" in data
    
    def test_list_models(self, tu):
        """Test listing all metabolic models."""
        result = tu.tools.BiGG_list_models(**{
            "operation": "list_models"
        })
        
        assert result.get("status") == "success" or "error" in result
        
        if result.get("status") == "success":
            assert "data" in result
            data = result["data"]
            assert "models" in data
            assert "count" in data
            assert isinstance(data["models"], list)
            
            if data["models"]:
                model = data["models"][0]
                assert "bigg_id" in model
                assert "organism" in model
    
    def test_get_model(self, tu):
        """Test getting model details."""
        result = tu.tools.BiGG_get_model(**{
            "operation": "get_model",
            "model_id": "e_coli_core"
        })
        
        assert result.get("status") == "success" or "error" in result
        
        if result.get("status") == "success":
            assert "data" in result
            data = result["data"]
            assert "model" in data or "organism" in data
    
    def test_search_metabolites(self, tu):
        """Test searching for metabolites."""
        result = tu.tools.BiGG_search(**{
            "operation": "search",
            "query": "glucose",
            "search_type": "metabolites"
        })
        
        assert result.get("status") == "success" or "error" in result
        
        if result.get("status") == "success":
            assert "data" in result
            data = result["data"]
            assert "results" in data
            assert "count" in data
    
    def test_get_reaction(self, tu):
        """Test getting reaction details."""
        result = tu.tools.BiGG_get_reaction(**{
            "operation": "get_reaction",
            "reaction_id": "GAPD",
            "model_id": "universal"
        })
        
        assert result.get("status") == "success" or "error" in result
        
        if result.get("status") == "success":
            assert "data" in result
            data = result["data"]
            assert "reaction" in data or "name" in data
