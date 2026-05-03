#!/usr/bin/env python3
"""
Test critical error handling and recovery scenarios - Cleaned Version

This test file covers important error handling scenarios:
1. ToolUniverse error handling
2. Invalid tool responses
3. Memory issues
4. Concurrent access issues
5. Resource cleanup
"""

import sys
import unittest
from pathlib import Path
import pytest
from unittest.mock import patch, Mock, MagicMock
import time
import threading

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse import ToolUniverse
from tooluniverse.exceptions import ToolError, ToolValidationError


@pytest.mark.unit
class TestCriticalErrorHandling(unittest.TestCase):
    """Test critical error handling and recovery scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tu = ToolUniverse()
        # Load tools for real testing
        self.tu.load_tools()
    
    def test_invalid_tool_name_handling(self):
        """Test that invalid tool names return an error dict."""
        result = self.tu.run({
            "name": "NonExistentTool",
            "arguments": {"test": "value"}
        })

        self.assertIsInstance(result, dict)
        self.assertIn("error", result, "Expected error dict for unknown tool name")
    
    def test_invalid_arguments_handling(self):
        """Invalid params (missing required 'accession') must return an error dict."""
        result = self.tu.run({
            "name": "UniProt_get_entry_by_accession",
            "arguments": {"invalid_param": "value"}
        })

        self.assertIsInstance(result, dict)
        self.assertIn("error", result, "Expected validation error for invalid params")

    def test_empty_arguments_handling(self):
        """Empty arguments dict (missing required 'accession') must return an error dict."""
        result = self.tu.run({
            "name": "UniProt_get_entry_by_accession",
            "arguments": {}
        })

        self.assertIsInstance(result, dict)
        self.assertIn("error", result, "Expected validation error for empty arguments")

    def test_none_arguments_handling(self):
        """None arguments must return an error dict, not crash."""
        result = self.tu.run({
            "name": "UniProt_get_entry_by_accession",
            "arguments": None
        })

        self.assertIsInstance(result, dict)
        self.assertIn("error", result, "Expected error dict for None arguments")
    
    def test_malformed_query_handling(self):
        """Malformed queries must return error dicts, not raise exceptions."""
        malformed_queries = [
            {"name": "UniProt_get_entry_by_accession"},  # Missing arguments key
            {"arguments": {"accession": "P05067"}},      # Missing name key
            {"name": "", "arguments": {"accession": "P05067"}},  # Empty name
            {"name": "UniProt_get_entry_by_accession", "arguments": ""},   # String args
            {"name": "UniProt_get_entry_by_accession", "arguments": []},   # List args
        ]

        for query in malformed_queries:
            result = self.tu.run(query)
            self.assertIsInstance(result, dict, f"Expected dict for query {query!r}")
            self.assertIn("error", result, f"Expected error dict for malformed query {query!r}")
    
    @pytest.mark.network
    def test_large_argument_handling(self):
        """Large extra arguments are stripped by validation; accession still works."""
        large_args = {
            "accession": "P05067",
            "large_string": "A" * 100000,
            "large_array": ["item"] * 10000,
        }
        result = self.tu.run({
            "name": "UniProt_get_entry_by_accession",
            "arguments": large_args
        })
        self.assertIsInstance(result, dict)

    @pytest.mark.network
    def test_concurrent_tool_access(self):
        """Concurrent tool calls must all return dicts (no crashes or deadlocks)."""
        results = []

        def make_call(call_id):
            result = self.tu.run({
                "name": "UniProt_get_entry_by_accession",
                "arguments": {"accession": f"P{call_id:05d}"}
            })
            results.append(result)

        threads = [threading.Thread(target=make_call, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        self.assertEqual(len(results), 5, "All 5 threads must complete")
        for result in results:
            self.assertIsInstance(result, dict)
    
    def test_tool_initialization_failure(self):
        """Test handling of tool initialization failures."""
        # Test with invalid tool configuration
        invalid_tool = {
            "name": "InvalidTool",
            "type": "NonExistentType",
            "description": "Invalid tool"
        }
        
        self.tu.all_tools.append(invalid_tool)
        self.tu.all_tool_dict["InvalidTool"] = invalid_tool
        
        result = self.tu.run({
            "name": "InvalidTool",
            "arguments": {"test": "value"}
        })
        
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
    
    @pytest.mark.network
    def test_memory_pressure_handling(self):
        """run() must succeed (or return error dict) even under memory pressure."""
        large_objects = []
        try:
            for i in range(100):
                large_objects.append(["data"] * 10000)

            result = self.tu.run({
                "name": "UniProt_get_entry_by_accession",
                "arguments": {"accession": "P05067"}
            })
            self.assertIsInstance(result, dict)
        finally:
            del large_objects
    
    def test_resource_cleanup(self):
        """Test proper resource cleanup."""
        # Test that resources are properly cleaned up
        _ = len(self.tu.all_tools)
        
        # Add some tools
        test_tool = {
            "name": "TestTool",
            "type": "TestType",
            "description": "Test tool"
        }
        
        self.tu.all_tools.append(test_tool)
        self.tu.all_tool_dict["TestTool"] = test_tool
        
        # Clear tools
        self.tu.all_tools.clear()
        self.tu.all_tool_dict.clear()
        
        # Verify cleanup
        self.assertEqual(len(self.tu.all_tools), 0)
        self.assertEqual(len(self.tu.all_tool_dict), 0)
    
    def test_error_propagation(self):
        """All error conditions must return error dicts, not raise exceptions."""
        error_cases = [
            {"name": "NonExistentTool", "arguments": {}},
            {"name": "UniProt_get_entry_by_accession", "arguments": {"invalid": "param"}},
            {"name": "", "arguments": {}},
            {"name": "UniProt_get_entry_by_accession", "arguments": None},
        ]

        for query in error_cases:
            result = self.tu.run(query)
            self.assertIsInstance(result, dict, f"Expected dict for {query!r}")
            self.assertIn("error", result, f"Expected error key for {query!r}")

    @pytest.mark.network
    def test_partial_failure_recovery(self):
        """System must remain stable across multiple sequential network calls."""
        results = []
        for i in range(5):
            result = self.tu.run({
                "name": "UniProt_get_entry_by_accession",
                "arguments": {"accession": f"P{i:05d}"}
            })
            results.append(result)

        self.assertEqual(len(results), 5)
        for result in results:
            self.assertIsInstance(result, dict)
    
    def test_circuit_breaker_pattern(self):
        """Test circuit breaker pattern for repeated failures."""
        # Test multiple calls with invalid tool
        results = []
        
        for i in range(5):
            result = self.tu.run({
                "name": "NonExistentTool",
                "arguments": {"test": f"value_{i}"}
            })
            results.append(result)
        
        # All should fail gracefully
        self.assertEqual(len(results), 5)
        for result in results:
            self.assertIsInstance(result, dict)
            self.assertIn("error", result)
    
    def test_graceful_degradation(self):
        """Unknown tool must return an error dict, not raise."""
        result = self.tu.run({
            "name": "NonExistentService",
            "arguments": {"query": "test"}
        })

        self.assertIsInstance(result, dict)
        self.assertIn("error", result, "Expected error dict for unknown tool")
    
    def test_data_corruption_handling(self):
        """Test handling of corrupted data."""
        # Test with corrupted arguments
        corrupted_args = {
            "accession": "P05067\x00\x00",  # Null bytes
            "invalid_unicode": "test\xff\xfe",  # Invalid Unicode
        }
        
        result = self.tu.run({
            "name": "UniProt_get_entry_by_accession",
            "arguments": corrupted_args
        })
        
        self.assertIsInstance(result, dict)
        # Should handle corrupted data gracefully
    
    def test_tool_health_check_under_stress(self):
        """Test tool health check under stress."""
        # Test health check
        health = self.tu.get_tool_health()
        
        self.assertIsInstance(health, dict)
        self.assertIn("total", health)
        self.assertIn("available", health)
        self.assertIn("unavailable", health)
        self.assertIn("unavailable_list", health)
        self.assertIn("details", health)
        
        # Verify totals make sense
        self.assertEqual(health["total"], health["available"] + health["unavailable"])
    
    def test_cache_management_under_stress(self):
        """Test cache management under stress."""
        # Test cache operations under stress
        self.tu.clear_cache()
        
        # Add many items to cache using the proper API
        for i in range(100):
            self.tu._cache.set(f"item_{i}", {"data": f"value_{i}"})
        
        # Verify cache operations
        self.assertEqual(len(self.tu._cache), 100)
        
        # Clear cache
        self.tu.clear_cache()
        self.assertEqual(len(self.tu._cache), 0)
    
    def test_tool_specification_edge_cases(self):
        """Test tool specification edge cases."""
        # Test with non-existent tool
        spec = self.tu.tool_specification("NonExistentTool")
        self.assertIsNone(spec)
        
        # Test with empty string
        spec = self.tu.tool_specification("")
        self.assertIsNone(spec)
        
        # Test with None
        spec = self.tu.tool_specification(None)
        self.assertIsNone(spec)
    
    def test_tool_listing_edge_cases(self):
        """Test tool listing edge cases."""
        # Test with invalid mode
        tools = self.tu.list_built_in_tools(mode="invalid_mode")
        self.assertIsInstance(tools, dict)
        
        # Test with None mode
        tools = self.tu.list_built_in_tools(mode=None)
        self.assertIsInstance(tools, dict)
    
    def test_tool_filtering_edge_cases(self):
        """Test tool filtering edge cases."""
        # Test with empty category filter
        tools = self.tu.get_available_tools(category_filter="")
        self.assertIsInstance(tools, list)
        
        # Test with None category filter
        tools = self.tu.get_available_tools(category_filter=None)
        self.assertIsInstance(tools, list)
        
        # Test with non-existent category
        tools = self.tu.get_available_tools(category_filter="non_existent_category")
        self.assertIsInstance(tools, list)
    
    def test_tool_search_edge_cases(self):
        """Test tool search edge cases."""
        # Test with empty pattern
        results = self.tu.find_tools_by_pattern("")
        self.assertIsInstance(results, list)
        
        # Test with None pattern
        results = self.tu.find_tools_by_pattern(None)
        self.assertIsInstance(results, list)
        
        # Test with invalid search_in parameter
        results = self.tu.find_tools_by_pattern("test", search_in="invalid_field")
        self.assertIsInstance(results, list)


if __name__ == "__main__":
    unittest.main()
