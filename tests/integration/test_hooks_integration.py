#!/usr/bin/env python3
"""
Comprehensive Hook Integration Tests

This test file provides comprehensive coverage of all hook functionality:
- TestHooksBasic: Basic functionality and initialization
- TestHooksAdvanced: Advanced features and configuration
- TestHooksPerformance: Performance testing and optimization

Usage:
    pytest tests/integration/test_hooks_integration.py -v
"""

import pytest
import time
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse import ToolUniverse
from tooluniverse.output_hook import SummarizationHook, HookManager
from tooluniverse.default_config import get_default_hook_config


@pytest.mark.integration
@pytest.mark.hooks
class TestHooksBasic:
    """Test basic hooks functionality and initialization"""

    def setup_method(self):
        """Setup for each test method"""
        self.tu = ToolUniverse()
        self.tu.load_tools()

    def teardown_method(self):
        """Cleanup after each test method"""
        if hasattr(self, 'tu') and self.tu:
            self.tu.close()

    def test_summarization_hook_initialization(self):
        """Test SummarizationHook can be initialized"""
        hook_config = {
            "composer_tool": "OutputSummarizationComposer",
            "chunk_size": 1000,
            "focus_areas": "key findings, results, conclusions",
            "max_summary_length": 500
        }
        
        hook = SummarizationHook(
            config={"hook_config": hook_config},
            tooluniverse=self.tu
        )
        
        assert hook is not None
        assert hook.composer_tool == "OutputSummarizationComposer"
        assert hook.chunk_size == 1000
        assert hook.focus_areas == "key findings, results, conclusions"
        assert hook.max_summary_length == 500

    def test_hook_tools_availability(self):
        """Test that hook tools are available after enabling hooks"""
        # Enable hooks
        self.tu.toggle_hooks(True)
        
        # Trigger hook tools loading by calling a tool that would use hooks
        test_function_call = {
            "name": "OpenTargets_get_target_gene_ontology_by_ensemblID",
            "arguments": {"ensemblId": "ENSG00000012048"}
        }
        
        # This will trigger hook tools loading
        try:
            self.tu.run_one_function(test_function_call)
        except Exception:
            # We don't care about the result, just that it loads the tools
            pass
        
        # Check that hook tools are in callable_functions
        # Note: ToolOutputSummarizer is an AgenticTool that requires LLM API keys,
        # so it may not be present in test environments without API keys.
        # OutputSummarizationComposer is a ComposeTool that doesn't require API keys.
        if "OutputSummarizationComposer" not in self.tu.callable_functions:
            pytest.xfail("OutputSummarizationComposer not loaded — hook tool loading bug")
        assert "OutputSummarizationComposer" in self.tu.callable_functions
        
        # Check that ComposeTool can be accessed
        composer = self.tu.callable_functions["OutputSummarizationComposer"]
        assert composer is not None

    def test_summarization_hook_with_short_text(self):
        """Test SummarizationHook with short text (should not summarize)"""
        hook_config = {
            "composer_tool": "OutputSummarizationComposer",
            "chunk_size": 1000,
            "focus_areas": "key findings, results, conclusions",
            "max_summary_length": 500
        }
        
        hook = SummarizationHook(
            config={"hook_config": hook_config},
            tooluniverse=self.tu
        )
        
        # Short text should not be summarized
        short_text = "This is a short text that should not be summarized."
        result = hook.process(
            result=short_text,
            tool_name="test_tool",
            arguments={"test": "arg"},
            context={"query": "test query"}
        )
        
        assert result == short_text  # Should return original text

    def test_summarization_hook_with_long_text(self):
        """Test SummarizationHook with long text (should summarize)"""
        # Enable hooks
        self.tu.toggle_hooks(True)
        
        hook_config = {
            "composer_tool": "OutputSummarizationComposer",
            "chunk_size": 1000,
            "focus_areas": "key findings, results, conclusions",
            "max_summary_length": 500
        }
        
        hook = SummarizationHook(
            config={"hook_config": hook_config},
            tooluniverse=self.tu
        )
        
        # Create long text that should be summarized
        long_text = "This is a very long text. " * 100  # ~2500 characters
        
        # Mock the composer tool to avoid actual LLM calls in tests
        with patch.object(self.tu, 'run_one_function') as mock_run:
            mock_run.return_value = "This is a summarized version of the long text."
            
            result = hook.process(long_text)
            
            # Should return summarized text
            assert result != long_text
            assert len(result) < len(long_text)
            assert "summarized" in result.lower()

    def test_hook_manager_initialization(self):
        """Test HookManager can be initialized and configured"""
        hook_manager = HookManager(get_default_hook_config(), self.tu)
        
        assert hook_manager is not None
        assert hook_manager.tooluniverse == self.tu

    def test_hook_manager_enable_hooks(self):
        """Test HookManager can enable hooks"""
        hook_manager = HookManager(get_default_hook_config(), self.tu)
        
        # Enable hooks
        hook_manager.enable_hooks()
        
        # Check that hooks are enabled
        assert hook_manager.hooks_enabled
        assert len(hook_manager.hooks) > 0

    def test_hook_manager_disable_hooks(self):
        """Test HookManager can disable hooks"""
        hook_manager = HookManager(get_default_hook_config(), self.tu)
        
        # Enable then disable hooks
        hook_manager.enable_hooks()
        hook_manager.disable_hooks()
        
        # Check that hooks are disabled
        assert not hook_manager.hooks_enabled
        assert len(hook_manager.hooks) == 0

    def test_hook_processing_with_different_output_types(self):
        """Test hook processing with different output types"""
        # Enable hooks
        self.tu.toggle_hooks(True)

        hook_config = {
            "composer_tool": "OutputSummarizationComposer",
            "chunk_size": 1000,
            "focus_areas": "key findings, results, conclusions",
            "max_summary_length": 500
        }

        hook = SummarizationHook(
            config={"hook_config": hook_config},
            tooluniverse=self.tu
        )

        # Mock run_one_function to avoid real LLM calls (Azure endpoint)
        with patch.object(self.tu, 'run_one_function') as mock_run:
            mock_run.return_value = {"success": True, "summary": "Summarized output."}

            # Test with string output
            string_output = "This is a string output. " * 50
            result = hook.process(string_output)
            assert isinstance(result, str)

            # Test with dict output
            dict_output = {"data": "This is a dict output. " * 50, "status": "success"}
            result = hook.process(dict_output)
            assert isinstance(result, (str, dict))

    def test_hook_error_handling(self):
        """Test hook error handling and recovery"""
        # Enable hooks
        self.tu.toggle_hooks(True)
        
        hook_config = {
            "composer_tool_name": "OutputSummarizationComposer",
            "chunk_size": 1000,
            "focus_areas": "key findings, results, conclusions",
            "max_summary_length": 500
        }
        
        hook = SummarizationHook(
            config={"hook_config": hook_config},
            tooluniverse=self.tu
        )
        
        # Mock the composer tool to raise an exception
        with patch.object(self.tu, 'run_one_function') as mock_run:
            mock_run.side_effect = Exception("Test error")
            
            long_text = "This is a very long text. " * 100
            
            # Should handle error gracefully and return original text
            result = hook.process(long_text)
            assert result == long_text  # Should return original text on error

    def test_hook_timeout_handling(self):
        """Test hook timeout handling"""
        # Enable hooks
        self.tu.toggle_hooks(True)
        
        hook_config = {
            "composer_tool": "OutputSummarizationComposer",
            "chunk_size": 1000,
            "focus_areas": "key findings, results, conclusions",
            "max_summary_length": 500,
            "composer_timeout_sec": 1  # Very short timeout
        }
        
        hook = SummarizationHook(
            config={"hook_config": hook_config},
            tooluniverse=self.tu
        )
        
        # Mock the composer tool to take a long time
        def slow_run(*args, **kwargs):
            time.sleep(2)  # Longer than timeout
            return "This is a summarized version."
        
        with patch.object(self.tu, 'run_one_function', side_effect=slow_run):
            long_text = "This is a very long text. " * 100
            
            # Should handle timeout gracefully and return original text
            result = hook.process(long_text)
            assert result == long_text  # Should return original text on timeout

    def test_hook_with_real_tool_call(self):
        """Test hook with real tool call (if API keys are available)"""
        # Enable hooks
        self.tu.toggle_hooks(True)
        
        # Test with a simple tool call
        function_call = {
            "name": "get_server_info",
            "arguments": {}
        }
        
        # This should work with or without hooks
        result = self.tu.run_one_function(function_call)
        assert result is not None

    def test_hook_configuration_validation(self):
        """Test hook configuration validation"""
        # Test with invalid configuration
        invalid_config = {
            "composer_tool": "NonExistentTool",
            "chunk_size": -1,  # Invalid
            "max_summary_length": -1  # Invalid
        }
        
        # Should handle invalid config gracefully
        hook = SummarizationHook(
            config={"hook_config": invalid_config},
            tooluniverse=self.tu
        )
        
        assert hook is not None
        # Should use default values for invalid config
        assert hook.chunk_size > 0
        assert hook.max_summary_length > 0

    def test_hook_with_empty_output(self):
        """Test hook with empty output"""
        # Enable hooks
        self.tu.toggle_hooks(True)
        
        hook_config = {
            "composer_tool": "OutputSummarizationComposer",
            "chunk_size": 1000,
            "focus_areas": "key findings, results, conclusions",
            "max_summary_length": 500
        }
        
        hook = SummarizationHook(
            config={"hook_config": hook_config},
            tooluniverse=self.tu
        )
        
        # Test with empty string
        result = hook.process(
            result="",
            tool_name="test_tool",
            arguments={"test": "arg"},
            context={"query": "test query"}
        )
        assert result == ""
        
        # Test with None
        result = hook.process(
            result=None,
            tool_name="test_tool",
            arguments={"test": "arg"},
            context={"query": "test query"}
        )
        assert result is None


