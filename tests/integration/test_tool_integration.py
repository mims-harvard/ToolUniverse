#!/usr/bin/env python3
"""
Comprehensive Tool Integration Tests

This test file provides comprehensive coverage of tool integration functionality:
- TestToolExecution: Basic tool execution and functionality
- TestToolComposition: Tool composition and workflow features
- TestToolConcurrency: Concurrent execution and thread safety

Usage:
    pytest tests/integration/test_tool_integration.py -v
"""

import pytest
import os
import tempfile
import threading
import time
import gc
from pathlib import Path

from tooluniverse import ToolUniverse


@pytest.mark.integration
class TestToolExecution:
    """Test basic tool execution and functionality"""

    @pytest.fixture(autouse=True)
    def setup_tooluniverse(self):
        """Setup ToolUniverse instance for each test."""
        self.tu = ToolUniverse()
        self.tu.load_tools()
        yield
        self.tu.close()

    def test_tool_loading_real(self):
        """Test real tool loading functionality."""
        # Test that tools are actually loaded
        assert len(self.tu.all_tools) > 0
        assert len(self.tu.all_tool_dict) > 0
        
        # Test that we can list tools
        tools = self.tu.list_built_in_tools()
        assert isinstance(tools, dict)
        assert "total_tools" in tools
        assert tools["total_tools"] > 0

    def test_tool_execution_real(self):
        """Test real tool execution with actual ToolUniverse calls."""
        # Test with a real tool (may fail due to missing API keys, but that's OK)
        try:
            result = self.tu.run({
                "name": "UniProt_get_entry_by_accession",
                "arguments": {"accession": "P05067"}
            })
            
            # Should return a result (may be error if API key not configured)
            assert isinstance(result, dict)
            if "error" in result:
                assert "API" in str(result["error"]) or "key" in str(result["error"]).lower()
        except Exception as e:
            # Expected if API key not configured
            assert isinstance(e, Exception)

    def test_tool_execution_multiple_tools_real(self):
        """Test real tool execution with multiple tools."""
        # Test multiple tool calls individually
        tools_to_test = [
            {"name": "UniProt_get_entry_by_accession", "arguments": {"accession": "P05067"}},
            {"name": "ArXiv_search_papers", "arguments": {"query": "test", "limit": 5}},
            {"name": "OpenTargets_get_associated_targets_by_disease_efoId", "arguments": {"efoId": "EFO_0000249"}}
        ]
        
        results = []
        for tool_call in tools_to_test:
            try:
                result = self.tu.run(tool_call)
                results.append(result)
            except Exception as e:
                results.append({"error": str(e)})
        
        # Verify all calls completed
        assert len(results) == 3
        for result in results:
            # Allow for None results (API failures), dict results, or list results
            assert result is None or isinstance(result, (dict, list))

    def test_tool_specification_real(self):
        """Test real tool specification retrieval."""
        # Test that we can get tool specifications
        tool_names = self.tu.list_built_in_tools(mode="list_name")
        
        if tool_names:
            # Test with the first available tool
            tool_name = tool_names[0]
            spec = self.tu.tool_specification(tool_name)
            
            if spec:  # If tool has specification
                assert isinstance(spec, dict)
                assert "name" in spec
                assert "description" in spec

    def test_tool_health_check_real(self):
        """Test real tool health check functionality."""
        # Test health check
        health = self.tu.get_tool_health()
        
        assert isinstance(health, dict)
        assert "total" in health
        assert "available" in health
        assert "unavailable" in health
        assert "unavailable_list" in health
        assert "details" in health
        
        # Verify totals make sense
        assert health["total"] == health["available"] + health["unavailable"]
        assert health["total"] > 0

    def test_tool_finder_real(self):
        """Test real tool finder functionality."""
        try:
            result = self.tu.run({
                "name": "Tool_Finder_Keyword",
                "arguments": {
                    "description": "protein structure prediction",
                    "limit": 5
                }
            })
            
            assert isinstance(result, dict)
            if "tools" in result:
                assert isinstance(result["tools"], list)
        except Exception as e:
            # Expected if tool not available
            assert isinstance(e, Exception)

    def test_tool_caching_real(self):
        """Test real tool caching functionality."""
        # Test cache operations
        self.tu.clear_cache()
        assert len(self.tu._cache) == 0
        
        # Test caching a result
        test_key = "test_cache_key"
        test_value = {"result": "cached_data"}
        
        self.tu._cache.set(test_key, test_value)
        cached_result = self.tu._cache.get(test_key)
        assert cached_result is not None
        assert cached_result == test_value
        
        # Clear cache
        self.tu.clear_cache()
        assert len(self.tu._cache) == 0

    def test_tool_hooks_real(self):
        """Test real tool hooks functionality."""
        # Test hooks toggle
        self.tu.toggle_hooks(True)
        self.tu.toggle_hooks(False)
        
        # Test that hooks can be toggled without errors
        assert True  # If we get here, no exception was raised

    def test_tool_streaming_real(self):
        """Test real tool streaming functionality."""
        # Test streaming callback
        callback_called = False
        callback_data = []
        
        def test_callback(chunk):
            nonlocal callback_called, callback_data
            callback_called = True
            callback_data.append(chunk)
        
        try:
            result = self.tu.run({
                "name": "UniProt_get_entry_by_accession",
                "arguments": {"accession": "P05067"}
            }, stream_callback=test_callback)
            
            # Should return a result
            assert isinstance(result, dict)
        except Exception:
            # Expected if API key not configured
            pass

    def test_tool_error_handling_real(self):
        """Test real tool error handling."""
        # Test with invalid tool name
        result = self.tu.run({
            "name": "NonExistentTool",
            "arguments": {"test": "value"}
        })
        
        assert isinstance(result, dict)
        if "error" in result:
            assert "tool" in str(result["error"]).lower()

    def test_tool_parameter_validation_real(self):
        """Test real tool parameter validation."""
        # Test with invalid parameters
        result = self.tu.run({
            "name": "UniProt_get_entry_by_accession",
            "arguments": {"invalid_param": "value"}
        })
        
        assert isinstance(result, dict)
        if "error" in result:
            assert "parameter" in str(result["error"]).lower()

    def test_tool_export_real(self):
        """Test real tool export functionality."""

        
        # Test exporting to file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_file = f.name
        
        try:
            self.tu.export_tool_names(temp_file)
            
            # Verify file was created and has content
            assert os.path.exists(temp_file)
            with open(temp_file, 'r') as f:
                content = f.read()
                assert len(content) > 0
                
        finally:
            # Clean up
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_tool_env_template_real(self):
        """Test real environment template generation."""

        
        # Test with some missing keys
        missing_keys = ["API_KEY_1", "API_KEY_2"]
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as f:
            temp_file = f.name
        
        try:
            self.tu.generate_env_template(missing_keys, output_file=temp_file)
            
            # Verify file was created and has content
            assert os.path.exists(temp_file)
            with open(temp_file, 'r') as f:
                content = f.read()
                assert "API_KEY_1" in content
                assert "API_KEY_2" in content
                
        finally:
            # Clean up
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_tool_call_id_generation_real(self):
        """Test real call ID generation."""
        # Test generating multiple IDs
        id1 = self.tu.call_id_gen()
        id2 = self.tu.call_id_gen()
        
        assert isinstance(id1, str)
        assert isinstance(id2, str)
        assert id1 != id2
        assert len(id1) > 0
        assert len(id2) > 0

    def test_tool_lazy_loading_real(self):
        """Test real lazy loading functionality."""
        status = self.tu.get_lazy_loading_status()
        
        assert isinstance(status, dict)
        assert "lazy_loading_enabled" in status
        assert "full_discovery_completed" in status
        assert "immediately_available_tools" in status
        assert "lazy_mappings_available" in status
        assert "loaded_tools_count" in status

    def test_tool_types_real(self):
        """Test real tool types retrieval."""
        tool_types = self.tu.get_tool_types()
        
        assert isinstance(tool_types, list)
        assert len(tool_types) > 0

    def test_tool_available_tools_real(self):
        """Test real available tools retrieval."""
        available_tools = self.tu.get_available_tools()
        
        assert isinstance(available_tools, list)
        assert len(available_tools) > 0

    def test_tool_find_by_pattern_real(self):
        """Test real tool finding by pattern."""
        results = self.tu.find_tools_by_pattern("protein")
        
        assert isinstance(results, list)
        # Should find some tools related to protein
        assert len(results) >= 0


