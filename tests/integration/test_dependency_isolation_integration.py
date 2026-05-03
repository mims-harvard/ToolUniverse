"""Integration tests for dependency isolation functionality."""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse import ToolUniverse
from tooluniverse.tool_registry import get_tool_errors, mark_tool_unavailable


class TestDependencyIsolationIntegration:
    """Integration tests for dependency isolation with real tool loading."""

    def setup_method(self):
        """Clear error registry before each test."""
        from tooluniverse.tool_registry import _TOOL_ERRORS
        _TOOL_ERRORS.clear()

    def test_real_tool_loading_with_isolation(self):
        """Test that real tools load with isolation system active."""
        tu = ToolUniverse()
        try:
            tu.load_tools()
            
            # Should have loaded tools
            assert len(tu.all_tool_dict) > 0
            
            # Health check should work
            health = tu.get_tool_health()
            assert health["total"] > 0
            assert health["available"] >= 0
            assert health["unavailable"] >= 0
        finally:
            tu.close()

    def test_tool_execution_with_isolation(self):
        """Test that tool execution works with isolation system."""
        tu = ToolUniverse()
        try:
            tu.load_tools()
            
            # Try to execute a tool
            tool_name = list(tu.all_tool_dict.keys())[0]
            
            # Should not crash even if tool has issues
            try:
                result = tu.run_one_function({
                    "name": tool_name,
                    "arguments": {}
                })
                # Result might be None or actual result, both are OK
                assert result is None or isinstance(result, (dict, str))
            except Exception as e:
                # If it fails, it should be a controlled failure, not a crash
                assert "ImportError" not in str(e) or "No module named" not in str(e)
        finally:
            tu.close()

    def test_simulated_dependency_failure_integration(self):
        """Test integration with simulated dependency failures."""
        tu = ToolUniverse()
        try:
            tu.load_tools()
            
            # Simulate some tool failures
            mark_tool_unavailable("SimulatedTool1", ImportError('No module named "torch"'))
            mark_tool_unavailable("SimulatedTool2", ImportError('No module named "admet_ai"'))
            
            # Health check should reflect the failures
            health = tu.get_tool_health()
            assert health["unavailable"] >= 2
            assert "SimulatedTool1" in health["unavailable_list"]
            assert "SimulatedTool2" in health["unavailable_list"]
            
            # Details should contain error information
            details = health["details"]
            assert "SimulatedTool1" in details
            assert "SimulatedTool2" in details
            assert details["SimulatedTool1"]["missing_package"] == "torch"
            assert details["SimulatedTool2"]["missing_package"] == "admet_ai"
        finally:
            tu.close()

    def test_tool_instance_creation_with_failures(self):
        """Test tool instance creation when some tools have failures."""
        tu = ToolUniverse()
        try:
            tu.load_tools()
            
            # Mark a tool as unavailable
            mark_tool_unavailable("BrokenTool", ImportError('No module named "test"'))
            
            # Add it to tool dict to simulate it being in config
            tu.all_tool_dict["BrokenTool"] = {
                "type": "BrokenTool",
                "name": "BrokenTool",
                "description": "A broken tool"
            }
            
            # Should return None without crashing
            result = tu._get_tool_instance("BrokenTool")
            assert result is None
            
            # Should not be in callable_functions
            assert "BrokenTool" not in tu.callable_functions
        finally:
            tu.close()

    def test_mixed_success_and_failure_scenario(self):
        """Test scenario with both successful and failed tools."""
        tu = ToolUniverse()
        try:
            tu.load_tools()
            
            # Mark some tools as failed
            mark_tool_unavailable("FailedTool1", ImportError('No module named "torch"'))
            mark_tool_unavailable("FailedTool2", ImportError('No module named "admet_ai"'))
            
            # Get a working tool
            working_tools = [name for name in tu.all_tool_dict.keys() 
                            if name not in ["FailedTool1", "FailedTool2"]]
            
            if working_tools:
                working_tool = working_tools[0]
                
                # Should be able to create instance
                result = tu._get_tool_instance(working_tool)
                # Result might be None (if tool has other issues) or actual instance
                assert result is None or hasattr(result, 'run')
                
                # Should be cached if successful
                if result is not None:
                    assert working_tool in tu.callable_functions
        finally:
            tu.close()

    def test_doctor_cli_integration(self):
        """Test doctor CLI with real ToolUniverse."""
        from tooluniverse.doctor import main
        
        # Should run without crashing
        result = main()
        assert result == 0

    def test_error_recovery_after_fix(self):
        """Test that system can recover after fixing dependencies."""
        tu = ToolUniverse()
        try:
            tu.load_tools()
            
            # Simulate a tool failure
            mark_tool_unavailable("RecoverableTool", ImportError('No module named "test"'))
            
            # Health should show failure
            health = tu.get_tool_health()
            assert "RecoverableTool" in health["unavailable_list"]
            
            # Clear the error (simulating fix)
            from tooluniverse.tool_registry import _TOOL_ERRORS
            _TOOL_ERRORS.clear()
            
            # Health should now show no failures
            health = tu.get_tool_health()
            assert "RecoverableTool" not in health["unavailable_list"]
        finally:
            tu.close()

    def test_lazy_loading_with_failures(self):
        """Test lazy loading behavior when tools have failures."""
        tu = ToolUniverse()
        try:
            tu.load_tools()
            
            # Mark a tool as failed
            mark_tool_unavailable("LazyFailedTool", ImportError('No module named "test"'))
            
            # Add to tool dict
            tu.all_tool_dict["LazyFailedTool"] = {
                "type": "LazyFailedTool",
                "name": "LazyFailedTool"
            }
            
            # Should not try to load the failed tool
            result = tu._get_tool_instance("LazyFailedTool")
            assert result is None
        finally:
            tu.close()

    def test_health_check_performance(self):
        """Test that health checks are performant."""
        import time
        
        tu = ToolUniverse()
        try:
            tu.load_tools()
            
            # Time the health check
            start_time = time.time()
            health = tu.get_tool_health()
            end_time = time.time()
            
            # Should be fast (less than 1 second)
            assert (end_time - start_time) < 1.0
            
            # Should return valid data
            assert isinstance(health, dict)
            assert "total" in health
            assert "available" in health
            assert "unavailable" in health
        finally:
            tu.close()

    @pytest.mark.skip(reason="Requires GPU and heavy ML model loading")
    def test_concurrent_tool_access_with_failures(self):
        """Test concurrent access to tools when some have failures."""
        import threading
        import time
        
        tu = ToolUniverse()
        try:
            tu.load_tools()
            
            # Mark some tools as failed
            mark_tool_unavailable("ConcurrentFailedTool", ImportError('No module named "test"'))
            
            results = []
            errors = []
            
            def access_tool(tool_name):
                try:
                    result = tu._get_tool_instance(tool_name)
                    results.append((tool_name, result))
                except Exception as e:
                    errors.append((tool_name, str(e)))
            
            # Get some tool names
            tool_names = list(tu.all_tool_dict.keys())[:5]
            tool_names.append("ConcurrentFailedTool")  # Add the failed one
            
            # Create threads
            threads = []
            for tool_name in tool_names:
                thread = threading.Thread(target=access_tool, args=(tool_name,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads
            for thread in threads:
                thread.join()
            
            # Should not have any errors (failures should be handled gracefully)
            assert len(errors) == 0
            
            # Should have results for all tools
            assert len(results) == len(tool_names)
            
            # Failed tool should have None result
            failed_results = [r for r in results if r[0] == "ConcurrentFailedTool"]
            assert len(failed_results) == 1
            assert failed_results[0][1] is None
        finally:
            tu.close()