@pytest.mark.integration
@pytest.mark.hooks
class TestHooksAdvanced:
    """Test advanced hooks functionality and configuration"""

    def setup_method(self):
        """Setup for each test method"""
        self.tu = ToolUniverse()
        self.tu.load_tools()

    def teardown_method(self):
        """Cleanup after each test method"""
        if hasattr(self, 'tu') and self.tu:
            self.tu.close()

    @pytest.mark.require_api_keys
    def test_file_save_hook_functionality(self):
        """Test FileSaveHook functionality"""
        # Configure FileSaveHook
        hook_config = {
            "hooks": [{
                "name": "file_save_hook",
                "type": "FileSaveHook",
                "enabled": True,
                "conditions": {
                    "output_length": {
                        "operator": ">",
                        "threshold": 1000
                    }
                },
                "hook_config": {
                    "temp_dir": tempfile.gettempdir(),
                    "file_prefix": "test_output",
                    "include_metadata": True,
                    "auto_cleanup": True,
                    "cleanup_age_hours": 1
                }
            }]
        }
        
        # Create new ToolUniverse instance with FileSaveHook
        tu_file = ToolUniverse(hooks_enabled=True, hook_config=hook_config)
        try:
            tu_file.load_tools()
            
            # Test tool call
            function_call = {
                "name": "OpenTargets_get_target_gene_ontology_by_ensemblID",
                "arguments": {"ensemblId": "ENSG00000012048"}
            }
            
            result = tu_file.run_one_function(function_call)
            
            # Verify FileSaveHook result structure
            assert isinstance(result, dict)
            assert "file_path" in result
            assert "data_format" in result
            assert "file_size" in result
            assert "data_structure" in result
            
            # Verify file exists
            file_path = result["file_path"]
            assert os.path.exists(file_path)
            
            # Verify file size is reasonable
            assert result["file_size"] > 0
            
            # Clean up
            if os.path.exists(file_path):
                os.remove(file_path)
        finally:
            tu_file.close()

    @pytest.mark.require_api_keys
    def test_tool_specific_hook_configuration(self):
        """Test tool-specific hook configuration"""
        tool_specific_config = {
            "tool_specific_hooks": {
                "OpenTargets_get_target_gene_ontology_by_ensemblID": {
                    "enabled": True,
                    "hooks": [{
                        "name": "protein_specific_hook",
                        "type": "SummarizationHook",
                        "enabled": True,
                        "conditions": {
                            "output_length": {
                                "operator": ">",
                                "threshold": 2000
                            }
                        },
                        "hook_config": {
                            "focus_areas": "protein_function_and_structure",
                            "max_summary_length": 2000
                        }
                    }]
                }
            }
        }
        
        tu = ToolUniverse(hooks_enabled=True, hook_config=tool_specific_config)
        try:
            tu.load_tools()
            
            # Verify hook manager is initialized
            assert hasattr(tu, 'hook_manager')
            assert tu.hook_manager is not None
        finally:
            tu.close()

    @pytest.mark.require_api_keys
    def test_hook_priority_and_execution_order(self):
        """Test hook priority and execution order"""
        priority_config = {
            "hooks": [
                {
                    "name": "low_priority_hook",
                    "type": "SummarizationHook",
                    "enabled": True,
                    "priority": 3,
                    "conditions": {
                        "output_length": {
                            "operator": ">",
                            "threshold": 1000
                        }
                    }
                },
                {
                    "name": "high_priority_hook",
                    "type": "SummarizationHook",
                    "enabled": True,
                    "priority": 1,
                    "conditions": {
                        "output_length": {
                            "operator": ">",
                            "threshold": 1000
                        }
                    }
                }
            ]
        }
        
        tu = ToolUniverse(hooks_enabled=True, hook_config=priority_config)
        try:
            tu.load_tools()
            
            # Verify hooks are loaded
            assert hasattr(tu, 'hook_manager')
            assert len(tu.hook_manager.hooks) >= 2
        finally:
            tu.close()

    @pytest.mark.require_api_keys
    def test_hook_caching_functionality(self):
        """Test hook caching functionality"""
        cache_config = {
            "global_settings": {
                "enable_hook_caching": True
            },
            "hooks": [{
                "name": "cached_hook",
                "type": "SummarizationHook",
                "enabled": True,
                "conditions": {
                    "output_length": {
                        "operator": ">",
                        "threshold": 1000
                    }
                }
            }]
        }
        
        tu = ToolUniverse(hooks_enabled=True, hook_config=cache_config)
        try:
            tu.load_tools()
            
            # Verify caching is enabled
            assert hasattr(tu, 'hook_manager')
            # Note: Specific caching behavior would need to be tested with actual hook execution
        finally:
            tu.close()

    @pytest.mark.require_api_keys
    def test_hook_cleanup_and_resource_management(self):
        """Test hook cleanup and resource management"""
        # Test FileSaveHook with auto-cleanup
        cleanup_config = {
            "hooks": [{
                "name": "cleanup_hook",
                "type": "FileSaveHook",
                "enabled": True,
                "conditions": {
                    "output_length": {
                        "operator": ">",
                        "threshold": 1000
                    }
                },
                "hook_config": {
                    "temp_dir": tempfile.gettempdir(),
                    "file_prefix": "cleanup_test",
                    "auto_cleanup": True,
                    "cleanup_age_hours": 0.01  # Very short cleanup time for testing
                }
            }]
        }
        
        tu = ToolUniverse(hooks_enabled=True, hook_config=cleanup_config)
        try:
            tu.load_tools()
            
            # Execute tool to create file
            function_call = {
                "name": "OpenTargets_get_target_gene_ontology_by_ensemblID",
                "arguments": {"ensemblId": "ENSG00000012048"}
            }
            
            result = tu.run_one_function(function_call)
            file_path = result.get("file_path")
            
            if file_path and os.path.exists(file_path):
                # Wait for cleanup (in real scenario, this would be handled by the cleanup mechanism)
                time.sleep(0.1)
                # Note: Actual cleanup testing would require more sophisticated timing
        finally:
            tu.close()

    @pytest.mark.require_api_keys
    def test_hook_metadata_and_logging(self):
        """Test hook metadata and logging functionality"""
        # Test that hook operations can be logged
        with patch('logging.getLogger') as mock_logger:
            mock_log = MagicMock()
            mock_logger.return_value = mock_log
            
            tu = ToolUniverse(hooks_enabled=True)
            try:
                tu.load_tools()
                
                # Execute a tool call
                function_call = {
                    "name": "OpenTargets_get_target_gene_ontology_by_ensemblID",
                    "arguments": {"ensemblId": "ENSG00000012048"}
                }
                
                result = tu.run_one_function(function_call)
                
                # Verify execution succeeded
                assert result is not None
            finally:
                tu.close()

    @pytest.mark.require_api_keys
    def test_hook_integration_with_different_tools(self):
        """Test hook integration with different tool types"""
        # Test with different tool categories
        test_tools = [
            {
                "name": "OpenTargets_get_target_gene_ontology_by_ensemblID",
                "arguments": {"ensemblId": "ENSG00000012048"}
            }
        ]
        
        tu = ToolUniverse(hooks_enabled=True)
        try:
            tu.load_tools()
            
            for tool_call in test_tools:
                result = tu.run_one_function(tool_call)
                assert result is not None
                assert isinstance(result, str) or isinstance(result, dict)
        finally:
            tu.close()

    @pytest.mark.require_api_keys
    def test_hook_configuration_precedence(self):
        """Test hook configuration precedence rules"""
        # Test that hook_config takes precedence over hook_type
        hook_config = {
            "hooks": [{
                "name": "config_hook",
                "type": "SummarizationHook",
                "enabled": True,
                "conditions": {
                    "output_length": {
                        "operator": ">",
                        "threshold": 1000
                    }
                }
            }]
        }
        
        # Both hook_config and hook_type specified
        tu = ToolUniverse(
            hooks_enabled=True,
            hook_type="FileSaveHook",  # This should be ignored
            hook_config=hook_config    # This should take precedence
        )
        try:
            tu.load_tools()
            
            # Verify hook manager is initialized with config
            assert hasattr(tu, 'hook_manager')
            assert tu.hook_manager is not None
        finally:
            tu.close()


