"""Tests for error handling and recovery in dependency isolation."""

import pytest
from unittest.mock import patch, MagicMock
from tooluniverse.tool_registry import (
    mark_tool_unavailable,
    get_tool_errors,
    _TOOL_ERRORS,
)
from tooluniverse.execute_function import ToolUniverse


class TestErrorHandlingAndRecovery:
    """Test error handling and recovery mechanisms."""

    def setup_method(self):
        """Clear error registry before each test."""
        _TOOL_ERRORS.clear()

    def test_error_classification(self):
        """Test that different error types are properly classified."""
        # Test ImportError
        import_error = ImportError('No module named "torch"')
        mark_tool_unavailable("Tool1", import_error)
        
        # Test AttributeError
        attr_error = AttributeError("'NoneType' object has no attribute 'run'")
        mark_tool_unavailable("Tool2", attr_error)
        
        # Test generic Exception
        generic_error = Exception("Something went wrong")
        mark_tool_unavailable("Tool3", generic_error)
        
        errors = get_tool_errors()
        assert len(errors) == 3
        assert errors["Tool1"]["error_type"] == "ImportError"
        assert errors["Tool2"]["error_type"] == "AttributeError"
        assert errors["Tool3"]["error_type"] == "Exception"

    def test_missing_package_extraction_edge_cases(self):
        """Test edge cases in missing package extraction."""
        from tooluniverse.tool_registry import _extract_missing_package
        
        # Test various error message formats
        test_cases = [
            ('No module named "torch"', "torch"),
            ("No module named 'torch'", "torch"),
            ('No module named "torch.nn"', "torch"),
            ('No module named "torch.nn.functional"', "torch"),
            ('ModuleNotFoundError: No module named "test"', "test"),
            ('ImportError: No module named "test"', "test"),
            ('No module named "test"', "test"),
            ('No module named "test-package"', "test-package"),
            ('No module named "test_package"', "test_package"),
            ('No module named "test.package"', "test"),
            ('No module named "test-package.submodule"', "test-package"),
        ]
        
        for error_msg, expected in test_cases:
            result = _extract_missing_package(error_msg)
            assert result == expected, f"Failed for: {error_msg}"

    def test_error_persistence_across_instances(self):
        """Test that errors persist across ToolUniverse instances."""
        # Mark a tool as unavailable
        mark_tool_unavailable("PersistentTool", ImportError('No module named "test"'))
        
        try:
            # Create first instance
            tu1 = ToolUniverse()
            health1 = tu1.get_tool_health()
            assert "PersistentTool" in health1["unavailable_list"]
            
            # Create second instance
            tu2 = ToolUniverse()
            health2 = tu2.get_tool_health()
            assert "PersistentTool" in health2["unavailable_list"]
            
            # Should be the same error
            assert health1["details"]["PersistentTool"] == health2["details"]["PersistentTool"]
        finally:
            if 'tu1' in locals():
                tu1.close()
            if 'tu2' in locals():
                tu2.close()

    def test_error_clearing_and_recovery(self):
        """Test clearing errors and system recovery."""
        # Mark tools as unavailable
        mark_tool_unavailable("Tool1", ImportError('No module named "test1"'))
        mark_tool_unavailable("Tool2", ImportError('No module named "test2"'))
        
        # Verify errors exist
        errors = get_tool_errors()
        assert len(errors) == 2
        
        # Clear errors
        _TOOL_ERRORS.clear()
        
        # Verify errors are gone
        errors = get_tool_errors()
        assert len(errors) == 0
        
        try:
            # System should be clean
            tu = ToolUniverse()
            health = tu.get_tool_health()
            assert health["unavailable"] == 0
        finally:
            if 'tu' in locals():
                tu.close()

    def test_partial_error_recovery(self):
        """Test recovering from some errors while keeping others."""
        # Mark multiple tools as unavailable
        mark_tool_unavailable("Tool1", ImportError('No module named "test1"'))
        mark_tool_unavailable("Tool2", ImportError('No module named "test2"'))
        mark_tool_unavailable("Tool3", ImportError('No module named "test3"'))
        
        # Verify all errors exist
        errors = get_tool_errors()
        assert len(errors) == 3
        
        # Remove one error (simulating fix)
        del _TOOL_ERRORS["Tool2"]
        
        # Verify partial recovery
        errors = get_tool_errors()
        assert len(errors) == 2
        assert "Tool1" in errors
        assert "Tool2" not in errors
        assert "Tool3" in errors

    def test_error_details_completeness(self):
        """Test that error details contain all necessary information."""
        error = ImportError('No module named "torch"')
        mark_tool_unavailable("TestTool", error, "test_module")
        
        errors = get_tool_errors()
        tool_error = errors["TestTool"]
        
        # Should contain all required fields
        required_fields = ["error", "error_type", "module", "missing_package"]
        for field in required_fields:
            assert field in tool_error
        
        # Should have correct values
        assert tool_error["error"] == 'No module named "torch"'
        assert tool_error["error_type"] == "ImportError"
        assert tool_error["module"] == "test_module"
        assert tool_error["missing_package"] == "torch"

    def test_error_handling_with_none_values(self):
        """Test error handling with None values."""
        # Test with None module
        error = ImportError('No module named "test"')
        mark_tool_unavailable("TestTool", error, None)
        
        errors = get_tool_errors()
        assert errors["TestTool"]["module"] is None
        
        # Test with empty string module
        mark_tool_unavailable("TestTool2", error, "")
        errors = get_tool_errors()
        assert errors["TestTool2"]["module"] == ""

    def test_concurrent_error_tracking(self):
        """Test error tracking under concurrent access."""
        import threading
        import time
        
        errors_added = []
        
        def add_error(tool_name, error_msg):
            error = ImportError(error_msg)
            mark_tool_unavailable(tool_name, error)
            errors_added.append(tool_name)
        
        # Create multiple threads adding errors
        threads = []
        for i in range(10):
            thread = threading.Thread(
                target=add_error, 
                args=(f"ConcurrentTool{i}", f'No module named "test{i}"')
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify all errors were added
        errors = get_tool_errors()
        assert len(errors) == 10
        
        # Verify all expected tools are present
        for i in range(10):
            assert f"ConcurrentTool{i}" in errors

    def test_error_registry_isolation(self):
        """Test that error registry is properly isolated."""
        # Clear registry
        _TOOL_ERRORS.clear()
        
        # Add some errors
        mark_tool_unavailable("Tool1", ImportError('No module named "test1"'))
        mark_tool_unavailable("Tool2", ImportError('No module named "test2"'))
        
        # Get copy
        errors_copy = get_tool_errors()
        
        # Modify the copy
        errors_copy["Tool3"] = {"error": "test", "error_type": "Test"}
        
        # Original should be unchanged
        original_errors = get_tool_errors()
        assert "Tool3" not in original_errors
        assert len(original_errors) == 2

    def test_error_message_truncation(self):
        """Test handling of very long error messages."""
        # Create a very long error message with proper format
        long_error_msg = 'No module named "' + "very_long_package_name_" * 100 + '"'
        error = ImportError(long_error_msg)
        
        mark_tool_unavailable("LongErrorTool", error)
        
        errors = get_tool_errors()
        tool_error = errors["LongErrorTool"]
        
        # Should store the full error message
        assert len(tool_error["error"]) > 1000
        assert "very_long_package_name_" in tool_error["error"]
        
        # Should extract package name correctly (first part only)
        expected_package = "very_long_package_name_" * 100
        assert tool_error["missing_package"] == expected_package

    def test_special_characters_in_error_messages(self):
        """Test handling of special characters in error messages."""
        special_chars = [
            'No module named "test-package"',
            'No module named "test_package"',
            'No module named "test.package"',
            'No module named "test+package"',
            'No module named "test/package"',
            'No module named "test\\package"',
        ]
        
        for i, error_msg in enumerate(special_chars):
            error = ImportError(error_msg)
            mark_tool_unavailable(f"SpecialTool{i}", error)
        
        errors = get_tool_errors()
        assert len(errors) == len(special_chars)
        
        # Verify package names are extracted correctly
        for i, error_msg in enumerate(special_chars):
            tool_name = f"SpecialTool{i}"
            expected_package = error_msg.split('"')[1].split('.')[0]
            assert errors[tool_name]["missing_package"] == expected_package
