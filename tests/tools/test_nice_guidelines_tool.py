#!/usr/bin/env python3
"""
Unit tests for NICE Clinical Guidelines Search tool.
"""

import pytest
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tooluniverse import ToolUniverse


@pytest.mark.integration
class TestNICEGuidelinesTool:
    """Test class for NICE Clinical Guidelines Search tool."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test environment before each test."""
        self.tu = ToolUniverse()
        self.tu.load_tools(["guidelines"])
        self.tool_name = "NICE_Clinical_Guidelines_Search"
        yield
        self.tu.close()
    
    def test_tool_loading(self):
        """Test that the NICE guidelines tool is loaded correctly."""
        # Test by trying to run the tool - if it works, it's loaded
        result = self.tu.run({
            "name": self.tool_name,
            "arguments": {
                "query": "test",
                "limit": 1
            }
        })
        # Should not return "tool not found" error
        assert not (isinstance(result, str) and "not found" in result.lower())
    
    def test_diabetes_query(self):
        """Test searching for diabetes guidelines."""
        result = self.tu.run({
            "name": self.tool_name,
            "arguments": {
                "query": "diabetes",
                "limit": 2
            }
        })
        
        # Should return a list of results
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Check structure of first result
        first_result = result[0]
        assert "title" in first_result
        assert "url" in first_result
        assert "source" in first_result
        assert first_result["source"] == "NICE"
        assert first_result["is_guideline"] is True
        
        # Check that title contains diabetes-related content
        title = first_result["title"].lower()
        assert "diabetes" in title or "diabetic" in title
    
    def test_hypertension_query(self):
        """Test searching for hypertension guidelines."""
        result = self.tu.run({
            "name": self.tool_name,
            "arguments": {
                "query": "hypertension",
                "limit": 2
            }
        })
        
        # Should return a list of results
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Check structure of first result
        first_result = result[0]
        assert "title" in first_result
        assert "url" in first_result
        assert "source" in first_result
        assert first_result["source"] == "NICE"
        assert first_result["is_guideline"] is True
        
        # Check that title contains hypertension-related content
        title = first_result["title"].lower()
        assert "hypertension" in title or "blood pressure" in title
    
    def test_cancer_query(self):
        """Test searching for cancer guidelines."""
        result = self.tu.run({
            "name": self.tool_name,
            "arguments": {
                "query": "cancer",
                "limit": 2
            }
        })
        
        # Should return a list of results
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Check structure of first result
        first_result = result[0]
        assert "title" in first_result
        assert "url" in first_result
        assert "source" in first_result
        assert first_result["source"] == "NICE"
        assert first_result["is_guideline"] is True
        
        # Check that title contains cancer-related content
        title = first_result["title"].lower()
        assert "cancer" in title
    
    def test_empty_query(self):
        """Test behavior with empty query."""
        result = self.tu.run({
            "name": self.tool_name,
            "arguments": {
                "query": "",
                "limit": 2
            }
        })
        
        # Should return an error for empty query
        assert isinstance(result, dict)
        assert "error" in result
        assert "required" in result["error"].lower()
    
    def test_missing_query(self):
        """Test behavior with missing query parameter."""
        result = self.tu.run({
            "name": self.tool_name,
            "arguments": {
                "limit": 2
            }
        })
        
        # Should return an error for missing query
        assert isinstance(result, dict)
        assert "error" in result
        assert "required" in result["error"].lower()
    
    def test_limit_parameter(self):
        """Test that limit parameter works correctly."""
        result = self.tu.run({
            "name": self.tool_name,
            "arguments": {
                "query": "diabetes",
                "limit": 1
            }
        })
        
        # Should return exactly 1 result when limit is 1
        assert isinstance(result, list)
        assert len(result) <= 1
    
    def test_result_structure(self):
        """Test that results have the expected structure."""
        result = self.tu.run({
            "name": self.tool_name,
            "arguments": {
                "query": "diabetes",
                "limit": 1
            }
        })
        
        if isinstance(result, list) and len(result) > 0:
            item = result[0]
            
            # Required fields
            required_fields = ["title", "url", "source", "is_guideline", "category"]
            for field in required_fields:
                assert field in item, f"Missing required field: {field}"
            
            # Field types
            assert isinstance(item["title"], str)
            assert isinstance(item["url"], str)
            assert isinstance(item["source"], str)
            assert isinstance(item["is_guideline"], bool)
            assert isinstance(item["category"], str)
            
            # Field values
            assert len(item["title"]) > 0
            assert item["url"].startswith("https://")
            assert item["source"] == "NICE"
            assert item["is_guideline"] is True
            assert item["category"] == "Clinical Guidelines"
    
    def test_url_validity(self):
        """Test that returned URLs are valid NICE URLs."""
        result = self.tu.run({
            "name": self.tool_name,
            "arguments": {
                "query": "diabetes",
                "limit": 2
            }
        })
        
        if isinstance(result, list):
            for item in result:
                url = item.get("url", "")
                assert url.startswith("https://www.nice.org.uk/guidance/")
    
    def test_guideline_id_extraction(self):
        """Test that guideline IDs are properly extracted from URLs."""
        result = self.tu.run({
            "name": self.tool_name,
            "arguments": {
                "query": "diabetes",
                "limit": 2
            }
        })
        
        if isinstance(result, list):
            for item in result:
                url = item.get("url", "")
                if "/guidance/" in url:
                    # Extract guideline ID from URL
                    guideline_id = url.split("/guidance/")[-1].split("/")[0]
                    assert len(guideline_id) > 0
                    assert guideline_id.startswith("ng") or guideline_id.startswith("cg")


if __name__ == "__main__":
    pytest.main([__file__])