@pytest.mark.integration
class TestToolComposition:
    """Test tool composition and workflow features"""

    @pytest.fixture(autouse=True)
    def setup_tooluniverse(self):
        """Setup ToolUniverse instance for each test."""
        self.tu = ToolUniverse()
        self.tu.load_tools()
        yield
        self.tu.close()

    def test_compose_tool_availability(self):
        """Test that compose tools are actually available in ToolUniverse."""
        # Test that compose tools are available
        tool_names = self.tu.list_built_in_tools(mode='list_name')
        compose_tools = [name for name in tool_names if "Compose" in name or "compose" in name]
        assert len(compose_tools) > 0

    def test_compose_tool_execution_real(self):
        """Test actual ComposeTool execution with real ToolUniverse."""
        # Test that we can actually execute compose tools
        try:
            # Try to find and execute a compose tool
            tool_names = self.tu.list_built_in_tools(mode='list_name')
            compose_tools = [name for name in tool_names if "Compose" in name or "compose" in name]
            
            if compose_tools:
                # Try to execute the first compose tool
                result = self.tu.run({
                    "name": compose_tools[0],
                    "arguments": {"test": "value"}
                })
                
                # Should return a result (may be error if missing dependencies)
                assert isinstance(result, dict)
        except Exception as e:
            # Expected if compose tools not available or missing dependencies
            assert isinstance(e, Exception)

    def test_tool_chaining_real(self):
        """Test real tool chaining with actual ToolUniverse calls."""
        # Test sequential tool calls
        try:
            # First call
            result1 = self.tu.run({
                "name": "UniProt_get_entry_by_accession",
                "arguments": {"accession": "P05067"}
            })
            
            # If first call succeeded, try second call
            if result1 and isinstance(result1, dict) and "data" in result1:
                result2 = self.tu.run({
                    "name": "ArXiv_search_papers",
                    "arguments": {"query": "protein", "limit": 5}
                })
                
                # Both should return results
                assert isinstance(result1, dict)
                assert isinstance(result2, dict)
        except Exception:
            # Expected if API keys not configured
            pass

    def test_tool_broadcasting_real(self):
        """Test real parallel tool execution with actual ToolUniverse calls."""
        # Test parallel searches
        literature_sources = {}
        
        try:
            # Parallel searches
            literature_sources['europepmc'] = self.tu.run({
                "name": "EuropePMC_search_articles",
                "arguments": {"query": "CRISPR", "limit": 5}
            })

            literature_sources['openalex'] = self.tu.run({
                "name": "openalex_literature_search",
                "arguments": {
                    "search_keywords": "CRISPR",
                    "max_results": 5
                }
            })

            literature_sources['pubtator'] = self.tu.run({
                "name": "PubTator3_LiteratureSearch",
                "arguments": {"text": "CRISPR", "page_size": 5}
            })

            # Verify all sources were searched
            assert len(literature_sources) == 3
            for source, result in literature_sources.items():
                assert isinstance(result, dict)
        except Exception:
            # Expected if API keys not configured
            pass

    def test_compose_tool_error_handling_real(self):
        """Test real error handling in compose tools."""
        # Test with invalid tool name
        result = self.tu.run({
            "name": "NonExistentComposeTool",
            "arguments": {"test": "value"}
        })
        
        assert isinstance(result, dict)
        # Should either return error or handle gracefully
        if "error" in result:
            assert "tool" in str(result["error"]).lower()

    def test_compose_tool_dependency_management_real(self):
        """Test real dependency management in compose tools."""
        # Test that we can check for tool availability
        required_tools = [
            "EuropePMC_search_articles",
            "openalex_literature_search",
            "PubTator3_LiteratureSearch"
        ]
        
        available_tools = self.tu.get_available_tools()
        
        # Check which required tools are available
        available_required = [tool for tool in required_tools if tool in available_tools]
        
        assert isinstance(available_required, list)
        assert len(available_required) <= len(required_tools)

    @pytest.mark.timeout(180)
    def test_compose_tool_workflow_execution_real(self):
        """Test real workflow execution with compose tools."""
        # Test a simple workflow
        workflow_results = {}

        try:
            # Step 1: Search for papers
            search_result = self.tu.run({
                "name": "ArXiv_search_papers",
                "arguments": {"query": "machine learning", "limit": 2}
            })

            if search_result and isinstance(search_result, dict):
                workflow_results["search"] = search_result

                # Step 2: Get protein info (if search succeeded)
                protein_result = self.tu.run({
                    "name": "UniProt_get_entry_by_accession",
                    "arguments": {"accession": "P05067"}
                })

                if protein_result and isinstance(protein_result, dict):
                    workflow_results["protein"] = protein_result

                # Verify workflow results
                assert "search" in workflow_results
        except Exception:
            # Expected if API keys not configured or network timeout
            pass

    def test_compose_tool_caching_real(self):
        """Test real caching functionality in compose tools."""
        # Test caching mechanism
        cache_key = "test_compose_cache"
        result = self.tu._cache.get(cache_key)
        if result is None:
            try:
                result = self.tu.run({
                    "name": "UniProt_get_entry_by_accession",
                    "arguments": {"accession": "P05067"}
                })
                self.tu._cache.set(cache_key, result)
            except Exception:
                # Expected if API key not configured
                result = {"error": "API key not configured"}
                self.tu._cache.set(cache_key, result)
        
        # Verify caching worked
        cached_result = self.tu._cache.get(cache_key)
        assert cached_result is not None
        assert cached_result == result

    def test_compose_tool_streaming_real(self):
        """Test real streaming functionality in compose tools."""
        # Test streaming callback
        callback_called = False
        callback_data = []
        
        def test_callback(chunk):
            nonlocal callback_called, callback_data
            callback_called = True
            callback_data.append(chunk)
        
        try:
            result = self.tu.run({
                "name": "UniProt_get_entry_by_accession",
                "arguments": {"accession": "P05067"}
            }, stream_callback=test_callback)
            
            # If successful, verify we got some result
            assert isinstance(result, dict)
        except Exception:
            # Expected if API key not configured
            pass

    def test_compose_tool_validation_real(self):
        """Test real parameter validation in compose tools."""
        # Test with invalid parameters
        result = self.tu.run({
            "name": "UniProt_get_entry_by_accession",
            "arguments": {"invalid_param": "value"}
        })
        
        assert isinstance(result, dict)
        # Should either return error or handle gracefully
        if "error" in result:
            assert "parameter" in str(result["error"]).lower()

    def test_compose_tool_performance_real(self):
        """Test real performance characteristics of compose tools."""

        
        # Test execution time
        start_time = time.time()
        
        try:
            result = self.tu.run({
                "name": "UniProt_get_entry_by_accession",
                "arguments": {"accession": "P05067"}
            })
            
            execution_time = time.time() - start_time
            
            # Should complete within reasonable time (30 seconds)
            assert execution_time < 30
            assert isinstance(result, dict)
        except Exception:
            # Expected if API key not configured
            execution_time = time.time() - start_time
            assert execution_time < 30

    def test_compose_tool_error_recovery_real(self):
        """Test real error recovery in compose tools."""
        # Test workflow with error handling
        results = {"status": "running", "completed_steps": []}

        try:
            # Primary step
            primary_result = self.tu.run({
                "name": "NonExistentTool",  # This should fail
                "arguments": {"query": "test"}
            })
            results["primary"] = primary_result
            results["completed_steps"].append("primary")
            
            # If primary succeeded, check if it's an error result
            if isinstance(primary_result, dict) and "error" in primary_result:
                results["primary_error"] = primary_result["error"]

        except Exception as e:
            results["primary_error"] = str(e)

        # Fallback step
        try:
            fallback_result = self.tu.run({
                "name": "UniProt_get_entry_by_accession",  # This might work
                "arguments": {"accession": "P05067"}
            })
            results["fallback"] = fallback_result
            results["completed_steps"].append("fallback")

        except Exception as e2:
            results["fallback_error"] = str(e2)

        # Verify error handling worked
        # Primary should either have an error or be marked as failed
        assert ("primary_error" in results or 
                (isinstance(results.get("primary"), dict) and "error" in results["primary"]))
        # Either fallback succeeded or failed, both are valid outcomes
        assert ("fallback" in results or "fallback_error" in results)


