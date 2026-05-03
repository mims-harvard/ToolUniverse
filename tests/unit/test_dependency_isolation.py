"""Unit tests for dependency isolation functionality."""

import pytest
from unittest.mock import patch, MagicMock
from tooluniverse.tool_registry import (
    mark_tool_unavailable,
    get_tool_errors,
    _extract_missing_package,
    _TOOL_ERRORS,
)
from tooluniverse.execute_function import ToolUniverse


class TestDependencyIsolation:
    """Test dependency isolation and error tracking functionality."""

    def setup_method(self):
        """Clear error registry before each test."""
        _TOOL_ERRORS.clear()

    def test_extract_missing_package(self):
        """Test extraction of missing package names from ImportError messages."""
        # Test standard ImportError message
        error_msg = 'No module named "torch"'
        assert _extract_missing_package(error_msg) == "torch"
        
        # Test with single quotes
        error_msg = "No module named 'admet_ai'"
        assert _extract_missing_package(error_msg) == "admet_ai"
        
        # Test with submodule
        error_msg = 'No module named "torch.nn"'
        assert _extract_missing_package(error_msg) == "torch"
        
        # Test non-ImportError message
        error_msg = "Some other error"
        assert _extract_missing_package(error_msg) is None
        
        # Test empty message
        assert _extract_missing_package("") is None

    def test_mark_tool_unavailable(self):
        """Test marking tools as unavailable."""
        # Test with ImportError
        error = ImportError('No module named "torch"')
        mark_tool_unavailable("TestTool", error, "test_module")
        
        errors = get_tool_errors()
        assert "TestTool" in errors
        assert errors["TestTool"]["error"] == 'No module named "torch"'
        assert errors["TestTool"]["error_type"] == "ImportError"
        assert errors["TestTool"]["module"] == "test_module"
        assert errors["TestTool"]["missing_package"] == "torch"

    def test_mark_tool_unavailable_without_module(self):
        """Test marking tools as unavailable without module info."""
        error = ImportError('No module named "admet_ai"')
        mark_tool_unavailable("TestTool2", error)
        
        errors = get_tool_errors()
        assert "TestTool2" in errors
        assert errors["TestTool2"]["module"] is None
        assert errors["TestTool2"]["missing_package"] == "admet_ai"

    def test_get_tool_errors_returns_copy(self):
        """Test that get_tool_errors returns a copy, not the original dict."""
        error = ImportError('No module named "test"')
        mark_tool_unavailable("TestTool3", error)
        
        errors1 = get_tool_errors()
        errors2 = get_tool_errors()
        
        # Should be different objects
        assert errors1 is not errors2
        # But should have same content
        assert errors1 == errors2

    def test_multiple_tool_failures(self):
        """Test tracking multiple tool failures."""
        errors = [
            ImportError('No module named "torch"'),
            ImportError('No module named "admet_ai"'),
            ImportError('No module named "nonexistent"'),
        ]
        
        for i, error in enumerate(errors):
            mark_tool_unavailable(f"Tool{i}", error)
        
        tool_errors = get_tool_errors()
        assert len(tool_errors) == 3
        assert "Tool0" in tool_errors
        assert "Tool1" in tool_errors
        assert "Tool2" in tool_errors

    def test_tool_universe_get_tool_health_no_tools(self):
        """Test get_tool_health after explicitly clearing all tools."""
        try:
            tu = ToolUniverse()
            # clear_tools() resets to a clean empty state regardless of
            # workspace auto-load (Phase 11 behaviour)
            tu.clear_tools()
            health = tu.get_tool_health()

            assert health["total"] == 0
            assert health["available"] == 0
            assert health["unavailable"] == 0
            assert health["unavailable_list"] == []
            assert health["details"] == {}
        finally:
            tu.close()

    def test_tool_universe_get_tool_health_specific_tool(self):
        """Test get_tool_health for specific tool."""
        try:
            tu = ToolUniverse()
            
            # Test non-existent tool
            health = tu.get_tool_health("NonExistentTool")
            assert health["available"] is False
            assert health["error"] == "Not found"
            
            # Test tool with error
            mark_tool_unavailable("BrokenTool", ImportError('No module named "test"'))
            health = tu.get_tool_health("BrokenTool")
            # For tools with errors, it returns the error details directly
            assert "error" in health
            assert "error_type" in health
            assert "missing_package" in health
            assert health["error"] == 'No module named "test"'
        finally:
            tu.close()

    def test_tool_universe_get_tool_health_with_loaded_tools(self):
        """Test get_tool_health with loaded tools."""
        try:
            tu = ToolUniverse()
            tu.load_tools()
            
            health = tu.get_tool_health()
            assert health["total"] > 0
            assert health["available"] >= 0
            assert health["unavailable"] >= 0
            assert health["total"] == health["available"] + health["unavailable"]
        finally:
            tu.close()

    @patch('tooluniverse.execute_function.get_tool_class_lazy')
    def test_init_tool_handles_failure_gracefully(self, mock_get_tool_class):
        """Test that init_tool handles failures gracefully."""
        try:
            tu = ToolUniverse()
            
            # Mock tool class that raises exception
            mock_tool_class = MagicMock()
            mock_tool_class.side_effect = ImportError('No module named "test"')
            mock_get_tool_class.return_value = mock_tool_class
            
            # Should return None instead of raising
            result = tu.init_tool(tool_name="TestTool")
            assert result is None
            
            # Should have recorded the error
            errors = get_tool_errors()
            assert "TestTool" in errors
        finally:
            tu.close()

    @patch('tooluniverse.execute_function.get_tool_class_lazy')
    def test_get_tool_instance_checks_error_registry(self, mock_get_tool_class):
        """Test that _get_tool_instance checks error registry."""
        try:
            tu = ToolUniverse()
            
            # Mark a tool as unavailable
            mark_tool_unavailable("BrokenTool", ImportError('No module named "test"'))
            
            # Mock tool config
            tu.all_tool_dict["BrokenTool"] = {"type": "BrokenTool", "name": "BrokenTool"}
            
            # Should return None without trying to initialize
            result = tu._get_tool_instance("BrokenTool")
            assert result is None
            
            # Should not have called get_tool_class_lazy
            mock_get_tool_class.assert_not_called()
        finally:
            tu.close()

    def test_get_tool_instance_caches_successful_tools(self):
        """Test that successful tools are cached."""
        try:
            tu = ToolUniverse()
            # Load only a small subset of tools to avoid timeout
            tu.load_tools(include_tools=[
                "UniProt_get_entry_by_accession", 
                "ChEMBL_get_molecule_by_chembl_id"
            ])
            
            # Find a tool that can be successfully initialized
            successful_tool = None
            for tool_name in list(tu.all_tool_dict.keys()):
                try:
                    result = tu._get_tool_instance(tool_name)
                    if result is not None:
                        successful_tool = tool_name
                        break
                except Exception:
                    continue
            
            # If we found a successful tool, test caching
            if successful_tool:
                # Should be cached
                assert successful_tool in tu.callable_functions
                
                # Second call should return cached instance
                result2 = tu._get_tool_instance(successful_tool)
                assert tu.callable_functions[successful_tool] is result2
            else:
                # If no tools can be initialized, that's also a valid test result
                pytest.skip("No tools could be successfully initialized")
        finally:
            if 'tu' in locals():
                tu.close()

    def test_error_registry_persistence(self):
        """Test that error registry persists across multiple operations."""
        # Mark multiple tools as unavailable
        mark_tool_unavailable("Tool1", ImportError('No module named "torch"'))
        mark_tool_unavailable("Tool2", ImportError('No module named "admet_ai"'))
        
        try:
            # Create new ToolUniverse instance
            tu = ToolUniverse()
            
            # Errors should still be there
            errors = get_tool_errors()
            assert len(errors) == 2
            assert "Tool1" in errors
            assert "Tool2" in errors
        finally:
            tu.close()

    def test_doctor_cli_import(self):
        """Test that doctor CLI can be imported."""
        from tooluniverse.doctor import main
        assert callable(main)

    @patch('tooluniverse.ToolUniverse')
    def test_doctor_cli_with_failures(self, mock_tu_class):
        """Test doctor CLI with simulated failures."""
        from tooluniverse.doctor import main
        
        # Mock ToolUniverse instance
        mock_tu = MagicMock()
        mock_tu.get_tool_health.return_value = {
            "total": 100,
            "available": 95,
            "unavailable": 5,
            "unavailable_list": ["Tool1", "Tool2"],
            "details": {
                "Tool1": {
                    "error": "No module named 'torch'",
                    "missing_package": "torch"
                },
                "Tool2": {
                    "error": "No module named 'admet_ai'",
                    "missing_package": "admet_ai"
                }
            }
        }
        mock_tu_class.return_value = mock_tu
        
        # Should return 0 (success)
        result = main()
        assert result == 0
        
        # Should have called load_tools and get_tool_health
        mock_tu.load_tools.assert_called_once()
        mock_tu.get_tool_health.assert_called_once()

    @patch('tooluniverse.ToolUniverse')
    def test_doctor_cli_all_tools_working(self, mock_tu_class):
        """Test doctor CLI when all tools are working."""
        from tooluniverse.doctor import main
        
        # Mock ToolUniverse instance
        mock_tu = MagicMock()
        mock_tu.get_tool_health.return_value = {
            "total": 100,
            "available": 100,
            "unavailable": 0,
            "unavailable_list": [],
            "details": {}
        }
        mock_tu_class.return_value = mock_tu
        
        # Should return 0 (success)
        result = main()
        assert result == 0

    @patch('tooluniverse.ToolUniverse')
    def test_doctor_cli_initialization_failure(self, mock_tu_class):
        """Test doctor CLI when ToolUniverse initialization fails."""
        from tooluniverse.doctor import main
        
        # Mock ToolUniverse to raise exception
        mock_tu_class.side_effect = Exception("Initialization failed")
        
        # Should return 1 (failure)
        result = main()
        assert result == 1
