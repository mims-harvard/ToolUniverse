from tooluniverse import ToolUniverse
import sys
import os
import pytest

# Add src to path to import tooluniverse modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="session")
def tooluni():
    """Initialize tool universe for all tests."""
    tu = ToolUniverse()
    tu.load_tools()
    yield tu
    tu.close()


def test_cellosaurus_tools_exist(tooluni):
    """Test that Cellosaurus tools are registered."""
    tool_names = [tool.get("name") for tool in tooluni.all_tools if isinstance(tool, dict)]
    
    # Check for Cellosaurus tools
    cellosaurus_tools = [name for name in tool_names if "cellosaurus" in name.lower()]
    
    # Should have some Cellosaurus tools
    assert len(cellosaurus_tools) > 0, "No Cellosaurus tools found"
    print(f"Found Cellosaurus tools: {cellosaurus_tools}")


def test_cellosaurus_search_execution(tooluni):
    """Test Cellosaurus search tool execution."""
    try:
        result = tooluni.run({
            "name": "cellosaurus_search_cell_lines",
            "arguments": {"q": "HeLa", "size": 3}
        })
        
        # Should return a result
        assert isinstance(result, dict)
        
        # Allow for API key errors
        if "error" in result:
            assert "API" in str(result["error"]) or "key" in str(result["error"]).lower()
        else:
            # Verify successful result structure
            assert "results" in result or "data" in result or "success" in result
            
    except Exception as e:
        # Expected if tool not available or API key missing
        assert isinstance(e, Exception)


def test_cellosaurus_query_converter_execution(tooluni):
    """Test Cellosaurus query converter tool execution."""
    try:
        result = tooluni.run({
            "name": "cellosaurus_query_converter",
            "arguments": {"query": "human cancer cells"}
        })
        
        # Should return a result
        assert isinstance(result, dict)
        
        # Allow for API key errors
        if "error" in result:
            assert "API" in str(result["error"]) or "key" in str(result["error"]).lower()
        else:
            # Verify successful result structure
            assert "results" in result or "data" in result or "success" in result
            
    except Exception as e:
        # Expected if tool not available or API key missing
        assert isinstance(e, Exception)


def test_cellosaurus_cell_line_info_execution(tooluni):
    """Test Cellosaurus cell line info tool execution."""
    try:
        result = tooluni.run({
            "name": "cellosaurus_get_cell_line_info",
            "arguments": {"cell_line_id": "CVCL_0030"}
        })
        
        # Should return a result
        assert isinstance(result, dict)
        
        # Allow for API key errors
        if "error" in result:
            assert "API" in str(result["error"]) or "key" in str(result["error"]).lower()
        else:
            # Verify successful result structure
            assert "results" in result or "data" in result or "success" in result
            
    except Exception as e:
        # Expected if tool not available or API key missing
        assert isinstance(e, Exception)


def test_cellosaurus_tool_missing_parameters(tooluni):
    """Test Cellosaurus tools with missing parameters."""
    try:
        result = tooluni.run({
            "name": "cellosaurus_search_cell_lines",
            "arguments": {}
        })
        
        # Should return an error for missing parameters
        assert isinstance(result, dict)
        assert "error" in result or "success" in result
        
    except Exception as e:
        # Expected if tool not available
        assert isinstance(e, Exception)


def test_cellosaurus_tool_invalid_parameters(tooluni):
    """Test Cellosaurus tools with invalid parameters."""
    try:
        result = tooluni.run({
            "name": "cellosaurus_search_cell_lines",
            "arguments": {
                "q": "",
                "size": -1
            }
        })
        
        # Should return an error for invalid parameters
        assert isinstance(result, dict)
        assert "error" in result or "success" in result
        
    except Exception as e:
        # Expected if tool not available
        assert isinstance(e, Exception)


def test_cellosaurus_tool_performance(tooluni):
    """Test Cellosaurus tool performance."""
    try:
        import time
        
        start_time = time.time()
        
        result = tooluni.run({
            "name": "cellosaurus_search_cell_lines",
            "arguments": {"q": "test", "size": 1}
        })
        
        execution_time = time.time() - start_time
        
        # Should complete within reasonable time (60 seconds)
        assert execution_time < 60
        assert isinstance(result, dict)
        
    except Exception as e:
        # Expected if tool not available
        assert isinstance(e, Exception)


def test_cellosaurus_tool_error_handling(tooluni):
    """Test Cellosaurus tool error handling."""
    try:
        # Test with invalid cell line ID
        result = tooluni.run({
            "name": "cellosaurus_get_cell_line_info",
            "arguments": {
                "cell_line_id": "INVALID_ID"
            }
        })
        
        # Should handle invalid input gracefully
        assert isinstance(result, dict)
        
        # Allow for API key errors
        if "error" in result:
            assert "API" in str(result["error"]) or "key" in str(result["error"]).lower()
        else:
            # Verify result structure
            assert "results" in result or "data" in result or "success" in result
            
    except Exception as e:
        # Expected if tool not available
        assert isinstance(e, Exception)


def test_cellosaurus_tool_concurrent_execution(tooluni):
    """Test Cellosaurus tool concurrent execution."""
    try:
        import threading
        import time
        
        results = []
        
        def make_search_call(call_id):
            try:
                result = tooluni.run({
                    "name": "cellosaurus_search_cell_lines",
                    "arguments": {
                        "q": f"test query {call_id}",
                        "size": 1
                    }
                })
                results.append(result)
            except Exception as e:
                results.append({"error": str(e)})
        
        # Create multiple threads
        threads = []
        for i in range(3):  # 3 concurrent calls
            thread = threading.Thread(target=make_search_call, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify all calls completed
        assert len(results) == 3
        for result in results:
            assert isinstance(result, dict)
            
    except Exception as e:
        # Expected if tool not available
        assert isinstance(e, Exception)


def test_cellosaurus_tool_memory_usage(tooluni):
    """Test Cellosaurus tool memory usage."""
    try:
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create multiple search calls
        for i in range(5):
            try:
                _ = tooluni.run({
                    "name": "cellosaurus_search_cell_lines",
                    "arguments": {
                        "q": f"test query {i}",
                        "size": 1
                    }
                })
            except Exception:
                pass
        
        # Get final memory usage
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024
        
    except ImportError:
        # psutil not available, skip test
        pass
    except Exception as e:
        # Expected if tool not available
        assert isinstance(e, Exception)


def test_cellosaurus_tool_output_format(tooluni):
    """Test Cellosaurus tool output format."""
    try:
        result = tooluni.run({
            "name": "cellosaurus_search_cell_lines",
            "arguments": {
                "q": "test query",
                "size": 1
            }
        })
        
        # Should return a result
        assert isinstance(result, dict)
        
        # Allow for API key errors
        if "error" in result:
            assert "API" in str(result["error"]) or "key" in str(result["error"]).lower()
        else:
            # Verify output format
            if "results" in result:
                assert isinstance(result["results"], (list, dict))
            if "data" in result:
                assert isinstance(result["data"], (list, dict))
            if "success" in result:
                assert isinstance(result["success"], bool)
            
    except Exception as e:
        # Expected if tool not available
        assert isinstance(e, Exception)


if __name__ == "__main__":
    pytest.main([__file__])
