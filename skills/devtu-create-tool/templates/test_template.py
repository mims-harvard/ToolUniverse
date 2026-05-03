"""
Unit Test Template for ToolUniverse Tools

Use this template to create comprehensive tests for your tools.
"""

import pytest
from tooluniverse import ToolUniverse


class TestToolCategory:
    """Test suite for {category} tools."""
    
    @pytest.fixture
    def tu(self):
        """Create ToolUniverse instance for testing."""
        return ToolUniverse()
    
    def test_tool_loads(self, tu):
        """Test that tool loads without errors."""
        tools = tu.list_tools()
        assert "example_tool" in tools, "Tool 'example_tool' not found in loaded tools"
    
    def test_tool_with_valid_input(self, tu):
        """Test tool execution with valid input."""
        result = tu.run_tool(
            "example_tool",
            {
                "param1": "test_value",
                "param2": "optional_value"
            }
        )
        
        # Check response structure
        assert result is not None, "Result is None"
        assert isinstance(result, dict), "Result is not a dictionary"
        
        # Check status
        assert result.get("status") == "success", f"Expected success, got: {result.get('status')}"
        
        # Check data presence
        assert "data" in result, "No 'data' field in result"
        assert result["data"] is not None, "Data field is None"
        assert result["data"] != {}, "Data field is empty"
    
    def test_tool_with_minimal_input(self, tu):
        """Test tool with only required parameters."""
        result = tu.run_tool(
            "example_tool",
            {
                "param1": "test_value"
            }
        )
        
        assert result is not None
        assert result.get("status") == "success"
    
    def test_tool_missing_required_parameter(self, tu):
        """Test tool error handling with missing required parameter."""
        result = tu.run_tool(
            "example_tool",
            {}
        )
        
        # Should return error
        assert result is not None
        assert result.get("status") == "error", "Expected error status for missing parameter"
        assert "error" in result, "No error message provided"
        assert "param1" in result["error"].lower(), "Error message should mention missing parameter"
    
    def test_tool_invalid_parameter_type(self, tu):
        """Test tool error handling with invalid parameter type."""
        result = tu.run_tool(
            "example_tool",
            {
                "param1": 12345  # Should be string
            }
        )
        
        # May succeed with type coercion or fail - either is acceptable
        # Just ensure it doesn't crash
        assert result is not None
        assert "status" in result
    
    def test_tool_invalid_parameter_value(self, tu):
        """Test tool error handling with invalid parameter value."""
        result = tu.run_tool(
            "example_tool",
            {
                "param1": ""  # Empty string
            }
        )
        
        # Should return error or empty results
        assert result is not None
        if result.get("status") == "error":
            assert "error" in result
    
    def test_tool_response_structure(self, tu):
        """Test that response matches expected schema."""
        result = tu.run_tool(
            "example_tool",
            {
                "param1": "test_value"
            }
        )
        
        # Check required fields
        assert "status" in result, "Missing 'status' field"
        
        if result["status"] == "success":
            assert "data" in result, "Success response missing 'data' field"
        elif result["status"] == "error":
            assert "error" in result, "Error response missing 'error' field"
    
    def test_multiple_tools_load(self, tu):
        """Test that all tools in category load correctly."""
        tools = tu.list_tools()
        
        # List all tools in this category
        category_tools = [
            "example_tool_1",
            "example_tool_2",
            "example_tool_3"
        ]
        
        for tool_name in category_tools:
            assert tool_name in tools, f"Tool '{tool_name}' not found"
    
    def test_tool_with_edge_cases(self, tu):
        """Test tool with edge case inputs."""
        edge_cases = [
            {"param1": "a"},  # Single character
            {"param1": "a" * 1000},  # Very long string
            {"param1": "test with spaces"},  # Spaces
            {"param1": "test-with-dashes"},  # Special characters
            {"param1": "test_with_underscores"},  # Underscores
        ]
        
        for test_case in edge_cases:
            result = tu.run_tool("example_tool", test_case)
            assert result is not None, f"No result for test case: {test_case}"
            assert "status" in result, f"No status for test case: {test_case}"


class TestToolIntegration:
    """Integration tests for tool workflows."""
    
    @pytest.fixture
    def tu(self):
        """Create ToolUniverse instance for testing."""
        return ToolUniverse()
    
    def test_search_and_detail_workflow(self, tu):
        """Test workflow: search for items, then get details."""
        # Step 1: Search for items
        search_result = tu.run_tool(
            "search_items",
            {"query": "test"}
        )
        
        assert search_result.get("status") == "success"
        assert "results" in search_result
        assert len(search_result["results"]) > 0, "Search returned no results"
        
        # Step 2: Get details for first result
        item_id = search_result["results"][0]["id"]
        detail_result = tu.run_tool(
            "get_item_details",
            {"item_id": item_id}
        )
        
        assert detail_result.get("status") == "success"
        assert "data" in detail_result
        assert detail_result["data"]["id"] == item_id
    
    def test_pagination_workflow(self, tu):
        """Test pagination through multiple pages."""
        page1 = tu.run_tool(
            "search_items",
            {"query": "test", "page": 1, "limit": 10}
        )
        
        assert page1.get("status") == "success"
        
        if page1.get("next"):
            page2 = tu.run_tool(
                "search_items",
                {"query": "test", "page": 2, "limit": 10}
            )
            assert page2.get("status") == "success"
            # Results should be different
            assert page1["results"] != page2["results"]


# Performance tests (optional)
class TestToolPerformance:
    """Performance tests for tools."""
    
    @pytest.fixture
    def tu(self):
        return ToolUniverse()
    
    def test_tool_response_time(self, tu):
        """Test that tool responds within acceptable time."""
        import time
        
        start = time.time()
        result = tu.run_tool(
            "example_tool",
            {"param1": "test_value"}
        )
        elapsed = time.time() - start
        
        assert result is not None
        assert elapsed < 10.0, f"Tool took too long: {elapsed:.2f}s"
    
    def test_batch_performance(self, tu):
        """Test performance with multiple requests."""
        import time
        
        num_requests = 10
        start = time.time()
        
        for i in range(num_requests):
            result = tu.run_tool(
                "example_tool",
                {"param1": f"test_{i}"}
            )
            assert result is not None
        
        elapsed = time.time() - start
        avg_time = elapsed / num_requests
        
        print(f"\nBatch performance: {num_requests} requests in {elapsed:.2f}s")
        print(f"Average: {avg_time:.3f}s per request")
        
        assert avg_time < 2.0, f"Average request time too high: {avg_time:.3f}s"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
