#!/usr/bin/env python3
"""
Tests for BaseTool.run() parameter passing.

This module tests that run_one_function parameters (stream_callback, use_cache, validate)
are correctly passed to tool instances.
"""

import json
import threading

import pytest
from unittest.mock import Mock, MagicMock
from tooluniverse import ToolUniverse
from tooluniverse.base_tool import BaseTool


@pytest.mark.unit
class TestRunParameterPassing:
    """Test that parameters are correctly passed to tool.run()"""

    def setup_method(self):
        """Set up test fixtures."""
        self.tu = ToolUniverse()

    def test_tool_receives_all_parameters(self):
        """Test that a tool can receive all run_one_function parameters."""
        
        # Create a mock tool that accepts all parameters
        class MockTool(BaseTool):
            def __init__(self, tool_config):
                super().__init__(tool_config)
                self.called_with = None
            
            def run(self, arguments=None, stream_callback=None, use_cache=False, validate=True):
                self.called_with = {
                    "arguments": arguments,
                    "stream_callback": stream_callback,
                    "use_cache": use_cache,
                    "validate": validate
                }
                return {"result": "success"}
        
        # Create and register the tool
        tool_config = {
            "name": "test_tool",
            "type": "MockTool",
            "description": "Test tool",
            "cacheable": False,
            "parameter": {
                "type": "object",
                "properties": {
                    "test_param": {"type": "string"}
                }
            }
        }
        
        tool_instance = MockTool(tool_config)
        self.tu.callable_functions["test_tool"] = tool_instance
        self.tu.all_tool_dict["test_tool"] = tool_config
        
        # Call with all parameters
        callback = Mock()
        _ = self.tu.run_one_function(
            {"name": "test_tool", "arguments": {"test_param": "value"}},
            stream_callback=callback,
            use_cache=True,
            validate=False
        )
        
        # Verify the tool received all parameters
        assert tool_instance.called_with is not None
        assert tool_instance.called_with["arguments"] == {"test_param": "value"}
        assert tool_instance.called_with["stream_callback"] == callback
        assert tool_instance.called_with["use_cache"] is True
        assert tool_instance.called_with["validate"] is False

    def test_backward_compatibility_simple_run(self):
        """Test that tools with simple run(arguments) still work."""
        
        # Create a tool with old-style run signature
        class OldStyleTool(BaseTool):
            def __init__(self, tool_config):
                super().__init__(tool_config)
                self.was_called = False
            
            def run(self, arguments=None):
                self.was_called = True
                return {"result": "old_style"}
        
        tool_config = {
            "name": "old_tool",
            "type": "OldStyleTool",
            "description": "Old style tool",
            "cacheable": False,
            "parameter": {"type": "object", "properties": {}}
        }
        
        tool_instance = OldStyleTool(tool_config)
        self.tu.callable_functions["old_tool"] = tool_instance
        self.tu.all_tool_dict["old_tool"] = tool_config
        
        # Call with new parameters - tool should still work
        result = self.tu.run_one_function(
            {"name": "old_tool", "arguments": {}},
            stream_callback=Mock(),
            use_cache=True,
            validate=False
        )
        
        # Verify the tool was called and worked
        assert tool_instance.was_called
        assert result == {"result": "old_style"}

    def test_partial_parameter_support(self):
        """Test tools that support some but not all parameters."""
        
        # Tool that only accepts stream_callback
        class PartialTool(BaseTool):
            def __init__(self, tool_config):
                super().__init__(tool_config)
                self.received_stream_callback = None
            
            def run(self, arguments=None, stream_callback=None):
                self.received_stream_callback = stream_callback
                return {"result": "partial"}
        
        tool_config = {
            "name": "partial_tool",
            "type": "PartialTool",
            "description": "Partial tool",
            "cacheable": False,
            "parameter": {"type": "object", "properties": {}}
        }
        
        tool_instance = PartialTool(tool_config)
        self.tu.callable_functions["partial_tool"] = tool_instance
        self.tu.all_tool_dict["partial_tool"] = tool_config
        
        # Call with all parameters
        callback = Mock()
        result = self.tu.run_one_function(
            {"name": "partial_tool", "arguments": {}},
            stream_callback=callback,
            use_cache=True,
            validate=False
        )
        
        # Tool should receive stream_callback but not use_cache/validate
        assert tool_instance.received_stream_callback == callback
        assert result == {"result": "partial"}

    def test_use_cache_parameter_awareness(self):
        """Test that tools can optimize based on use_cache parameter."""
        
        class CacheAwareTool(BaseTool):
            def __init__(self, tool_config):
                super().__init__(tool_config)
                self.used_cache_mode = None
            
            def run(self, arguments=None, use_cache=False, **kwargs):
                self.used_cache_mode = use_cache
                if use_cache:
                    return {"result": "cached_mode"}
                else:
                    return {"result": "fresh_mode"}
        
        tool_config = {
            "name": "cache_tool",
            "type": "CacheAwareTool",
            "description": "Cache aware tool",
            "cacheable": False,
            "parameter": {"type": "object", "properties": {}}
        }
        
        tool_instance = CacheAwareTool(tool_config)
        self.tu.callable_functions["cache_tool"] = tool_instance
        self.tu.all_tool_dict["cache_tool"] = tool_config
        
        # Test with cache enabled
        result1 = self.tu.run_one_function(
            {"name": "cache_tool", "arguments": {}},
            use_cache=True
        )
        assert tool_instance.used_cache_mode is True
        assert result1 == {"result": "cached_mode"}
        
        # Test with cache disabled
        result2 = self.tu.run_one_function(
            {"name": "cache_tool", "arguments": {}},
            use_cache=False
        )
        assert tool_instance.used_cache_mode is False
        assert result2 == {"result": "fresh_mode"}

    def test_validate_parameter_awareness(self):
        """Test that tools can know if validation was performed."""
        
        class ValidationAwareTool(BaseTool):
            def __init__(self, tool_config):
                super().__init__(tool_config)
                self.validation_status = None
            
            def run(self, arguments=None, validate=True, **kwargs):
                self.validation_status = validate
                if validate:
                    return {"result": "validated"}
                else:
                    return {"result": "unvalidated", "warning": "no validation"}
        
        tool_config = {
            "name": "validate_tool",
            "type": "ValidationAwareTool",
            "description": "Validation aware tool",
            "cacheable": False,
            "parameter": {"type": "object", "properties": {}}
        }
        
        tool_instance = ValidationAwareTool(tool_config)
        self.tu.callable_functions["validate_tool"] = tool_instance
        self.tu.all_tool_dict["validate_tool"] = tool_config
        
        # Test with validation enabled
        result1 = self.tu.run_one_function(
            {"name": "validate_tool", "arguments": {}},
            validate=True
        )
        assert tool_instance.validation_status is True
        assert result1 == {"result": "validated"}
        
        # Test with validation disabled
        result2 = self.tu.run_one_function(
            {"name": "validate_tool", "arguments": {}},
            validate=False
        )
        assert tool_instance.validation_status is False
        assert "warning" in result2

    def test_run_batch_parallel_preserves_order_and_cache_flag(self):
        """run() should support batched inputs and expose cache toggles."""

        class RecordingBatchTool(BaseTool):
            def __init__(self, tool_config):
                super().__init__(tool_config)
                self.use_cache_values = []
                self.lock = threading.Lock()

            def run(self, arguments=None, use_cache=False, **kwargs):
                with self.lock:
                    self.use_cache_values.append(use_cache)
                return {"value": arguments["value"]}

        tool_config = {
            "name": "batch_tool",
            "type": "RecordingBatchTool",
            "description": "Batch capable tool",
            "cacheable": False,
            "parameter": {
                "type": "object",
                "properties": {"value": {"type": "integer"}},
                "required": ["value"],
            },
        }

        tool_instance = RecordingBatchTool(tool_config)
        self.tu.callable_functions["batch_tool"] = tool_instance
        self.tu.all_tool_dict["batch_tool"] = tool_config

        function_calls = [
            {"name": "batch_tool", "arguments": {"value": i}} for i in range(10)
        ]

        messages = self.tu.run(
            function_calls,
            use_cache=True,
            max_workers=4,
            return_message=True,
        )

        assert messages[0]["role"] == "assistant"

        tool_messages = [msg for msg in messages[1:] if msg.get("role") == "tool"]
        assert len(tool_messages) == len(function_calls)

        observed_values = [
            json.loads(msg["content"])["content"]["value"] for msg in tool_messages
        ]
        assert observed_values == list(range(10))

        assert tool_instance.use_cache_values == [True] * len(function_calls)