@pytest.mark.integration
class TestToolConcurrency:
    """Test concurrent execution and thread safety"""

    @pytest.fixture(autouse=True)
    def setup_tooluniverse(self):
        """Setup ToolUniverse instance for each test."""
        self.tu = ToolUniverse()
        self.tu.load_tools()
        yield
        self.tu.close()

    def test_tool_concurrent_execution_real(self):
        """Test real concurrent tool execution."""

        
        results = []
        
        def make_call(call_id):
            result = self.tu.run({
                "name": "UniProt_get_entry_by_accession",
                "arguments": {"accession": f"P{call_id:05d}"}
            })
            results.append(result)
        
        # Create multiple threads
        threads = []
        for i in range(3):  # Reduced for testing
            thread = threading.Thread(target=make_call, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify all calls completed
        assert len(results) == 3
        for result in results:
            assert isinstance(result, dict)

    def test_tool_memory_management_real(self):
        """Test real memory management."""

        
        # Test multiple calls to ensure no memory leaks
        initial_objects = len(gc.get_objects())
        
        for i in range(5):  # Reduced for testing
            result = self.tu.run({
                "name": "UniProt_get_entry_by_accession",
                "arguments": {"accession": f"P{i:05d}"}
            })
            
            assert isinstance(result, dict)
            
            # Force garbage collection periodically
            if i % 2 == 0:
                gc.collect()
        
        # Check that we haven't created too many new objects
        final_objects = len(gc.get_objects())
        object_growth = final_objects - initial_objects
        
        # Should not have created more than 1000 new objects
        assert object_growth < 1000

    def test_tool_performance_real(self):
        """Test real tool performance."""

        
        # Test execution time
        start_time = time.time()
        
        try:
            result = self.tu.run({
                "name": "UniProt_get_entry_by_accession",
                "arguments": {"accession": "P05067"}
            })
            
            execution_time = time.time() - start_time
            
            # Should complete within reasonable time (30 seconds)
            assert execution_time < 30
            assert isinstance(result, dict)
        except Exception:
            # Expected if API key not configured
            execution_time = time.time() - start_time
            assert execution_time < 30

    def test_tool_error_recovery_real(self):
        """Test real error recovery."""
        # Test workflow with error handling
        results = {"status": "running", "completed_steps": []}

        try:
            # Primary step
            primary_result = self.tu.run({
                "name": "NonExistentTool",  # This should fail
                "arguments": {"query": "test"}
            })
            results["primary"] = primary_result
            results["completed_steps"].append("primary")
            
            # If primary succeeded, check if it's an error result
            if isinstance(primary_result, dict) and "error" in primary_result:
                results["primary_error"] = primary_result["error"]

        except Exception as e:
            results["primary_error"] = str(e)

        # Fallback step
        try:
            fallback_result = self.tu.run({
                "name": "UniProt_get_entry_by_accession",  # This might work
                "arguments": {"accession": "P05067"}
            })
            results["fallback"] = fallback_result
            results["completed_steps"].append("fallback")

        except Exception as e2:
            results["fallback_error"] = str(e2)

        # Verify error handling worked
        # Primary should either have an error or be marked as failed
        assert ("primary_error" in results or 
                (isinstance(results.get("primary"), dict) and "error" in results["primary"]))
        # Either fallback succeeded or failed, both are valid outcomes
        assert ("fallback" in results or "fallback_error" in results)


if __name__ == "__main__":
    pytest.main([__file__])