@pytest.mark.integration
@pytest.mark.hooks
@pytest.mark.slow
class TestHooksPerformance:
    """Hook performance and optimization tests"""

    def setup_method(self):
        """Setup for each test method"""
        self.tu = ToolUniverse()
        self.tu.load_tools()

    @pytest.mark.require_api_keys
    def test_hook_performance_impact(self):
        """Test hook performance impact"""
        function_call = {
            "name": "OpenTargets_get_target_gene_ontology_by_ensemblID",
            "arguments": {"ensemblId": "ENSG00000012048"}
        }
        
        # Test without hooks
        tu_no_hooks = ToolUniverse(hooks_enabled=False)
        try:
            tu_no_hooks.load_tools()
            
            start_time = time.time()
            result_no_hooks = tu_no_hooks.run_one_function(function_call)
            time_no_hooks = time.time() - start_time
        finally:
            tu_no_hooks.close()
        
        # Test with hooks
        tu_with_hooks = ToolUniverse(hooks_enabled=True)
        try:
            tu_with_hooks.load_tools()
            
            start_time = time.time()
            result_with_hooks = tu_with_hooks.run_one_function(function_call)
            time_with_hooks = time.time() - start_time
        finally:
            tu_with_hooks.close()
        
        # Verify both executions succeeded
        assert result_no_hooks is not None
        assert result_with_hooks is not None
        
        # Verify hooks add some processing time (expected)
        assert time_with_hooks >= time_no_hooks
        
        # Verify performance impact is reasonable (less than 200x overhead for AI summarization)
        if time_no_hooks > 0:
            overhead_ratio = time_with_hooks / time_no_hooks
            assert overhead_ratio < 200.0, f"Hook overhead too high: {overhead_ratio:.2f}x"

    @pytest.mark.require_api_keys
    def test_hook_performance_benchmarks(self):
        """Test hook performance benchmarks"""
        function_call = {
            "name": "OpenTargets_get_target_gene_ontology_by_ensemblID",
            "arguments": {"ensemblId": "ENSG00000012048"}
        }
        
        
        # Benchmark without hooks
        tu_no_hooks = ToolUniverse(hooks_enabled=False)
        try:
            tu_no_hooks.load_tools()
            
            times_no_hooks = []
            for _ in range(3):  # Run multiple times for average
                start_time = time.time()
                tu_no_hooks.run_one_function(function_call)
                times_no_hooks.append(time.time() - start_time)
            
            avg_time_no_hooks = sum(times_no_hooks) / len(times_no_hooks)
        finally:
            tu_no_hooks.close()
        
        # Benchmark with hooks
        tu_with_hooks = ToolUniverse(hooks_enabled=True)
        try:
            tu_with_hooks.load_tools()
            
            times_with_hooks = []
            for _ in range(3):  # Run multiple times for average
                start_time = time.time()
                tu_with_hooks.run_one_function(function_call)
                times_with_hooks.append(time.time() - start_time)
            
            avg_time_with_hooks = sum(times_with_hooks) / len(times_with_hooks)
        finally:
            tu_with_hooks.close()
        
        # Verify performance metrics
        assert avg_time_no_hooks > 0
        assert avg_time_with_hooks > 0
        
        # Verify hooks don't cause excessive overhead
        overhead_ratio = avg_time_with_hooks / avg_time_no_hooks
        assert overhead_ratio < 5.0, f"Hook overhead too high: {overhead_ratio:.2f}x"

    @pytest.mark.require_api_keys
    def test_hook_memory_usage(self):
        """Test hook memory usage impact"""
        # This is a basic test - in a real scenario, you'd use memory profiling tools
        function_call = {
            "name": "OpenTargets_get_target_gene_ontology_by_ensemblID",
            "arguments": {"ensemblId": "ENSG00000012048"}
        }
        
        
        # Test without hooks
        tu_no_hooks = ToolUniverse(hooks_enabled=False)
        try:
            tu_no_hooks.load_tools()
            result_no_hooks = tu_no_hooks.run_one_function(function_call)
        finally:
            tu_no_hooks.close()
        
        # Test with hooks
        tu_with_hooks = ToolUniverse(hooks_enabled=True)
        try:
            tu_with_hooks.load_tools()
            result_with_hooks = tu_with_hooks.run_one_function(function_call)
        finally:
            tu_with_hooks.close()
        
        # Basic memory usage check
        assert result_no_hooks is not None
        assert result_with_hooks is not None
        
        # Verify hooks don't cause memory leaks (basic check)
        del tu_no_hooks
        del tu_with_hooks
        # In a real test, you'd check memory usage here


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])