class TestDynamicAPIParameterPassing:
    """Test parameter passing through dynamic API (tu.tools.*)"""

    def setup_method(self):
        """Set up test fixtures."""
        self.tu = ToolUniverse()

    def test_dynamic_api_passes_parameters(self):
        """Test that tu.tools.* API passes parameters correctly."""
        
        class DynamicTool(BaseTool):
            def __init__(self, tool_config):
                super().__init__(tool_config)
                self.params_received = None
            
            def run(self, arguments=None, stream_callback=None, use_cache=False, validate=True):
                self.params_received = {
                    "stream_callback": stream_callback,
                    "use_cache": use_cache,
                    "validate": validate
                }
                return {"result": "dynamic"}
        
        tool_config = {
            "name": "dynamic_test",
            "type": "DynamicTool",
            "description": "Dynamic test tool",
            "cacheable": False,
            "parameter": {"type": "object", "properties": {}}
        }
        
        tool_instance = DynamicTool(tool_config)
        self.tu.callable_functions["dynamic_test"] = tool_instance
        self.tu.all_tool_dict["dynamic_test"] = tool_config
        
        # Call through dynamic API
        callback = Mock()
        _ = self.tu.tools.dynamic_test(
            stream_callback=callback,
            use_cache=True,
            validate=False
        )
        
        # Verify parameters were passed
        assert tool_instance.params_received is not None
        assert tool_instance.params_received["stream_callback"] == callback
        assert tool_instance.params_received["use_cache"] is True
        assert tool_instance.params_received["validate"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
