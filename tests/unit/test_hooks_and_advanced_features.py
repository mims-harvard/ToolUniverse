#!/usr/bin/env python3
"""
Test Hooks and Advanced Features - Cleaned Version

This test file covers important hooks and advanced features:
1. Real hook functionality testing
2. Streaming tools support
3. Visualization tools
4. Performance optimization features
"""

import sys
import unittest
from pathlib import Path
import pytest
from unittest.mock import patch, Mock, MagicMock
import json
import tempfile
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse import ToolUniverse


@pytest.mark.unit
class TestHooksAndAdvancedFeatures(unittest.TestCase):
    """Test hooks and advanced features functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tu = ToolUniverse()
        # Don't load tools to avoid embedding model loading issues
        self.tu.all_tools = []
        self.tu.all_tool_dict = {}
    
    def tearDown(self):
        """Tear down test fixtures."""
        if hasattr(self, 'tu'):
            self.tu.close()
    
    def test_hook_toggle_functionality(self):
        """Test that hook toggle actually changes the enabled state."""
        self.tu.toggle_hooks(True)
        self.assertTrue(self.tu.hooks_enabled, "Expected hooks_enabled=True after toggle_hooks(True)")

        self.tu.toggle_hooks(False)
        self.assertFalse(self.tu.hooks_enabled, "Expected hooks_enabled=False after toggle_hooks(False)")
    
    def test_streaming_callback_accepted(self):
        """run() must accept a stream_callback kwarg without raising.

        Uses a guaranteed-unknown tool name so we get an error dict immediately,
        without any network call.
        """
        callback_called = False

        def test_callback(chunk):
            nonlocal callback_called
            callback_called = True

        result = self.tu.run(
            {"name": "NonExistentTool_XYZ_12345", "arguments": {"x": "y"}},
            stream_callback=test_callback,
        )
        # run() must return a dict with an error key for unknown tool
        self.assertIsInstance(result, dict)
        self.assertIn("error", result, "Expected error dict for unknown tool")

    def test_unknown_tool_returns_error_dict(self):
        """run() for an unknown tool must return an error dict, never raise."""
        result = self.tu.run({
            "name": "visualize_protein_structure_3d",
            "arguments": {"pdb_id": "1CRN", "style": "cartoon"},
        })
        self.assertIsInstance(result, dict)
        self.assertIn("error", result, "Expected error dict for unknown tool")
    
    def test_cache_functionality_real(self):
        """Test that caching actually works."""
        # Clear cache first
        self.tu.clear_cache()
        self.assertEqual(len(self.tu._cache), 0)
        
        # Test caching a result
        test_key = "test_cache_key"
        test_value = {"result": "cached_data"}
        
        # Add to cache using proper API
        self.tu._cache.set(test_key, test_value)
        
        # Verify it's in cache
        self.assertEqual(self.tu._cache.get(test_key), test_value)
        
        # Clear cache
        self.tu.clear_cache()
        self.assertEqual(len(self.tu._cache), 0)
    
    def test_tool_health_check_real(self):
        """Test tool health check with real ToolUniverse."""
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
    
    def test_tool_listing_real(self):
        """Test tool listing with real ToolUniverse."""
        # Test different listing modes
        tools_dict = self.tu.list_built_in_tools()
        self.assertIsInstance(tools_dict, dict)
        self.assertIn("total_tools", tools_dict)
        
        tools_list = self.tu.list_built_in_tools(mode="list_name")
        self.assertIsInstance(tools_list, list)
        
        # Test that we can get available tools
        available_tools = self.tu.get_available_tools()
        self.assertIsInstance(available_tools, list)
    
    def test_tool_specification_real(self):
        """Test tool specification with real ToolUniverse."""
        # Load some tools first
        self.tu.load_tools()
        
        if self.tu.all_tools:
            # Get a tool name from the loaded tools
            tool_name = self.tu.all_tools[0].get("name")
            if tool_name:
                spec = self.tu.tool_specification(tool_name)
                if spec:  # If tool has specification
                    self.assertIsInstance(spec, dict)
                    self.assertIn("name", spec)
    
    def test_error_handling_real(self):
        """Test error handling with real ToolUniverse calls."""
        # Test with invalid tool name
        result = self.tu.run({
            "name": "NonExistentTool",
            "arguments": {"test": "value"}
        })
        
        self.assertIsInstance(result, dict)
        # Should either return error or None
        if result:
            self.assertIn("error", result)
    
    def test_export_functionality_real(self):
        """Test export functionality with real ToolUniverse."""

        
        # Test exporting to file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_file = f.name
        
        try:
            self.tu.export_tool_names(temp_file)
            
            # Verify file was created and has content
            self.assertTrue(os.path.exists(temp_file))
            with open(temp_file, 'r') as f:
                content = f.read()
                self.assertGreater(len(content), 0)
                
        finally:
            # Clean up
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_env_template_generation_real(self):
        """Test environment template generation with real ToolUniverse."""

        
        # Test with some missing keys
        missing_keys = ["API_KEY_1", "API_KEY_2"]
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as f:
            temp_file = f.name
        
        try:
            self.tu.generate_env_template(missing_keys, output_file=temp_file)
            
            # Verify file was created and has content
            self.assertTrue(os.path.exists(temp_file))
            with open(temp_file, 'r') as f:
                content = f.read()
                self.assertIn("API_KEY_1", content)
                self.assertIn("API_KEY_2", content)
                
        finally:
            # Clean up
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_call_id_generation_real(self):
        """Test call ID generation with real ToolUniverse."""
        # Test generating multiple IDs
        id1 = self.tu.call_id_gen()
        id2 = self.tu.call_id_gen()
        
        self.assertIsInstance(id1, str)
        self.assertIsInstance(id2, str)
        self.assertNotEqual(id1, id2)
        self.assertGreater(len(id1), 0)
        self.assertGreater(len(id2), 0)
    
    def test_lazy_loading_status_real(self):
        """Test lazy loading status with real ToolUniverse."""
        status = self.tu.get_lazy_loading_status()
        
        self.assertIsInstance(status, dict)
        self.assertIn("lazy_loading_enabled", status)
        self.assertIn("full_discovery_completed", status)
        self.assertIn("immediately_available_tools", status)
        self.assertIn("lazy_mappings_available", status)
        self.assertIn("loaded_tools_count", status)
    
    def test_tool_types_retrieval_real(self):
        """Test tool types retrieval with real ToolUniverse."""
        tool_types = self.tu.get_tool_types()
        
        self.assertIsInstance(tool_types, list)
        # Should contain some tool types
        self.assertGreater(len(tool_types), 0)

    def test_summarization_hook_basic_functionality(self):
        """Test basic SummarizationHook functionality"""
        from tooluniverse.output_hook import SummarizationHook
        
        # Create a mock tooluniverse
        mock_tu = MagicMock()
        mock_tu.callable_functions = {
            "OutputSummarizationComposer": MagicMock()
        }
        
        # Test hook initialization
        hook_config = {
            "composer_tool": "OutputSummarizationComposer",
            "chunk_size": 1000,
            "focus_areas": "key findings, results",
            "max_summary_length": 500
        }
        
        hook = SummarizationHook(
            config={"hook_config": hook_config},
            tooluniverse=mock_tu
        )
        
        self.assertEqual(hook.composer_tool, "OutputSummarizationComposer")
        self.assertEqual(hook.chunk_size, 1000)
        self.assertEqual(hook.focus_areas, "key findings, results")
        self.assertEqual(hook.max_summary_length, 500)

    def test_summarization_hook_short_text(self):
        """Test SummarizationHook with short text (should not summarize)"""
        from tooluniverse.output_hook import SummarizationHook
        
        # Create a mock tooluniverse
        mock_tu = MagicMock()
        mock_tu.callable_functions = {
            "OutputSummarizationComposer": MagicMock()
        }
        
        hook_config = {
            "composer_tool": "OutputSummarizationComposer",
            "chunk_size": 1000,
            "focus_areas": "key findings, results",
            "max_summary_length": 500
        }
        
        hook = SummarizationHook(
            config={"hook_config": hook_config},
            tooluniverse=mock_tu
        )
        
        # Short text should not be summarized
        short_text = "This is a short text."
        result = hook.process(short_text)
        self.assertEqual(result, short_text)

    def test_summarization_hook_long_text(self):
        """Test SummarizationHook with long text (should summarize)"""
        from tooluniverse.output_hook import SummarizationHook
        
        # Create a mock tooluniverse
        mock_tu = MagicMock()
        mock_tu.callable_functions = {
            "OutputSummarizationComposer": MagicMock()
        }
        
        # Mock the composer tool
        mock_tu.run_one_function.return_value = "This is a summarized version."
        
        hook_config = {
            "composer_tool": "OutputSummarizationComposer",
            "chunk_size": 1000,
            "focus_areas": "key findings, results",
            "max_summary_length": 500
        }
        
        hook = SummarizationHook(
            config={"hook_config": hook_config},
            tooluniverse=mock_tu
        )
        
        # Long text should be summarized
        long_text = "This is a very long text. " * 100
        result = hook.process(long_text)
        
        self.assertNotEqual(result, long_text)
        self.assertIn("summarized", result.lower())

    def test_hook_manager_basic_functionality(self):
        """Test HookManager basic functionality"""
        from tooluniverse.output_hook import HookManager
        from tooluniverse.default_config import get_default_hook_config
        
        # Create a mock tooluniverse
        mock_tu = MagicMock()
        mock_tu.all_tool_dict = {
            "ToolOutputSummarizer": {},
            "OutputSummarizationComposer": {}
        }
        mock_tu.callable_functions = {}
        
        hook_manager = HookManager(get_default_hook_config(), mock_tu)
        
        # Test enabling hooks
        hook_manager.enable_hooks()
        self.assertTrue(hook_manager.hooks_enabled)
        
        # Test disabling hooks
        hook_manager.disable_hooks()
        self.assertFalse(hook_manager.hooks_enabled)

    def test_hook_error_handling(self):
        """Test hook error handling"""
        from tooluniverse.output_hook import SummarizationHook
        
        # Create a mock tooluniverse that raises an exception
        mock_tu = MagicMock()
        mock_tu.callable_functions = {
            "OutputSummarizationComposer": MagicMock()
        }
        mock_tu.run_one_function.side_effect = Exception("Test error")
        
        hook_config = {
            "composer_tool": "OutputSummarizationComposer",
            "chunk_size": 1000,
            "focus_areas": "key findings, results",
            "max_summary_length": 500
        }
        
        hook = SummarizationHook(
            config={"hook_config": hook_config},
            tooluniverse=mock_tu
        )
        
        # Should handle error gracefully
        long_text = "This is a very long text. " * 100
        result = hook.process(long_text)
        
        # Should return original text on error
        self.assertEqual(result, long_text)

    def test_hook_with_different_output_types(self):
        """Test hook with different output types"""
        from tooluniverse.output_hook import SummarizationHook
        
        # Create a mock tooluniverse
        mock_tu = MagicMock()
        mock_tu.callable_functions = {
            "OutputSummarizationComposer": MagicMock()
        }
        mock_tu.run_one_function.return_value = "Summarized content"
        
        hook_config = {
            "composer_tool": "OutputSummarizationComposer",
            "chunk_size": 1000,
            "focus_areas": "key findings, results",
            "max_summary_length": 500
        }
        
        hook = SummarizationHook(
            config={"hook_config": hook_config},
            tooluniverse=mock_tu
        )
        
        # Test with string
        string_output = "This is a string output. " * 50
        result = hook.process(string_output)
        self.assertIsInstance(result, str)
        
        # Test with dict
        dict_output = {"data": "This is a dict output. " * 50}
        result = hook.process(dict_output)
        self.assertIsInstance(result, (str, dict))


if __name__ == "__main__":
    unittest.main()
